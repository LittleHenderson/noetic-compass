# Fixes C and D — the licensed recipe brain wired into HELM's live loop (2026-10-18)

Owner approvals: `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` — "recipe brain is
canonical", "plain-rule valve", "start the fixes" (C and D). Laptop only, pure Python, 0 USD. Platform of every
number below: **Windows 11, Python 3.14.0** (not run on Linux).

Claim status of the wiring: **ENGINEERED-NOT-VALIDATED.** The brain's own license (c34 PASS `R1_BEATS_GB3`)
stays **synthetic worlds only**. Wiring it in does not extend that license to real kitchens or real data.

## What changed, per file

| File | Change |
|---|---|
| `helm_brain_canonical.py` (new) | Loads the licensed brain **by path** from `C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3` (override: env `HELM_CANONICAL_BRAIN_DIR`). Before import it checks `PACKAGE_FREEZE.json` sha256 `8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b` and the sha256 of each of the 17 loaded members against that freeze; it refuses on any mismatch or if a module loads from elsewhere. No source is copied. Loaded part: the Task B recipe book `rb2.brain_b.RecipeBookBrain`, its writer `rb2.writer_b.teach_step_b`, its algebra `rb2.compose`. |
| `helm_end_to_end_loop.py` | Rewritten around the circuit: CCE skin → S0 atlas head → S1 trigger ^8 → S2 Bias ^5 → S3 arrival ^9 → S4 operating point → S5 RPM link (real gate + real repair performer) → brain → store → S6 next. Every station writes a receipt line. The `Decimal("10")` fill is gone. The "verified: True when cce is missing" shim is gone. New teaching channel `witness_batch(...)`. New `run_live_trace()`. |
| `tks_meta_valve_controller.py` | The learned sigmoid aperture is removed from the deciding path. Written two-table rule in the docstring. Essential reagents come from the recipe's own prerequisite list (no Flour/Water hard-code). G-ABSENT kept. Labeled **ENGINEERED-NOT-VALIDATED**. `tks_meta_valve_weights_v0_4.json` kept as a historical file and **never opened**. |
| `helm_brain_22x40.py` | Labeled **DEMO STAND-IN**; `DEMO_STANDIN` and `IS_CANONICAL = False` added. The loop never imports it. |
| `test_helm_end_to_end_loop.py` | Replaced: 18 tests, one or more per change (list below). |
| `test_helm_chat_nuance.py` | Sequence B turn 3 updated: a free-English recipe request now gets a CLARIFY with zero writes and no invented amount, instead of the old "missing Water" answer. |

## Tests run (recorded output: `docs/working/traces/TEST_OUTPUT_WIRE_RECIPE_BRAIN_20261018.txt`)

- `test_helm_end_to_end_loop.py`: **Ran 18 tests, OK.**
  01 canonical brain is Station S0 (freeze and 17 member hashes match) · 02 cookie brain is a demo stand-in, never
  default · 03 torch-only parts not imported, blocker installed · 04 no invented quantity · 05 round trip checked ·
  06 round-trip mismatch → CLARIFY, zero writes · 07 missing checker → NOT_VERIFIED · 08 absent ingredient →
  UNDETERMINED/CLARIFY, zero writes · 09 real gate called with a real `GateRequest` (no label field) · 10 store
  write only after gate PROCEED and the read-back receipt · 11 repair child glues its ACTUAL result · 12 repair
  opens on a REAL detected failure · 13 valve written rule · 14 unparseable English → CLARIFY · 15 stated recipe
  not taken · 16 pantry read writes nothing · 17 kept paths and voice · 18 live trace.
- `test_helm_chat_nuance.py`: **5 passed.**
- `tks_meta_valve_controller.py` self-test: **3 written-rule cases PASS.**
- `repair_performer/test_all.py` (unchanged, regression): **RESULT: ALL PASS.**
- pyflakes on the 4 new or rewritten files: **clean.**

## The live end-to-end trace (EXECUTION_QUEUE row 15)

`docs/working/traces/HELM_LIVE_TRACE_20261018.jsonl` — 88 lines, sha256
`4f94ccee22ea9829072ebfd59fe7690f56d3f28f49527cf2f39b140283fe6fba` (also in the `.sha256` file beside it).
Made by `C:\Python314\python.exe -X utf8 -B helm_end_to_end_loop.py`.

| tick | what came in | result | cubes written |
|---|---|---|---|
| 1 | witnessed batch: 10 Flour, 8 Water → 5 Bread, Flour ran out | WITNESS_ADMITTED (Flour per Bread = 2) | 1 |
| 2 | witnessed batch: 10 Flour, 2 Water → 2 Bread, Water ran out | WITNESS_ADMITTED (Water per Bread = 1) | 1 |
| 3 | `There is 12 of Ω_Flour.` | INVENTORY_RECORDED | 2 |
| 4 | `Topic: Ω_Bread.` | **UNDETERMINED_CLARIFY** — Water is ABSENT; gate REPAIR; child found no stored Water; asks "How much Water is there?" | **0** |
| 5 | `How much bread could we bake with whatever is around?` | **CLARIFY_NOT_CCE** | **0** |
| 6 | `There is 9 of Ω_Water.` | INVENTORY_RECORDED | 2 |
| 7 | `Topic: Ω_Bread.` | SUCCESS_EVALUATED — 6 Bread, Flour runs out first | 1 (CHECKED) |
| 8 | witnessed batch: 10 Flour, 8 Water → 4 Bread, Flour ran out | **CONFLICT_UNDETERMINED** (real detected failure, below) | **0** |
| 9 | later session, same store and brain: `There is 20 of Ω_Flour.` | INVENTORY_RECORDED | 2 |
| 10 | later session: `Topic: Ω_Bread.` | gate REPAIR → child reads 9 Water from the store → glued → parent gate PROCEED → 9 Bread, Water runs out first | 1 |

## How the failure is now real (EXECUTION_QUEUE row 17)

Tick 8 reports a batch whose numbers say Flour per Bread is 10/4 = 5/2. The brain already holds 2 (from tick 1).
The brain's **own writer** (`rb2.writer_b.teach_step_b`, candidate rule witnessed_lr_ratio_v1) refuses it:
`refused_conflict`, old `2/1`, new `5/2`, reason `REFUSED_CONFLICT`. The loop turns that refusal into an
`RpmCause` naming the gap "a requirement of Ω_Flour for Ω_Bread that agrees with every witnessed batch"; the
real gate answers REPAIR; the real repair performer checks depth and runs the child, which replays all three
witnessed batches on a fresh brain through the same writer. The replay refuses the third batch again, so the
child returns not-ok, the repair disengages (`CHILD_REFUSED`), nothing is written, the learned state is unchanged,
and HELM asks which batch is right. No test or loop code sets a failure flag. Test 12 checks the detection record,
the cause the gate actually read, and a control batch that agrees (admitted, no repair opened).

## What this does NOT do, plainly

- **The licensed brain's world is small.** It has 8 stock cells and 4 recipes with a fixed, programmed layout.
  The everyday names (Bread = Flour + Water, Frosting = Sugar + Butter, Starter = Milk + Egg + Yeast, Meringue =
  Sugar + Egg + Salt) are a labeled naming map (OUR_CONVENTION, sha256 in every receipt). A product whose
  ingredients do not match one of the four layouts cannot be represented.
- **It never takes a stated recipe.** It learns each requirement only from a witnessed batch, one limiting
  ingredient per batch. That is the licensed brain's rule, not a choice made here.
- **Free English does not reach it.** Only checked-form (CCE) text does. Everyday-English input is fix E/F work.
  Until then a free-English recipe question gets a CLARIFY. `helm_chat.py` still has its own English inventory
  path that writes to the cube store outside this circuit — not changed here.
- **Teaching enters on a teaching channel** (`witness_batch`), not as a chat sentence: CCE has no batch-report form.
- **Torch:** nothing loaded needs torch. The torch-only parts of the package (`make_worlds.py`, `t_on_b/`,
  `t_task_a/score_t.py`, `r1/t_gb_check.py`) are never imported. Side effect: importing the brain installs the
  package's own blocker, so the same process then refuses `import torch` / `import numpy`.
- **The repair_performer demonstration itself is unchanged** (its README still says its own demo failure is
  planted). The real detected failure now runs in the live loop, not in that demo.
- The Atlas return address (trigger spec step 2) is still not wired; S0 here is the brain's address map, not the
  Real Atlas.
- The agentic-goal path and free-English cube-store reads are outside the circuit and unchanged.
