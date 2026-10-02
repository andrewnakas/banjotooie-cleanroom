# Banjo-Tooie clean room: status

## State (2026-10-01 evening)
- ROM found: `D:/n64work/banjotooie/rom/Banjo-Tooie (USA).z64`, sha1 af1a89e1… (the decomp's `baserom.us`).
- Clean ROM builds: `python -m games.banjotooie.build_rom D:/n64work/banjotooie/spec D:/n64work/banjotooie/build/bt_clean.z64`.
  Boots natively (mupen64plus, `tools/m64p_test.py`): Dolby screen, title, attract demos, PRESS START (`shots/boot1/sheet.png`).
- Texture taint: **0 failing** (`python -m games.banjotooie.taint_report <retail> <clean>`; 33110 streams).
- Audio: sound bank resynthesis (827 waves) in progress -> `build/sound/{ctl,tbl}.bin`; the first ROM was silent.
- Web: EmulatorJS site assembled in `D:/n64work/banjotooie/devsite` (not yet verified in a browser, not published).
- Not published yet. Repo `andrewnakas/banjotooie-cleanroom` does not exist yet.

## Decisions (log)
- **Web route 3: clean ROM + WASM N64 emulator** (EmulatorJS 4.2.3 + mupen64plus-next, core ROM-DB entry pointed at our MD5 for EEPROM 16K; `ports/ejs`). Why: no PC port with a web target; the recomp needs RT64; same route as Banjo-Kazooie.
- **No decomp build needed**: code, overlays, header and IPL3 are byte-identical to what the matching decomp builds, so `rom_kept.bin` = retail ROM with the asset filesystem (0x5180..0x1A14580) and sound bank (0x1A14580..0x1E29B60) zeroed; `build_rom.py` refills them with generated data and recomputes the CIC-6105 checksum.
- Asset FS (`assetfs.py`): 0x3667 slots, Rare deflate via `tools/rarezip/rarezip.dll` (rebuild of retail is byte-identical).
- Regenerated: model textures, external textures (type 0x13, uid >= 0x1EF6), sprites (0x17/0x07), fonts (0x18): colour grid + noise + 2-bit alpha / intensity outline, own CI palettes, own mip chains. Sound: every wave resynthesised from its outline, own 4-predictor books (retail size), own loop states.
- Kept as facts: geometry, animations (0x16), midi (0x19), encrypted text (0x1A), level/setup binaries (0x13 below 0x1EF6: checked, structured data, no pixels), 59 type-0x12 tables (checked: not images).

## Next
1. Audio into the ROM, audio taint, browser check (boot, keys), publish repo + Pages.
2. Sprites: ~130 dialog head icons and HUD items are 32x32 and turn to mush: facepaint briefs (`faces.py` hook), buttons/letters re-typeset (A, B, C arrows, Z, R, START, ?).
3. Title logo "BANJO-TOOIE" re-lettered; other text-bearing textures (signs).
4. Character eye textures on models (briefs).
5. Look for pixel data inside code/overlays (boot logos, crash font) and add to taint.
6. Voices: Piper placeholders + practice pack `D:/n64work/banjotooie/practice/`.

## For the morning
- (pending publish) https://andrewnakas.github.io/banjotooie-cleanroom/
