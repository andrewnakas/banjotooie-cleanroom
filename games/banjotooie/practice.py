"""Practice pack for recording Banjo-Tooie's voice-like sound effects (PERSONAL USE: made from your own
ROM, written outside the repo, never published).

    python -m games.banjotooie.practice <rom.z64> <out dir>
The decomp has no sound-effect names, so voice slots are found by ear-like measures on instrument 0
(the 695 sound effects): 0.25-2.5 s, not looped, mostly voiced (pYIN), pitch that moves like speech.
They are grouped by median pitch into LOW / MID / HIGH voices (the cast is not known per slot).
Writes clips/<nn>_sfx<idx>.wav, practice_<who>_call_and_response.wav (clip, 0.3 s, 80 ms 880 Hz beep,
gap 1.5x + 1.5 s), SCRIPT.txt with `== <who>` sections, and games/banjotooie/voice_slots.json
(labels only: sound index, wave offset, group, seconds).
"""
import json
import os
import sys
import wave

import numpy as np

from cleanroom.audio import vadpcm
from games.banjotooie import audio

HZ = 22050


def wr(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(HZ)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main(argv):
    import librosa
    rom, out = argv[1], argv[2]
    ctl, tbl = audio._regions(rom)
    rate, insts, offs = audio.layout(ctl)
    os.makedirs(os.path.join(out, "clips"), exist_ok=True)
    found, seen = [], set()
    for idx in range(insts[0]["first"], insts[0]["first"] + insts[0]["count"]):
        s = audio.sound(ctl, offs[idx])
        dur = s["len"] // 9 * 16 / rate
        if s["base"] in seen or s["loop"][2] or not 0.25 <= dur <= 2.5:
            continue
        seen.add(s["base"])
        x = vadpcm.decode(tbl[s["base"]:s["base"] + s["len"] // 9 * 9], s, s["len"] // 9 * 16).astype(np.float32) / 32768
        f0, voiced, _ = librosa.pyin(x, fmin=80, fmax=1000, sr=rate, frame_length=1024)
        loud = librosa.feature.rms(y=x, frame_length=1024, hop_length=256)[0][:len(voiced)] > 0.02
        if loud.sum() < 8:
            continue
        v = voiced[:len(loud)] & loud
        if v.sum() / loud.sum() < 0.6:
            continue
        f = f0[:len(loud)][v]
        med, spread = float(np.median(f)), float(np.percentile(f, 90) / np.percentile(f, 10))
        if spread < 1.15 or not 90 <= med <= 900:
            continue
        who = "LOW" if med < 180 else "MID" if med < 350 else "HIGH"
        found.append({"sfx": idx, "base": s["base"], "who": who, "sec": round(dur, 2), "f0": round(med)})
        if rate != HZ:
            x = np.interp(np.arange(0, len(x) * HZ / rate) * rate / HZ, np.arange(len(x)), x).astype(np.float32)
        found[-1]["_x"] = x
    beep = (0.2 * np.sin(2 * np.pi * 880 * np.arange(int(0.08 * HZ)) / HZ)).astype(np.float32)
    lines = ["Banjo-Tooie voice practice script (personal use; never publish these clips).",
             "Play practice_<who>_call_and_response.wav and repeat each sound after the beep, in character.",
             "Slots were picked automatically: skip anything that is not a voice.", ""]
    n = 0
    for who in ("LOW", "MID", "HIGH"):
        items = [f for f in found if f["who"] == who]
        if not items:
            continue
        lines.append(f"== {who}")
        parts = []
        for f in items:
            n += 1
            x = f.pop("_x")
            wr(os.path.join(out, "clips", f"{n:03d}_sfx{f['sfx']}.wav"), x)
            parts += [x, np.zeros(int(0.3 * HZ), np.float32), beep, np.zeros(int((len(x) / HZ * 1.5 + 1.5) * HZ), np.float32)]
            lines.append(f"{n:03d}  sfx{f['sfx']:<4d} max {f['sec']:.1f}s  pitch ~{f['f0']} Hz  (imitate the sound)")
        wr(os.path.join(out, f"practice_{who}_call_and_response.wav"), np.concatenate(parts))
        lines.append("")
    open(os.path.join(out, "SCRIPT.txt"), "w", encoding="utf8").write("\n".join(lines))
    json.dump(found, open(os.path.join(os.path.dirname(__file__), "voice_slots.json"), "w"), indent=0)
    c = {w: sum(1 for f in found if f["who"] == w) for w in ("LOW", "MID", "HIGH")}
    print(f"practice: {len(found)} voice-like slots {c}, {sum(f['sec'] for f in found):.0f} s of clips -> {out}")


if __name__ == "__main__":
    main(sys.argv)
