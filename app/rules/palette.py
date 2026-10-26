"""Brand palette check for uploaded images (dominant colours vs approved colours)."""
import io
import math

from PIL import Image

from ..types import Finding
from .contrast import hex_to_rgb


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def dominant_colours(image_bytes: bytes, n: int = 6) -> list[tuple[tuple[int, int, int], float]]:
    """Return [(rgb, share_of_pixels)] sorted by share, using a small quantised copy."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((120, 120))
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette() or []
    total = img.width * img.height
    out = []
    for count, idx in q.getcolors() or []:
        rgb = tuple(palette[idx * 3 : idx * 3 + 3])
        out.append((rgb, count / total))
    return sorted(out, key=lambda t: -t[1])


def check_palette(
    image_bytes: bytes,
    palette: list[str],
    tolerance: float = 60.0,
    min_share: float = 0.10,
    neutrals_ok: bool = True,
) -> list[Finding]:
    """Flag large colour areas that are not close to any approved brand colour.

    Limits (stated in the UI): this looks at dominant colours only. Photos will
    always contain many colours, so use it on banners, graphics and slides.
    """
    if not palette:
        return []
    brand = [hex_to_rgb(c) for c in palette]
    findings: list[Finding] = []
    for rgb, share in dominant_colours(image_bytes):
        if share < min_share:
            continue
        if neutrals_ok and max(rgb) - min(rgb) < 18:  # near-grey / white / black
            continue
        nearest = min(brand, key=lambda b: _dist(rgb, b))
        d = _dist(rgb, nearest)
        if d > tolerance:
            hex_found = "#%02X%02X%02X" % rgb
            hex_near = "#%02X%02X%02X" % nearest
            findings.append(
                Finding(
                    rule_id="palette:off-brand-colour",
                    category="palette",
                    severity="medium",
                    message=f"About {share:.0%} of the image uses {hex_found}, which is not in the brand palette.",
                    source="rules",
                    original=hex_found,
                    suggestion=f"Use the nearest brand colour {hex_near}.",
                    evidence={"type": "measurement", "share": round(share, 3), "distance": round(d, 1), "palette": palette},
                )
            )
    return findings
