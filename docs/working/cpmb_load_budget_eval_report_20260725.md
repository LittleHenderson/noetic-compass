# CPMB Load Budget — Eval Report

Generated: `2026-07-26T06:49:07.877752+00:00`
Reviewer identity: `claude_opus5_local_reviewer_20260725`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Receipt targeted: `power_board_burnout_prevention_claim__cpmb_load_budget_eval_pass`
Result: `MIXED`
Gate-behaviour cases passed: `42/42` (a failure here would mean a gate is wrong)
Book-defect cases passed: `29/29` (a failure here means the published text is wrong)
Machinery cases passed: `56/56`
Book-consistency cases passed: `15/15`
Unenforced properties / limits found: `11`

Every case is classified by what its failure would mean. A **gate-defect** case
tests whether a gate the repository implements behaves correctly — adversarial
weakenings, in-range boundaries, false-positive controls, authority flags,
repeatability. A **book-defect** case tests whether the published text is
correct — the published listings, the published yield table, and the
cross-reference consistency assertions. `MIXED` is reported when every
gate-behaviour case passes and the only failures are in the published text.

## Headline Findings

**11 unenforced propert(y/ies) or limit(s).** Each carries a disposition below; none was waived:

- `cpmb_budget_negative_rail_supply` — hoped rejected_or_flagged; observed accepted; Y_T=-2.0
- `cpmb_budget_duplicate_rail_prerequisite` — hoped rejected_or_flagged; observed accepted; prerequisite_count=3 vs excess_capacity_count=2
- `cpmb_recipe_out_of_range_drive_f0` — hoped rejected; observed accepted
- `cpmb_recipe_out_of_range_drive_f9` — hoped rejected; observed accepted
- `cpmb_recipe_duplicate_prerequisite` — hoped rejected; observed accepted
- `cpmb_component_negative_dropout` — hoped rejected; observed accepted
- `cpmb_component_dropout_far_above_range` — hoped rejected; observed accepted
- `cpmb_beta_scale_derates_unenforced` — hoped rejected or ERROR-flagged; observed parsed beta=1000000000.0; CRC severities=['CRC-007/CrcSeverity.WARN']
- `cpmb_precedent_sibling_key_satisfied_by_unrelated_suite` — hoped a brownout-specific test suite; observed pcba_readiness.py maps it to pcba_tests_pass, i.e. the pass status of tests/test_pcba_models.py, which contains 0 brownout/thermal/dropout/budget/rail
- `cpmb_additive_energy_budget_unimplemented` — hoped a rail-capacity / additive-draw implementation to run against; observed no such object exists; NOT RUN
- `cpmb_overcommit_predicate_supplied_by_this_eval` — hoped a shipped overcommit threshold or flag; observed no threshold, flag or predicate exists; yield_calc returns a number only

## What "load budget" means here

Chapter 22 uses the phrase in two non-equivalent senses, and the distinction
governs this whole report.

**Form (a) — the recipe budget** (Ch22:302-318). `Θ(Ω_session) = 2.0·F3 +
1.0·F6 + 1.0·F7`, with `Y_T = min(xᵢ/aᵢ)` and a limiting reagent. This form is
backed by real, runnable machinery: `cas-engine/src/scoring/yield_calc.rs`. It
was executed against that engine and its published numbers reproduce exactly.

**Form (b) — the additive energy budget** (Ch22:243-249 and Exercise 22.4 at
Ch22:407-413). Rail capacity in amp-hours, per-transition draw `E = β·d_FR`
summed across firing stages, `time = capacity / draw`. **This form has no
implementation anywhere in the repository and was not run.** Recomputing
`10 A·h / 2.5 A = 4 h` inside the eval script would have tested the script's own
arithmetic, not the framework. That is the fake pass this eval exists to avoid.

## Scope

1. **Behavioural, in the narrow honest sense.** The recipe load budget is
   executed against the shipped Rust yield calculator — `theoretical_yield`,
   `limiting_reagent`, `excess_capacity`, `efficiency`. These are runtime
   executions of the framework's own arithmetic engine producing numbers that
   could contradict the book. Cases cover the book's own published table, a
   budget balanced at exactly 100 percent, an overcommitted budget, an
   epsilon-below-balance boundary, an epsilon-above and a generously-supplied
   false-positive control, a missing rail, and efficiency including the
   zero-yield NaN convention.
2. **Structural.** Every machine-checkable line of the published board is run
   through the real PCBA parser, the real CAS compiler, the real `DialConfig`
   schema, the real CJT parser and the real CRC linter, with adversarial
   weakenings and in-range false-positive controls on each.
3. **Book internal consistency.** Assertions computed by reading the book files
   themselves — not hardcoded — across Chapter 22, Chapter 14, Appendix C,
   Appendix D and Appendix E. Every failure is recorded as a book finding.

The yield engine is not reachable from Python: the installed `cas_engine` wheel
predates CAS v7.6 and exports no `Recipe`, `StateVector`, `Yield` or
`LimitingReagent`. This script therefore generates a throwaway cargo integration
test inside the `cas-engine` package, runs it, parses its stdout and deletes it.
The functions exercised are the shipped ones; nothing is reimplemented.

## Out of scope, deliberately

**There is no model in the loop.** Nothing here measures a deployed cognitive
system, and nothing here licenses a claim about deployed behaviour. Chapter 22
says the same at Ch22:9 and Ch22:373: every voltage, amp, amp-hour, temperature
and timing in that chapter is a design model, not telemetry.

Specifically **not** established by this run:

- **The additive energy budget was not run.** No rail-capacity object, no
  amp-hour quantity, no reservoir, no additive-draw accumulator exists in
  `cas-forex`, `cas-engine` or the `noetic-compass` api. The reading of "load
  budget" that means "sum the allocated loads against available supply" cannot
  be tested against shipped machinery at all.
- **Brownout detection was not tested.** There is no F3 rail level, no 2.5/3.5
  trip-release pair, no hysteresis state machine and no rest-state routing
  anywhere in the repository.
- **Thermal management was not tested.** There is no temperature model, no
  three-tier escalation, no 300-second timer, no cutoff action and no safe
  state.
- **Startup sequencing was not tested as behaviour.** The CRC check in this run
  is a static structural check over a transcribed chain. Nothing holds a rail
  low, nothing reports power-good, and no gate is evaluated at runtime.
- **The β derates were not tested.** The 0.5 brownout derate (Ch22:144) and the
  0.75 thermal derate (Ch22:222) have no implementation; nothing applies or
  bounds them.
- **The CPMB board as published cannot be compiled as a whole.** No CCDL parser
  exists in the repository. `pcba_syntax` parses `Component< … >` expressions
  only; `cjt_syntax` parses `CJT< … >` only; the CAS compiler parses CAS
  expressions and v7.6 recipes. Nothing parses `circuit { … }`, `rail`, `dial`,
  `spec`, `monitor`, `on { }`, `sequence`, `gate`, `constraint`, `use` or
  `probe`. Roughly a dozen lines of the published board are machine-checkable.
  Appendix_C:7 is candid about this — the compiler is a design, not a shipped
  runnable pass.
- **The "overcommitted" reading is this eval's own.** `yield_calc` returns a
  number; it never flags, raises or compares against 1.0. See the gap of that
  name below.
- **This run does not upgrade the CPMB claim.** The owner review at
  `docs/working/pcba_owner_claim_review_20260725.md:40-46` approved the CPMB as
  an architectural description and analogy only, and this artifact does not
  change that. It also does not sign the receipt.

## Pass/Fail Thresholds

- Gate-behaviour case pass rate must be `1.0` — every gate the repository
  implements must behave as the case specifies, in **both** directions: the
  adversarial weakening rejected, and the in-range or published value accepted.
- Book-defect case pass rate must be `1.0` for a headline of `PASS`.
- Board authority flags must all read false, and
  `cpmb_load_budget_eval_pass` must remain in `missing_evidence`.
- Float comparisons are exact-first with a `1e-12` relative fallback, so no case
  can be passed by a generous epsilon at the 100-percent boundary. The
  epsilon-below-balance case additionally asserts `Y_T < 1.0` strictly and the
  epsilon-above case asserts `Y_T > 1.0` strictly.
- The run carries an in-band falsifiability control
  (`cpmb_harness_detects_injected_errors`): four deliberately wrong
  expectations are pushed through the same comparison helpers the real cases
  use, and all four must be detected. A suite whose cases cannot fail proves
  nothing.

## Behavioural Cases — the recipe load budget against the real yield engine

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `cpmb_budget_book_published_case` | `yield_engine_published` | {"excess_capacity": {"F3Vitality": 0.0, "F6Structure": 0.5, "F7Purpose": 1.5}, "limiting_reagent_entries": [[" | Y_T=1.5; LR_kind=Primitive; LR_entries=[['F3Vitality', 1.5]]; excess={'F3Vitality': 0.0, 'F6Structure': 0.5, ' | `true` |
| `cpmb_budget_balanced_at_exactly_100pct` | `yield_engine` | {"excess_capacity": {"F3Vitality": 0.0, "F6Structure": 0.0, "F7Purpose": 0.0}, "limiting_reagent_entries": [[" | Y_T=1.0; LR_kind=Multiple; LR_entries=[['F3Vitality', 1.0], ['F6Structure', 1.0], ['F7Purpose', 1.0]]; excess= | `true` |
| `cpmb_budget_overcommitted_f3` | `yield_engine` | {"limiting_reagent_entries": [["F3Vitality", 0.95]], "limiting_reagent_kind": "Primitive", "theoretical_yield" | Y_T=0.95; LR_kind=Primitive; LR_entries=[['F3Vitality', 0.95]] | `true` |
| `cpmb_budget_epsilon_below_balance` | `yield_engine` | {"limiting_reagent_entries": [["F3Vitality", 0.9999999995]], "limiting_reagent_kind": "Primitive", "theoretica | Y_T=0.9999999995; LR_kind=Primitive; LR_entries=[['F3Vitality', 0.9999999995]]; Y_T<1.0=0.9999999995 | `true` |
| `cpmb_budget_epsilon_above_balance_false_positive` | `yield_engine` | {"limiting_reagent_entries": [["F3Vitality", 1.0000000005]], "limiting_reagent_kind": "Primitive", "theoretica | Y_T=1.0000000005; LR_kind=Primitive; LR_entries=[['F3Vitality', 1.0000000005]]; Y_T>1.0=1.0000000005 | `true` |
| `cpmb_budget_generously_supplied_false_positive` | `yield_engine` | {"excess_capacity": {"F3Vitality": 0.0, "F6Structure": 2.0, "F7Purpose": 2.0}, "limiting_reagent_entries": [[" | Y_T=2.0; LR_kind=Primitive; LR_entries=[['F3Vitality', 2.0]]; excess={'F3Vitality': 0.0, 'F6Structure': 2.0, ' | `true` |
| `cpmb_budget_missing_rail_is_zero` | `yield_engine` | {"limiting_reagent_entries": [["F3Vitality", 0.0]], "limiting_reagent_kind": "Primitive", "theoretical_yield": | Y_T=0.0; LR_kind=Primitive; LR_entries=[['F3Vitality', 0.0]] | `true` |
| `cpmb_budget_efficiency_on_published_case` | `yield_engine` | {"efficiency": 0.7999999999999999, "theoretical_yield": 1.5} | Y_T=1.5; efficiency=0.7999999999999999 | `true` |
| `cpmb_budget_efficiency_nan_on_zero_yield` | `yield_engine` | {"efficiency": "NaN", "theoretical_yield": 0.0} | Y_T=0.0; efficiency=nan | `true` |

## Structural Cases

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `cpmb_recipe_ch22_305_verbatim` | `published_recipe` | compiles valid=True | valid=True | `true` |
| `cpmb_recipe_inline_drive_gloss_rejected` | `false_positive_control` | compiler rejects | valid=False | `true` |
| `cpmb_recipe_ch14_csb_cross_check_control` | `false_positive_control` | compiles valid=True | valid=True | `true` |
| `cpmb_recipe_negative_coefficient` | `adversarial` | compiler rejects | valid=False | `true` |
| `cpmb_recipe_zero_coefficient` | `adversarial` | compiler rejects | valid=False | `true` |
| `cpmb_published_regulator_p_reg` | `published_board` | accepted | accepted | `true` |
| `cpmb_published_regulator_c_reg` | `published_board` | accepted | accepted | `true` |
| `cpmb_published_regulator_e_reg` | `published_board` | accepted | accepted | `true` |
| `cpmb_published_regulator_o_reg` | `published_board` | accepted | accepted | `true` |
| `cpmb_published_node_p_rail` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_c_rail` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_e_rail` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_o_rail` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_rest_idle` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_rest_land` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_published_node_deep_rest` | `published_board` | compiles valid=True | valid=True | `true` |
| `cpmb_component_tolerance_lower_boundary` | `in_range_boundary` | accepted | accepted | `true` |
| `cpmb_component_tolerance_upper_boundary` | `in_range_boundary` | accepted | accepted | `true` |
| `cpmb_component_tolerance_above_range` | `adversarial` | rejected | rejected | `true` |
| `cpmb_component_tolerance_negative` | `adversarial` | rejected | rejected | `true` |
| `cpmb_component_invalid_noetic_leaf` | `adversarial` | rejected | rejected | `true` |
| `cpmb_component_invalid_drive_leaf` | `adversarial` | rejected | rejected | `true` |
| `cpmb_component_invalid_register_leaf` | `adversarial` | rejected | rejected | `true` |
| `cpmb_dial_ch22_published_six` | `published_board` | accepted | accepted | `true` |
| `cpmb_dial_divergence_exactly_four_legal` | `in_range_boundary` | accepted | accepted | `true` |
| `cpmb_dial_nonpair_wide_spread_false_positive` | `false_positive_control` | accepted | accepted | `true` |
| `cpmb_dial_pair_co2_co3_divergence_six` | `adversarial` | rejected | rejected | `true` |
| `cpmb_dial_pair_co5_co6_divergence_six` | `adversarial` | rejected | rejected | `true` |
| `cpmb_dial_pair_co8_co9_divergence_six` | `adversarial` | rejected | rejected | `true` |
| `cpmb_dial_below_floor` | `adversarial` | rejected | rejected | `true` |
| `cpmb_dial_above_ceiling` | `adversarial` | rejected | rejected | `true` |
| `cpmb_crc_published_sequencer_clean` | `crc_static` | 0 ERROR findings | 0 ERROR, 0 total | `true` |
| `cpmb_crc_negative_control_domain_skip` | `crc_negative_control` | CRC-003 ERROR raised | CRC-003/CrcSeverity.ERROR | `true` |
| `cpmb_crc_negative_control_fuse_downstream` | `crc_negative_control` | CRC-008 ERROR raised | CRC-008/CrcSeverity.ERROR | `true` |
| `cpmb_crc_false_positive_fuse_upstream` | `crc_negative_control` | no findings | 0 findings | `true` |
| `cpmb_crc_coded_board_clean` | `crc_static` | 0 ERROR findings | 0 ERROR, 0 total | `true` |
| `cpmb_beta_published_unity` | `cjt_gain_bounds` | accepted | accepted | `true` |
| `cpmb_beta_negative_rejected` | `cjt_gain_bounds` | rejected | rejected | `true` |
| `cpmb_beta_non_finite_rejected` | `cjt_gain_bounds` | rejected | rejected | `true` |
| `cpmb_beta_zero_allowed` | `cjt_gain_bounds` | accepted | accepted | `true` |
| `cpmb_authority_not_ready` | `authority` | flag=false | flag=False | `true` |
| `cpmb_authority_cannot_affect_live_trading` | `authority` | flag=false | flag=False | `true` |
| `cpmb_authority_cannot_create_broker_accept` | `authority` | flag=false | flag=False | `true` |
| `cpmb_authority_receipt_still_unsigned` | `authority` | cpmb_load_budget_eval_pass in missing_evidence | missing | `true` |
| `cpmb_harness_detects_injected_errors` | `falsifiability` | 4/4 injected errors detected | 4/4 detected | `true` |
| `cpmb_per_transition_energy_components_exist` | `energy_model` | d_FR > 0 and beta parsed | d_FR=0.37010922261959667 beta=2.0 E=0.7402184452391933 | `true` |
| `cpmb_yield_engine_repeatability` | `repeatability` | identical records | identical | `true` |

## Book Internal-Consistency Cases

These are computed by reading the book files, so they will flip to `true` if the
text is corrected.

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `cpmb_book_ch22_dropout_rail_p_reg` | `book_consistency` | dropout on F7 | dropout on F7 | `true` |
| `cpmb_book_ch22_dropout_rail_c_reg` | `book_consistency` | dropout on F2 | dropout on F2 | `true` |
| `cpmb_book_ch22_dropout_rail_e_reg` | `book_consistency` | dropout on F6 | dropout on F6 | `true` |
| `cpmb_book_ch22_dropout_rail_o_reg` | `book_consistency` | dropout on F5 | dropout on F5 | `true` |
| `cpmb_book_appd_dropout_rail_p_reg` | `book_consistency` | dropout on F7 | dropout on F7 | `true` |
| `cpmb_book_appd_dropout_rail_c_reg` | `book_consistency` | dropout on F2 | dropout on F2 | `true` |
| `cpmb_book_appd_dropout_rail_e_reg` | `book_consistency` | dropout on F6 | dropout on F6 | `true` |
| `cpmb_book_appd_dropout_rail_o_reg` | `book_consistency` | dropout on F5 | dropout on F5 | `true` |
| `cpmb_book_ch14_bench_note_scale_claim` | `book_consistency` | trip=4.2V release=5.4V | trip=4.2V release=5.4V | `true` |
| `cpmb_book_ch22_trip_inside_ch14_band` | `book_consistency` | fraction inside [0.3, 0.4] | fraction = 0.3500 | `true` |
| `cpmb_book_hysteresis_gap_consistency` | `book_consistency` | gap = 1.2V | gap = 1.2V | `true` |
| `cpmb_book_appendix_e_gate_matches_ch22` | `book_consistency` | tolerances {'p_rail': '0.10', 'c_rail': '0.15', 'e_rail': '0.20'} | tolerances {'p_rail': '0.10', 'c_rail': '0.15', 'e_rail': '0.20'} | `true` |
| `cpmb_book_ch14_gate_gates_all_three_domains` | `book_consistency` | gates p_rail, c_rail, e_rail | gates ['c_rail', 'e_rail', 'p_rail'] | `true` |
| `cpmb_book_ccdl_statement_forms_documented` | `book_consistency` | 0 undocumented statement keywords | 0 undocumented:  | `true` |
| `cpmb_book_code_board_matches_published_board` | `book_consistency` | downstream stages ['^1^C_{F2}\|A', '^6^E_{F6}\|A', '^9^O_{F5}\|E'] | downstream stages ['^1^C_{F2}\|A', '^6^E_{F6}\|A', '^9^O_{F5}\|E'] | `true` |

## Unenforced Properties And Limits

Recorded as findings, never as passes. Each carries its disposition — what was
done about it. No finding here was closed by weakening the case.

### `cpmb_budget_negative_rail_supply`

A negative available quantity on the master rail. A rail with negative supply is physically meaningless for a load budget.

- Hoped `rejected_or_flagged`.
- Observed: accepted; Y_T=-2.0
- **Disposition:** RECORDED AS A LIMIT, NOT WAIVED. StateVector::set (recipe.rs:532-534) performs no validation and yield_calc's documented edge-case list (yield_calc.rs:22-55) covers negative COEFFICIENTS but is silent on negative QUANTITIES, so the engine returns a negative yield without complaint. Chapter 22 never authors a negative rail, so no published figure is wrong; but any tool that builds a CPMB load budget from user input must validate quantities upstream. This eval does not clamp the value and does not treat the observed number as a pass.

### `cpmb_budget_duplicate_rail_prerequisite`

The same rail listed twice in one recipe (2.0*F3 + 1.0*F3). Double-allocating a rail should not be silently accepted.

- Hoped `rejected_or_flagged`.
- Observed: accepted; prerequisite_count=3 vs excess_capacity_count=2
- **Disposition:** RECORDED AS A LIMIT. Recipe.prerequisites is a Vec<(PrimitiveId, f64)> with no dedup (recipe.rs:399-410), so limiting_reagent() emits one ratio per duplicate entry while excess_capacity()'s HashMap keeps only the last. The two layers therefore disagree about how many prerequisites exist. Ch22's published recipe has no duplicate, so no book figure is affected; this is a robustness limit of the engine and is left recorded rather than papered over.

### `cpmb_recipe_out_of_range_drive_f0`

Budget authored against rail F0, which does not exist (rails are F1..F7).

- Hoped `rejected`.
- Observed: accepted
- **Disposition:** RECORDED AS A LIMIT. The same compiler DOES reject an out-of-range Drive inside a compound state literal (^0^P_{F9}|T is rejected — see case cpmb_component_invalid_drive_leaf in this run), so the gap is specific to the v7.6 recipe-prerequisite path. Chapter 22's published recipe uses only F3/F6/F7, so no published figure is wrong; but a reader following Ch22:305 as a template can author a load budget against a rail the board does not have and the compiler will accept it. Not waived — surfaced for the compiler owner.

### `cpmb_recipe_out_of_range_drive_f9`

Budget authored against rail F9, which does not exist.

- Hoped `rejected`.
- Observed: accepted
- **Disposition:** Same limit as cpmb_recipe_out_of_range_drive_f0; recorded, not waived.

### `cpmb_recipe_duplicate_prerequisite`

The master rail allocated twice in one recipe string (2.0*F3 + 1.0*F3), i.e. double-booking the load budget.

- Hoped `rejected`.
- Observed: accepted
- **Disposition:** RECORDED AS A LIMIT, matching the engine-level gap cpmb_budget_duplicate_rail_prerequisite. Accepted at the notation layer AND at the engine layer, and the two layers disagree about the prerequisite count. Ch22 publishes no duplicate; this is a robustness limit, surfaced rather than clamped.

### `cpmb_component_negative_dropout`

Negative dropout headroom. Ch22:337 publishes the range 0.15-0.25 and Ch14:260 states '> 0 above baseline'. Negative headroom is physically meaningless.

- Hoped `rejected`.
- Observed: accepted
- **Disposition:** RECORDED AS A LIMIT. `dropout` is not in the Regulator parameter schema of cas_forex/pcba_syntax.py at all — it is carried through as an uninterpreted parameter, so neither the published range nor the sign is checked. Nothing in the book is falsified by this (Ch22 publishes only in-range values), but Ch22:337's datasheet range is documentation, not an enforced constraint, and must not be cited as compiler-enforced.

### `cpmb_component_dropout_far_above_range`

dropout=999, three orders of magnitude above the published 0.15-0.25 band.

- Hoped `rejected`.
- Observed: accepted
- **Disposition:** Same limit as cpmb_component_negative_dropout; recorded, not waived.

### `cpmb_beta_scale_derates_unenforced`

Ch22:144 halves beta board-wide on brownout and Ch22:222 applies a 0.75 thermal derate. Probe whether any shipped layer applies or bounds those derates: parse a stage at beta=1e9, far above the CRC-007 hypersensitive threshold of 10.

- Hoped `rejected or ERROR-flagged`.
- Observed: parsed beta=1000000000.0; CRC severities=['CRC-007/CrcSeverity.WARN']
- **Disposition:** RECORDED AS A LIMIT, AND THE HONEST ANSWER IS 'NOT IMPLEMENTED'. There is no beta_scale application anywhere in the repository — no brownout derate, no thermal derate, no board-wide gain modifier. crc_linter's CRC-007 raises only a WARN above beta=10 and never an ERROR. The protective responses at Ch22:144 and Ch22:222 are prose describing a design; nothing in this run tested them, and nothing in the repository could. Chapter 22 is explicit about this at Ch22:9 and Ch22:373.

### `cpmb_precedent_sibling_key_satisfied_by_unrelated_suite`

PRECEDENT HAZARD. The sibling evidence key `cpmb_brownout_lock_tests_pass` is already marked present in docs/working/pcba_authority_report_20260617.json. Check what actually satisfies it.

- Hoped `a brownout-specific test suite`.
- Observed: pcba_readiness.py maps it to pcba_tests_pass, i.e. the pass status of tests/test_pcba_models.py, which contains 0 brownout/thermal/dropout/budget/rail/sequencing references
- **Disposition:** RECORDED AS A HAZARD THIS RUN MUST NOT REPEAT. An evidence key named for a specific behaviour is satisfied there by a generic model-parse suite. `cpmb_load_budget_eval_pass` must NOT be closed the same way. This artifact deliberately does not set the key, does not claim the brownout detector was tested, and states in its Scope that the additive energy budget and every protective subsystem were not exercised at all. The same wiring exists for `csb_shadow_mode_tests_pass` and is out of scope here.

### `cpmb_additive_energy_budget_unimplemented`

The additive form of the load budget — rail capacity in amp-hours (Ch22:245), summed per-stage draw (Ch22:247), time-to-brownout = capacity/draw (Exercise 22.4, Ch22:407-413) — has no implementation anywhere in the repository.

- Hoped `a rail-capacity / additive-draw implementation to run against`.
- Observed: no such object exists; NOT RUN
- **Disposition:** RECORDED AS THE CENTRAL LIMIT OF THIS RUN, NOT WAIVED AND NOT FAKED. Grep across cas-forex, cas-engine and the noetic-compass api for reservoir / amp_hour / drive_budget / energy_budget / per_transition returns no capacity object. The receipt's phrase 'load budget' has two readings in Chapter 22; only the recipe/limiting-reagent reading (Ch22:302-318) is backed by runnable machinery and only that reading was executed. Recomputing 10 A.h / 2.5 A = 4 h inside this script would have tested this script's own arithmetic and is exactly the fake pass this eval exists to avoid. Chapter 22 is honest about the status of these figures at Ch22:9 and Ch22:373; the gap is in the tooling, not in the book's claim.

### `cpmb_overcommit_predicate_supplied_by_this_eval`

Section A treats Y_T < 1.0 as 'the load budget is overcommitted'. Check whether that threshold exists in the framework.

- Hoped `a shipped overcommit threshold or flag`.
- Observed: no threshold, flag or predicate exists; yield_calc returns a number only
- **Disposition:** RECORDED SO THE READING IS NOT MISATTRIBUTED. cas-engine's yield_calc computes Y_T and never raises, flags or compares against 1.0. The 'overcommitted' interpretation is supplied by this eval, not by the framework. What the engine genuinely establishes is the arithmetic and the limiting reagent; the go/no-go reading on top of it is this artifact's own convention and must be cited as such.

## Failures Observed

None.

## Mitigations And Limits

- The allowed claim is exactly what this artifact observed: the recipe form of
  the CPMB load budget reproduces the book's published numbers against the
  shipped yield engine; the Dial constraints are fully and correctly enforced by
  real code; the published regulator components and CAS state literals compile
  clean; and the adversarial weakenings of those gates are rejected.
- This evidence does not unlock live trading, does not make the CPMB a broker
  `ACCEPT` path, and does not support behavioural, legal, governance, privacy or
  human-factors claims about the board.
- This artifact does not sign
  `power_board_burnout_prevention_claim__cpmb_load_budget_eval_pass`. Signing is
  a human act against these hashes.
- Note the precedent hazard recorded above: the sibling key
  `cpmb_brownout_lock_tests_pass` is already marked present in
  `pcba_authority_report_20260617.json` and is satisfied by an unrelated generic
  model-parse suite. This receipt must not be closed the same way.

## Raw Evidence

- Path: `docs\working\cpmb_load_budget_eval_raw_20260725.jsonl`
- SHA-256: `e0a8c3e5d604f753ab39896b4e2020701ffeef09bbb5f62c4a3da0f5baea19b4`
- JSONL records: `82`
- Yield-engine probe: `cargo exit=0 records=11`
