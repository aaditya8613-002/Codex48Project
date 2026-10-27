"""Review orchestrator: exact rules first, then claims, then grounded AI checks.

The rules and claim checks never need the AI. If Gemini is missing or fails, the
review still returns every exact finding plus an ai_error note.
"""
from datetime import date

from sqlalchemy.orm import Session

from .ai import gemini
from .ai.grounded_review import adjudicate_claims, review_with_passages
from .claims import ClaimResult, FactRef, check_claims, to_findings
from .config import settings
from .kb.retrieval import retrieve
from .models import ApprovalAudit, Fact, FindingRow, Organisation, Review, ReviewRevision, Term
from .rules import alt_text, contrast, palette, terms
from .types import Finding

MAX_CHARS = 20_000
AI_NOTICE = (
    "AI is used for tone and claim checks (Google Gemini via Google AI Studio). "
    "Only the content and the guideline passages retrieved for it are sent. "
    "Suggestions are never applied automatically."
)


def load_org_data(session: Session, org_id: int):
    org = session.get(Organisation, org_id)
    if org is None:
        raise LookupError(f"Organisation {org_id} not found")
    term_rules = [
        terms.TermRule(t.id, t.kind, t.phrase, t.preferred, t.reason, t.severity)
        for t in session.query(Term).filter(Term.org_id == org_id).all()
    ]
    facts = [
        FactRef(f.id, f.key, f.statement, f.value, f.unit, list(f.keywords or []), f.source, f.valid_from, f.valid_to)
        for f in session.query(Fact).filter(Fact.org_id == org_id).all()
    ]
    return org, term_rules, facts


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple] = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.rule_id, f.start, f.end, f.original)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _overlaps(a: Finding, b: Finding) -> bool:
    if None in (a.start, a.end, b.start, b.end):
        return False
    return a.start < b.end and b.start < a.end


def exact_review(
    text: str, org: Organisation, term_rules: list[terms.TermRule], facts: list[FactRef], today: date | None = None
) -> tuple[list[Finding], list[ClaimResult]]:
    findings: list[Finding] = []
    findings += terms.check_terms(text, term_rules)
    findings += terms.check_product_names(text, list(org.product_names or []))
    findings += alt_text.check_alt_text(text)
    findings += contrast.scan_html_inline_styles(text, list(org.palette or []))
    claim_results = check_claims(text, facts, today)
    return findings, claim_results


def run_review(
    session: Session,
    org_id: int,
    text: str,
    channel: str = "",
    use_ai: bool = True,
    user_id: int | None = None,
    persist: bool = True,
    today: date | None = None,
    title: str = "Untitled Draft",
    creator_name: str = "Maya (Content Creator)",
) -> dict:
    if not text or not text.strip():
        raise ValueError("Content is empty.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Content is too long ({len(text)} characters, limit {MAX_CHARS}).")

    org, term_rules, facts = load_org_data(session, org_id)
    findings, claim_results = exact_review(text, org, term_rules, facts, today)

    ai_used, ai_error = False, ""
    if use_ai:
        if not gemini.is_configured():
            ai_error = "AI checks skipped: GEMINI_API_KEY is not set."
        else:
            try:
                claim_results = adjudicate_claims(claim_results, facts)
                passages = retrieve(session, org_id, text, settings.retrieval_top_k)
                ai_findings = review_with_passages(text, channel, passages)
                exact_so_far = findings + to_findings(claim_results)
                # drop AI findings that repeat something an exact check already flagged
                findings += [a for a in ai_findings if not any(_overlaps(a, e) for e in exact_so_far)]
                ai_used = True
            except gemini.AIUnavailable as exc:
                ai_error = f"AI checks unavailable: {exc}"

    findings += to_findings(claim_results)
    findings = sorted(_dedupe(findings), key=lambda f: (f.start if f.start is not None else 10**9, f.rule_id))

    result = {
        "ai_used": ai_used,
        "ai_error": ai_error,
        "notice": AI_NOTICE if ai_used else "Exact rule checks only; no AI was used for this review.",
        "claims": [
            {
                "text": c.text,
                "verdict": c.verdict,
                "explanation": c.explanation,
                "fact_id": c.fact.id if c.fact else None,
                "start": c.start,
                "end": c.end,
            }
            for c in claim_results
        ],
        "findings": [f.to_dict() for f in findings],
    }

    if persist:
        review = Review(
            org_id=org_id,
            user_id=user_id,
            title=title or "Untitled Draft",
            channel=channel or "General",
            status="draft",
            creator_name=creator_name or "Maya (Content Creator)",
            assigned_reviewer="Jordan (Brand Manager)",
            content=text,
            version=1,
            ai_used=ai_used,
            ai_error=ai_error,
        )
        for f in findings:
            review.findings.append(
                FindingRow(
                    org_id=org_id, rule_id=f.rule_id, category=f.category, severity=f.severity, source=f.source,
                    verdict=f.verdict, message=f.message, original=f.original, suggestion=f.suggestion,
                    start=f.start, end=f.end, evidence=f.evidence,
                )
            )
        review.revisions.append(
            ReviewRevision(
                version_number=1,
                content=text,
                change_summary="Initial draft created",
                created_by=creator_name or "Maya (Content Creator)",
            )
        )
        review.audit_logs.append(
            ApprovalAudit(
                action="created",
                actor_name=creator_name or "Maya (Content Creator)",
                actor_role="creator",
                notes="Initial scan and review created",
            )
        )
        session.add(review)
        session.commit()
        result["review_id"] = review.id
        result["status"] = review.status
        result["title"] = review.title
        result["version"] = review.version
        for payload, row in zip(result["findings"], review.findings):
            payload["id"] = row.id
    return result


def review_image(
    session: Session, org_id: int, image_bytes: bytes, alt: str | None, persist: bool = True
) -> dict:
    org = session.get(Organisation, org_id)
    if org is None:
        raise LookupError(f"Organisation {org_id} not found")
    try:
        findings = palette.check_palette(image_bytes, list(org.palette or []))
    except Exception as exc:  # Pillow cannot read it
        raise ValueError(f"Could not read the image: {exc}") from exc
    findings += alt_text.check_alt_value(alt)

    result = {"findings": [f.to_dict() for f in findings], "ai_used": False}
    if persist:
        review = Review(org_id=org_id, channel="image upload", content=f"[image] alt={alt or ''}")
        for f in findings:
            review.findings.append(
                FindingRow(
                    org_id=org_id, rule_id=f.rule_id, category=f.category, severity=f.severity, source=f.source,
                    message=f.message, original=f.original, suggestion=f.suggestion, evidence=f.evidence,
                )
            )
        session.add(review)
        session.commit()
        result["review_id"] = review.id
        for payload, row in zip(result["findings"], review.findings):
            payload["id"] = row.id
    return result
