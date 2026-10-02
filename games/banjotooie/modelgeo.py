"""Banjo-Tooie model geometry: which triangles (positions + texture coordinates) use each texture.

Model file (magic 0xB): s32 at 0xC = display list block (u32 count, u32 pad, F3DEX2 commands),
s32 at 0x10 = vertex block (0x18-byte header, then 16-byte Vtx), u16 at 8 = texture list.
Segments: 1 = vertices, 2 = texture data, 3 = this display list. F3DEX2: G_VTX 0x01, G_TRI1 0x05,
G_TRI2 0x06, G_DL 0xDE, G_ENDDL 0xDF, G_TEXTURE 0xD7, G_GEOMETRYMODE 0xD9, G_SETTIMG 0xFD.

    tris_by_texture(model_bytes, all_tris=None) -> {texture index: [((x,y,z)*3, (s,t)*3), ...]}
        all_tris (a list) also receives every triangle: (pos*3, st*3, rgba*3, texture index or None, lit)
s,t are in texels (the Vtx's 10.5 fixed point / 32, times the G_TEXTURE scale).
"""
import struct

from games.banjotooie import formats as F


def textures(d):
    """[{i, w, h}] for the model's texture list (inline or external)."""
    _, _, _, infos = F.tex_list(d)
    return [{"i": i, "w": w or 256, "h": h or 256, "type": typ} for i, (off, typ, w, h) in enumerate(infos)]


def tris_by_texture(d, all_tris=None):
    if len(d) < 0x38 or struct.unpack_from(">I", d, 0)[0] != 0xB:
        return {}
    gfx = struct.unpack_from(">i", d, 0xC)[0]
    vtx = struct.unpack_from(">i", d, 0x10)[0]
    if gfx <= 0 or vtx <= 0:
        return {}
    flags, _, _, infos = F.tex_list(d)
    offs = {}
    acc = 0
    for i, (off, typ, w, h) in enumerate(infos):
        if flags & 0x100:                       # external: textures are concatenated in list order
            off = acc
            fs = F.MODEL_TYPES.get(typ & 0xFF)
            n = 0
            if fs:
                n = (w or 256) * (h or 256) * F.BITS[fs[1]] // 8 + ((0x20 if fs[1] == 0 else 0x200) if fs[0] == 2 else 0)
                if typ & 0x8000:
                    n += n // 2
            acc += n
        offs.setdefault(off, i)
        if typ & 1:
            offs.setdefault(off + 0x20, i)      # CI4: pixels follow the 16-colour palette
        if typ & 2:
            offs.setdefault(off + 0x200, i)     # CI8
    vbase = vtx + 0x18
    gbase = gfx + 8
    ncmd = struct.unpack_from(">I", d, gfx)[0]
    out = {}
    cache = [None] * 64
    cur = [None]
    scale = [1.0, 1.0]
    textured = [True]
    lit = [False]

    def run(pc):
        while 0 <= pc < ncmd * 8 and gbase + pc + 8 <= len(d):
            w0, w1 = struct.unpack_from(">II", d, gbase + pc)
            op = w0 >> 24
            pc += 8
            if op == 0x01:
                n = (w0 >> 12) & 0xFF
                v0 = ((w0 >> 1) & 0x7F) - n
                a = (w1 & 0xFFFFFF) // 16
                for k in range(n):
                    if 0 <= v0 + k < 64 and vbase + 16 * (a + k) + 16 <= len(d):
                        x, y, z, fl, s, t = struct.unpack_from(">hhhHhh", d, vbase + 16 * (a + k))
                        col = tuple(d[vbase + 16 * (a + k) + 12:vbase + 16 * (a + k) + 16])
                        cache[v0 + k] = ((x, y, z), (s / 32.0 * scale[0], t / 32.0 * scale[1]), col)
            elif op in (0x05, 0x06, 0x07):
                ids = [(w0 >> 16) & 0xFF, (w0 >> 8) & 0xFF, w0 & 0xFF]
                if op != 0x05:
                    ids += [(w1 >> 16) & 0xFF, (w1 >> 8) & 0xFF, w1 & 0xFF]
                ids = [i // 2 for i in ids]
                for j in range(0, len(ids), 3):
                    vs = [cache[i] if i < 64 else None for i in ids[j:j + 3]]
                    if all(vs):
                        if cur[0] is not None:
                            out.setdefault(cur[0], []).append(([v[0] for v in vs], [v[1] for v in vs]))
                        if all_tris is not None:
                            all_tris.append(([v[0] for v in vs], [v[1] for v in vs], [v[2] for v in vs],
                                             cur[0] if textured[0] else None, lit[0]))
            elif op == 0xD9:                      # G_GEOMETRYMODE: clear ~w0, set w1 (G_LIGHTING = 0x20000)
                if w1 & 0x20000:
                    lit[0] = True
                elif not (w0 & 0x20000):
                    lit[0] = False
            elif op == 0xD7:                      # G_TEXTURE
                scale[0] = max(1, w1 >> 16) / 65536.0
                scale[1] = max(1, w1 & 0xFFFF) / 65536.0
                textured[0] = bool(w0 & 0xFF)
            elif op == 0xFD:
                seg, off = w1 >> 24, w1 & 0xFFFFFF
                cur[0] = offs.get(off) if seg == 2 else None
            elif op == 0xDE:
                if (w0 >> 16) & 0xFF == 1:
                    return
            elif op == 0xDF:
                return

    pc = 0
    while pc < ncmd * 8:                          # chunks are called from the geo layout: walk them all
        run(pc)
        while pc < ncmd * 8 and struct.unpack_from(">I", d, gbase + pc)[0] >> 24 != 0xDF:
            pc += 8
        pc += 8
    return out
