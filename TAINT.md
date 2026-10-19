# Taint scan evidence

Verbatim output of the last taint scan saved in the local work directory, committed as evidence.
It was not re-run for this commit; check the log date against the date of the published build.

Command: `python -m games.banjotooie.taint_report "<retail rom>" D:/n64work/banjotooie/build/bt_clean.z64 (inside tools/publish.sh)`

Live-build check (2026-10-19): the published `bt.z64` (git blob b887564d7b) equals `D:/n64work/banjotooie/site/bt.z64`; this log was written 20 s before that gh-pages commit (2026-10-01 22:43, "39 model-rendered dialog heads").

## `taint.log` (written 2026-10-01 22:43)

```
taint: textures 33110 streams, 6450 with any shared window; audio 5; FAILING (>= 32 B run): 0
```
