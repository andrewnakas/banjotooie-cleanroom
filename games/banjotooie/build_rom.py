"""CLEAN ROOM: spec -> clean ROM.

    python -m games.banjotooie.build_rom <spec dir> <out.z64> [--no-audio] [--only 0x639,0x64e]
ROM = rom_kept.bin (header, IPL3, code, overlays: kept facts, identical to what the matching decomp
builds) + the asset filesystem rebuilt from generated assets (generate.py) + the sound bank built
from the spec (audio.py), then the header checksum (CIC-6105) is recomputed.
The asset table sits at a fixed ROM address and the sound bank follows the assets, so the rebuilt
filesystem must fit the retail region (build fails otherwise).
"""
import os
import struct
import sys
import time

from games.banjotooie import assetfs as A, generate

M32 = 0xFFFFFFFF
CTL, TBL, TBL_END = 0x1A14580, 0x1A46560, 0x1E29B60


def cic6105_crc(rom):
    t1 = t2 = t3 = t4 = t5 = t6 = 0xDF26F436
    words = struct.unpack(">%dI" % (0x100000 // 4), bytes(rom[0x1000:0x101000]))
    ipl = struct.unpack(">64I", bytes(rom[0x40 + 0x710:0x40 + 0x710 + 256]))
    for i, d in enumerate(words):
        if (t6 + d) & M32 < t6:
            t4 = (t4 + 1) & M32
        t6 = (t6 + d) & M32
        t3 ^= d
        sh = d & 0x1F
        r = ((d << sh) | (d >> (32 - sh))) & M32 if sh else d
        t5 = (t5 + r) & M32
        t2 ^= r if t2 > d else (t6 ^ d)
        t1 = (t1 + (ipl[i & 0x3F] ^ d)) & M32
    return t6 ^ t4 ^ t3, t5 ^ t2 ^ t1


def assemble(kept, entries, ctl=None, tbl=None):
    rom = bytearray(kept)
    blob, used = A.build(entries)
    rom[A.TABLE:A.END] = blob
    if ctl is not None:
        assert len(ctl) == TBL - CTL and len(tbl) == TBL_END - TBL, (len(ctl), len(tbl))
        rom[CTL:TBL] = ctl
        rom[TBL:TBL_END] = tbl
    c1, c2 = cic6105_crc(rom)
    rom[0x10:0x18] = struct.pack(">II", c1, c2)
    return rom, used


def main(argv):
    spec, dst = argv[1], argv[2]
    t = time.time()
    only = None
    if "--only" in argv:
        only = {int(x, 16) for x in argv[argv.index("--only") + 1].split(",")}
    es = generate.build_entries(spec, only)
    print(f"assets: {sum(bool(e.raw) for e in es)} generated ({time.time() - t:.0f}s)", flush=True)
    ctl = tbl = None
    if "--no-audio" not in argv:
        from games.banjotooie import audio
        sd = os.path.join(os.path.dirname(dst), "sound")
        if os.path.exists(os.path.join(sd, "ctl.bin")) and "--audio" not in argv:
            ctl, tbl = open(os.path.join(sd, "ctl.bin"), "rb").read(), open(os.path.join(sd, "tbl.bin"), "rb").read()
        else:
            ctl, tbl = audio.build(spec)
    kept = open(os.path.join(spec, "rom_kept.bin"), "rb").read()
    rom, used = assemble(kept, es, ctl, tbl)
    open(dst, "wb").write(rom)
    print(f"rom: {dst} assets {used / 1e6:.2f} of {(A.END - A.TABLE) / 1e6:.2f} MB, audio {'yes' if ctl else 'SILENT'}, "
          f"crc {rom[0x10:0x18].hex()} ({time.time() - t:.0f}s)")


if __name__ == "__main__":
    main(sys.argv)
