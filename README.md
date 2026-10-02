# Banjo-Tooie — clean room

Play: https://andrewnakas.github.io/banjotooie-cleanroom/

A web build of Banjo-Tooie where the game code is the one built by the
[Mr-Wiseguy/banjo-tooie](https://github.com/Mr-Wiseguy/banjo-tooie) matching decompilation and
**every texture, sprite, font and sound sample is regenerated** from coarse facts
(format, size, a 4x4 colour grid, a 2-bit alpha outline; sample length, rate, loop points, a coarse
spectral outline and median pitch). Geometry, animation, text and note sequences are kept as facts.
No retail pixels or samples are in the published ROM: a taint scan (`games/banjotooie/taint_report.py`)
must report 0 failing before each publish.

- `games/banjotooie/` — asset filesystem, formats, dirty-room spec extraction, clean-room generator,
  sprite face briefs, sound bank resynthesis, ROM builder, taint report.
- `cleanroom/` — shared library (texture formats, facepaint briefs, VADPCM, outline resynthesis, voices).
- `ports/ejs/` — the page (EmulatorJS + mupen64plus-next core, see the site's `THIRD_PARTY.md`).
- `STATUS.md` — what works, decisions, what is next.

You need your own ROM to run the dirty-room step; nothing in this repository contains retail data.
Voices are placeholders (text-to-speech); no real performer is imitated.
