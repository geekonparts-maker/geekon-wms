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


def _label_pill(draw, cx, cy, text, font, fill, pad_x, pad_y, pill_alpha=235):
    """Κείμενο με λευκό στρογγυλεμένο φόντο, ώστε να διαβάζεται πάνω σε φωτογραφία."""
    w, h = _text_size(draw, text, font)
    x0, y0 = cx - w / 2 - pad_x, cy - h / 2 - pad_y
    x1, y1 = cx + w / 2 + pad_x, cy + h / 2 + pad_y
    draw.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2,
                           fill=(255, 255, 255, pill_alpha))
    _draw_centered_text(draw, cx, cy, text, font, fill)


def _double_arrow(draw, p1, p2, label, font, color, lw, head_l, head_w,
                  pill=False, pad_x=14, pad_y=8):
    """Βέλος δύο κατευθύνσεων (οριζόντιο ή κατακόρυφο) με την ετικέτα σε κενό
    στη μέση της γραμμής, όπως στα τεχνικά σχέδια."""
    x1, y1 = p1
    x2, y2 = p2
    horizontal = abs(x2 - x1) >= abs(y2 - y1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    tw, th = _text_size(draw, label, font)

    if horizontal:
        gap = tw / 2 + pad_x + 10
        # γραμμές αριστερά/δεξιά από την ετικέτα
        if cx - gap > x1 + head_l:
            draw.line([x1 + head_l, y1, cx - gap, y1], fill=color, width=lw)
        if cx + gap < x2 - head_l:
            draw.line([cx + gap, y2, x2 - head_l, y2], fill=color, width=lw)
        # αιχμές
        draw.polygon([(x1, y1), (x1 + head_l, y1 - head_w / 2),
                      (x1 + head_l, y1 + head_w / 2)], fill=color)
        draw.polygon([(x2, y2), (x2 - head_l, y2 - head_w / 2),
                      (x2 - head_l, y2 + head_w / 2)], fill=color)
    else:
        gap = th / 2 + pad_y + 10
        if cy - gap > y1 + head_l:
            draw.line([x1, y1 + head_l, x1, cy - gap], fill=color, width=lw)
        if cy + gap < y2 - head_l:
            draw.line([x2, cy + gap, x2, y2 - head_l], fill=color, width=lw)
        draw.polygon([(x1, y1), (x1 - head_w / 2, y1 + head_l),
                      (x1 + head_w / 2, y1 + head_l)], fill=color)
        draw.polygon([(x2, y2), (x2 - head_w / 2, y2 - head_l),
                      (x2 + head_w / 2, y2 - head_l)], fill=color)

    if pill:
        _label_pill(draw, cx, cy, label, font, color, pad_x, pad_y)
    else:
        _draw_centered_text(draw, cx, cy, label, font, color)


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
    f_dim = _load_font("bold", round(46 * s))
    f_footer = _load_font("bold", round(42 * s))
    f_chip = _load_font("bold", round(32 * s))

    lw = max(3, round(7 * s))
    head_l, head_w = round(30 * s), round(24 * s)

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
        draw.rounded_rectangle([ax0, ay0, ax1, ay1], radius=36 * s,
                               outline=ORANGE + (255,), width=max(4, round(10 * s)))
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
