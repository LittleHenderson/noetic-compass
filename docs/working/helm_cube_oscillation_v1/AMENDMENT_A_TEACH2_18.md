
## Amendment A-TEACH2-18 (2026-10-22 PDT) — how the TEACH-2 package is built and sealed with the CUBE TRAIN weights; written before any exam code

Status: appended after A-TEACH2-17 (`8d7e0ff0…`); nothing above is edited. Where it disagrees with the pre-code (`f7b6183b…`) §2–§13 or A-TEACH2-1 to -17, this governs. Nothing of the exam was built, drawn or run when it was written. The owner writes nothing (A-TEACH2-17); the operator writes this.

**The owner's words (verbatim, 2026-10-22):** "Yes: pin the CUBE TRAIN weights into the TEACH-2 package and seal it (0 USD), ready for the CUBE EXAM at 1 USD."

**Where it starts.** CUBE TRAIN ran as job c57 and read `TRAIN_READY` (spec §7.125 follow-up 17; record `cube_train/run_c57/`). Its weights exist and are fingerprinted. The TEACH-2 exam itself was designed (pre-code, A-TEACH2-1 to -17) but no exam code exists.

**P1. The package.** One folder `HELM_TEACH2_20261022/`, sealed as one zip, holding:
- `helm_now/` — HELM cut by `git show` at the commit named in its contract file, exactly as TEACH-1 (`contract/HELM_CUT_TEACH2.json`); the wave-1 brain package beside it, checked by its freeze.
- `ctt/` — the CUBE TRAIN package's `helm_cas_translator/` and `cube_task/` byte for byte from the sealed zip `706e1fa6…`, its `data/vocab.json`, and the four c57 final weights: A4-s1 `c39eafb6db92845a463a0c6bc711c73d45ddcb482b5e5eaffad466f337d7a69a`, A4-s2 `3bfbf1f064e4dd96980bfa971cbd089706a4b99cfdaba0b84324f4a4b3a883ee`, A4-s3 `6418ef1e27ffd18df9f571e9f5410af1afae6843d9d56cbcb01d31ccf947564b`, A5-s1 `07a54adcdb58cfb746f35e0d4350a9bde536eb72f97d6b29451960313fca4bc1`. These four sha256 are I16's pins.
- `teach2/` — the exam harness, adapted from TEACH-1's (worlds, plan, turns checker, person, quizzes, damage, custody, units, pool, reader); the exam-side rule reader `teach2_rule_reader.py` (A-TEACH2-2 B2, A-TEACH2-3) copied in.
- `contract/` — the writer brief and key format with the TRAP kind (P6), the custodian procedure, the cut contract.
- `tests_teach2/`.

**P2. Serving the CTT.** One serving process per unit loads the three voting copies (A4-s1..s3) and, in CUBE_OSC only, the twin A5-s1. It is TEACH-2's own `teach2/ctt_server.py`: the same write-audit hook installed before torch is imported (`helm_cas_translator.audit`), the same locked greedy decoding (`model.greedy_locked`, `cube_task.target.automaton_for`, direction `[B]`), the same `require_cuda()` (no CPU fallback). One process instead of one per copy because the laptop practice would not fit three torch processes in memory; the decoding is the same function. The answer is turned into the target string by `cube_task.target.canonical` and read by HELM's own adapter (`helm_cube_osc.reading_from_ctt` through `CTTProposer`). An incomplete decode is no reading. The audit is judged by `cube_task.audit_judge` with the package's `ctt/` and `data` folders forbidden for writes; any violation, any network call, any process start, a dead server or a missing audit report makes the new instrument row **I20** false.

**P3. A5-s1 is reported only.** In CUBE_OSC every teaching line is also read by A5-s1; the reading is logged beside the vote and never reaches HELM (pre-code §2 "the c45 twin as a size check").

**P4. The exam host.** The decoder needs a GPU (`require_cuda`, and the house rule: neural work never runs on a CPU). The exam therefore runs on **one GPU host** (g4dn.xlarge; g5.xlarge only on refused capacity), not the "one CPU host" written in OPEN_QUESTIONS Q8. The cap stays **1 USD** (`CUBE EXAM at 1 USD`, A-TEACH2-1 item 8, unchanged); the host type is an operational detail. If the run cannot finish under the cap, it stops and reads `INCONCLUSIVE`.

**P5. The arms and their memory** (A-TEACH2-15 T4 made concrete):

| Arm | Memory | Reader | Decides |
|---|---|---|---|
| CUBE_OSC | size-limit path (T1) at the T2 limits; stand-in cloud | CTT, 3 copies, rounds | the arm under test |
| REPLAY | CUBE_OSC again, fresh process | as CUBE_OSC | HG-REPLAY |
| QUOTE_ONLY | TEACH-1's COMPACT_ON exactly (budget 12, no cube) | — | C1 |
| TABLE | plain `(thing, slot) → value` dict; the text FIFO at budget 12, no compactor | rule reader | C2 |
| TABLE_OSC | as TABLE | the CTT's agreed readings | reported |
| ONE_READER | size-limit path, cubes | rule reader, no rounds | C3 |
| CTT_ONLY | size-limit path, cubes | CTT unanimous, no check, no say-back | C3 |
| EYE_OFF | size-limit path with the Eye's lean records, move-off and folding switched off (plain capsule list) | CTT, rounds | reported |
| FIRST8 | CUBE_OSC with clue words from the first lines only (`clue_every_line` off) | CTT, rounds | reported |
| VERBATIM_ONLY | TEACH-1's VERBATIM_ONLY (budget 10,000, no cube, nothing fades) | — | U1, C4, S-SPACE, the limits |
| FIFO_DROP | switch OFF, budget 12 | — | the floor |

The six "cube arms" (CUBE_OSC, REPLAY, ONE_READER, CTT_ONLY, EYE_OFF, FIRST8) run the size-limit memory; HG-LIMIT, HG-FADE, HG-OFFLINE, HG-HOLD apply to them. Every arm's variant is set up on the exam side; HELM's files are the same bytes in every arm.

**P6. The TRAP kind** (pre-code §4.2 made concrete). Plan per world, 32 slots: FACT 18, UNKNOWN 4, TRAP 4, FIX 2, RESTATE 2, SMALL 2. Two TRAP slots are the first statement of a known non-FIX fact (they replace two FACT slots); two are restatements-with-decoy of a known fact already stated (they replace two SMALL slots and come after the fact's first statement). Each TRAP fact carries one decoy drawn from the WORLD stream: a second number word of the same kind (count facts), a month belonging to another fact, or a "not" placed on a wrong value ("not X"). The canonical TRAP line is written by the generator; the exam's TRAP lines are written by the AI writers from it and keyed like a FACT (each keyer names the true value). Floors: 32 turns; ≥ 18 FACT; exactly 4 TRAP; ≥ 2 FIX; ≥ 2 SMALL; every fact stated.

**P7. The limits** (A-TEACH2-15 T2 made concrete). The worlds are drawn after the seal by the custodian, so the package freezes the **rule**, not the numbers: the pool runs VERBATIM_ONLY on every world first; its records give each world's working-memory bytes at the end of Q-REFRESHED (live user lines + capsules, the same count as `CubeOsc.working_bytes`); the working limit = ⌊median / 2 / 100⌋ × 100 bytes; the device limit = the working limit. The pool writes `LIMITS_TEACH2.json` before any cube arm starts; every cube unit records the limits it used; the reader recomputes them from the VERBATIM_ONLY records (new instrument row **I21**).

**P8. The offline window** (A-TEACH2-15 T3). Per world, one quiz phase, drawn from the QUIZ seed, is offline: the stand-in cloud refuses every call for that whole phase. The planted damage of TEACH-1 (one cold copy deleted, one corrupted, on the device) is kept in every compacting arm.

**P9. New measurement rows** (the harness records, the reader counts): every say-back line (a transparent recorder on `helm_cube_osc.say_back`); the store's branch table after every turn; each turn's id, kind and fact id; the Eye log (MOVE_OFF, FOLD, HOLD); batch log; cloud moves; working bytes after every turn and at every quiz; every cube answer (recorder on `CubeOsc.answer`) with its label, branch and source turn; the cloud's state during each answer.

**P10. Gates and rows made checkable** (definitions frozen now; the reader applies them):
- `CUBES_WRONG` — at the end of the unit, every current branch (newest per source, target and kind) whose referent (or amount) differs from the key value of the fact of the turn that wrote it; a branch written by a turn with no keyed fact, or by an UNKNOWN line, counts as wrong. `CUBES_TRAP_WRONG` — those written by TRAP lines. HG-WRONG-CUBE: 0 in every cube arm.
- HG-REVISION — the branch table only grows (every snapshot is a prefix of the next); no branch id repeats; a kept correction is a new branch.
- HG-NUMBER — 0 subject number words (two to nineteen, and their digits as standalone numbers) in any stored capsule row, index row, fold row or S2 record; CAS notation (`^n`) and fingerprints are not numbers.
- HG-FADE — every batch capsule has a COMPACTION receipt; every MOVE_OFF and FOLD has an Eye log entry with a digest; no line holding an unconfirmed current fact was faded.
- HG-SAYBACK — every say-back line has 0 CAS tokens and only the reading's own words plus "this replaces".
- HG-OFFLINE (harm) — 0 answers labelled EXACT whose source line was only in the stand-in cloud while it was offline.
- HG-HOLD (harm) — 0 answers served from a record in the Eye's HOLD log.
- HG-LIMIT — in every cube arm, working bytes after each turn's fading at or under the working limit, or the memory's flag names why (`OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX`).
- I17 — no observed line used more than 3 rounds (shadow rounds 4–6 are reported, never stored). The per-4-turn sweep is retired (A-TEACH2-15 T1), so the old "sweep period" part of I17 is void.
- The current-value scoring rule of pre-code §5 (Q1 a) replaces TEACH-1's "not"-only rule.

**P11. Seeds.** Bands above every band in use (CUBE TRAIN used 2,050 M and 2,051 M; A-CUBE-TRAIN-1 A3 reserved TEACH-2 above 2,052 M): WORLD 2,053,000,001–2,054,000,000; QUIZ 2,055,000,001–2,056,000,000; PERSON 2,057,000,001–2,058,000,000; TRAP 2,059,000,001–2,060,000,000. The used table names every range up to 2,052,000,000. Seeds by the house rule from `CUBE EXAM at 1 USD` and the sealed zip's sha256.

**P12. Practice before the seal (0 USD).** The builder runs practice worlds with rule-written practice turns (label `RULE_WRITTEN_PRACTICE`, practice seed texts). The arms without the CTT run on the laptop's CPU (no neural work). The CTT arms run on the laptop's own GPU (RTX 4070), the house rule's "smoke/dev only" use, on as few worlds as memory allows. Practice numbers are facts for FIX FIRST and decide nothing; a practice reading is always `INCONCLUSIVE` by I0.

**P13. The seal.** As TEACH-1: a freeze of every package file's sha256, a zip, the package tests run from a fresh extract, a backup to `D:/tksCAS-archive`. The zip is too big for git; the repo holds the freeze, the zip's sha256 and the builder tools. After the seal: a custodian session (not the builder) approves from the recorded line, draws, has the turns written by three model families and keyed by two others, and finishes; then `CUBE EXAM at 1 USD` runs on the GPU host; the frozen reader reads it.

**P14. Unchanged:** the arms' purposes, the marks C1–C4, U1/U2, S-SPACE (a)+(b), the status words and their order, the labels (`SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `CTT_RETRAINED_V1`, `EYE_REPORT_ONLY`), the licence ceiling. Every mechanism stays `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED`.
