# PREREGISTRATION LM-T4b — LM-T4 rerun under a reader sealed before the run, with the digit-and-eye-rows fix

Written 2026-10-20 (laptop, 0 USD) BEFORE any part of this rerun ran. Owner's order (verbatim, 2026-10-20):
"the LM-T4 corrected reading. rerun under a sealed reader with the bug fix".

## 1. The question

LM-T4 (spec sheet section 7.35; off-repo package `C:\Users\wakil\Documents\Codex\2026-10-15\lm_t4\`) asked whether the
recipe brain's thought can be read out in exact Controlled CAS English at every station of its path, with a receipt at
each station and no change to any answer, and whether a planted utterance starts the planted faculty at the planted
station while shuffled utterances start nothing. Its sealed reader (`merge_t4.sealed.py`, sha256
`37f4a0e09fe325ec80c4e0993431a9486c26fa29649cd83c21c56eb8b064e6b2`) read `INCONCLUSIVE` because of two reader
defects; a corrected reader applied after the run (amendment LMT4-A3) read the status words, but a post-run change to the
reading program is exactly what the governance rule forbids an agent to self-accept.

LM-T4b asks the same question again with the SAME run code and a reader that is fixed and sealed BEFORE any part runs,
so that the reading is not post-hoc. Precedent: section 7.25 (RB2b `INSTRUMENT_ERROR`) to section 7.26 (RB2c clean
rerun with the reader fix).

## 2. What is the same as LM-T4 (copied exactly; `FROZEN_LMT4B.json` carries LM-T4's `FROZEN.json` content verbatim)

- Run code byte-identical: `__init__.py`, `stations.py`, `tap_inject.py`, `continuity.py`, `eye_report_only.py`,
  `arms.py`, `run_t4.py`, `worker.py`, `test_lm_t4.py`, `static_check.py`, `supervisor.ps1`, `run_all_parts.ps1`,
  `PLAN.json`, `OWNER_APPROVAL_EVIDENCE.template.md`, `OWNER_APPROVAL_EVIDENCE.md`; `rb_i1` (`drives.py`,
  `faculties.py`, `dialogue.py`, `FROZEN.json`, `PLAN.json`, `__init__.py`) copied unchanged; every other import
  (RB2c brain, lm_t1, lm_t2, lm_t3, lacunarity machine, SDG bridge, the site compiler, the c25 / c26 references,
  the design packet) read in place, hash-verified by the supervisor and the worker before any part runs.
- Arms: A1 (circuit-carried: taps at every station, injections at the keyed station, eye report-only), A1_NOTAP,
  A1_NOEYE, A1_REPLAY, A2 (end-skin: utterances handled at the next thought boundary), A3 (LM-T2 dialogue path),
  A4 (dumb baselines: JSON dump, name-match injector, ask-rule), A5 (shuffled utterances, derangement seed 11), REF
  (the imported RB2c driver), A3_REF (imported t2.run_arm).
- Worlds: Task B 20 draws (draws 0-19, the same worlds as c25 / c26, C25_EQUALITY checked); dialogues seeds 11, 29,
  47 (48 worlds, 1,152 turns); calibration seed 5; 7 utterances per dialogue world, 5 keyed (QUESTION, THINK, NO, FACT,
  CONTRADICTION) + UNPARSEABLE + MISSING_FACT = 336 utterances, 240 keyed.
- Parts: P11-P18, the same units per part as LM-T4's `PLAN.json` (plan version `lm-t4-plan-2`), one worker process at
  a time, hard wall 300 s per part, worker guard 280 s, working-set cap 300 MiB (314,572,800 B), free RAM >= 150 MB at
  launch (wait up to 10 min), sockets blocked, host MSI, `C:\Python314\python.exe`, no network, no AWS, no spend.
- Seeds: LM-T4's `FROZEN.json` fixes every seed (Task B draws 0-19 from the c25 selection; dialogue seeds 11 / 29 / 47;
  calibration 5; derangement 11; dev seed 97 never scored). No seed is derived from a package hash, so the seeds are
  unchanged.
- Hard gates (14, as LM-T4): H1 receipts, H2 no invention, H3 replay, H4 provenance, H5 readout isolation, H6 controls
  (twin and shuffled b_chain <= 6; A5 keyed starts 0; A5 CREATED 0), H7 RB today reproduced (medians 16 and 16;
  REF == c26 rb_det; LM-T2 counts 96 / 96, 48 / 48, false 0, walks 24 / 24, no-walk 0 / 24, lacuna moves 144 / 144,
  invented 0, receipts 100%), H8 budget (512 keyed ticks per draw; <= 4,096 station ticks per dialogue world), H9 tap
  digest, H10 questions carry no value, H11 tests (12 of 12 in every part), no deadline hit, all units present
  (and the worlds check).
- Marks and thresholds (as LM-T4): TAP-1 round trip 100% of taps that said something; TAP-2 digest unchanged 100%;
  TAP-3 answers unchanged 20 of 20 draws and 48 of 48 worlds; TAP-4 FORM gaps (report only); INJECT-1 >= 228 of 240;
  INJECT-2 = 0 of 240; INJECT-3 CLARIFY 48 of 48, KNOWLEDGE_MISSING naming the slot 48 of 48, invented facts 0;
  INJECT-4 A1 earlier than A2 (bookkeeping); CONT-1 seams 96 of 96, tone 48 of 48, false 0; CONT-2 walks 24 of 24,
  no-walk false fires 0 of 24; CONT-3 provenance keys 100% (frozen); CONT-4 restlessness (report); ANSWER-1 Task B
  medians 16 and 16; ANSWER-2 NOT_EVALUATED (PRC-1); RECEIPTS-1 100%, deepest level <= 5; EYE-R1 one reading per
  stage end; EYE-R2 digest unchanged on every eye read; EYE-R3 the eye's receipt 100%; EYE-R4 (report); EYE-R5 door
  calls 0.
- Status-word order (as LM-T4's `status_word_rule`, computed by the reader from counts only): a failed hard gate ->
  `test_verdict` FAILURE and only `INCONCLUSIVE` with the failing gates named; else `LANGUAGE_RODE_THE_PATH` (all hard
  gates AND TAP-1, TAP-2, TAP-3, RECEIPTS-1 at 100% AND ANSWER-1 in A1), `INJECT_ROUTED` (INJECT-1 >= 228 AND
  INJECT-2 = 0 AND INJECT-3 at its marks), `CIRCUIT_EARLIER_NOT_BETTER` (INJECT_ROUTED AND INJECT-4 AND no A1 / A2
  difference on ANSWER-1; ANSWER_2 NOT_EVALUATED written beside it), `CIRCUIT_CHANGED_AN_ANSWER` (not a pass word),
  `VERIFY_DID_THE_WORK` NOT_EVALUATED, `INCONCLUSIVE` when none of the first three is awarded, `EYE_REPORTED` beside
  any of the above when EYE-R1, R2, R3 and R5 hold.
- Claim ceiling: SYNTHETIC_ONLY; FORM-only language claims (CCE v0.1c-R is a grammar, not a learned parser); no HELM
  claim; 0 learned parameters added.

## 3. The one change: the reader

`merge_t4b.py` = `merge_t4.sealed.py` + exactly the two fixes of LMT4-A3 (see `READER_FIX_DIFF.md`):
1. gates H2 / H10: a digit inside a copied outcome name (`Ω_zz0`, `Ω_decision_11`) is not "a value"; only a number
   token outside an `Ω_<name>` identifier counts;
2. mark EYE-R1: the twin brain's eye events, whose rows are not stored, count when their eta/epsilon receipt passed.

Nothing else in the reader changes. The post-run reader's extra per-brain breakdown of provenance mismatches is NOT
taken (reporting, not a defect).

NOT changed on purpose: the run-time defect behind mark CONT-3 (the run code writes the key CREATED instead of
ATTEMPTED on the untaught twin's asking crossings; 80 of 106,400 in LM-T4). The owner's order covers the reader fix
only; that defect lives in the run code, which stays byte-identical, so CONT-3 reads whatever it reads. If the run
repeats exactly, CONT-3 will read 106,320 of 106,400 (99.92%) and FAIL under the frozen 100% rule; it does not feed
any status word.

## 4. What is NOT licensed whatever the reading says

- No claim that language was carried across an RPA: the owner ruled on 2026-10-15 "RPA IS ATLAS I MEANT ATLAS"
  (the Recursive Possibility Atlas); LM-T4 read S0 as the RPM chain per CJT, and so does this rerun.
- No meaning claim (FORM-only); no HELM claim; nothing beyond SYNTHETIC_ONLY.
- "Better answers from the circuit": it ties on every answer by design ("earlier, not better").
- The LSR-family half (ANSWER-2, VERIFY_DID_THE_WORK): NOT_EVALUATED (PRC-1).
- The eye's judgement: report-only.
- The old corrected reading (LMT4-A3, `8606c5aa4ef45a6dccb4fc40337e3f967ff88f079a386424b6d9520a1c416bc8`) stays on
  the record as a note and never counts.

## 5. Forecast (written before the run)

Same run code, same seeds, same worlds: every instrument number should repeat exactly (TAP-1 64,756 of 64,756;
TAP-2 106,400 of 106,400; INJECT-1 240 of 240; INJECT-2 0 of 240; CONT-1 96 of 96; CONT-3 106,320 of 106,400;
RECEIPTS-1 106,400; EYE-R1 A1 6,716 = 6,436 rows + 280 twin events verified by receipt; EYE-R4 HELP 504 on A1
no-walk dialogues). With the two reader fixes sealed first, the forecast is: all 14 hard gates true, status words
`LANGUAGE_RODE_THE_PATH`, `INJECT_ROUTED`, `CIRCUIT_EARLIER_NOT_BETTER (ANSWER_2 NOT_EVALUATED)`, `EYE_REPORTED`;
mark CONT-3 FAIL at 99.92%. Any number that differs from LM-T4's table is a finding, reported, never smoothed.
Confidence about 0.8 that every number repeats exactly (the code is deterministic and seeded; the risk is an
environment difference on the same laptop).

## 6. Seal and launch

The package `LM_T4B_20261020_SOURCE.zip` is hashed before any run; `PACKAGE_FREEZE.json` holds every member's sha256;
`SOURCE_MANIFEST.json` (inside the package) is the supervisor's and the worker's drift check; the sign line is composed
by the operator from the owner's order, in LM-T4's form: `APPROVE lm_t4, source <manifest sha256 first 8>,
LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.` (not an owner signature; it promotes no claim). The parts run one at a time
from a fresh extract of the zip. The reader runs once, from the extract, after the eight parts.
