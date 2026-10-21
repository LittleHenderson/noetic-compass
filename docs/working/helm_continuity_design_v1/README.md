# HELM continuity design packet v1 — the station path wired into the live chat behind one switch, and the sealed exam that would earn it a word (2026-10-20 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every mechanism this packet names (the loop v3, the return address, continuity v4, the live loop, the chat) keeps its claim status `ENGINEERED-NOT-VALIDATED`. No claim moved. No file outside this folder, `CHANGELOG.md`, the spec sheet (§7.99 and the §11 row) and the rebuilt hub site was changed. No `.py` file was changed.

Owner's order (2026-10-20): "continuity packet". Owner's idea (2026-10-15): "LIKE INTERRUPTING A PERSON WHILE THEY DEEP IN THOUGHT OR ASKING SOMEONE TO THINK ABOUT SOMETHING". Owner ruling (2026-10-15): "RPA IS ATLAS" (the Recursive Possibility Atlas; spec sheet §7.35 tail).

## What this packet is, in plain words

Today HELM thinks in one pass per line and nothing is ever left in progress, so it cannot be interrupted and cannot pick a thought back up. This packet designs a **thread**: a thought with an Atlas anchor, a station path and steps left; a **cut** when a person types (the thread stops at its station boundary, the line is answered exactly as today); and a **resume by return address** afterwards (a six-field exact coordinate, never "what was I doing"). If the line changed a fact the thread relied on, the thread goes dirty and restarts honestly. All of it sits behind one switch, `HELM_CONTINUITY`, default OFF.

The exam beside it makes the cheap baseline a real threat: if saving the last claimed line of chat and starting over resumes as well as the path does, the status word is `CONTINUITY_NO_GAIN`.

## Files

| File | What |
|---|---|
| `README.md` | this page |
| `DESIGN_CONTINUITY_V1.md` | the wiring: switch, thread as data, interrupted / resume / cut defined, the exact hooks, the sequencing rule against wave 7 |
| `PREREGISTRATION_CONTINUITY_V1.precode.md` | the sealed-exam design: question, arms, worlds, families, hard gates, marks with frozen numbers, status words, licence ceiling, forecast, seeds, cost |
| `PREREGISTRATION_CONTINUITY_V1.precode.sha256` | the sha256 of the precode file |
| `OPEN_QUESTIONS.md` | the twelve decisions that are the owner's, each with a one-line recommendation |

## The hash

`PREREGISTRATION_CONTINUITY_V1.precode.md` sha256 `611235f3ad5764dd9147d329d59d69f21414ecad4020b7f823d719da6f77118b` (20,813 bytes).

## The short version of the exam

- Arms: **CONT_ON** (under test), RESTART_BLANK (throw the thread away), RESTART_LAST_LINE (restart from the last line the loop claimed; the cheap threat), CONT_OFF (today's live loop and chat), CONT_ON_REPLAY, CONT_ON_NOINT (the uninterrupted reference).
- Worlds: 64 synthetic chat worlds, 16 each in F-A small talk, F-B unrelated stock, F-C cited stock (must go dirty, never resume), F-D two threads; drawn blind by a custodian from bands WORLDS 1,996,000,001 to 1,997,000,000 and INTERRUPT 1,998,000,001 to 1,999,000,000.
- Marks: CUT (0 thread work inside any person's turn, 64 of 64; it can fail), CONV (every reply equal to CONT_OFF's), DIGEST (brain digests equal to the uninterrupted run), PLACE (resumed to the saved station by exact address, >= 46 of 48), RESUME (>= 46 of 48), ANSWER (>= 46 of 48 and >= 14 of 16 after a dirty restart), THREAT (beats RESTART_LAST_LINE by >= 12 answers and >= 32 station crossings).
- Status words, frozen order: `INCONCLUSIVE`, `CONTINUITY_HARMED`, `CONTINUITY_NO_GAIN`, `CONTINUITY_EARNED_KEEP`.
- Cost: laptop first, 0 USD (units at or under 300 MiB, at least 400 MiB free at start); AWS only if that rule fails, cap 1.00 USD, owner's line to sign `CONTINUITY at 1 USD`.

## Sequencing against wave 7 (§7.98)

Chosen: the two-file wiring (`helm_end_to_end_loop.py`, `helm_chat.py`) does not land before the wave 7 chat test (sealed v3 on HELM cut `dfc7158d`) has run, been scored, and been written onto the spec sheet. Reason: wave 7 is the first sealed exam of the chat and one chat change at a time keeps its reading clean. Honest note: at thread head `81098868` the cut is already not byte-identical for `helm_end_to_end_loop.py` (PR #417); `helm_chat.py` still is (`3076128f…`). A wrapper form that touches neither file is offered as Q1, not chosen.

## Sources read

Spec sheet §7.35, §7.48, §7.49, §7.56, §7.69, §7.78, §7.96, §7.98; `CONTINUITY_AND_DISENGAGE_20261016.md`; `docs/working/noetic_council/the_loop_v3/` (README, `loop.py`, `rpm_gate.py`, `asom.py`, `bias.py`); `.../return_address/` (README, `address.py`, `stack.py`, `dirty.py`, `atlas_binding.py`); `.../continuity_build_v4/` (README, `continuity.py`, `stations.py`, `atlas_adapter.py`, `provenance.py`, `disengage.py`); `helm_end_to_end_loop.py` (`__init__`, `process_turn`, `wants_turn`, `_emit`, `_finish`); `helm_chat.py` (`handle_turn`, `_speak`); `Documents\Codex\2026-10-15\helm_language_faculties_circuit_design_v1\` (house format); `Documents\Codex\2026-10-20\r1_wave7\PREREGISTRATION_R1W7.precode.md` (house format, bands, custody rule).
