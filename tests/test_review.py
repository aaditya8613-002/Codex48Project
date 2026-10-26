from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.ai import gemini, grounded_review
from app.claims import ClaimResult
from app.kb.ingest import chunk_text
from app.kb.retrieval import Passage
from app.main import app
from app.db import get_session
from app.models import FindingRow
from app.review import run_review

TODAY = date(2026, 10, 25)


def test_review_without_ai_returns_exact_findings_and_says_so(session, org_id):
    out = run_review(session, org_id, "Used by over 5 million customers, guaranteed.", use_ai=False, today=TODAY)
    rules = {f["rule_id"] for f in out["findings"]}
    assert {"claim:customer_teams", "terminology:customers", "banned_phrase:guaranteed"} <= rules
    assert out["ai_used"] is False and "no AI" in out["notice"]
    assert all("id" in f for f in out["findings"]) and out["review_id"]


def test_missing_api_key_still_returns_rule_findings(session, org_id):
    out = run_review(session, org_id, "the tool is cheap", use_ai=True, today=TODAY)
    assert out["findings"] and out["ai_used"] is False and "GEMINI_API_KEY" in out["ai_error"]


def test_empty_and_oversized_content_rejected(session, org_id):
    with pytest.raises(ValueError):
        run_review(session, org_id, "   ")
    with pytest.raises(ValueError):
        run_review(session, org_id, "x" * 20_001)


def test_unknown_org(session):
    with pytest.raises(LookupError):
        run_review(session, 999, "hello")


# ---- grounding: fabricated model output must not survive ----
PASSAGE = Passage(7, "Northwind Brand Guidelines", "Voice and tone",
                  "Do not use exclamation marks in headlines or in more than one sentence of a post.", 0.8)


def test_ai_findings_are_validated(monkeypatch):
    text = "Big news!!! FlowDesk is here!"
    fake = {"findings": [
        {"quote": "Big news!!!", "issue": "Too many exclamation marks.", "passage_id": 7,
         "passage_quote": "Do not use exclamation marks in headlines", "severity": "low", "suggestion": "Big news."},
        {"quote": "text that is not in the content", "issue": "x", "passage_id": 7, "passage_quote": "x"},
        {"quote": "FlowDesk is here!", "issue": "made-up rule", "passage_id": 999, "passage_quote": "invented"},
        {"quote": "FlowDesk", "issue": "bad quote", "passage_id": 7, "passage_quote": "this is not in the passage",
         "severity": "high", "suggestion": ""},
    ]}
    monkeypatch.setattr(gemini, "generate_json", lambda system, prompt: fake)
    found = grounded_review.review_with_passages(text, "LinkedIn post", [PASSAGE])
    assert [f.original for f in found] == ["Big news!!!", "FlowDesk"]  # invented quote and invented source dropped
    assert found[0].evidence["quote_verified"] is True and found[0].start == 0
    assert found[1].evidence["quote_verified"] is False  # kept, but the shown quote is the real passage text
    assert found[1].evidence["quote"].startswith("Do not use exclamation")


def test_claim_adjudication_needs_a_real_fact_id(monkeypatch):
    from app.claims import FactRef

    facts = [FactRef(1, "k", "3 million teams.", 3e6, "", ["teams"], "Fact sheet")]
    unresolved = ClaimResult("a claim", "a claim sentence", 0, 7, "cannot_verify", "no fact")
    monkeypatch.setattr(gemini, "generate_json",
                        lambda s, p: {"verdict": "supported", "fact_id": 42, "explanation": "trust me"})
    [r] = grounded_review.adjudicate_claims([unresolved], facts)
    assert r.verdict == "cannot_verify" and r.fact is None  # fact id 42 does not exist

    unresolved = ClaimResult("a claim", "a claim sentence", 0, 7, "cannot_verify", "no fact")
    monkeypatch.setattr(gemini, "generate_json",
                        lambda s, p: {"verdict": "supported", "fact_id": 1, "explanation": "matches"})
    [r] = grounded_review.adjudicate_claims([unresolved], facts)
    assert r.verdict == "supported" and r.fact.id == 1 and r.resolved_by == "ai"


def test_ai_failure_falls_back_to_rules(session, org_id, monkeypatch):
    monkeypatch.setattr(gemini, "is_configured", lambda: True)

    def boom(*a, **k):
        raise gemini.AIUnavailable("quota exceeded")

    monkeypatch.setattr("app.review.retrieve", boom)
    out = run_review(session, org_id, "the tool is great", use_ai=True, today=TODAY)
    assert out["findings"] and not out["ai_used"] and "quota exceeded" in out["ai_error"]


# ---- chunking ----
def test_chunking_keeps_headings_and_size_limit():
    text = "# Voice\n\nShort rule one.\n\nShort rule two.\n\n# Social\n\n" + ("word " * 400)
    chunks = chunk_text(text)
    assert chunks[0][0] == "Voice" and "rule one" in chunks[0][1] and "rule two" in chunks[0][1]
    assert all(len(c) <= 900 for _, c in chunks) and chunks[-1][0] == "Social" and len(chunks) >= 3


# ---- HTTP API ----
@pytest.fixture()
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_review_decide_and_insights(client, session, org_id):
    r = client.post(f"/orgs/{org_id}/review/text", json={"text": "The tool is cheap.", "use_ai": False})
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert len(findings) >= 2

    first = findings[0]["id"]
    assert client.patch(f"/findings/{first}", json={"status": "dismissed"}).status_code == 422  # reason required
    ok = client.patch(f"/findings/{first}", json={"status": "dismissed", "reason": "Quoting a competitor"})
    assert ok.status_code == 200
    assert client.patch(f"/findings/{findings[1]['id']}", json={"status": "accepted"}).status_code == 200

    insights = client.get(f"/orgs/{org_id}/insights/rules").json()
    top = insights[0]
    assert top["dismissal_rate"] == 1.0 and top["rule_id"] == findings[0]["rule_id"]


def test_api_contrast_and_errors(client, org_id):
    ok = client.post(f"/orgs/{org_id}/review/contrast", json={"fg": "#000", "bg": "#fff"}).json()
    assert ok["passes"] and ok["ratio"] == 21.0
    bad = client.post(f"/orgs/{org_id}/review/contrast", json={"fg": "#cccccc", "bg": "#ffffff"}).json()
    assert not bad["passes"] and bad["finding"]["category"] == "contrast"
    assert client.post(f"/orgs/{org_id}/review/contrast", json={"fg": "nope", "bg": "#fff"}).status_code == 422
    assert client.post("/orgs/999/review/text", json={"text": "hi"}).status_code == 404
    assert client.post(f"/orgs/{org_id}/review/text", json={"text": ""}).status_code == 422


def test_api_upload_text_document_and_term_validation(client, org_id):
    up = client.post(f"/orgs/{org_id}/kb/documents", files={"file": ("rules.md", b"# Tone\n\nBe calm and clear.")})
    assert up.status_code == 200 and up.json()["passages"] == 1 and up.json()["embedded"] == 0  # no key: no vectors
    assert client.post(f"/orgs/{org_id}/kb/documents", files={"file": ("x.exe", b"MZ")}).status_code == 422
    assert client.post(f"/orgs/{org_id}/kb/terms", json={"kind": "oops", "phrase": "x"}).status_code == 422
    assert client.post(f"/orgs/{org_id}/kb/terms", json={"kind": "banned_phrase", "phrase": "synergy"}).status_code == 200


def test_api_image_review(client, org_id):
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (60, 60), (255, 0, 200)).save(buf, "PNG")
    r = client.post(f"/orgs/{org_id}/review/image", files={"image": ("a.png", buf.getvalue(), "image/png")},
                    data={"alt_text": ""})
    cats = {f["category"] for f in r.json()["findings"]}
    assert r.status_code == 200 and cats == {"palette", "alt_text"}
    assert client.post(f"/orgs/{org_id}/review/image", files={"image": ("a.png", b"not an image", "image/png")}).status_code == 422
