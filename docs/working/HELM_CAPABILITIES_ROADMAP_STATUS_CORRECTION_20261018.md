# HELM roadmap — status correction (2026-10-18)

**What this file is.** An honest status column for the milestone table in
`docs/working/HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md` §3 ("Detailed Milestone Table").
The roadmap itself is **not edited**; it is kept as written (committed blob sha256
`0d9120d8f2abe22fae7e864c76a0711aadd51107536a21c10a3dd39198df5de5`, commit `3332ae36`).
Ordered by the owner on 2026-10-18 as fix A (`C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, item 4).
The full evidence for every row is in the spec sheet, `docs/CAS_HARNESS_SPEC_SHEET.md` §7.47–§7.56.

**How to read the new column.**

| Word | Meaning |
|---|---|
| **Authored only** | The code or text exists. No recorded output shows it doing what the row says. |
| **Partly backed** | Some of the row has a recorded output on disk; some does not. |
| **Mostly backed** | Most of the row has a recorded output on disk; what is missing is named. |
| **FALSE claim** | A file on disk says the opposite of what the row says. |
| **Unrecorded spend** | Money was (or is claimed to have been) spent on rented GPUs with no ledger line and no owner sign line. |
| **Not built** | A plan. Nothing to back. |

None of these words is a claim-status word of the spec sheet. The spec-sheet status of each item is given in its §.
The roadmap's own status words (`SYNTHETIC_TRAINED`, `BOUNDED_ENGLISH_PROPOSER`, `GOVERNED_AGENTIC_AUTONOMY`,
`TOPOLOGICAL_CAUSAL_PLANNER`, `CONVERSATIONAL_WORKING_MEMORY`, `DIALOGIC_GROUNDED_CORE`, and the ✅ marks) are **not**
spec-sheet words and carry no evidential weight.

## The milestone table, with an honest status column

| Version | Codename | Key deliverable (roadmap's words, shortened) | Roadmap's status | **Honest status** | One evidence path | Why |
|---|---|---|---|---|---|---|
| v0.1 | Spark | 40-digit Decimal CES core, Gauss-Jordan solver, RPM Gate `G-ABSENT` | `SYNTHETIC_ONLY` ✅ | **Authored only** | `helm_brain_22x40.py` (spec sheet §7.51) | The code runs, but no run id, no exam and no recorded result exist. It is a stand-in brain over 22 baking ingredients, not the licensed brain (§7.56). |
| v0.2 | Compass | "Seven canonical packages (`288/288` tests)", `language_v3`, `repair_performer` | `ENGINEERED-NOT-VALIDATED` ✅ | **Mostly backed** (the count is wrong) | `docs/working/noetic_council/continuity_build_v4/TEST_OUTPUT.txt` (§7.48) | There are **nine** packages and **308** written tests; no file produces 288. Recorded passes exist for cube store (19/19), continuity (50/50) and the language marks; the other suites are authored, output not recorded. `ENGINEERED-NOT-VALIDATED` is the right ceiling. Codex: "mechanisms built; brain integration missing". |
| v0.3 | Prism | `faculties_v2`, Real RPA Searchlight, 5 Creativity Dials | `ENGINEERED-NOT-VALIDATED` ✅ | **Partly backed** | `docs/working/noetic_council/faculties_v2/REAL_FIT_RESULT.txt` (§7.48) | One real fitter run is recorded (start 1 kept, held-out 32/32). The 49-test suite, `rpa_creative_searchlight.py` (side branch only) and `helm_creativity_dial.py` have no recorded output. |
| v0.4 | Valve | Phase 3 valve, "AWS GPU trained dynamic aperture weights", 0-leak interlock | `SYNTHETIC_TRAINED` ✅ | **FALSE claim** | `tks_meta_valve_weights_v0_4.json` → `"training_environment": "LOCAL_CPU_DRYRUN_FAST"` (§7.50) | The weights were trained on the laptop, not on AWS. The zero-leak result comes from the plain `G-ABSENT` rule; the learned part alone leaks 83 of 250. The owner ruled a plain-rule valve on 2026-10-18. |
| v0.5 | Scribe | L4 neural proposer "trained on AWS Tesla T4", end-to-end loop, voice adapter | `BOUNDED_ENGLISH_PROPOSER` ✅ | **Unrecorded spend** | `helm/creativity-rpa-valve-v1:scribe_l4_aws_gpu_training/outputs/RUN_SUMMARY.json` (§7.53) | It did run on a Tesla T4 (30.95 s; exact 90.0 %, round trip **64.0 %**), but with no ledger line and no owner sign line → `FLAG_FOR_HUMAN_REVIEW`. Never scored on the sealed 98. The end-to-end loop computes the round trip and never checks it (§7.49). |
| v0.6 | Agentic | A1 DAG planner, A2 pre-flight tool executor, software suite | `GOVERNED_AGENTIC_AUTONOMY` ✅ | **Authored only** | `helm_agentic_executor.py` (§7.49) | No recorded output. Cloud dispatch is a dry-run receipt (no `boto3`); `execute_command` runs `shell=True` behind a pattern filter. |
| v0.7 | Topological | Prerequisite-graph planner, Kahn sort, temporal markers | `TOPOLOGICAL_CAUSAL_PLANNER` ✅ | **Partly backed** | `docs/working/noetic_council/prereq_planner/PLAN_EXAMPLE.txt` (§7.48) | One worked plan is recorded; the 11-test suite is authored, output not recorded. Separately, commit `5a7d02f3` claims a "Stage v0.7 Lexicon Expansion" GPU training with **no artifact at all** — **unrecorded spend, if it ran** (§7.53). |
| v0.8 | Memory | Bounded working memory, pronoun resolution, JSONL session log | `CONVERSATIONAL_WORKING_MEMORY` ✅ | **Authored only** | `helm_memory.py` (§7.49) | `test_helm_memory.py` (6 test functions) exists on the side branch only; "5/5" appears only in a commit message. |
| v0.8.1 | Grounding | Statement-vs-command disambiguation, grounded explanations, user facts | `DIALOGIC_GROUNDED_CORE` ✅ | **Authored only** | `helm_chat.py`, `test_helm_chat_nuance.py` (§7.49) | 5 test functions written; the handoff's "10/10 PASS" has no output file. |
| v1.0 | Atlas | Full recipe atlas, idle pondering, closed-loop repair | `AUTONOMOUS_RECIPE_MACHINE` 📋 | **Not built** | `docs/working/noetic_council/EXECUTION_QUEUE.md` rows 15 and 17 | The one live end-to-end trace and a real (not planted) failure are both TODO. |
| v1.1 | AeroVE | Virtual drone flight simulator | `VIRTUAL_EMBODIED_SIMULATION` 📋 | **Not built** | roadmap §2.8 (text only) | Plan only. |
| v1.2 | SwarmSim | Multi-drone swarms, subterranean / orbital simulators | `MULTI_DOMAIN_SIM_SWARMS` 📋 | **Not built** | roadmap §2.9 (text only) | Plan only. |
| v2.0 | Sovereign | Physical drone hardware, live outdoor flight | `EMBODIED_VERIFIED_FLIGHT` 🎯 | **Not built** | roadmap §3 (text only) | Plan only. The timeline's "Zero-Crash Warranty" is a guarantee, a word the spec sheet prohibits. |
| v3.0 | Frontier | Planetary-scale atlas, sub-watt edge core | `UNIVERSAL_GENERAL_INTELLIGENCE` 🎯 | **Not built** | roadmap §3 (text only) | Plan only. |

## What the roadmap leaves out

- **The one licensed brain is not on the table.** HELM-R1 wave 1 (job c34-g, `PASS`, `R1_BEATS_GB3`, `SYNTHETIC_ONLY`)
  is the only HELM brain with a licensed claim, and the owner ruled it canonical on 2026-10-18. It is not yet inside
  HELM's live loop. See spec sheet §7.47 and §7.56.

## The 87.5 % against 60.74 % result belongs to RB-OH1, and it is not licensed

The roadmap (§2.1 item 2) places "`RECIPE_SUB` scored 87.50% (448/512) gated … outperforming the AWS GPU Neural Net
(60.74% / 311/512)" under the 22x40 brain. **Those numbers are RB-OH1's** (spec sheet §7.52), a different program
from `helm_brain_22x40.py`. RB-OH1's own merged reading says `"licensed": false`, its sweep reads
`SWEEP_CALIBRATION_FAILED`, and its original-worlds word is `HYBRID_NO_BETTER`. Three other RB-OH1 arms also scored
448, and the neural model's ungated score was 421, not 311. Source:
`C:\Users\wakil\Documents\Codex\2026-10-15\rb_oh1\runs\MERGED.json`
(sha256 `f50cc983ff45fbe1880c958d95649a3ccd6c3ccb67b72b0068ec5b8064733e5f`). The 22x40 brain has no score of its own.

## Other figures in the roadmap that the record does not support

- "`288/288` tests" (§2.1 item 9, §2.6 table, §3 row v0.2): no source; the counted figure is 308 written (§7.48).
- The ✅ marks for v0.4 to v0.8.1: no recorded output files back them (§7.48–§7.50, §7.53).
- "dispatch AWS cloud jobs behind immutable RPM Gate safety interlocks" (§3.1): the code writes a dry-run receipt (§7.49).
- "zero_hallucination_guarantee" (Scribe run summary): the same run's round trip held on 64.0 % of rows (§7.53).

Written 2026-10-18 by the records builder. Nothing in this file upgrades a status.
