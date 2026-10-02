"""Re-typeset fonts: Banjo-Tooie's three glyph fonts (asset type 0x18, IA8), drawn with open fonts.

  0xC21  dialog font, 14 px cells: glyph i = chr(0x21 + i) up to 'Z', then European letters
  0xC22  large menu font, 23 px cells: 0-9 : A-Z (c) (tm) ? ( ) < > " . ; - ! / '
  0xC23  small counter font, 10 px cells: 0-9 : - (blank)
Cell size and advance width are kept facts; the letters are Lilita One / Luckiest Guy (OFL / Apache).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(__file__), "fonts")
DIALOG = [chr(0x21 + k) for k in range(58)] + list("ÄÖÜßÀÂÇÉÈÊËÎÏÔÛÜÙÌÍÓÒÚÙÑÁ¡¿ªº©")
LARGE = list("0123456789:") + [chr(ord("A") + k) for k in range(26)] + list("©™?()<>\".;-!/'")
SMALL = list("0123456789:- ")
# uid -> (charset, face, cap height px, baseline px from the top, drop shadow)
SETS = {0xC21: (DIALOG, "LilitaOne-Regular.ttf", 10, 12, False),
        0xC22: (LARGE, "LuckiestGuy-Regular.ttf", 17, 20, True),
        0xC23: (SMALL, "LilitaOne-Regular.ttf", 8, 9, False)}


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def glyph_mask(ch, w, h, face, cap, base, adv=None):
    """Alpha mask (h, w) 0..1 of `ch`: capitals `cap` px tall, baseline `base` px from the top, left-aligned
    in its advance width, squeezed horizontally only when wider than the advance."""
    ss = 4
    hb = _font(face, 10 * ss).getbbox("H")
    f = _font(face, int(round(10 * ss * cap * ss / max(1, hb[3] - hb[1]))))
    hb = f.getbbox("H")
    l, t, r, b = f.getbbox(ch)
    gw = max(1, r - l)
    im = Image.new("L", (gw + 8 * ss, h * ss + 8 * ss), 0)
    ImageDraw.Draw(im).text((4 * ss - l, int(base * ss) - hb[3] + 4 * ss), ch, font=f, fill=255)
    im = im.crop((4 * ss - ss // 2, 4 * ss, 4 * ss + gw + ss // 2, 4 * ss + h * ss))
    aw = adv if adv and 0 < adv <= w else w
    W = max(ss, aw * ss - ss)
    if im.width > W:
        im = im.resize((W, im.height), Image.LANCZOS)
    out = Image.new("L", (w * ss, h * ss), 0)
    out.paste(im, ((W - im.width) // 2, 0))
    return np.asarray(out.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def hook(key, fact, rgba):
    if key[0] != "f":
        return None
    uid, i = int(key[1:].split(".")[0], 16), int(key.split(".")[1])
    if uid not in SETS:
        return None
    chars, face, cap, base, shadow = SETS[uid]
    w, h = fact["w"], fact["h"]
    if i >= len(chars) or chars[i] == " ":
        return np.zeros((h, w, 4), np.uint8)
    m = glyph_mask(chars[i], w, h, face, cap, base, fact.get("adv"))
    if shadow:                                   # white letter, dark edge towards the lower right
        sh = np.zeros_like(m)
        sh[1:, 1:] = m[:-1, :-1]
        a = np.maximum(m, sh)
        lum = 255 * np.clip(m * 1.4, 0, 1) / np.maximum(a, 1e-3) * (a > 0.05)
    else:                                        # white letter with a soft dark rim
        edge = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
        a = np.maximum(np.clip(m * 1.5, 0, 1), edge * 0.7)
        lum = 40 + 215 * np.clip(m * 1.6, 0, 1)
    lum = np.clip(lum, 0, 255)
    return np.dstack([lum, lum, lum, np.clip(a, 0, 1) * 255]).astype(np.uint8)
