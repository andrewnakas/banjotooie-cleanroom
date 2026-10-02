"""Banjo-Tooie sound bank (Rare's packed, pointer-free variant of the libultra ALBank; ONE bank).

ROM (USA): ctl 0x1A14580..0x1A46560 (0x31FE0 bytes), tbl 0x1A46560..0x1E29B60 (0x3E3600 bytes).
MIDI sequences are separate assets and are not handled here.  All values big-endian.

ctl layout (no pointers: everything is found by index)
  0x000  header, 8 bytes:   u16 instrument count (119), u16 0, u32 sample rate (22050)
  0x008  119 instrument records, 18 bytes each (= ALInstrument without the sound pointers):
           +0 u8 volume  +1 u8 pan  +2 u8 priority  +3 u8 flags
           +4 4 x u8 tremolo (type, rate, depth, delay)   +8 4 x u8 vibrato (same)
           +12 s16 bend range (200)   +14 u16 sound count   +16 u16 index of first sound
         (instrument 0 = the 695 sound effects; counts sum to 938, ranges are consecutive)
  0x866  938 sound records, 216 bytes each (ALSound + ALEnvelope + ALKeyMap + ALWaveTable +
         ALADPCMloop + ALADPCMBook flattened into one fixed record):
           +0   u16 0 (pad)
           +2   s32 attack time (us; always 0)   +6 s32 decay time (us; -1 = hold, on looped notes)
           +10  s32 release time (us)            +14 u8 attack volume   +15 u8 decay volume
           +16  u16 0 (pad)
           +18  keymap: u8 velocity min, u8 velocity max, u8 key min, u8 key max, u8 key base, s8 detune
           +24  u16 0 (pad)
           +26  u32 wave offset in tbl           +30 u32 wave length in bytes
           +34  loop: u32 start, u32 end (samples), u32 count (0 = no loop, 0xFFFFFFFF = forever)
           +46  s16[16] ADPCM loop state (garbage/uninitialised when the sound does not loop)
           +78  s32 predictor order (always 2)
           +82  s16[64] ADPCM book: 4 predictors x order 2 x 8 taps
           +210 s32 predictor count (always 4)
           +214 u8 sample pan   +215 u8 sample volume
  0x31FD6  10 zero bytes (pad to 16)
  The keymap byte order and the pad fields are inferred from value statistics (not from code); they are
  only kept verbatim, never interpreted here.

tbl: VADPCM, 9-byte frames (16 samples).  827 distinct waves (938 sounds; shared waves always have the
  same length), each starting on an 8-byte boundary, no overlaps.  About half of the lengths are 9k+1:
  one stray byte after the last frame.  Frames = len // 9.  Bytes between waves are alignment padding.

Dirty room:  python -m games.banjotooie.audio spec <rom> <spec dir>
  -> <spec>/sound/ctl.bin (all 938 books and loop states zeroed, everything else kept) and
     <spec>/sound/samples.json {"tbl_len", "ctl_len", "waves": {tbl offset: {len, nframes, rate, desc,
     f0?, loop [start, end, count]?, books [ctl offsets of the s32 order field; s16 book at +4, s32 npred
     at +132], loops [ctl offsets of the loop start field; state at +12; only looping sounds],
     order, npred}}}
Clean room:  build(spec_dir, overrides=None) -> (ctl, tbl); python -m games.banjotooie.audio build <spec> <out>
  every wave resynthesised from its outline, encoded with our own 4-predictor book, loop states from our
  data; tbl bytes outside waves are zero.
Dev check:   python -m games.banjotooie.audio check <rom> <out dir>
"""
import json
import os
import struct
import sys

import numpy as np

from cleanroom.audio import descriptor, vadpcm
from cleanroom.audio.pitch import median_f0
from cleanroom.decomp import gen

CTL_ROM, TBL_ROM, TBL_END = 0x1A14580, 0x1A46560, 0x1E29B60
CTL_LEN, TBL_LEN = TBL_ROM - CTL_ROM, TBL_END - TBL_ROM
HDR, INST, SND = 8, 18, 216
O_WAVE, O_LOOP, O_STATE, O_BOOK, O_COEF, O_NPRED = 26, 34, 46, 78, 82, 210


def layout(ctl):
    """-> (rate, [instrument dicts], [sound record offsets])."""
    ninst, _, rate = struct.unpack_from(">HHI", ctl, 0)
    insts, nsnd = [], 0
    for i in range(ninst):
        f = struct.unpack_from(">12BhHH", ctl, HDR + INST * i)
        insts.append({"volume": f[0], "pan": f[1], "priority": f[2], "flags": f[3], "trem": list(f[4:8]),
                      "vib": list(f[8:12]), "bend": f[12], "count": f[13], "first": f[14]})
        nsnd = max(nsnd, f[13] + f[14])
    s0 = HDR + INST * ninst
    assert s0 + SND * nsnd <= len(ctl) < s0 + SND * nsnd + 16, "unexpected ctl layout"
    return rate, insts, [s0 + SND * i for i in range(nsnd)]


def sound(ctl, o):
    base, ln, st, en, cnt = struct.unpack_from(">5I", ctl, o + O_WAVE)
    order, = struct.unpack_from(">i", ctl, o + O_BOOK)
    npred, = struct.unpack_from(">i", ctl, o + O_NPRED)
    return {"base": base, "len": ln, "loop": (st, en, cnt), "order": order, "npred": npred,
            "book": list(struct.unpack_from(">%dh" % (16 * npred), ctl, o + O_COEF))}


def k_predictors(x, k=4):
    """Our own predictor set: k-means over per-16-sample 2nd-order LPC fits."""
    fits = []
    for s in range(2, len(x) - 16, 16):
        y, p1, p2 = x[s:s + 16], x[s - 1:s + 15], x[s - 2:s + 14]
        if (y ** 2).sum() < 1e3:
            continue
        a, *_ = np.linalg.lstsq(np.stack([p1, p2], 1), y, rcond=None)
        fits.append(a)
    base = [(1.0, 0.0), (1.8, -0.82), (0.5, 0.0), (1.4, -0.5)]
    if len(fits) < k:
        return base[:k]
    f = np.clip(np.asarray(fits), [-1.95, -0.98], [1.95, 0.98])
    c = f[np.linspace(0, len(f) - 1, k).astype(int)]
    c = c[np.argsort(c[:, 0])].copy()
    for _ in range(12):
        lab = np.argmin(((f[:, None, :] - c[None]) ** 2).sum(-1), 1)
        for j in range(k):
            if (lab == j).any():
                c[j] = f[lab == j].mean(0)
    out = []
    for a1, a2 in c:
        a2 = float(np.clip(a2, -0.98, 0.98))
        out.append((float(np.clip(a1, -(1 - a2) + 0.02, (1 - a2) - 0.02)), a2))
    return out


def _regions(rom):
    with open(rom, "rb") as f:
        f.seek(CTL_ROM)
        return bytearray(f.read(CTL_LEN)), f.read(TBL_LEN)


def spec(rom, out):
    ctl, tbl = _regions(rom)
    rate, insts, offs = layout(ctl)
    os.makedirs(os.path.join(out, "sound"), exist_ok=True)
    by = {}
    for o in offs:
        by.setdefault(sound(ctl, o)["base"], []).append(o)
    facts, cov, nloop, clip, bad, end, overlap = {}, bytearray(len(tbl)), 0, 0, [], 0, 0
    for n, base in enumerate(sorted(by)):
        ss = [sound(ctl, o) for o in by[base]]
        s = ss[0]
        assert all(x["len"] == s["len"] and (x["order"], x["npred"]) == (2, 4) for x in ss), hex(base)
        overlap += base < end
        end = base + s["len"]
        cov[base:end] = b"\1" * s["len"]
        nf = s["len"] // 9 * 16
        pcm = vadpcm.decode(tbl[base:base + s["len"] // 9 * 9], s, nf)
        clip += int((np.abs(pcm.astype(np.int32)) >= 32767).sum())
        pcm = pcm.astype(np.float64)
        loops = [o for o, x in zip(by[base], ss) if x["loop"][2]]
        d = {"len": s["len"], "nframes": nf, "rate": rate, "desc": descriptor.describe(pcm, rate),
             "books": [o + O_BOOK for o in by[base]], "loops": [o + O_LOOP for o in loops],
             "order": s["order"], "npred": s["npred"]}
        if loops:
            lp = sound(ctl, loops[0])["loop"]
            d["loop"] = list(lp)
            nloop += len(loops)
            if not lp[0] < lp[1] <= nf:
                bad.append(base)
        f0 = median_f0((pcm / 32768).astype(np.float32), rate)
        if f0:
            d["f0"] = round(f0, 1)
        facts[base] = d
        if n % 200 == 0:
            print(f"  spec {n}/{len(by)}", flush=True)
    for o in offs:                             # retail-derived data: books and loop states (all records)
        ctl[o + O_STATE:o + O_STATE + 32] = bytes(32)
        ctl[o + O_COEF:o + O_COEF + 128] = bytes(128)
    stray = sum(1 for i in range(len(tbl)) if not cov[i] and tbl[i])
    open(os.path.join(out, "sound/ctl.bin"), "wb").write(ctl)
    json.dump({"tbl_len": len(tbl), "ctl_len": len(ctl), "waves": facts},
              open(os.path.join(out, "sound/samples.json"), "w"))
    c = sum(cov)
    print(f"bt sound: {len(insts)} insts, {len(offs)} sounds, {len(facts)} waves, {len(offs)} books zeroed, "
          f"{nloop} loops; tbl {c}/{len(tbl)} B covered ({len(tbl) - c} gap, {stray} nonzero), "
          f"{overlap} overlaps, {clip} clipped samples, {len(bad)} loops out of range")


def build(spec_dir, overrides=None, progress=False, only=None, prev=None):
    """only + prev=(ctl, tbl): re-encode just the waves whose tbl offset is in `only` into a previous build."""
    S = json.load(open(os.path.join(spec_dir, "sound/samples.json")))
    if prev:
        ctl, tbl = bytearray(prev[0]), bytearray(prev[1])
    else:
        ctl = bytearray(open(os.path.join(spec_dir, "sound/ctl.bin"), "rb").read())
        tbl = bytearray(S["tbl_len"])
    for i, (key, d) in enumerate(S["waves"].items()):
        base = int(key)
        if only is not None and base not in only:
            continue
        nf = d["nframes"]
        x = overrides(base, d) if overrides else None
        if x is None:
            x = descriptor.synthesize(d["desc"], nf, d["rate"], seed=gen.h32("bt", base))
        x = np.pad(np.asarray(x, np.float32)[:nf], (0, max(0, nf - len(x))))
        if "loop" in d:
            st, en, cnt = d["loop"]
            if cnt and en > st + 16:
                x = descriptor.make_loop_seamless(x, st, min(en, nf))
        dither = np.random.default_rng(gen.h32("dither", "bt", base)).integers(-1, 2, nf)
        pcm = np.clip(np.round(np.clip(x, -1, 1) * 30000) + dither, -32768, 32767).astype(np.int16)
        book = vadpcm.make_book(k_predictors(pcm.astype(np.float64), d["npred"]))
        assert (book["order"], book["npred"]) == (d["order"], d["npred"])
        data, _, dec = vadpcm.encode(pcm, book)
        n = d["len"] // 9 * 9                   # a stray byte after the last frame stays zero
        tbl[base:base + n] = bytes(data[:n]) + bytes(max(0, n - len(data)))
        vals = struct.pack(">%dh" % len(book["book"]), *book["book"])
        for bo in d["books"]:
            assert struct.unpack_from(">i", ctl, bo)[0] == book["order"]
            assert struct.unpack_from(">i", ctl, bo + 4 + len(vals))[0] == book["npred"]
            ctl[bo + 4:bo + 4 + len(vals)] = vals
        for lo in d["loops"]:                   # each sound's own loop start (kept in the ctl)
            start = struct.unpack_from(">I", ctl, lo)[0]
            ctl[lo + 12:lo + 44] = struct.pack(">16h", *[int(v) for v in vadpcm.loop_state(dec, min(start, nf))])
        if progress and i % 100 == 0:
            print(f"  build {i}/{len(S['waves'])}", flush=True)
    assert len(ctl) == S["ctl_len"] and len(tbl) == S["tbl_len"]
    return bytes(ctl), bytes(tbl)


def check(rom, out):
    rctl, rtbl = _regions(rom)
    ctl = open(os.path.join(out, "ctl.bin"), "rb").read()
    tbl = open(os.path.join(out, "tbl.bin"), "rb").read()
    rate, insts, offs = layout(ctl)
    ok = np.zeros(len(ctl), bool)
    for o in offs:
        ok[o + O_STATE:o + O_STATE + 32] = True
        ok[o + O_COEF:o + O_COEF + 128] = True
    diff = np.frombuffer(ctl, np.uint8) != np.frombuffer(bytes(rctl), np.uint8) if len(ctl) == len(rctl) else None
    a = diff is not None and not (diff & ~ok).any()
    b = len(tbl) == len(rtbl) == TBL_LEN
    same = 0                                    # 9-byte frames identical to retail at the same place
    seen, res = set(), []
    for o in offs:
        s = sound(ctl, o)
        if s["base"] in seen:
            continue
        seen.add(s["base"])
        seg, rseg = tbl[s["base"]:s["base"] + s["len"]], rtbl[s["base"]:s["base"] + s["len"]]
        same += sum(1 for f in range(0, len(seg) - 8, 9) if seg[f:f + 9] == rseg[f:f + 9] and any(seg[f:f + 9]))
        if len(seen) % 60 == 1:
            pcm = vadpcm.decode(seg[:s["len"] // 9 * 9], s).astype(np.float64)
            res.append((int((np.abs(pcm) >= 32767).sum()), float(np.sqrt((pcm ** 2).mean()))))
    rms = [r for _, r in res]
    c = all(n == 0 for n, _ in res) and all(20 < r < 25000 for r in rms)
    print(f"check: ctl diff only in books/states {'OK' if a else 'FAIL'} ({int(diff.sum()) if diff is not None else -1} B differ), "
          f"tbl size {'OK' if b else 'FAIL'}, {len(res)} waves redecoded {'OK' if c else 'FAIL'} "
          f"(clip {sum(n for n, _ in res)}, rms {min(rms):.0f}..{max(rms):.0f}), {same} nonzero frames equal to retail")
    return a and b and c


if __name__ == "__main__":
    if sys.argv[1] == "spec":
        spec(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "build":
        c, t = build(sys.argv[2], progress=True)
        os.makedirs(sys.argv[3], exist_ok=True)
        open(os.path.join(sys.argv[3], "ctl.bin"), "wb").write(c)
        open(os.path.join(sys.argv[3], "tbl.bin"), "wb").write(t)
        print(f"bt sound built: ctl {len(c)} B, tbl {len(t)} B, {sum(1 for b in t if b)} nonzero tbl bytes")
    elif sys.argv[1] == "check":
        sys.exit(0 if check(sys.argv[2], sys.argv[3]) else 1)
