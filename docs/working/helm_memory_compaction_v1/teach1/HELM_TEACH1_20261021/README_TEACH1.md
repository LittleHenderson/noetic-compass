# TEACH-1 — the sealed exam of HELM memory compaction v1 (package v1)

**Plainly.** TEACH-1 teaches HELM a small made-up subject (a family's hive yards, or a town's bus lines) through its
live chat, one typed line at a time. Then it squeezes HELM's working memory to 12 turns, so old turns must be compacted
into capsules, damages two of the saved originals on purpose, and asks the same 16 questions three times. Seven arms
differ only in their memory switches. A frozen reader turns the records into one status word. Nothing in this package
is a result. Status: SEALED, NOT RUN, NOT SCORED.

| Part | What |
|---|---|
| `PREREGISTRATION_TEACH1.md` | the pre-code (sha256 `7eef0edc…`) byte-identical, then amendment A-TEACH1-1 |
| `FROZEN_TEACH1.json` | every frozen number (a test checks it equals `teach1/common_t1.py`) |
| `helm_now/` | HELM's code under test: 173 files by `git show 9f0c359a…` (`SOURCE_CUT.json`) |
| `contract/` | the cut record, the disjointness check, the writer brief, the key format, this custodian procedure |
| `teach1/worlds_t1.py` | the SDG keyed worlds (two templates), the 32-slot teaching plan, the quizzes, the planted damage |
| `teach1/turns_t1.py` | the turn checker; the builder's rule-written PRACTICE turns (never the exam) |
| `teach1/arms_t1.py` | the seven arms as switch sets over `helm_chat.HELMConversationalSession.handle_turn`; the unit |
| `teach1/person_t1.py` | the scripted person (right 0.75 / "I don't remember" 0.25, from the key only) |
| `teach1/run_t1.py` | `unit`, `pool`, `cutcheck`, `suites`, `routecheck` |
| `teach1/custody_t1.py`, `seed_rule_t1.py`, `exam_t1.py` | the custodian's approve / draw / finish; the seed rule; the exam folder |
| `teach1/reader_t1.py` | the frozen reader: I1–I15, the 12 hard gates (HG-H8 first), U / R / F / S marks, the word |
| `tests_teach1/` | 19 unit tests with planted faults for every gate the reader computes |

**Every process** is `python -X utf8 -B -I <script> ...`. Run order for the exam, from a fresh extract, after the
custodian's hand-over: `run_t1.py cutcheck --out RUN`, `run_t1.py suites --out RUN --from-seal`,
`run_t1.py routecheck --exam EXAM --out RUN`, `run_t1.py pool --exam EXAM --out RUN` (one process at a time), then
`reader_t1.py --merge-input MERGE_INPUT_TEACH1.json --out TEACH1_READING.json`.

**Words, frozen order:** `INCONCLUSIVE`, `COMPACTION_HARMED`, `COMPACTION_NO_GAIN`, `COMPACTION_EARNED_KEEP`.
Labels printed with every word: `SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `RULE_CAPSULES_V1`, `EYE_REPORT_ONLY`.
`COMPACTION_EARNED_KEEP` means only "kept in the synthetic design for the next step"; nothing here is `VALIDATED` or
`LICENSED`, and every mechanism stays `ENGINEERED-NOT-VALIDATED`.
