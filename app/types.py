"""Plain data object shared by the rules engine, claim checker and AI review."""
from dataclasses import asdict, dataclass, field


@dataclass
class Finding:
    rule_id: str  # stable id, used for dashboard grouping, e.g. "terminology:flowdesk"
    category: str  # terminology | banned_phrase | claim | contrast | alt_text | palette | tone | messaging
    severity: str  # low | medium | high
    message: str  # why it was flagged, in plain words
    source: str  # rules | claims | ai
    original: str = ""  # the text that triggered it
    suggestion: str = ""  # proposed fix (a person always decides)
    start: int | None = None  # character offsets into the reviewed text
    end: int | None = None
    verdict: str | None = None  # claims only: supported | contradicted | cannot_verify
    evidence: dict = field(default_factory=dict)  # which guideline / fact / measurement was used

    def to_dict(self) -> dict:
        return asdict(self)
