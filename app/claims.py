"""Claim checking against the approved fact sheet.

Verdicts: supported | contradicted | cannot_verify. Nothing is ever marked
supported or contradicted without pointing at a specific approved fact.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from .types import Finding


@dataclass
class FactRef:
    id: int
    key: str
    statement: str
    value: float | None = None
    unit: str = ""  # "" | "%" | "usd"
    keywords: list[str] = field(default_factory=list)
    source: str = ""
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass
class ClaimResult:
    text: str  # the claim as written, e.g. "over 5 million"
    sentence: str
    start: int
    end: int
    verdict: str  # supported | contradicted | cannot_verify
    explanation: str
    fact: FactRef | None = None
    suggestion: str = ""
    resolved_by: str = "rules"  # rules | ai


MULTIPLIERS = {
    "": 1, "%": 1, "percent": 1,
    "thousand": 1e3, "k": 1e3,
    "lakh": 1e5,
    "million": 1e6, "m": 1e6,
    "crore": 1e7,
    "billion": 1e9, "bn": 1e9, "b": 1e9,
}

_NUMBER = re.compile(
    r"(?<![\w.])(?P<cur>[$₹€£])?\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s?(?P<suf>%|percent|billion|million|thousand|crore|lakh|bn|[mkb])?(?![\w])",
    re.IGNORECASE,
)
_QUALIFIER = re.compile(
    r"(?P<q>over|more than|at least|exceeds?|above|up to|under|less than|at most|below|nearly|almost|around|about|approximately|roughly)\s+$",
    re.IGNORECASE,
)
_LOWER_BOUND = {"over", "more than", "at least", "exceed", "exceeds", "above"}
_UPPER_BOUND = {"up to", "under", "less than", "at most", "below"}
_APPROX = {"nearly", "almost", "around", "about", "approximately", "roughly"}

_SUPERLATIVE = re.compile(
    r"\b(best|#1|number one|no\.\s?1|fastest|leading|world[’']s (?:best|first|largest|most)|"
    r"most (?:popular|trusted|secure|loved)|unmatched|unrivall?ed|market leader)\b",
    re.IGNORECASE,
)
# Numbers in a sentence with none of these cues are not treated as brand claims.
_STAT_CUES = re.compile(
    r"\b(customers?|users?|teams?|companies|clients?|downloads?|revenue|growth|faster|slower|savings?|save|"
    r"reduces?|increases?|uptime|rating|rated|trusted|used by|countries|employees|offices)\b",
    re.IGNORECASE,
)


def sentences(text: str):
    pos = 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(#$])|\n+", text):
        yield pos, text[pos : m.start()]
        pos = m.end()
    yield pos, text[pos:]


def format_value(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:g}%"
    prefix = "$" if unit == "usd" else ""
    for div, word in ((1e9, "billion"), (1e6, "million"), (1e3, "thousand")):
        if value >= div and abs(value / div - round(value / div, 2)) < 1e-9 and value / div < 1000:
            return f"{prefix}{value / div:g} {word}"
    return f"{prefix}{value:,.0f}" if float(value).is_integer() else f"{prefix}{value:g}"


def _unit_of(match: re.Match) -> str:
    suf = (match.group("suf") or "").lower()
    if suf in ("%", "percent"):
        return "%"
    if match.group("cur") == "$":
        return "usd"
    return ""


def _value_of(match: re.Match) -> float:
    base = float(match.group("num").replace(",", ""))
    return base * MULTIPLIERS.get((match.group("suf") or "").lower(), 1)


def _best_fact(window: str, facts: list[FactRef], anchor: int = 0) -> FactRef | None:
    """The fact whose keyword sits closest to the number (anchor = number position in window)."""
    low = window.lower()
    best: tuple[int, FactRef] | None = None
    for f in facts:
        dists = [abs(m.start() - anchor) for k in f.keywords for m in re.finditer(r"\b" + re.escape(k.lower()), low)]
        if dists and (best is None or min(dists) < best[0]):
            best = (min(dists), f)
    return best[1] if best else None


def _compare(claimed: float, fact_value: float, qualifier: str, unit: str = "") -> bool:
    q = qualifier.lower().strip()
    if q in _LOWER_BOUND:
        return claimed <= fact_value * 1.0001
    if q in _UPPER_BOUND:
        return claimed >= fact_value * 0.9999
    if unit == "%":  # percentages: compare in percentage points, not relative size
        return abs(claimed - fact_value) <= (1.0 if q in _APPROX else 0.05)
    if unit == "" and 1900 <= fact_value <= 2100 and float(fact_value).is_integer() and q not in _APPROX:
        return claimed == fact_value  # years must match exactly
    tol = 0.10 if q in _APPROX else 0.001  # exact claims: only rounding of the same figure
    return abs(claimed - fact_value) <= tol * abs(fact_value)


def check_claims(text: str, facts: list[FactRef], today: date | None = None) -> list[ClaimResult]:
    today = today or date.today()
    results: list[ClaimResult] = []

    for offset, sent in sentences(text):
        if not sent.strip():
            continue
        sent_fact = _best_fact(sent, facts)
        numeric_done = False

        # 1) numeric claims: each number is matched to the fact named right next to it
        for m in _NUMBER.finditer(sent):
            unit = _unit_of(m)
            w_start = max(0, m.start() - 30)
            window = sent[w_start : m.end() + 40]
            fact = _best_fact(window, facts, m.start() - w_start)
            if fact is not None and fact.value is not None and fact.unit != unit:
                continue
            if fact is None and not (_STAT_CUES.search(sent) or unit == "%"):
                continue
            if fact is None and m.group("suf") is None and 1900 <= float(m.group("num").replace(",", "")) <= 2100 and unit == "":
                continue  # a bare year
            if fact is not None and fact.value is None:
                continue  # non-numeric fact; handled below
            value = _value_of(m)
            q = _QUALIFIER.search(sent[: m.start()])
            qualifier = q.group("q") if q else ""
            span_start = offset + (q.start() if q else m.start())
            span_end = offset + m.end()
            claim_text = text[span_start:span_end]

            if fact is None:
                results.append(
                    ClaimResult(claim_text, sent, span_start, span_end, "cannot_verify",
                                "No approved fact covers this number, so it cannot be verified.",
                                suggestion="Add a source to the fact sheet, or remove the number.")
                )
                numeric_done = True
                continue
            if fact.valid_to and fact.valid_to < today:
                results.append(
                    ClaimResult(claim_text, sent, span_start, span_end, "cannot_verify",
                                f"The approved fact ({fact.source or fact.key}) expired on {fact.valid_to}, so it cannot be verified.",
                                fact=fact, suggestion="Ask the brand team for the current figure.")
                )
            elif fact.valid_from and fact.valid_from > today:
                results.append(
                    ClaimResult(claim_text, sent, span_start, span_end, "cannot_verify",
                                f"The approved fact is only valid from {fact.valid_from}.", fact=fact)
                )
            elif _compare(value, fact.value, qualifier, fact.unit):
                results.append(
                    ClaimResult(claim_text, sent, span_start, span_end, "supported",
                                f"Matches approved fact: {fact.statement} ({fact.source}).", fact=fact)
                )
            else:
                since = f", valid from {fact.valid_from}" if fact.valid_from else ""
                results.append(
                    ClaimResult(claim_text, sent, span_start, span_end, "contradicted",
                                f"Approved fact says: {fact.statement} ({fact.source}{since}).",
                                fact=fact, suggestion=format_value(fact.value, fact.unit))
                )
            numeric_done = True

        # 2) superlatives / unverifiable boasts
        if not numeric_done:
            for m in _SUPERLATIVE.finditer(sent):
                if sent_fact is not None and sent_fact.value is None:
                    results.append(
                        ClaimResult(m.group(0), sent, offset + m.start(), offset + m.end(), "supported",
                                    f"Backed by approved fact: {sent_fact.statement} ({sent_fact.source}).", fact=sent_fact)
                    )
                else:
                    results.append(
                        ClaimResult(m.group(0), sent, offset + m.start(), offset + m.end(), "cannot_verify",
                                    f'"{m.group(0)}" is a comparative claim with no approved evidence.',
                                    suggestion="Remove it, or add the supporting source to the fact sheet.")
                    )
    return results


def to_findings(results: list[ClaimResult]) -> list[Finding]:
    """Only contradicted and cannot-verify claims become findings."""
    out: list[Finding] = []
    for r in results:
        if r.verdict == "supported":
            continue
        key = r.fact.key if r.fact else "unverified"
        out.append(
            Finding(
                rule_id=f"claim:{key}",
                category="claim",
                severity="high" if r.verdict == "contradicted" else "medium",
                message=r.explanation,
                source="claims" if r.resolved_by == "rules" else "ai",
                original=r.text,
                suggestion=r.suggestion,
                start=r.start,
                end=r.end,
                verdict=r.verdict,
                evidence={
                    "type": "fact",
                    "id": r.fact.id if r.fact else None,
                    "statement": r.fact.statement if r.fact else None,
                    "source": r.fact.source if r.fact else None,
                },
            )
        )
    return out
