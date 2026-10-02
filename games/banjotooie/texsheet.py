"""Dev tool: contact sheet of textures / sprite frames / glyphs from a ROM (dirty or clean).

    python -m games.banjotooie.texsheet <rom.z64> <out.png> [--kind model|ext|sprite|font] [--uids 0x2d1,..]
        [--start N] [--n 320] [--first] [--minpx 0] [--cell 64]
--first: only the first frame / texture of each asset. Each tile is labelled with its key.
"""
import sys

import numpy as np
from PIL import Image, ImageDraw

from games.banjotooie import assetfs as A, formats as F


def tiles(es, kind, uids, first, minpx):
    for e, k, rs in F.all_regions(es):
        if k != kind or (uids and e.uid not in uids):
            continue
        if k == "sprite":
            for f in sorted(set(r["frame"] for r in rs)):
                fr = [r for r in rs if r["frame"] == f]
                yield fr[0]["key"], F.compose(e.data, fr)
                if first:
                    break
        else:
            for r in rs:
                if r["w"] * r["h"] >= minpx:
                    yield r["key"], F.decode_region(e.data, r)
                    if first:
                        break


def sheet(items, out, cell=64, cols=20):
    rows = (len(items) + cols - 1) // cols
    im = Image.new("RGB", (cols * (cell + 4), rows * (cell + 12)), (40, 40, 40))
    dr = ImageDraw.Draw(im)
    for k, (lab, px) in enumerate(items):
        h, w = px.shape[:2]
        s = min(cell / w, cell / h)
        t = Image.fromarray(np.ascontiguousarray(px), "RGBA").resize((max(1, int(w * s)), max(1, int(h * s))), Image.NEAREST)
        chk = np.indices(t.size[::-1]).sum(0) // 4 % 2
        bg = Image.fromarray(np.dstack([np.where(chk, 110, 150).astype(np.uint8)] * 3 + [np.full(chk.shape, 255, np.uint8)]), "RGBA")
        bg.alpha_composite(t)
        x, y = (k % cols) * (cell + 4), (k // cols) * (cell + 12)
        im.paste(bg.convert("RGB"), (x + 2, y + 1))
        dr.text((x + 1, y + cell), lab[1:], fill=(255, 255, 0))
    im.save(out)
    print(f"{len(items)} tiles -> {out}")


def main(argv):
    opt = lambda n, d=None: argv[argv.index(n) + 1] if n in argv else d
    es = A.parse(open(argv[1], "rb").read())
    uids = {int(x, 16) for x in opt("--uids").split(",")} if "--uids" in argv else None
    start, n = int(opt("--start", 0)), int(opt("--n", 320))
    got = list(tiles(es, opt("--kind", "model"), uids, "--first" in argv, int(opt("--minpx", 0))))
    print(f"{len(got)} total")
    sheet(got[start:start + n], argv[2], int(opt("--cell", 64)))


if __name__ == "__main__":
    main(sys.argv)
