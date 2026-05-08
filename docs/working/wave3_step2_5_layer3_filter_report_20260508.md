# Wave 2.5 Layer-3 Filter Report

Date: 2026-05-08

Input run:
`cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260508T110453Z.jsonl`

Status: **NOT GREEN**

## Summary

The earlier 500-record calibration was green under the then-current validator
stack: 398/500 accepted, 0 leakage, all categories above the numeric floor.

After the four-agent audit and a manual read of the 25-record clean-subset
pack, two new validator layers were added:

1. Expanded jargon leak detection for `operator slot`, `cognitive operation`,
   `CO-N`, `lambda`, and related phrasing.
2. Stage-local domain preservation for `let`-bound RPM chains.

Re-filtering the 398 accepted records under the stricter stack yields:

| Metric | Value |
| --- | ---: |
| Input accepted records | 398 |
| Layer-3 clean records | 305 |
| Layer-3 rejected records | 93 |
| Clean rate within accepted set | 76.6% |
| Clean rate relative to 500-record calibration | 61.0% |

## Per-Category Result

| Category | Clean / Total | Rate |
| --- | ---: | ---: |
| cross_register_omega | 50 / 50 | 100.0% |
| fractal_sequence | 51 / 51 | 100.0% |
| state_literal | 30 / 30 | 100.0% |
| let_binding | 37 / 38 | 97.4% |
| inversion | 23 / 25 | 92.0% |
| binary_composition | 38 / 45 | 84.4% |
| diagram_export | 29 / 38 | 76.3% |
| recipe | 31 / 47 | 66.0% |
| meta_logic_relation | 14 / 28 | 50.0% |
| rpm_chain | 2 / 46 | 4.3% |

## Interpretation

The previous green verdict was still too permissive.

The decisive finding is `rpm_chain`: most generated descriptions preserve
surface stage names but drift the bound domains inside the stage clauses.
For example, a stage bound to a principled state is narrated as evaluative
or cognitive. That is exactly the kind of structural corruption v1 must not
learn.

Meta-logic is also weak after expanded jargon detection. Many accepted
records used phrases such as "operator slot" or "cognitive operation",
which are not suitable plain-English training targets.

## Recommendation

Do not scale Wave 2.5 from this prompt/model configuration.

Next viable options:

1. Deterministically render more regular compiler shapes, especially
   `rpm_chain` stage tables and some meta-logic constructors.
2. Use a structured intermediate representation before fluentization.
3. Run a small higher-tier model bakeoff only on `rpm_chain`, `recipe`, and
   `meta_logic_relation`, since the regular/deterministic lanes are already
   good.

The current layer-3 clean subset is useful as a small high-confidence seed
set, not as a complete Wave 2.5 corpus.
