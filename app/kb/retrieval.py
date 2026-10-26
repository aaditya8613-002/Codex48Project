"""Find the guideline passages most relevant to a piece of content (cosine similarity in Python)."""
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from ..ai import gemini
from ..config import settings
from ..models import BrandDocument, KbChunk


@dataclass
class Passage:
    id: int
    document_title: str
    heading: str
    text: str
    score: float


def _normalise(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def retrieve(session: Session, org_id: int, query: str, k: int | None = None) -> list[Passage]:
    """Top-k passages for this organisation only. Raises AIUnavailable if embedding fails."""
    k = k or settings.retrieval_top_k
    rows = (
        session.query(KbChunk, BrandDocument.title)
        .join(BrandDocument, BrandDocument.id == KbChunk.document_id)
        .filter(KbChunk.org_id == org_id, KbChunk.embedding.isnot(None))
        .all()
    )
    if not rows:
        return []
    matrix = _normalise(np.array([r[0].embedding for r in rows], dtype=np.float32))
    q = np.array(gemini.embed_texts([query[:6000]], query=True)[0], dtype=np.float32)
    q = _normalise(q.reshape(1, -1))[0]
    scores = matrix @ q
    order = np.argsort(-scores)[:k]
    return [
        Passage(
            id=rows[i][0].id,
            document_title=rows[i][1],
            heading=rows[i][0].heading,
            text=rows[i][0].text,
            score=float(scores[i]),
        )
        for i in order
        if scores[i] >= settings.min_similarity
    ]
