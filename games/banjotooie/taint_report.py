"""DIRTY-ROOM CHECK: clean ROM vs retail ROM, over the regenerated data.

    python -m games.banjotooie.taint_report <retail.z64> <clean.z64> [--no-audio]
Retail expressive streams: every model / external texture, sprite chunk and font glyph region
(palette, pixels, mip tail: raw, and decoded to RGBA), the sound tbl (raw ADPCM and decoded PCM) and
the ADPCM books / loop states of the ctl. Clean streams: the same regions of the clean ROM.
Any shared run of >= 32 bytes (cleanroom.taint.FAIL_RUN) fails. Kept facts (code, geometry,
animation, text, sequences) are not scanned.
"""
import sys

from cleanroom import taint
from cleanroom.audio import vadpcm
from games.banjotooie import assetfs as A, audio, formats as F


def regions(es):
    """(label, bytes, is_rgba)"""
    for e, kind, rs in F.all_regions(es):
        d = e.data
        seen = set()
        for n, r in enumerate(rs):
            k = f"{r['key']}#{n}"
            for name in ("pal", "pix", "tail"):
                an = r.get(name)
                if an and an[1] and (name, an) not in seen:
                    seen.add((name, an))
                    yield f"{k}.{name}", bytes(d[an[0]:an[0] + an[1]]), False
            yield k + ".rgba", F.decode_region(d, r).tobytes(), True


def pcm_streams(rom):
    ctl, tbl = rom[audio.CTL_ROM:audio.TBL_ROM], rom[audio.TBL_ROM:audio.TBL_END]
    _, _, offs = audio.layout(ctl)
    seen = set()
    for o in offs:
        s = audio.sound(ctl, o)
        yield f"book@{o:x}", bytes(ctl[o + audio.O_STATE:o + audio.O_STATE + 32]) + bytes(ctl[o + audio.O_COEF:o + audio.O_COEF + 128])
        if s["base"] in seen:
            continue
        seen.add(s["base"])
        seg = tbl[s["base"]:s["base"] + s["len"] // 9 * 9]
        yield f"adpcm@{s['base']:x}", bytes(seg)
        if any(s["book"]):
            yield f"wave@{s['base']:x}", vadpcm.decode(seg, s, s["len"] // 9 * 16).astype("<i2").tobytes()


def main(argv):
    ret = open(argv[1], "rb").read()
    cl = open(argv[2], "rb").read()
    rr, cr = list(regions(A.parse(ret))), list(regions(A.parse(cl)))
    hits = taint.scan(taint.build_index(s for _, s, g in rr if not g), ((k, s) for k, s, g in cr if not g))
    hits += taint.scan(taint.build_index((s for _, s, g in rr if g), unit=4), ((k, s) for k, s, g in cr if g), unit=4)
    ahits = []
    if "--no-audio" not in argv:
        ahits = taint.scan(taint.build_index(s for _, s in pcm_streams(ret)), pcm_streams(cl))
    fail = [h for h in hits + ahits if h[3] >= taint.FAIL_RUN]
    print(f"taint: textures {len(cr)} streams, {len(hits)} with any shared window; audio {len(ahits)}; "
          f"FAILING (>= {taint.FAIL_RUN} B run): {len(fail)}")
    for h in sorted(fail, key=lambda h: -h[3])[:12]:
        print("  ", h)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
