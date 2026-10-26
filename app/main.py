"""FastAPI routes for the knowledge base, reviews and finding decisions.

Login / JWT roles are handled by the workflow module; plug its dependency in
where marked. Until then org_id is taken from the URL.
"""
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from . import review as review_service
from .ai import gemini
from .db import get_session, init_db
from .kb import ingest
from .models import BrandDocument, Fact, FindingRow, Organisation, Term
from .rules import contrast

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BrandGuard API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.get("/health")
def health() -> dict:
    return {"ok": True, "ai_configured": gemini.is_configured()}


def _org_or_404(session: Session, org_id: int) -> Organisation:
    org = session.get(Organisation, org_id)
    if org is None:
        raise HTTPException(404, "Organisation not found")
    return org


# ---------- organisations ----------
class OrgIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    product_names: list[str] = []
    palette: list[str] = []


@app.post("/orgs")
def create_org(body: OrgIn, session: Session = Depends(get_session)) -> dict:
    org = Organisation(name=body.name, product_names=body.product_names, palette=body.palette)
    session.add(org)
    session.commit()
    return {"id": org.id}


# ---------- knowledge base ----------
@app.post("/orgs/{org_id}/kb/documents")
async def upload_document(
    org_id: int,
    file: UploadFile = File(...),
    title: str = Form(""),
    kind: str = Form("guideline"),
    session: Session = Depends(get_session),
) -> dict:
    _org_or_404(session, org_id)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 10 MB")
    try:
        text = ingest.extract_text(file.filename or "", data)
        doc = ingest.add_document(session, org_id, title or file.filename or "Untitled", text, file.filename or "", kind)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    embedded = sum(1 for c in doc.chunks if c.embedding is not None)
    return {"id": doc.id, "passages": len(doc.chunks), "embedded": embedded}


@app.get("/orgs/{org_id}/kb/documents")
def list_documents(org_id: int, session: Session = Depends(get_session)) -> list[dict]:
    _org_or_404(session, org_id)
    docs = session.query(BrandDocument).filter(BrandDocument.org_id == org_id).all()
    return [{"id": d.id, "title": d.title, "kind": d.kind, "passages": len(d.chunks)} for d in docs]


@app.post("/orgs/{org_id}/kb/reembed")
def reembed(org_id: int, session: Session = Depends(get_session)) -> dict:
    _org_or_404(session, org_id)
    try:
        return {"embedded": ingest.reembed_missing(session, org_id)}
    except gemini.AIUnavailable as exc:
        raise HTTPException(503, str(exc))


class FactIn(BaseModel):
    key: str
    statement: str
    value: float | None = None
    unit: str = ""
    keywords: list[str] = []
    source: str = ""
    valid_from: date | None = None
    valid_to: date | None = None


@app.post("/orgs/{org_id}/kb/facts")
def add_fact(org_id: int, body: FactIn, session: Session = Depends(get_session)) -> dict:
    _org_or_404(session, org_id)
    fact = Fact(org_id=org_id, **body.model_dump())
    session.add(fact)
    session.commit()
    return {"id": fact.id}


@app.get("/orgs/{org_id}/kb/facts")
def list_facts(org_id: int, session: Session = Depends(get_session)) -> list[dict]:
    _org_or_404(session, org_id)
    rows = session.query(Fact).filter(Fact.org_id == org_id).all()
    return [
        {"id": f.id, "key": f.key, "statement": f.statement, "value": f.value, "unit": f.unit,
         "keywords": f.keywords, "source": f.source, "valid_from": f.valid_from, "valid_to": f.valid_to}
        for f in rows
    ]


class TermIn(BaseModel):
    kind: str = Field(pattern="^(terminology|banned_phrase)$")
    phrase: str = Field(min_length=1, max_length=200)
    preferred: str | None = None
    reason: str = ""
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")


@app.post("/orgs/{org_id}/kb/terms")
def add_term(org_id: int, body: TermIn, session: Session = Depends(get_session)) -> dict:
    _org_or_404(session, org_id)
    term = Term(org_id=org_id, **body.model_dump())
    session.add(term)
    session.commit()
    return {"id": term.id}


@app.get("/orgs/{org_id}/kb/terms")
def list_terms(org_id: int, session: Session = Depends(get_session)) -> list[dict]:
    _org_or_404(session, org_id)
    rows = session.query(Term).filter(Term.org_id == org_id).all()
    return [{"id": t.id, "kind": t.kind, "phrase": t.phrase, "preferred": t.preferred,
             "reason": t.reason, "severity": t.severity} for t in rows]


# ---------- reviews ----------
class ReviewIn(BaseModel):
    text: str
    channel: str = ""
    use_ai: bool = True


@app.post("/orgs/{org_id}/review/text")
def review_text(org_id: int, body: ReviewIn, session: Session = Depends(get_session)) -> dict:
    try:
        return review_service.run_review(session, org_id, body.text, body.channel, body.use_ai)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/orgs/{org_id}/review/image")
async def review_image(
    org_id: int,
    image: UploadFile = File(...),
    alt_text: str = Form(""),
    session: Session = Depends(get_session),
) -> dict:
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image is larger than 10 MB")
    try:
        return review_service.review_image(session, org_id, data, alt_text)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


class ContrastIn(BaseModel):
    fg: str
    bg: str
    large_text: bool = False
    level: str = Field(default="AA", pattern="^(AA|AAA)$")


@app.post("/orgs/{org_id}/review/contrast")
def review_contrast(org_id: int, body: ContrastIn, session: Session = Depends(get_session)) -> dict:
    org = _org_or_404(session, org_id)
    try:
        ratio = contrast.contrast_ratio(body.fg, body.bg)
        finding = contrast.check_contrast(body.fg, body.bg, list(org.palette or []), body.level, body.large_text)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"ratio": round(ratio, 2), "required": contrast.required_ratio(body.level, body.large_text),
            "passes": finding is None, "finding": finding.to_dict() if finding else None}


# ---------- creator decisions on findings ----------
class DecisionIn(BaseModel):
    status: str = Field(pattern="^(accepted|dismissed|open)$")
    reason: str = ""  # required when dismissing
    incorrect_finding: bool = False  # the "incorrect finding" button


@app.patch("/findings/{finding_id}")
def decide(finding_id: int, body: DecisionIn, session: Session = Depends(get_session)) -> dict:
    row = session.get(FindingRow, finding_id)
    if row is None:
        raise HTTPException(404, "Finding not found")
    if body.status == "dismissed" and not body.reason.strip() and not body.incorrect_finding:
        raise HTTPException(422, "Give a reason when dismissing a finding")
    row.status = body.status
    row.dismiss_reason = body.reason
    row.incorrect_finding = body.incorrect_finding
    row.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    return {"id": row.id, "status": row.status}


# ---------- numbers the dashboard needs ----------
@app.get("/orgs/{org_id}/insights/rules")
def rule_insights(org_id: int, session: Session = Depends(get_session)) -> list[dict]:
    """Per rule: how often it fired, how often people dismissed it, how often marked incorrect."""
    _org_or_404(session, org_id)
    rows = (
        session.query(
            FindingRow.rule_id,
            FindingRow.category,
            func.count(FindingRow.id),
            func.sum(case((FindingRow.status == "dismissed", 1), else_=0)),
            func.sum(case((FindingRow.incorrect_finding.is_(True), 1), else_=0)),
        )
        .filter(FindingRow.org_id == org_id)
        .group_by(FindingRow.rule_id, FindingRow.category)
        .all()
    )
    out = []
    for rule_id, category, total, dismissed, incorrect in rows:
        dismissed, incorrect = int(dismissed or 0), int(incorrect or 0)
        out.append({
            "rule_id": rule_id, "category": category, "total": total, "dismissed": dismissed,
            "incorrect": incorrect, "dismissal_rate": round(dismissed / total, 3) if total else 0,
        })
    return sorted(out, key=lambda r: (-r["dismissal_rate"], -r["total"]))
