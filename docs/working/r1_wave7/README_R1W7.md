# HELM-R1 wave 7 — the CHAT WAVE (sealed package)

**Plainly.** The owner ruled that the wide recipe brain is HELM's canonical brain and ordered it ON by default in the live
loop and in the chat (PR #414, commit `974fe36c`). Every sealed test so far drove HELM's loop directly. **v3 (amendments A-R1W7-2 and A-R1W7-3, FIX FIRST rounds 1 and 2):** HELM under test is commit `dfc7158d` (PR #416, 2 commits): the defects the v1 and v2 practice runs showed are fixed in HELM (the chat hands the wide brain every line the wide reader claims; wide answers said in the wide path's own exact words; kitchen fractions said exactly; no tool engine on kitchen sentences; wave 3b question forms and a greeting prefix read; "X or Y" binds X; "but we've run out of X" is a reader question). v1 (zip `5107b9c6…`) and v2 (zip `7e7fa066…`) are VOID_SUPERSEDED: never launched, no exam drawn. This wave types to
HELM's chat window (`helm_chat.py`: its memory, its intent routing, its everyday-English voice, its session log) line by
line, exactly as a person would, with the wide brain on as shipped, on three fresh exams drawn blind by a custodian: 128
real recipes (X7_REAL), 64 dialogues (X7_CONV) and the same 64 dialogues with two small-talk turns each (X7_NOISE). The
preregistration is `PREREGISTRATION_R1W7.md` (the frozen design + amendment A-R1W7-1 with the builder's deviations).

| Folder / file | What |
|---|---|
| `helm_now/` | HELM's code under test: 161 files cut by `git show` from commit `dfc7158d` (v3) (`SOURCE_CUT.json`; `helm_ui/` and `helm_hub/` are not cut) |
| `contract/HELM_CUT_R1W7.json` | every cut file's sha256, the commit, the pinned base of `helm_brain_canonical.py` (= `SOURCE_CUT.json`) |
| `contract/EXCLUDE_R1W7_PRIOR_USED.json` | every frame id excluded from the X7 draws (X-REAL, c46, c47, X6, X6v3, both RB-W1T practice draws, wave 6's practice pools), ids only, sources named with sha256 |
| `contract/CUSTODIAN_PROCEDURE_R1W7.md` | what the custodian runs (laptop, 0 USD) |
| `r1w7/common_w7.py` | frozen constants, the five neighbours by freeze, HELM imported from `helm_now/` only |
| `r1w7/chat_harness.py` | drives `HELMConversationalSession.handle_turn` per line; the transparent recorder (D-W7-4); LOOP_ON through wave 6's harness; ALWAYS_ASK |
| `r1w7/noise_w7.py` | X7_NOISE from X7_CONV with the twelve frozen sentences at the NOISE seed |
| `r1w7/units_w7.py`, `pool_w7.py`, `summary_w7.py` | the 14 host units (one process each, `python -X utf8 -B -I`), the pool, the host index |
| `r1w7/seed_rule_w7.py`, `custody_w7.py`, `check_w7.py`, `approval_w7.py` | the seed rule, the custodian's seal / practice draw, the receiver's check, the approval record (owner's signature first) |
| `r1w7/score_w7.py`, `merge_r1w7.py` | the frozen reader: instrument rows, hard gates, marks, status word, reported rows |
| `kit/` | the runner (`run_r1w7.py`), the run-proven supervisor and plan check (byte copies), the stage plan |
| `tests_r1w7/` | unit tests (planted-failure fixtures for every gate and mark), kit tests, the host run; `run_tests.py` for isolated mode; `fixtures/RECORDER_PRACTICE_TURNS.json` (practice dialogues for the recorder unit) |
| `practice/PRACTICE_POOLS_W7.json` | the builder's practice pool ids (= wave 6's published practice pool and RB-W1T's practice draw v2; excluded from the exam) |
| `FROZEN_R1W7.json`, `RUN_LIMITS_R1W7.json` | every frozen number; the run limits |

**Arms** (the chat's own switch `HELM_WIDE_BRAIN`): CHAT_ON (as shipped, the arm under test), CHAT_OFF (`=0`, the licensed brain alone,
the yardstick), CHAT_ON_REPLAY, CHAT_DIAG (`mode="cas_diagnostic"`), LOOP_ON (wave 6's harness, the loop driven directly, wide on, no
UNSETTLED_ASK rule: D-W7-6), ALWAYS_ASK. 14 units; expected under 2 minutes of compute on the host.

**Neighbours shipped beside (never copied in, never edited):** wave 1 v3 `31f97d67…` (the licensed brain the chat's loop loads), wave 3 v3
`152bca2a…` and wave 3b `a4f82556…` (phrase pools, `import_helm`, `run_item`), wave 6 v3 `f1b64a5e…` (the dialogue generator, the
scoring functions, the loop harness), RB-W1T v3 `3a8ae37e…` (the real-recipe frame, draw and keys). Folder layout on the host:
`../../<name>/<top folder>` (see `kit/STAGE_R1W7.json`), or `R1W7_<W1|W3|W3B|W6|RBW1T>_DIR`.

**Every process is `python -X utf8 -B -I <script> ...`** (isolated: no PYTHONPATH, no site customisation); each entry script puts its own
package on `sys.path`. HELM's own suites that run on the host are the eight unittest files wave 6 ran (`test_helm_chat_nuance.py`,
`test_helm_memory.py` and `test_helm_agentic_planner.py` are pytest-style and are carried in the cut but not run as unittest suites).

**What the custodian runs** (from an extracted copy of the sealed zip, after the owner has signed and the approval record exists):

    python -X utf8 -B -I HELM_R1_W7_20261020/r1w7/custody_w7.py seal --frames-dir <x_real/frames>
           --approval <APPROVAL_RECORD_R1W7.json> --zip <HELM_R1_W7_20261020_SOURCE_R1W7.zip> --out-dir <x7_custody>

**What the reader runs** (laptop, fresh extract, neighbours beside it, after the host run):

    python -X utf8 -B -I HELM_R1_W7_20261020/r1w7/merge_r1w7.py --merge-input MERGE_INPUT_R1W7.json --out R1_W7_READING.json

Nothing in this package is a result. Practice counts (builder, practice data only) are in `TEST_RECORD_R1W7.md` beside the zip.
