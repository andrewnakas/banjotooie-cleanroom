"""CLEAN ROOM: spec -> clean asset entries. Reads nothing from a ROM.

For every model texture, external texture, sprite frame and font glyph: pixels from the kept facts
(colour grid + detail noise + 2-bit alpha outline), or from an override hook (text labels / briefs /
renders), encoded to the slot's format; CI slots get our own palette. Mip strips are filled with a
downsampled chain. All other asset bytes come from the kept spec.
"""
import gzip
import json
import os

import numpy as np
from PIL import Image

from cleanroom.decomp.gen import from_digest, h32, unpack_alpha2
from cleanroom.gfx import texfmt as T
from games.banjotooie import assetfs as A, formats as F, logos

HOOKS = []          # functions (key, fact, rgba) -> rgba or None
OVERRIDE = {}       # texture key -> rgba (whole-model bakes: logos)


def quantize(rgba, n):
    """Our own palette: -> (index array (h, w), palette (n, 4) uint8)."""
    im = Image.fromarray(np.ascontiguousarray(rgba), "RGBA")
    q = im.quantize(colors=n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette("RGBA")[:4 * n] or [0] * 4 * n, np.uint8).reshape(-1, 4)
    pal = np.vstack([pal, np.zeros((n - len(pal), 4), np.uint8)])[:n]
    idx = np.array(q, np.uint8)
    pal[:, 3] = np.where(pal[:, 3] >= 128, 255, 0)
    return idx, pal


def nearest(img, pal):
    d = ((img[:, :, None, :].astype(int) - pal[None, None].astype(int)) ** 2).sum(-1)
    return d.argmin(-1).astype(np.uint8)


def mip_strip(rgba, fmt, siz, nbytes, pal_rgba=None):
    """Mip tail: a strip as wide as the texture and half as tall, levels side by side (16, 8, 4, ...)."""
    h, w = rgba.shape[:2]
    strip = np.zeros((max(1, h // 2), w, 4), np.uint8)
    x, lw, lh = 0, w // 2, h // 2
    while lw >= 1 and lh >= 1 and x + lw <= w:
        strip[:lh, x:x + lw] = np.array(Image.fromarray(rgba, "RGBA").resize((lw, lh), Image.BOX))
        x, lw, lh = x + lw, lw // 2, lh // 2
    if fmt == T.CI:
        idx = nearest(strip, pal_rgba)
        b = T.encode(np.dstack([idx] * 4), T.CI, siz)
    else:
        b = T.encode(strip, fmt, siz)
    return (bytes(b) + bytes(nbytes))[:nbytes]


def dither(key, rgba, amp=6):
    """Per-texel noise so smooth areas never repeat retail texel runs after 5-bit quantisation."""
    rng = np.random.default_rng(h32("dither", key))
    n = rng.integers(-amp, amp + 1, rgba.shape[:2] + (1,))
    out = rgba.astype(np.int16)
    out[..., :3] += n
    return np.clip(out, 0, 255).astype(np.uint8)


def pixels(key, fact):
    if key in OVERRIDE:
        return OVERRIDE[key]
    rgba = from_digest(key, fact)
    if "ishape2" in fact:                     # intensity sprite: our own soft shape from the kept outline
        from PIL import ImageFilter
        v = unpack_alpha2(fact["ishape2"], fact["w"], fact["h"])
        v = np.asarray(Image.fromarray(v.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32)
        rgba = rgba.copy()
        rgba[..., :3] = np.clip(v[..., None] * 1.1, 0, 255).astype(np.uint8)
    for hook in HOOKS:
        r = hook(key, fact, rgba)
        if r is not None:
            return np.asarray(r, np.uint8)
    return dither(key, rgba)


def put_tex(d, r, rgba):
    """Encode rgba into region r (palette, pixels, mip tail)."""
    pr = None
    if r["fmt"] == T.CI:
        idx, pr = quantize(rgba, 16 if r["siz"] == T.B4 else 256)
        a, n = r["pal"]
        d[a:a + n] = T.encode(pr[None], T.RGBA, T.B16)[:n]
        pix = T.encode(np.dstack([idx] * 4), T.CI, r["siz"])
    else:
        pix = T.encode(rgba, r["fmt"], r["siz"])
    a, n = r["pix"]
    d[a:a + n] = pix[:n]
    a, n = r.get("tail", (0, 0))
    if n:
        d[a:a + n] = mip_strip(rgba, r["fmt"], r["siz"], n, pr) if r.get("type", 0) & 0x8000 else bytes(n)


def gen_tex(d, regs, facts):
    for r in regs:
        fact = facts.get(r["key"])
        if fact is not None:
            put_tex(d, r, pixels(r["key"], fact))


def gen_sprite(d, regs, facts):
    frames = {}
    for r in regs:
        frames.setdefault(r["key"], []).append(r)
    cells = []                                   # (region, rgba)
    for key, fr in frames.items():
        fact = facts.get(key)
        if fact is None:
            continue
        img = pixels(key, fact)
        fh, fw = img.shape[:2]
        for r in fr:
            ys = np.clip(np.arange(r["y"], r["y"] + r["h"]), 0, fh - 1)
            xs = np.clip(np.arange(r["x"], r["x"] + r["w"]), 0, fw - 1)
            cells.append((r, img[ys][:, xs]))
    groups = {}
    for r, c in cells:
        if r["fmt"] == T.CI:
            groups.setdefault(r["pal"], []).append((r, c))
        else:
            a, n = r["pix"]
            d[a:a + n] = T.encode(c, r["fmt"], r["siz"])[:n]
    for (pa, pn), rc in groups.items():          # one palette per palette slot, shared by its chunks
        strip = np.concatenate([c.reshape(-1, 4) for _, c in rc])[None]
        if strip.shape[1] > 65536:               # many frames share one palette: quantise a sample
            step = strip.shape[1] // 65536 + 1
            _, pal = quantize(strip[:, ::step], pn // 2)
        else:
            _, pal = quantize(strip, pn // 2)
        d[pa:pa + pn] = T.encode(pal[None], T.RGBA, T.B16)[:pn]
        opaque = pal.copy()
        for r, c in rc:
            idx = nearest(c, opaque)
            a, n = r["pix"]
            d[a:a + n] = T.encode(np.dstack([idx] * 4), T.CI, r["siz"])[:n]


def load_spec(spec):
    meta = json.load(open(os.path.join(spec, "kept_assets.json")))
    blob = open(os.path.join(spec, "kept_assets.bin"), "rb").read()
    with gzip.open(os.path.join(spec, "textures.json.gz"), "rt") as f:
        facts = json.load(f)
    return meta, blob, facts


def register_hooks():
    if HOOKS:
        return
    import importlib
    for name in ("text", "faces", "drawn"):
        try:
            m = importlib.import_module("games.banjotooie." + name)
        except ModuleNotFoundError:
            continue
        HOOKS.append(m.hook)


def build_entries(spec, only=None):
    """-> list of assetfs.Entry with clean content. `only`: set of uids to regenerate (others kept zeroed)."""
    register_hooks()
    meta, blob, facts = load_spec(spec)
    es = []
    for m in meta:
        e = A.Entry(m["uid"], m["t"], b"")
        if m["off"] is not None:
            e._data = blob[m["off"]:m["off"] + m["len"]]
        es.append(e)
    info = F.ext_info(es)
    for e in es:
        if not e._data:
            continue
        d = bytearray(e._data)
        if only is None or e.uid in only:
            if e.type == 0x10:
                if e.uid in logos.SIGNS:
                    OVERRIDE.update({f"m{e.uid:x}.{i}": t for i, t in logos.sign_textures(e.uid, bytes(d)).items()})
                gen_tex(d, F.model_textures(e.uid, d), facts)
            elif e.type == 0x13 and e.uid in info:
                gen_tex(d, F.ext_texture(e.uid, d, info[e.uid]), facts)
            elif e.type in (0x17, 0x07):
                gen_sprite(d, F.sprite_chunks(e.uid, d), facts)
            elif e.type == 0x18:
                gen_tex(d, F.font_glyphs(e.uid, d), facts)
        e.set(d)
    return es
