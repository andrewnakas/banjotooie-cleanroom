"""Banjo-Tooie asset formats: locate every pixel and palette region.

Used by the dirty-room spec step (coarse facts), by the clean generator (overwrite the regions with
generated pixels of the same format and size) and by the taint report. Everything outside the
regions (headers, geometry, display lists, vertices, collision) is kept as-is.

Asset types (table flag byte): 0x10 model, 0x13 external texture (uid >= EXT_BASE) or binary,
0x17 / 0x07 sprite, 0x18 font, 0x16 / 0x06 animation, 0x19 midi, 0x1A encrypted text, 0x12 2048-byte tables.

Model (magic 0x0000000B): u16 at 8 = texture list offset. List: u32 size (from the list start),
u16 count, u16 flags (0x100 = external), count x {u32 offset | external index, u16 type, u8 w, u8 h}.
type: 1 CI4, 2 CI8, 4 RGBA16, 8 RGBA32, 0x10 IA8; | 0x8000 = mip tail (half the main size) follows.
Inline data follows the list; external textures are assets EXT_BASE + index (the game concatenates
them in list order behind segment 2). CI textures start with their palette (0x20 / 0x200 bytes).
`h` can cover several stacked frames, each with its own palette.

Sprite: u16 frames, u16 format code, 4 x u16, u16 w, u16 h, 2 x u16, (0x10:) u32 pixel data offset (upper bits: flags;
really align8(0x1C + 12 * frames)), u32 vertex offset, u32 display list offset; (0x1C:) frames x 12 bytes
{u16, u16, u16 first Gfx index, s16, u32 pixel offset}.
The display list (F3DEX2) is self-describing: SETTIMG addresses are segment 2 = pixel data offset,
segment 1 = vertices. A frame is a set of textured quads ("chunks").

Font (type 0x18): u16 glyph count, u16 format (0x100 = IA8? see font_glyphs), u16 cell w, u16 cell h,
u32 pixel base; glyphs x {u8 w, u8 h, u8 ?, u8 ?, u32 offset}.
"""
import struct

from cleanroom.gfx import texfmt as T

EXT_BASE = 0x1EF6
MODEL_TYPES = {1: (T.CI, T.B4), 2: (T.CI, T.B8), 4: (T.RGBA, T.B16), 8: (T.RGBA, T.B32), 0x10: (T.IA, T.B8)}
BITS = {T.B4: 4, T.B8: 8, T.B16: 16, T.B32: 32}


def _u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def _s16(b, o):
    return struct.unpack_from(">h", b, o)[0]


def _u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def tex_list(d):
    """-> (flags, base offset of inline data, size of inline data, [(offset|index, type, w, h)])"""
    if len(d) < 0x38 or _u32(d, 0) != 0xB:
        return 0, 0, 0, []
    tl = _u16(d, 8)
    if not tl:
        return 0, 0, 0, []
    size, cnt, flags = _u32(d, tl), _u16(d, tl + 4), _u16(d, tl + 6)
    infos = [struct.unpack_from(">IHBB", d, tl + 8 + 8 * i) for i in range(cnt)]
    return flags, tl + 8 + 8 * cnt, size - 8 - 8 * cnt, infos


def _frames(typ, w, h, start, total, key):
    """Regions of one texture slot occupying `total` bytes at `start`."""
    fs = MODEL_TYPES.get(typ & 0xFF)
    if fs is None:
        return []
    w, h = w or 256, h or 256            # u8 fields: 0 = 256
    fmt, siz = fs
    paln = (0x20 if siz == T.B4 else 0x200) if fmt == T.CI else 0
    unit = lambda fh: paln + w * fh * BITS[siz] // 8
    n, fh = 1, h
    if unit(h) != total and not (typ & 0x8000):      # animated / stacked frames: the largest frame height that tiles the slot
        k = h
        while k >= 4:
            if h % k == 0 and total % unit(k) == 0:
                n, fh = total // unit(k), k
                break
            k //= 2
    out = []
    for f in range(n):
        p = start + f * unit(fh)
        pal = (p, paln) if paln else None
        plen = w * fh * BITS[siz] // 8
        end = start + (f + 1) * unit(fh) if n > 1 else start + total
        if p + paln + plen > start + total:
            break
        out.append({"key": key if n == 1 else f"{key}.{f}", "fmt": fmt, "siz": siz, "w": w, "h": fh, "pal": pal,
                    "pix": (p + paln, plen), "tail": (p + paln + plen, max(0, end - p - paln - plen)), "type": typ})
    return out


def model_textures(uid, d):
    flags, base, size, infos = tex_list(d)
    if flags & 0x100 or not infos:
        return []
    offs = sorted(set(x[0] for x in infos)) + [size]
    out = []
    for i, (off, typ, w, h) in enumerate(infos):
        end = min(x for x in offs if x > off)
        out += _frames(typ, w, h, base + off, end - off, f"m{uid:x}.{i}")
    return out


def ext_refs(d):
    """External textures a model uses: [(asset uid, type, w, h)]."""
    flags, base, size, infos = tex_list(d)
    if not flags & 0x100:
        return []
    return [(EXT_BASE + o, typ, w, h) for o, typ, w, h in infos]


def ext_texture(uid, d, info):
    typ, w, h = info
    return _frames(typ, w, h, 0, len(d), f"x{uid:x}")


def sprite_chunks(uid, d):
    """-> list of chunks {key (frame key), frame, fmt, siz, w, h, pal, pix, x, y (texel position in the frame)}"""
    if len(d) < 0x20:
        return []
    n = _u16(d, 0)
    po, vo, go = (0x1C + 12 * n + 7) & ~7, _u32(d, 0x14), _u32(d, 0x18)
    if not go or go >= len(d):                       # no display list: one raw image after the header
        fmt = {0x400: (T.RGBA, T.B16), 0x800: (T.RGBA, T.B32), 0x40: (T.I, T.B8)}.get(_u16(d, 2))
        w, h = _u16(d, 8), _u16(d, 10)
        if fmt is None or po + w * h * BITS[fmt[1]] // 8 > len(d):
            return []
        return [{"key": f"s{uid:x}.0", "frame": 0, "fmt": fmt[0], "siz": fmt[1], "w": w, "h": h, "pal": None,
                 "pix": (po, w * h * BITS[fmt[1]] // 8), "x": 0, "y": 0}]
    ng = (len(d) - go) // 8
    starts = [_u16(d, 0x20 + 12 * f) for f in range(n)] + [ng]   # frame entries start at 0x1C; +4 = first Gfx
    out = []
    for f in range(n):
        pal = None
        timg = None
        cur = None
        vbase = 0
        chunks = []
        for i in range(starts[f], min(starts[f + 1], ng)):
            w0, w1 = struct.unpack_from(">II", d, go + 8 * i)
            op = w0 >> 24
            if op == 0xFD:
                timg = w1 & 0xFFFFFF
            elif op == 0xF0:                           # LOADTLUT
                cnt = ((w1 >> 14) & 0x3FF) + 1
                pal = (po + timg, cnt * 2)
            elif op == 0xF5 and (w1 >> 24) & 7 == 0 and timg is not None:   # SETTILE for the render tile
                cur = {"fmt": (w0 >> 21) & 7, "siz": (w0 >> 19) & 3, "off": po + timg}
            elif op == 0xF2 and cur is not None:
                cur["w"] = ((w1 >> 12) & 0xFFF) // 4 + 1
                cur["h"] = (w1 & 0xFFF) // 4 + 1
            elif op == 0x01:
                vbase = (w1 & 0xFFFFFF) // 16
            elif op in (0x05, 0x06) and cur is not None and "w" in cur:
                vi = vbase + ((w0 >> 16) & 0xFF) // 2
                xs, ys = [], []
                for k in range(4):
                    x, y = struct.unpack_from(">hh", d, vo + 16 * (vbase + k))
                    xs.append(x)
                    ys.append(y)
                c = dict(cur, vx=(min(xs), max(xs)), vy=(min(ys), max(ys)))
                c["pal"] = pal if c["fmt"] == T.CI else None
                chunks.append(c)
                cur = None
        if not chunks:
            continue
        # texel positions: quads span their texture, y is up
        sx = [(c["vx"][1] - c["vx"][0]) / c["w"] for c in chunks if c["vx"][1] > c["vx"][0]]
        sy = [(c["vy"][1] - c["vy"][0]) / c["h"] for c in chunks if c["vy"][1] > c["vy"][0]]
        ux = sorted(sx)[len(sx) // 2] if sx else 1.0
        uy = sorted(sy)[len(sy) // 2] if sy else 1.0
        x0 = min(c["vx"][0] for c in chunks)
        y1 = max(c["vy"][1] for c in chunks)
        for c in chunks:
            nb = c["w"] * c["h"] * BITS[c["siz"]] // 8
            if c["off"] + nb > len(d):
                continue
            out.append({"key": f"s{uid:x}.{f}", "frame": f, "fmt": c["fmt"], "siz": c["siz"], "w": c["w"], "h": c["h"],
                        "pal": c["pal"], "pix": (c["off"], nb),
                        "x": int(round((c["vx"][0] - x0) / ux)), "y": int(round((y1 - c["vy"][1]) / uy))})
    return out


def font_glyphs(uid, d):
    """-> list of {key, i, fmt, siz, w, h, pix, adv}"""
    n, form, cw, ch = struct.unpack_from(">HHHH", d, 0)
    base = _u32(d, 8)
    out = []
    for i in range(n):
        w, h, a, b, off = struct.unpack_from(">BBBBI", d, 12 + 8 * i)
        if w == 0 or h == 0 or base + off + w * h > len(d):
            continue
        out.append({"key": f"f{uid:x}.{i}", "i": i, "fmt": T.IA if form == 0x100 else T.I, "siz": T.B8, "w": w, "h": h,
                    "pal": None, "pix": (base + off, w * h), "a": a, "b": b})
    return out


def decode_region(d, r):
    """RGBA8 (h, w, 4) of a region (palette applied)."""
    pal = None
    if r["pal"]:
        po, pn = r["pal"]
        pal = T.decode(bytes(d[po:po + pn]), pn // 2, 1, T.RGBA, T.B16)[0]
    return T.decode(bytes(d[r["pix"][0]:r["pix"][0] + r["pix"][1]]), r["w"], r["h"], r["fmt"], r["siz"], pal)


def compose(d, chunks):
    """Sprite frame image from its chunks -> RGBA (h, w, 4)."""
    import numpy as np
    fw = max(c["x"] + c["w"] for c in chunks)
    fh = max(c["y"] + c["h"] for c in chunks)
    img = np.zeros((fh, fw, 4), np.uint8)
    for c in chunks:
        img[c["y"]:c["y"] + c["h"], c["x"]:c["x"] + c["w"]] = decode_region(d, c)
    return img


def ext_info(entries):
    """{ext texture uid: (type, w, h)} from every model's texture list."""
    out = {}
    for e in entries:
        if e.type == 0x10 and e.data:
            for uid, typ, w, h in ext_refs(e.data):
                out.setdefault(uid, (typ, w, h))
    return out


def all_regions(entries, info=None):
    """Yield (entry, kind, regions) for every asset with pixel data. kind: model | ext | sprite | font"""
    info = info or ext_info(entries)
    for e in entries:
        d = e.data
        if not d:
            continue
        if e.type == 0x10:
            r = model_textures(e.uid, d)
            k = "model"
        elif e.type == 0x13 and e.uid in info:
            r = ext_texture(e.uid, d, info[e.uid])
            k = "ext"
        elif e.type in (0x17, 0x07):
            r = sprite_chunks(e.uid, d)
            k = "sprite"
        elif e.type == 0x18:
            r = font_glyphs(e.uid, d)
            k = "font"
        else:
            continue
        if r:
            yield e, k, r
