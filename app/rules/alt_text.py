"""Alt-text checks for HTML <img> tags and Markdown images."""
import re

from ..types import Finding

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_MD_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
_ATTR = re.compile(r'([a-zA-Z\-:]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')

_FILENAME_LIKE = re.compile(r"\.(png|jpe?g|gif|webp|svg)$|^img[_\-]?\d*$|^image\d*$|^dsc[_\-]?\d+$", re.IGNORECASE)
_GENERIC = {"image", "photo", "picture", "graphic", "img", "screenshot", "banner", "logo"}


def _quality_problem(alt: str) -> str | None:
    a = alt.strip()
    if _FILENAME_LIKE.search(a):
        return "looks like a file name"
    if a.lower() in _GENERIC:
        return "is too generic to describe the image"
    if len(a) > 150:
        return "is very long (keep alt text under about 150 characters)"
    return None


def _finding(message: str, original: str, start: int, end: int, suggestion: str) -> Finding:
    return Finding(
        rule_id="alt-text:missing" if "missing" in message else "alt-text:quality",
        category="alt_text",
        severity="high" if "missing" in message else "medium",
        message=message,
        source="rules",
        original=original,
        suggestion=suggestion,
        start=start,
        end=end,
        evidence={"type": "wcag", "criterion": "1.1.1 Non-text Content"},
    )


def check_alt_value(alt: str | None, location: str = "uploaded image") -> list[Finding]:
    """Check an alt text supplied separately from the image (for example in an upload form)."""
    if alt is None or not alt.strip():
        return [_finding("Image has missing alt text (WCAG 1.1.1).", location, 0, 0,
                         "Add a short description of what the image shows.")]
    problem = _quality_problem(alt)
    if problem:
        return [_finding(f'Alt text "{alt}" {problem}.', location, 0, 0,
                         "Write a short description of what the image conveys.")]
    return []


def check_alt_text(content: str) -> list[Finding]:
    findings: list[Finding] = []

    for m in _IMG_TAG.finditer(content):
        tag = m.group(0)
        attrs = {k.lower(): (v1 or v2) for k, v1, v2 in _ATTR.findall(tag)}
        decorative = attrs.get("role", "").lower() in {"presentation", "none"} or attrs.get("aria-hidden") == "true"
        if "alt" not in attrs:
            findings.append(
                _finding("Image has missing alt text (WCAG 1.1.1).", tag, m.start(), m.end(),
                         'Add alt="..." describing what the image shows, or alt="" if it is purely decorative.')
            )
        elif not attrs["alt"].strip() and not decorative:
            findings.append(
                _finding("Image has missing alt text: the alt attribute is empty and the image is not marked decorative.",
                         tag, m.start(), m.end(), "Describe the image, or mark it decorative with role=\"presentation\".")
            )
        elif attrs["alt"].strip():
            problem = _quality_problem(attrs["alt"])
            if problem:
                findings.append(
                    _finding(f'Alt text "{attrs["alt"]}" {problem}.', tag, m.start(), m.end(),
                             "Write a short description of what the image conveys.")
                )

    for m in _MD_IMG.finditer(content):
        alt = m.group(1)
        if not alt.strip():
            findings.append(
                _finding("Image has missing alt text (WCAG 1.1.1).", m.group(0), m.start(), m.end(),
                         "Put a short description between the square brackets.")
            )
        else:
            problem = _quality_problem(alt)
            if problem:
                findings.append(
                    _finding(f'Alt text "{alt}" {problem}.', m.group(0), m.start(), m.end(),
                             "Write a short description of what the image conveys.")
                )
    return findings
