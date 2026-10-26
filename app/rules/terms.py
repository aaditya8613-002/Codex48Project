"""Exact checks for terminology, banned phrases and product-name variants."""
import re
from dataclasses import dataclass

from ..types import Finding


@dataclass
class TermRule:
    id: int | str
    kind: str  # terminology | banned_phrase
    phrase: str
    preferred: str | None = None
    reason: str = ""
    severity: str = "medium"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _phrase_regex(phrase: str) -> re.Pattern:
    # Whole-word, case-insensitive; internal spaces match any run of whitespace.
    parts = [re.escape(p) for p in phrase.split()]
    return re.compile(r"(?<![\w])" + r"\s+".join(parts) + r"(?![\w])", re.IGNORECASE)


def _split_camel(name: str) -> list[str]:
    parts = re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", name)
    return parts or [name]


def _product_variant_regex(name: str) -> re.Pattern:
    parts = [re.escape(p) for p in _split_camel(name)]
    return re.compile(r"(?<![\w])" + r"[\s\-]?".join(parts) + r"(?![\w])", re.IGNORECASE)


def check_terms(text: str, rules: list[TermRule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        for m in _phrase_regex(rule.phrase).finditer(text):
            if rule.kind == "banned_phrase":
                message = rule.reason or f'"{m.group(0)}" is not allowed in brand content.'
                suggestion = f'Remove or replace "{m.group(0)}".'
                if rule.preferred:
                    suggestion = rule.preferred
            else:
                message = rule.reason or f'Use "{rule.preferred}" instead of "{m.group(0)}".'
                suggestion = rule.preferred or ""
            findings.append(
                Finding(
                    rule_id=f"{rule.kind}:{_slug(rule.phrase)}",
                    category=rule.kind,
                    severity=rule.severity,
                    message=message,
                    source="rules",
                    original=m.group(0),
                    suggestion=suggestion,
                    start=m.start(),
                    end=m.end(),
                    evidence={"type": "term", "id": rule.id, "rule": rule.phrase, "preferred": rule.preferred},
                )
            )
    return findings


def check_product_names(text: str, product_names: list[str]) -> list[Finding]:
    """Flag spelling/spacing/case variants of an official product name."""
    findings: list[Finding] = []
    for name in product_names:
        for m in _product_variant_regex(name).finditer(text):
            if m.group(0) == name:
                continue
            findings.append(
                Finding(
                    rule_id=f"product-name:{_slug(name)}",
                    category="terminology",
                    severity="medium",
                    message=f'The product name is always written "{name}", not "{m.group(0)}".',
                    source="rules",
                    original=m.group(0),
                    suggestion=name,
                    start=m.start(),
                    end=m.end(),
                    evidence={"type": "product_name", "official": name},
                )
            )
    return findings
