# Banjo-Tooie clean room: status

## State (2026-10-01 night)
- ROM: `D:/n64work/banjotooie/rom/Banjo-Tooie (USA).z64`, sha1 af1a89e1… (the decomp's `baserom.us`).
- Clean ROM: `python -m games.banjotooie.build_rom D:/n64work/banjotooie/spec D:/n64work/banjotooie/build/bt_clean.z64` (~90 s; reuses `build/sound/{ctl,tbl}.bin`, add `--audio` to resynthesise, ~25 min).
- **Boots and plays**: natively (mupen64plus, `tools/m64p_test.py`: title, attract demos) and in headless Edge (EmulatorJS: boot, title, Enter -> file select -> into the game; `shots/web1/sheet.png`).
- **Audio**: all 827 waves resynthesised, own 4-predictor books, bank sizes = retail. `audio check` OK.
- **Taint: 0 failing** (33110 texture streams raw + RGBA, ADPCM + decoded PCM + books).
- **Published and live**: https://andrewnakas.github.io/banjotooie-cleanroom/ (verified in headless Edge: loads, boots to the title with the re-typeset copyright line; first load takes about a minute for the 32 MB ROM). Source: https://github.com/andrewnakas/banjotooie-cleanroom ; republish via `sh tools/publish.sh "msg"` (always runs the taint scan first and aborts on any failure).

## Readable / faces / pictures done
- Title logo, GAME OVER, THE END re-lettered in model space and baked into their tiles (`logos.py`, `modelgeo.py` F3DEX2, `project.py`).
- All three fonts re-typeset with open fonts (`text.py`: dialog 0xC21, large 0xC22, counter 0xC23).
- HUD buttons re-typeset (A, B, C arrows, R, Z, START, ?) and ~110 dialog head icons / item sprites given eyes, noses, mouths, outlines from briefs (`faces.py`, preview: `python -m games.banjotooie.facesheet <spec> out.png`).
- 26 level sign textures re-typeset (`signs.py`: FLOOR n, FIRE EXIT, NO ENTRY, CLOSED, TICKETS, BOILER PLANT, SEWER ACCESS, QUALITY CONTROL, CABLE ROOM, REPAIR DEPOT, PACKING ROOM, HAILFIRE PEAKS OIL PIPELINE, SAUCER of PERIL, CAVE OF HORRORS, JOLLY'S, HAG 1, GO, GUN POWDER, SOUR MILK). Plus the 14 name plaques x31e7..x31f4 (two uncertain readings: K. CONWELL, D. PASHUTE; the middle floor sign is typeset FLOOR 4 but may be FLOOR 2). Not yet: WEIRD ALIEN neon (x2568..), EMPTY (x2f2c), tiny notes (m8bb.10).
- 13 two-dot eye textures painted (`dot_eye_keys.json`).
- Placeholder voices: 96 voice-like slots carry Piper gibberish (`voices.py`).
- Clock faces drawn (`drawn.py`).
- Verified in the browser (2026-10-01 20:40, `shots/web2/sheet.png`): new game -> intro story text, Klungo and Mumbo dialog with heads and the re-typeset font, card game scene.
- Clock faces drawn (`drawn.py`).
- Verified in the browser (2026-10-01 20:40, `shots/web2/sheet.png`): new game -> intro story text, Klungo and Mumbo dialog with heads and the re-typeset font, card game scene.
- **Dialog heads rendered from the characters' own models** with our textures for 39 icons (`portraits.py`: sprite -> model + head crop; front view). Mumbo (0xBD9 -> model 0x661), 0xB9D and 0xBB4 were tried and dropped: the head crop frames badly (render3d centres on the crop but does not clip). The other ~70 briefed icons keep grid colours + eyes (`faces.py`); extend `portraits.MAP` using `sheets/c_models0.png` / `c_models1.png` (labelled renders of all 194 eyed models).
- 276 model eye textures (190 models) painted from one generic eye brief; iris / eyelid colour from the kept grid (`eye_keys.json` is only a list of texture keys).

## Decisions (log)
- **Web route 3: clean ROM + WASM N64 emulator** (EmulatorJS 4.2.3 + mupen64plus-next, core ROM-DB entry pointed at our MD5 for EEPROM 16K; `ports/ejs`). Why: no PC port with a web target; the recomp needs RT64; same route as Banjo-Kazooie.
- **No decomp build needed**: code, overlays, header and IPL3 are byte-identical to what the matching decomp builds, so `rom_kept.bin` = retail ROM with the asset filesystem (0x5180..0x1A14580) and sound bank (0x1A14580..0x1E29B60) zeroed; `build_rom.py` refills them and recomputes the CIC-6105 checksum.
- Asset FS (`assetfs.py`): 0x3667 slots, Rare deflate via `tools/rarezip/rarezip.dll` (rebuild of retail is byte-identical).
- Kept as facts: geometry, animations (0x16), midi (0x19), encrypted text (0x1A), level/setup binaries (0x13 below 0x1EF6: checked, structured data, no pixels), 59 type-0x12 tables (checked: not images).
- Fonts were first generated from a 2-bit intensity outline (readable, but too close to the retail glyph art): replaced by re-typeset glyphs.
- The Dolby logo and PRESS START / NO CONTROLLER letters still come from the kept 2-bit alpha outline.

## Hard-won facts
- **Mostly-empty tiles stall the game**: the re-lettered title logo first compressed to 14 KB (retail 55 KB) and the native emulator froze ~25 s in (bisected to asset 0x8A8). Fix: transparent texels carry the outline colour plus noise (`logos.sign_textures`). Keep generated assets from collapsing far below retail size.
- BT models are F3DEX2 (G_VTX 0x01, G_TRI 0x05/0x06, G_ENDDL 0xDF); texture list entries are 8 bytes.
- BT eye textures: 16x16 CI4, iris right/below centre, highlight lower left, eyelid band along the bottom.
- The decomp has no sound-effect names: voice slots must be found another way (pitch + duration).

- Pattern seen four times: the FIRST native run of a freshly built ROM times out after 2 of 3 frames and the rerun passes (first-run effect in the native emulator for a new ROM MD5, cause not found; the browser build with a fresh profile is not affected). Rerun before believing a stall.
- The native boot test (`tools/m64p_test.py`) timed out twice on ROMs that passed on reruns (machine load from other sessions, or an intermittent emulator stall). So the earlier "empty tiles stall the game" diagnosis rests on two failed runs and may have been partly this; the noise fill is harmless either way.

## Next
1. Verify the briefed faces in game (dialog heads, pause menu icons) and fix eye positions that are off.
2. More text-bearing textures: signs in levels (list in `sheets/d_eyes1.png` bottom row: 2b82..2b84), Jamjars / Wumba signs, "SUPERLIFE"/"BAZZA" (0x7E4), playing cards (0x8AE..), clock face.
3. Two-dot eyes (white square, two black dots) and big 32/64 px eyes (0x85F, 0x91D..).
4. More model-rendered portraits (Jinjos, hooded frogs, robots, the remaining characters); item icons (eggs, feathers, notes, Jiggy) rendered from their models.
5. Pixel data inside code/overlays (boot logos, crash font): find and add to taint.

## Pending (2026-10-01 ~22:45)
- **Not yet published**: the ROM with 39 model-rendered heads (`build/bt_clean.z64`, commit a600c52) booted natively, but its publish job was stopped by Claude Code because the PC ran critically low on memory during the taint scan. The live site still has the 33-head build (taint 0 failing). To publish: `sh tools/publish.sh "39 model-rendered dialog heads"` (runs the taint scan, ~10 min, needs a few GB of RAM free).

## For the morning
- Play https://andrewnakas.github.io/banjotooie-cleanroom/ in Chrome/Edge (first load ~1 min). Keys: arrows move, X = A, C = B, Z = Z, S = R, Q = L, Enter = Start, I/J/K/L = C buttons.
- Look at: title screen, file select, first dialog (heads + font), pause menu.
- **Voices**: the decomp names no sound effects, so 96 voice-like slots were picked automatically (short, voiced, speech-like pitch) and grouped LOW / MID / HIGH by pitch. They now carry Piper gibberish placeholders (`games/banjotooie/voices/<sfx>.wav`). Some slots may be non-voice effects: listen and delete the wav of any that is wrong (then rerun the two commands below after a full `audio build`).
- **Record**: practice pack at `D:/n64work/banjotooie/practice/` (`SCRIPT.txt`, `practice_LOW|MID|HIGH_call_and_response.wav`, `clips/`; personal use, never publish). Save each take as `games/banjotooie/voices/<sfx index>.wav`, then:
  `python -m games.banjotooie.voices apply D:/n64work/banjotooie/spec D:/n64work/banjotooie/build/sound`,
  `python -m games.banjotooie.build_rom D:/n64work/banjotooie/spec D:/n64work/banjotooie/build/bt_clean.z64`, `sh tools/publish.sh "voices"`.
- Disk: D: was down to 10-14 GB free during the night (other sessions); this game uses ~0.3 GB.
