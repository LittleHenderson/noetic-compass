# Analogy wiring probe: run log (append-only)

## Attempt 1: STOPPED at the pre-set wall limit. No reading.

| Item | Value |
|---|---|
| Started, ended | 2026-09-23 01:18:01 -> 01:33:25 PDT (924 s wall, including the start-up before the in-script timer) |
| Command | 9 models in one invocation: fresh containers at seeds 20260917, 20260918 and 20260919; `initial.pt` and `final.pt` of `receipt_2026091{7,8,9}` |
| Probe sha256 (file on disk at launch) | `5665daf18f9054ca7d713c3c581270704d4f44ffb7f88ecf9f6d352a20cebd26` |
| Prereg sha256 | `6fe1c2e13514fac3b5d9ce085a87a270d60af1435d781af6df82121c78660185` |
| Exit | `WALL_LIMIT_REACHED`, exit 4. No JSON written. No metric was computed |
| GPU | Admitted at 64 C with 7182 MiB free. Forward passes only |
| Why it stopped | The frozen course load ran on the CPU while the trusted-rescore job was loading the same course in a second process. The load took most of the 900 s budget. The per-invocation limit worked as written |
| Retry | No automatic retry. A new attempt is a separately started, separately recorded job |

**Lesson.** Nine models behind one contended course load does not fit 900 s. Next attempt:
- run after the rescore job ends;
- probe at most 3 models per invocation;
- record the load time.
