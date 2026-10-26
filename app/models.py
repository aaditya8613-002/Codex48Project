"""TiDB / MySQL schema.

Embeddings are stored as JSON arrays and compared in Python (fine for a small
knowledge base). Every row that belongs to a company carries org_id so data is
separated per organisation.
"""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Official product names the terminology rules protect, e.g. ["BrandGuard"]
    product_names: Mapped[list] = mapped_column(JSON, default=list)
    # Approved brand colours as hex strings, e.g. ["#1F4E79", "#F2A900"]
    palette: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class User(Base):
    """Owned by the schema; login/JWT endpoints live in the workflow module."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="creator")  # creator|manager|reviewer|admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class BrandDocument(Base):
    __tablename__ = "brand_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(30), default="guideline")  # guideline|tone|policy
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    chunks: Mapped[list["KbChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KbChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("brand_documents.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    heading: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    document: Mapped[BrandDocument] = relationship(back_populates="chunks")


class Fact(Base):
    """An approved, dated fact the claim checker can cite."""

    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    key: Mapped[str] = mapped_column(String(120))  # e.g. "customer_teams"
    statement: Mapped[str] = mapped_column(Text)  # human readable: "3 million teams use FlowDesk"
    value: Mapped[float | None] = mapped_column(Float, nullable=True)  # normalised number if numeric
    unit: Mapped[str] = mapped_column(String(30), default="")  # "", "%", "usd", ...
    keywords: Mapped[list] = mapped_column(JSON, default=list)  # words that tie a claim to this fact
    source: Mapped[str] = mapped_column(String(300), default="")  # "Fact sheet v3"
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Term(Base):
    """Preferred / banned wording."""

    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # terminology | banned_phrase
    phrase: Mapped[str] = mapped_column(String(200))  # what to look for
    preferred: Mapped[str | None] = mapped_column(String(200), nullable=True)  # what to use instead
    reason: Mapped[str] = mapped_column(String(500), default="")
    severity: Mapped[str] = mapped_column(String(10), default="medium")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(100), default="")  # "LinkedIn post"
    content: Mapped[str] = mapped_column(Text)
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_error: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    findings: Mapped[list["FindingRow"]] = relationship(back_populates="review", cascade="all, delete-orphan")


class FindingRow(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), index=True)
    org_id: Mapped[int] = mapped_column(Integer, index=True)
    rule_id: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(10))  # rules | claims | ai
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)  # supported|contradicted|cannot_verify
    message: Mapped[str] = mapped_column(Text)
    original: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    # Creator decision: open | accepted | dismissed
    status: Mapped[str] = mapped_column(String(12), default="open")
    dismiss_reason: Mapped[str] = mapped_column(String(500), default="")
    incorrect_finding: Mapped[bool] = mapped_column(Boolean, default=False)  # "incorrect finding" button
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    review: Mapped[Review] = relationship(back_populates="findings")
