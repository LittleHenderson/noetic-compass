# TEACH-2 — the CUBE EXAM package (HELM cube oscillation v1)

**Plainly.** This package is the exam that can give HELM's cube memory its first word. It teaches HELM a made-up subject
(a family's hive yards, or a town's bus lines) through its chat, 32 lines per world, 16 worlds. HELM keeps a fact as a
cube only when its retrained CTT translator (three copies, voting) and its brain side agree in rounds. Its working
memory is held under a byte limit by the Eye's capsules, moved off, folded, and copied to a stand-in cloud that goes
offline once per world. Then HELM is asked the same 16 questions three times, under 11 arms, and a frozen reader prints
one word: `INCONCLUSIVE`, `CUBES_HARMED`, `CUBES_NO_GAIN` or `CUBES_EARNED_KEEP`.

Status: built and sealed by the builder; **not drawn, not run**. Every mechanism stays `ENGINEERED-NOT-VALIDATED`; the
Eye's acting stays `NOT LICENSED`. The money line is `CUBE EXAM at 1 USD` (one GPU host).

| Part | What |
|---|---|
| `PREREGISTRATION_TEACH2.md` | the pre-code (sha256 `f7b6183b…`) + amendments A-TEACH2-1 to -22, byte for byte |
| `FROZEN_TEACH2.json` | every frozen number (a package test checks it equals `teach2/common_t2.py`) |
| `helm_now/` | HELM, cut by `git show` at the commit in `contract/HELM_CUT_TEACH2.json` |
| `brain/HELM_R1_W1_20261015_v3/` | the wave-1 brain package HELM loads (checked by its own freeze) |
| `ctt/` | the CTT: `helm_cas_translator/` and `cube_task/` from the sealed CUBE TRAIN zip `706e1fa6…`, `vocab.json`, and `weights/` = the c57 final weights pinned in `common_t2.CTT_WEIGHTS_SHA256` (I16) |
| `teach2/` | the harness: worlds (`worlds_t2`), turns checker and practice turns (`turns_t2`), exam carrier (`exam_t2`), scripted person, seed rule, the CTT server and client, the units and pool (`arms_t2`, `run_t2`), the custodian (`custody_t2`), the frozen reader (`reader_t2`), the exam-side rule reader |
| `contract/` | writer brief, key format, custodian procedure, the cut, the disjointness check |
| `tests_teach2/` | the package tests (no HELM run, no GPU) |

**How it runs.** The custodian (a separate session) follows `contract/CUSTODIAN_PROCEDURE_TEACH2.md`: approve from the
recorded line, draw, have the turns written by three model families and keyed by two others, finish. Then on one GPU
host, from a fresh extract: `teach2/run_t2.py cutcheck`, `suites --from-seal`, `routecheck`, `pool` (VERBATIM_ONLY on
every world first; the limits by the frozen rule; then the other 10 arms), and `teach2/reader_t2.py`.

**What a pass would mean, and not.** `CUBES_EARNED_KEEP` means only "kept in the synthetic design for the next step".
Never licensed by this test: that HELM learns like a person; real subjects or real people; the Eye's acting; the CTT
outside these two subject templates. The turns are AI-written (`LLM_WRITTEN_ONLY`).
