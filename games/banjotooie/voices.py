"""Placeholder voices (Piper TTS, our own performances) for Banjo-Tooie's voice-like sound effects.

The decomp names no sound effects, so the slots are the ones games/banjotooie/practice.py found
(voice_slots.json: sound index, wave offset, pitch group). Each gets short gibberish spoken by a stock
TTS voice chosen by pitch group, pitched by a speed change and fitted to the slot's length. No real
performer is imitated and nothing is trained on retail audio. To use your own take, save it as
games/banjotooie/voices/<sfx index>.wav (mono, any rate/length) and run `apply`.

    python -m games.banjotooie.voices build <spec dir>          -> voices/<sfx>.wav (placeholders; keeps existing files)
    python -m games.banjotooie.voices apply <spec dir> <sound dir>   re-encode only those waves into ctl.bin / tbl.bin
"""
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voices")
PIPER = os.environ.get("PIPER_VOICES", "C:/Users/andre/n64work/piper_voices")
# pitch group -> (piper model, semitones up, speaking length scale)
CAST = {"LOW": ("en_US-joe-medium", -1, 1.0), "MID": ("en_US-ryan-high", 3, 0.9), "HIGH": ("en_US-amy-medium", 8, 0.8)}
GIBBERISH = ["guh huh", "ah hah", "buh duh", "ooh ah", "heh huh", "oh eh", "wuh huh", "ha huh", "yeh", "woah", "hey", "uh oh",
             "bah", "doh", "eek", "aha", "mm hm", "nah", "oi", "whee"]
_V = {}


def slots():
    return json.load(open(os.path.join(HERE, "voice_slots.json")))


def speak(who, text, n, rate):
    import librosa
    from piper import PiperVoice, SynthesisConfig
    model, semi, length = CAST[who]
    if model not in _V:
        _V[model] = PiperVoice.load(os.path.join(PIPER, model + ".onnx"))
    v = _V[model]
    f = 2 ** (semi / 12)
    cfg = SynthesisConfig(length_scale=length * f, noise_scale=0.8, noise_w_scale=0.9)
    x = np.concatenate([c.audio_float_array for c in v.synthesize(text + "!", syn_config=cfg)]).astype(np.float32)
    x = librosa.resample(x, orig_sr=v.config.sample_rate * f, target_sr=rate).astype(np.float32)
    return fit(x, n)


def fit(x, n):
    import librosa
    nz = np.nonzero(np.abs(x) > 0.01)[0]
    if len(nz):
        x = x[max(0, nz[0] - 200):nz[-1] + 400]
    if len(x) > n:                                    # speed up to fit the slot
        x = librosa.effects.time_stretch(x, rate=len(x) / n * 1.02)[:n]
    x = np.pad(x, (0, n - len(x)))
    fade = min(256, n // 8)
    if fade:
        x[-fade:] *= np.linspace(1, 0, fade)
    return x / max(1e-3, np.abs(x).max()) * 0.8


def build(spec_dir):
    S = json.load(open(os.path.join(spec_dir, "sound/samples.json")))["waves"]
    os.makedirs(OUT, exist_ok=True)
    made = kept = 0
    for s in slots():
        p = os.path.join(OUT, f"{s['sfx']}.wav")
        if os.path.exists(p):
            kept += 1
            continue
        d = S[str(s["base"])]
        x = speak(s["who"], GIBBERISH[s["sfx"] % len(GIBBERISH)], d["nframes"], d["rate"])
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(d["rate"])
            w.writeframes((x * 32767).astype("<i2").tobytes())
        made += 1
    print(f"voices: {made} placeholder lines made, {kept} existing files kept -> {OUT}")


def override(base, d):
    """audio.build hook: the wave for a voice slot (resampled and fitted), or None."""
    k = _BY_BASE().get(base)
    p = os.path.join(OUT, f"{k}.wav")
    if k is None or not os.path.exists(p):
        return None
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(1)
        sr = w.getframerate()
    if sr != d["rate"]:
        import librosa
        x = librosa.resample(x, orig_sr=sr, target_sr=d["rate"])
    return fit(x, d["nframes"]) if len(x) != d["nframes"] else x


_B = None


def _BY_BASE():
    global _B
    if _B is None:
        _B = {s["base"]: s["sfx"] for s in slots()}
    return _B


def apply(spec_dir, sound_dir):
    from games.banjotooie import audio
    prev = (open(os.path.join(sound_dir, "ctl.bin"), "rb").read(), open(os.path.join(sound_dir, "tbl.bin"), "rb").read())
    ctl, tbl = audio.build(spec_dir, override, only=set(_BY_BASE()), prev=prev)
    open(os.path.join(sound_dir, "ctl.bin"), "wb").write(ctl)
    open(os.path.join(sound_dir, "tbl.bin"), "wb").write(tbl)
    print(f"voices applied: {len(_BY_BASE())} waves re-encoded in {sound_dir}")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2])
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], sys.argv[3])
