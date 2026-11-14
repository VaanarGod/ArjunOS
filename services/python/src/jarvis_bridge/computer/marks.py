"""Marked screenshots ("set of marks"): numbered boxes drawn on the screenshot that match the [n] control list.

A small vision model is bad at saying WHERE something is, but good at reading a number next to it. So the bridge draws a box and a number on every
control it can place, and the prompt says "box 7 is control [7]". Only numbers are drawn, never labels or values, so nothing private is added to the
picture. The picture is only for the model: the original screenshot is what the loop compares to notice that nothing changed.

Pillow is optional. Without it, or with any image it cannot read safely, the original screenshot is used unchanged.
"""
from __future__ import annotations
import base64, binascii, io
from dataclasses import dataclass

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except Exception:                                   # pragma: no cover - exercised only where Pillow is missing
    HAVE_PIL = False

MAX_PIXELS = 12_000_000                             # refuse to decode anything larger (a decompression bomb would otherwise cost seconds and gigabytes)
MAX_B64 = 6_000_000                                 # the same ceiling parse_observation applies to a screenshot
PALETTE = ((230, 40, 40), (0, 120, 255), (20, 160, 60), (230, 130, 0), (160, 60, 220), (0, 160, 170))


@dataclass
class Marked:
    b64: str                                        # the picture to give the model (the original when nothing could be drawn)
    marked: tuple = ()                              # the control numbers that got a box, in order
    changed: bool = False


def _font(size: int):
    try: return ImageFont.load_default(size=size)   # Pillow >= 10.1
    except Exception:
        try: return ImageFont.load_default()
        except Exception: return None


def _placeable(e, sx: float, sy: float, w: int, h: int):
    """The control's box in image pixels, clipped to the picture, or None when it has no usable box."""
    if e.w <= 0 or e.h <= 0: return None
    x0, y0, x1, y1 = e.x * sx, e.y * sy, (e.x + e.w) * sx, (e.y + e.h) * sy
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(w - 1), x1), min(float(h - 1), y1)
    if x1 - x0 < 4 or y1 - y0 < 4: return None
    return x0, y0, x1, y1


def mark_screenshot(b64: str, elements, *, width: int = 0, height: int = 0, max_marks: int = 40) -> Marked:
    """Draws up to max_marks numbered boxes. `width`/`height` are the size the control coordinates refer to; when the picture differs, boxes are scaled."""
    plain = Marked(b64 or "")
    if not HAVE_PIL or not b64 or not elements: return plain
    try:
        raw = base64.b64decode(b64, validate=False)
        img = Image.open(io.BytesIO(raw))
        if img.width * img.height > MAX_PIXELS or img.width < 16 or img.height < 16: return plain
        img = img.convert("RGB")
    except Exception:                               # not an image, truncated, a bomb: whatever it is, use the original
        return plain
    w, h = img.size
    sx = (w / width) if width > 0 else 1.0
    sy = (h / height) if height > 0 else 1.0
    draw = ImageDraw.Draw(img, "RGBA")
    font = _font(max(11, min(18, h // 55)))
    drawn: list = []
    taken: list = []                                # badge rectangles already used, so numbers do not pile on top of each other
    for e in elements:
        if len(drawn) >= max_marks: break
        box = _placeable(e, sx, sy, w, h)
        if box is None: continue
        colour = PALETTE[e.i % len(PALETTE)]
        draw.rectangle(box, outline=colour + (255,), width=2)
        text = str(e.i)
        try:
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            tw, th = r - l, b - t
        except Exception:
            tw, th = 7 * len(text), 11
        pad = 2
        bw, bh = tw + 2 * pad + 2, th + 2 * pad + 2
        bx, by = box[0], box[1] - bh if box[1] - bh >= 0 else box[1]            # above the box when there is room, inside it otherwise
        bx = min(bx, w - bw - 1)
        for _ in range(4):                                                        # nudge down while another badge is in the way
            if any(not (bx + bw < o[0] or o[2] < bx or by + bh < o[1] or o[3] < by) for o in taken): by += bh
            else: break
        by = min(by, h - bh - 1)
        taken.append((bx, by, bx + bw, by + bh))
        draw.rectangle((bx, by, bx + bw, by + bh), fill=colour + (235,))
        draw.text((bx + pad + 1, by + pad - 1), text, fill=(255, 255, 255, 255), font=font)
        drawn.append(e.i)
    if not drawn: return plain
    out = io.BytesIO()
    img.save(out, "PNG", optimize=False)
    enc = base64.b64encode(out.getvalue()).decode("ascii")
    if len(enc) > MAX_B64:                                                         # a big PNG: fall back to JPEG so the picture still fits
        out = io.BytesIO(); img.save(out, "JPEG", quality=85)
        enc = base64.b64encode(out.getvalue()).decode("ascii")
        if len(enc) > MAX_B64: return plain
    return Marked(enc, tuple(drawn), True)
