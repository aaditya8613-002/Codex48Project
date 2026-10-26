"""WCAG 2.2 colour contrast (success criterion 1.4.3), calculated exactly."""
import re

from ..types import Finding

# Minimum ratios: AA normal 4.5, AA large 3.0, AAA normal 7.0, AAA large 4.5
THRESHOLDS = {("AA", False): 4.5, ("AA", True): 3.0, ("AAA", False): 7.0, ("AAA", True): 4.5}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        raise ValueError(f"Not a hex colour: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = relative_luminance(hex_to_rgb(fg))
    l2 = relative_luminance(hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def required_ratio(level: str = "AA", large_text: bool = False) -> float:
    return THRESHOLDS[(level, large_text)]


def suggest_colour(bg: str, palette: list[str], level: str = "AA", large_text: bool = False) -> str | None:
    """Brand colour with the lowest contrast that still passes (closest to the original look)."""
    need = required_ratio(level, large_text)
    passing = [(contrast_ratio(c, bg), c) for c in palette]
    passing = [p for p in passing if p[0] >= need]
    return min(passing)[1] if passing else None


def check_contrast(
    fg: str,
    bg: str,
    palette: list[str] | None = None,
    level: str = "AA",
    large_text: bool = False,
    location: str = "",
) -> Finding | None:
    ratio = contrast_ratio(fg, bg)
    need = required_ratio(level, large_text)
    if ratio >= need:
        return None
    fix = suggest_colour(bg, palette or [], level, large_text)
    return Finding(
        rule_id="contrast:wcag-aa" if level == "AA" else "contrast:wcag-aaa",
        category="contrast",
        severity="high" if ratio < 3.0 else "medium",
        message=f"WCAG {level} needs {need}:1 for {'large' if large_text else 'normal'} text, this measures {ratio:.1f}:1.",
        source="rules",
        original=f"{fg} on {bg}" + (f" ({location})" if location else ""),
        suggestion=f"Use {fix}" if fix else "Use a darker text colour or a lighter background.",
        evidence={"type": "measurement", "ratio": round(ratio, 2), "required": need, "level": level, "fg": fg, "bg": bg},
    )


_STYLE_ATTR = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)
_COLOR = re.compile(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{3,6})\b")
_BG = re.compile(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,6})\b")


def scan_html_inline_styles(html: str, palette: list[str] | None = None) -> list[Finding]:
    """Check inline style attributes that set both a text colour and a background colour."""
    findings: list[Finding] = []
    for m in _STYLE_ATTR.finditer(html):
        style = m.group(1)
        fg, bg = _COLOR.search(style), _BG.search(style)
        if not (fg and bg):
            continue
        finding = check_contrast(fg.group(1), bg.group(1), palette)
        if finding:
            finding.start, finding.end = m.start(), m.end()
            finding.original = m.group(0)
            findings.append(finding)
    return findings
