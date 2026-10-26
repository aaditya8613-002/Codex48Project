import io

from PIL import Image

from app.rules import alt_text, contrast, palette, terms


# ---- contrast: reference values from the WCAG formula ----
def test_black_on_white_is_21():
    assert round(contrast.contrast_ratio("#000000", "#ffffff"), 2) == 21.0


def test_grey_777_just_fails_aa_and_grey_767676_passes():
    assert contrast.check_contrast("#777777", "#ffffff") is not None  # 4.48:1
    assert contrast.check_contrast("#767676", "#ffffff") is None  # 4.54:1


def test_large_text_threshold_is_3():
    assert contrast.check_contrast("#949494", "#ffffff", large_text=True) is None  # about 3.03:1
    assert contrast.check_contrast("#949494", "#ffffff") is not None


def test_short_hex_and_fix_suggestion_uses_brand_palette():
    f = contrast.check_contrast("#999", "#fff", palette=["#1F4E79", "#F2A900"])
    assert f and "#1F4E79" in f.suggestion and f.evidence["ratio"] < 4.5


def test_inline_style_scan_offsets_point_at_the_style_attribute():
    html = '<p style="color:#cccccc;background:#ffffff">Hi</p>'
    [f] = contrast.scan_html_inline_styles(html)
    assert html[f.start:f.end].startswith("style=")


# ---- terminology and product names ----
def test_banned_phrase_whole_word_only():
    rules = [terms.TermRule(1, "banned_phrase", "cheap", "affordable")]
    assert terms.check_terms("A cheap plan.", rules)
    assert not terms.check_terms("Cheaper plans exist.", rules)  # different word


def test_terminology_offsets_and_suggestion():
    rules = [terms.TermRule(1, "terminology", "the tool", "FlowDesk")]
    text = "Try the tool today."
    [f] = terms.check_terms(text, rules)
    assert text[f.start:f.end] == "the tool" and f.suggestion == "FlowDesk"


def test_product_name_variants_but_not_the_correct_form():
    text = "FlowDesk, Flow Desk, flowdesk, flow-desk and FLOWDESK."
    found = [text[f.start:f.end] for f in terms.check_product_names(text, ["FlowDesk"])]
    assert found == ["Flow Desk", "flowdesk", "flow-desk", "FLOWDESK"]


# ---- alt text ----
def test_missing_empty_and_filename_alt_text():
    html = '<img src="a.png"> <img src="b.png" alt=""> <img src="c.png" alt="IMG_1234"> <img src="d.png" alt="">'
    assert len(alt_text.check_alt_text(html)) == 4
    ok = '<img src="x.png" alt="A chart of weekly signups"> <img src="y.png" alt="" role="presentation">'
    assert alt_text.check_alt_text(ok) == []


def test_markdown_images():
    assert len(alt_text.check_alt_text("![](a.png) ![image](b.png) ![A real description](c.png)")) == 2


def test_alt_value_check():
    assert alt_text.check_alt_value(None) and alt_text.check_alt_value("  ")
    assert alt_text.check_alt_value("A team reviewing a plan") == []


# ---- palette ----
def _png(color, size=(80, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def test_palette_flags_off_brand_colour_and_accepts_brand_colour():
    brand = ["#1F4E79", "#F2A900"]
    assert palette.check_palette(_png((255, 0, 200)), brand)  # magenta
    assert not palette.check_palette(_png((31, 78, 121)), brand)  # exact brand blue
    assert not palette.check_palette(_png((240, 240, 240)), brand)  # neutral grey allowed
