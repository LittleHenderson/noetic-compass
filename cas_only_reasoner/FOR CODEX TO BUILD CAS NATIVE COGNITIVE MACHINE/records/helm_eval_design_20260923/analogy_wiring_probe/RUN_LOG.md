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

## Attempts 2 and 3: probe v0.2 and preservation, 02:29:58 -> 04:46:44 PDT. Probe CRASHED; preservation PARTIAL.

- **Probe v0.2, seeds 20260917, 20260918 and 20260919** (3 invocations). Every invocation stopped with
  `ValueError: TYPED_SOURCE_WORLD_RECONSTRUCTION` at the first counterfactual. The cause: `slots.compile_slots`
  validates the source bank and refuses an altered world. **No metric was written.** Fixed by Amendment A1.
- **Preservation.** The run for seed 20260919 completed all 3 models: `preservation_reference_20208c92_seed20260919.json`
  (tool before A1; the digest code is identical after A1). The runs for seeds 20260917 and 20260918 stopped at
  `WALL_LIMIT_REACHED` (1,800 s) after 2 models, with no JSON written. The digests they printed are kept here
  as a reproducibility check for the re-run:

  | Model | Overall digest |
  |---|---|
  | h2_fresh_20260917 | `8bce418f5ea641f0241f9cbfebdca30f1e3393b3beda8c98bb364454802b3749` |
  | h2_initial_20260917 | `0138af72c05a4e05ddbe6b03c049dad5afae7e47ec0fa69ead191b0e2103d975` |
  | h2_fresh_20260918 | `2e8dbaead32b6eb565fc80b24ee75c009122228ee8127c5f504ecc88f749fbd5` |
  | h2_initial_20260918 | `b5aae9c55f3d8a5798d0442199109ba4ce35414a0f2c496744999d85dbe6d84d` |
  | h2_fresh_20260919 | `06b77b70dc1f3709edd527ded29e933c1fd1c3e2ed1b7c46160f37d930c2bacf` |
  | h2_initial_20260919 | `ee551016c03e4f41d3c666d105637f7e9892be5c98775ec19f2c03cd1390eb68` |
  | h2_final_20260919 | `3a5957ee8e9951657c1d0667f60d81172601c253c0531f3c406dfdcb7a2bbeea` |

- **Log:** `before_reading_v0_2.log`. No automatic retries: each re-run is a separately started job.

## Attempt 4 (after amendment A1): 04:48:31 PDT -> about 05:27. PARTIAL: the laptop ran out of memory.

| Invocation | Result |
|---|---|
| Probe, seed 20260917 | **complete**: `before_reading_v0_2_seed20260917.json`, wall 1455.3 s, course load 249.1 s |
| Probe, seed 20260918 | **partial**: 2 of 3 models saved (`h2_fresh_20260918`, `h2_initial_20260918`) in `before_reading_v0_2_seed20260918.json` (`"complete": false`, wall 731.2 s). The third model, `h2_final_20260918`, did not run |
| Everything queued after it | **did not start**: probe seed 20260919, preservation seeds 20260917 and 20260918, the probe self-test, the D-1 oracle self-test |

**Every completed model reads `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT`**, with `delta0 = M1z = M2z = max M3z = max K = 0.0`, as predicted. That is 5 models so far: fresh, initial and final for 20260917; fresh and initial for 20260918.

**The cause** (measured after the stop):
- The shell logged `fork: retry: Resource temporarily unavailable` (errno 11).
- Afterwards the machine had **345 MB of 16,085 MB** RAM free, with none of these jobs running.
- Other desktop applications held most of the memory. The largest were the ChatGPT desktop app (13 processes, about 2.3 GB) and Chrome (23 processes, about 2.2 GB).
- The probe process exited with code 4. Its own `WALL_LIMIT_REACHED` could not have fired after 731 s of a 3,600 s budget, so the exit is recorded as **caused by memory exhaustion, reason not printed**.
- No file was left half-written: each JSON is rewritten whole after each model.
