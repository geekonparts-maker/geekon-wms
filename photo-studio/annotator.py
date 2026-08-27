# -*- coding: utf-8 -*-
"""Μηχανή σχεδίασης διαστάσεων πάνω σε φωτογραφίες προϊόντων.

Όλα τα βέλη, πλαίσια και κείμενα σχεδιάζονται προγραμματιστικά (Pillow),
ώστε τα νούμερα να είναι πάντα ακριβή και η εμφάνιση ενιαία σε όλο το eshop.
"""

import os
from PIL import Image, ImageDraw, ImageFont

# GeekOn design tokens
ORANGE = (237, 135, 45)      # #ED872D
DARK = (23, 25, 30)          # #17191E
MUTED = (107, 114, 128)      # #6B7280
WHITE = (255, 255, 255)

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

_FONT_FILES = {
    "extrabold": "Commissioner-ExtraBold.ttf",
    "bold": "Commissioner-Bold.ttf",
    "medium": "Commissioner-Medium.ttf",
    "mono": "IBMPlexMono-SemiBold.ttf",
}

# Fallbacks αν λείπουν τα τοπικά fonts (π.χ. φρέσκο clone χωρίς το fonts/)
_SYSTEM_FALLBACKS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, _FONT_FILES[kind])
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    for fb in _SYSTEM_FALLBACKS:
        if os.path.exists(fb):
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default(size)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return r - l, b - t


def _draw_centered_text(draw, cx, cy, text, font, fill):
    w, h = _text_size(draw, text, font)
    draw.text((cx - w / 2, cy - h / 2), text, font=font, fill=fill, anchor=None)


def _round_line(draw, p1, p2, color, lw):
    """Γραμμή με στρογγυλεμένες άκρες (round caps)."""
    draw.line([p1, p2], fill=color, width=lw)
    r = lw / 2
    for (x, y) in (p1, p2):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _label_pill(draw, cx, cy, text, font, fg, bg, pad_x, pad_y):
    """Ετικέτα σε γεμάτο στρογγυλό pill (μοντέρνο chip)."""
    w, h = _text_size(draw, text, font)
    x0, y0 = cx - w / 2 - pad_x, cy - h / 2 - pad_y
    x1, y1 = cx + w / 2 + pad_x, cy + h / 2 + pad_y
    draw.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2, fill=bg)
    _draw_centered_text(draw, cx, cy, text, font, fg)


def _double_arrow(draw, p1, p2, label, font, color, lw, head_l, head_w, **_kw):
    """Μοντέρνο βέλος δύο κατευθύνσεων: λεπτή γραμμή με round caps, ανοιχτές
    chevron αιχμές, και το νούμερο σε πορτοκαλί pill με λευκά γράμματα."""
    x1, y1 = p1
    x2, y2 = p2
    horizontal = abs(x2 - x1) >= abs(y2 - y1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

    _round_line(draw, p1, p2, color, lw)
    if horizontal:
        # chevrons: δύο γραμμές από κάθε άκρη προς τα μέσα
        _round_line(draw, (x1, y1), (x1 + head_l, y1 - head_w / 2), color, lw)
        _round_line(draw, (x1, y1), (x1 + head_l, y1 + head_w / 2), color, lw)
        _round_line(draw, (x2, y2), (x2 - head_l, y2 - head_w / 2), color, lw)
        _round_line(draw, (x2, y2), (x2 - head_l, y2 + head_w / 2), color, lw)
    else:
        _round_line(draw, (x1, y1), (x1 - head_w / 2, y1 + head_l), color, lw)
        _round_line(draw, (x1, y1), (x1 + head_w / 2, y1 + head_l), color, lw)
        _round_line(draw, (x2, y2), (x2 - head_w / 2, y2 - head_l), color, lw)
        _round_line(draw, (x2, y2), (x2 + head_w / 2, y2 - head_l), color, lw)

    _label_pill(draw, cx, cy, label, font, WHITE + (255,), color,
                pad_x=head_l * 0.75, pad_y=head_l * 0.42)


def draw_dim_on_image(img: Image.Image, p1, p2, label: str,
                      scale_ref: float | None = None) -> Image.Image:
    """Ζωγραφίζει ένα βέλος διάστασης απευθείας πάνω σε εικόνα (για preview).
    p1/p2 σε pixels της εικόνας. Ευθυγραμμίζεται οριζόντια ή κατακόρυφα."""
    s = (scale_ref or img.width) / 1500.0
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)
    f = _load_font("bold", max(12, round(38 * s)))
    lw = max(2, round(5 * s))
    head_l, head_w = max(6, round(28 * s)), max(6, round(26 * s))
    (x1, y1), (x2, y2) = p1, p2
    if abs(x2 - x1) >= abs(y2 - y1):   # οριζόντιο
        y = (y1 + y2) / 2
        a, b = (min(x1, x2), y), (max(x1, x2), y)
    else:                              # κατακόρυφο
        x = (x1 + x2) / 2
        a, b = (x, min(y1, y2)), (x, max(y1, y2))
    _double_arrow(draw, a, b, label, f, ORANGE + (255,), lw, head_l, head_w)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def render_custom_dims(
    product: Image.Image,
    dims: list,
    *,
    title: str = "",
    subtitle: str = "",
    footer: str = "",
    canvas: int = 1500,
    logo: Image.Image | None = None,
) -> Image.Image:
    """Τελική εικόνα με μετρήσεις σε ελεύθερες θέσεις.

    dims: λίστα από dicts {"x1","y1","x2","y2","label"} με συντεταγμένες σε
    pixels της φωτογραφίας προϊόντος (όπως τις έδωσαν τα κλικ του χρήστη).
    """
    S = canvas
    s = S / 1500.0
    f_title = _load_font("extrabold", round(60 * s))
    f_sub = _load_font("medium", round(30 * s))
    f_dim = _load_font("bold", round(38 * s))
    f_footer = _load_font("bold", round(42 * s))
    lw = max(2, round(5 * s))
    head_l, head_w = round(28 * s), round(26 * s)

    base = Image.new("RGB", (S, S), WHITE)
    top_zone = 0.13 * S if (title or subtitle) else 0.06 * S
    footer_zone = 0.12 * S if footer else 0.06 * S
    margin = 0.06 * S

    box_x0, box_x1 = margin, S - margin
    box_y0, box_y1 = top_zone, S - footer_zone
    p = product.convert("RGBA")
    bw, bh = box_x1 - box_x0, box_y1 - box_y0
    scale = min(bw / p.width, bh / p.height)
    nw, nh = max(1, round(p.width * scale)), max(1, round(p.height * scale))
    p2 = p.resize((nw, nh), Image.LANCZOS)
    px = round(box_x0 + (bw - nw) / 2)
    py = round(box_y0 + (bh - nh) / 2)
    base.paste(p2, (px, py), p2)

    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)
    if title:
        _draw_centered_text(draw, S / 2, 0.055 * S, title, f_title, DARK + (255,))
    if subtitle:
        _draw_centered_text(draw, S / 2, 0.105 * S, subtitle, f_sub, MUTED + (255,))

    def tx(x): return px + x * scale
    def ty(y): return py + y * scale

    for d in dims:
        x1, y1, x2, y2 = tx(d["x1"]), ty(d["y1"]), tx(d["x2"]), ty(d["y2"])
        if abs(x2 - x1) >= abs(y2 - y1):
            y = (y1 + y2) / 2
            a, b = (min(x1, x2), y), (max(x1, x2), y)
        else:
            x = (x1 + x2) / 2
            a, b = (x, min(y1, y2)), (x, max(y1, y2))
        _double_arrow(draw, a, b, d["label"], f_dim, ORANGE + (255,), lw, head_l, head_w)

    if footer:
        _draw_centered_text(draw, S / 2, S - footer_zone / 2, footer, f_footer, ORANGE + (255,))

    out = Image.alpha_composite(base.convert("RGBA"), ov)
    if logo is not None:
        lg = logo.convert("RGBA")
        lh = round(0.042 * S)
        lw_ = round(lg.width * lh / lg.height)
        lg = lg.resize((lw_, lh), Image.LANCZOS)
        out.paste(lg, (round(0.05 * S), round(S - 0.05 * S - lh)), lg)
    return out.convert("RGB")


def render_annotated(
    product: Image.Image,
    *,
    title: str = "",
    subtitle: str = "",
    outer_w: str = "",
    outer_h: str = "",
    active_w: str = "",
    active_h: str = "",
    footer: str = "",
    depth_chip: str = "",
    show_bottom: bool = False,
    canvas: int = 1500,
    inset_pct: float = 0.07,
    logo: Image.Image | None = None,
) -> Image.Image:
    """Τοποθετεί το προϊόν σε λευκό τετράγωνο καμβά και σχεδιάζει τίτλο,
    βέλη εξωτερικών διαστάσεων, πλαίσιο/βέλη active area και footer."""
    S = canvas
    s = S / 1500.0  # συντελεστής κλίμακας για όλα τα μεγέθη

    f_title = _load_font("extrabold", round(60 * s))
    f_sub = _load_font("medium", round(30 * s))
    f_dim = _load_font("bold", round(38 * s))
    f_footer = _load_font("bold", round(42 * s))
    f_chip = _load_font("bold", round(32 * s))

    lw = max(2, round(5 * s))
    head_l, head_w = round(28 * s), round(26 * s)

    base = Image.new("RGB", (S, S), WHITE)

    # --- Ζώνες διάταξης ---
    has_title = bool(title or subtitle)
    has_footer_zone = bool(footer or (active_w and active_h) or depth_chip)
    top_zone = 0.13 * S if has_title else 0.06 * S
    arrow_zone = 0.065 * S if outer_w else 0.015 * S
    bottom_arrow_zone = 0.06 * S if (show_bottom and outer_w) else 0.0
    footer_zone = 0.13 * S if has_footer_zone else 0.05 * S
    right_zone = 0.17 * S if outer_h else 0.05 * S
    left_margin = 0.07 * S

    box_x0 = left_margin
    box_x1 = S - right_zone
    box_y0 = top_zone + arrow_zone
    box_y1 = S - footer_zone - bottom_arrow_zone

    # --- Τοποθέτηση προϊόντος (fit, χωρίς παραμόρφωση) ---
    p = product.convert("RGBA")
    bw, bh = box_x1 - box_x0, box_y1 - box_y0
    scale = min(bw / p.width, bh / p.height)
    nw, nh = max(1, round(p.width * scale)), max(1, round(p.height * scale))
    p = p.resize((nw, nh), Image.LANCZOS)
    px = round(box_x0 + (bw - nw) / 2)
    py = round(box_y0 + (bh - nh) / 2)
    base.paste(p, (px, py), p)

    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)

    # --- Τίτλος / υπότιτλος ---
    if title:
        _draw_centered_text(draw, S / 2, 0.055 * S, title, f_title, DARK + (255,))
    if subtitle:
        _draw_centered_text(draw, S / 2, 0.105 * S, subtitle, f_sub, MUTED + (255,))

    # --- Εξωτερικά βέλη ---
    if outer_w:
        y = max(py - 0.045 * S, top_zone + 0.02 * S)
        _double_arrow(draw, (px, y), (px + nw, y), outer_w, f_dim,
                      ORANGE + (255,), lw, head_l, head_w)
    if outer_h:
        x = min(px + nw + 0.075 * S, S - 0.045 * S)
        _double_arrow(draw, (x, py), (x, py + nh), outer_h, f_dim,
                      ORANGE + (255,), lw, head_l, head_w, pill=True)
    if show_bottom and outer_w:
        y = min(py + nh + 0.045 * S, S - footer_zone - 0.015 * S)
        _double_arrow(draw, (px, y), (px + nw, y), outer_w, f_dim,
                      ORANGE + (255,), lw, head_l, head_w)

    # --- Active area: πορτοκαλί πλαίσιο + εσωτερικά βέλη ---
    if active_w or active_h:
        ins_x, ins_y = inset_pct * nw, inset_pct * nh
        ax0, ay0 = px + ins_x, py + ins_y
        ax1, ay1 = px + nw - ins_x, py + nh - ins_y
        draw.rounded_rectangle([ax0, ay0, ax1, ay1], radius=44 * s,
                               outline=ORANGE + (235,), width=max(3, round(7 * s)))
        pad = 0.055 * min(ax1 - ax0, ay1 - ay0) + head_l
        if active_h:
            x = ax0 + 0.24 * (ax1 - ax0)
            _double_arrow(draw, (x, ay0 + pad), (x, ay1 - pad), active_h, f_dim,
                          ORANGE + (255,), lw, head_l, head_w, pill=True)
        if active_w:
            y = ay0 + 0.74 * (ay1 - ay0)
            _double_arrow(draw, (ax0 + pad, y), (ax1 - pad, y), active_w, f_dim,
                          ORANGE + (255,), lw, head_l, head_w, pill=True)

    # --- Footer ---
    if not footer and active_w and active_h:
        footer = f"Active Area: {active_w} x {active_h}"
    fy = S - footer_zone / 2
    if footer:
        _draw_centered_text(draw, S / 2, fy - (0.028 * S if depth_chip else 0),
                            footer, f_footer, ORANGE + (255,))
    if depth_chip:
        cy = fy + (0.028 * S if footer else 0)
        w, h = _text_size(draw, depth_chip, f_chip)
        x0, y0 = S / 2 - w / 2 - 24 * s, cy - h / 2 - 12 * s
        x1, y1 = S / 2 + w / 2 + 24 * s, cy + h / 2 + 12 * s
        draw.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2,
                               fill=(253, 241, 230, 255))  # #FDF1E6
        _draw_centered_text(draw, S / 2, cy, depth_chip, f_chip, (201, 111, 30, 255))

    out = Image.alpha_composite(base.convert("RGBA"), ov)

    # --- Λογότυπο (προαιρετικό) ---
    if logo is not None:
        lg = logo.convert("RGBA")
        lh = round(0.042 * S)
        lw_ = round(lg.width * lh / lg.height)
        lg = lg.resize((lw_, lh), Image.LANCZOS)
        out.paste(lg, (round(0.05 * S), round(S - 0.05 * S - lh)), lg)

    return out.convert("RGB")
