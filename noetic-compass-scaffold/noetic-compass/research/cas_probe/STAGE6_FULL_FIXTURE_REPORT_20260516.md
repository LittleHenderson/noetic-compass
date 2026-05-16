# Stage 6.2 - Full Role-Bound Noetic Fixture

**Status:** LOCKED FIXTURE BUILT. No activation capture, probe training, or
mechanistic claim is made by this artifact.

## Purpose

Stage 6.0 proved the role-bound data shape on a 100-row pilot. Stage 6.1
proved the focus-token activation capture plumbing on that same pilot. Stage
6.2 scales the dataset shape to the full locked fixture described in
`STAGE6_ROUNDTABLE_V3_PLAN_20260516.md`.

The scientific question for the next stage is whether an open model can read
the intended noetic role from the same sentence when only the focus changes.
This report does not answer that question. It only freezes the fixture that a
claim-bearing evaluation may use.

## Artifacts

- Builder:
  `build_stage6_role_bound_full.py`
- Dataset:
  `stage6_role_bound_full_20260516.jsonl`
- Manifest:
  `stage6_role_bound_full_manifest_20260516.json`
- Validation report:
  `stage6_role_bound_full_validation_20260516.json`

Dataset SHA-256:

```text
450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710
```

Split SHA-256:

```text
train  62bc3877d26e2495a9c454674697cc22a4b5181abd40be6219051a5886b5715b
val    69b54b8e3076acc95b40eb327795e29ae8de170cfde9e46fd675448a1462e6c8
test   bd85fd6aea871117d818e2ea0d11abc1f6d03ad54ad16e29eeb1294d4bae795f
```

## Shape

| Field | Count |
|---|---:|
| Total rows | 3,000 |
| Contrast bundles | 60 |
| Counterfactual pairs | 1,500 |
| Rows per noetic label | 300 |
| Train rows | 1,200 |
| Val rows | 400 |
| Locked test rows | 1,400 |

Class distribution is exactly balanced:

```text
^0 300
^1 300
^2 300
^3 300
^4 300
^5 300
^6 300
^7 300
^8 300
^9 300
```

## Design

Each row contains one plain-English sentence with two role markers, `A` and
`B`, followed by a terminal focus marker:

```text
... Focus: A.
... Focus: B.
```

For each counterfactual pair:

- the base sentence is identical
- one row focuses `A`
- one row focuses `B`
- the noetic label changes because the focused role changes

This is the important Stage 6 structure: the model should not be able to solve
the task by broad topic, scenario, or sentence template alone. It must use the
focused role.

The hard noetic pairs are:

- `^0` vs `^1`
- `^2` vs `^3`
- `^4` vs `^7`
- `^5` vs `^6`
- `^8` vs `^9`

The full fixture uses 60 lexical bundles:

- 30 train bundles
- 10 val bundles
- 20 locked-test bundles

Core paraphrase families are present across all splits:

- `role_inverse_minimal`
- `no_alias_plain`
- `concrete_human`
- `system_process`

Locked-test-only paraphrase families add held-out pressure:

- `compressed_minimal`
- `long_embedded_clause`
- `counter_alias_hard_negative`

## Validation

Command:

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\validate_stage6_role_bound.py --input stage6_role_bound_full_20260516.jsonl --out-report stage6_role_bound_full_validation_20260516.json
```

Result:

```text
status: pass
n_errors: 0
n_warnings: 653
```

Warning breakdown:

```text
labelish_tokens_present: 652
token_concentration_audit: 1
```

The token concentration audit inspected 725 recurring tokens. Maximum
concentration was `0.5`, and every token above `0.4` was tied across labels.
No non-tied token concentration exceeded the validator threshold.

The warnings are expected because the fixture intentionally uses ordinary
English words like "toward", "built", "shaped", "repeated", "cue", and
"result". Those words are allowed only when the validator sees that they are
counterbalanced instead of acting as single-label shortcuts.

## Boundary

What this fixture supports:

- a reproducible Stage 6.3 activation capture
- a locked train/val/test split
- a frozen test SHA before any claim-bearing probe evaluation
- an audit trail for split isolation and leakage checks

What it does not support yet:

- "Pythia encodes CAS"
- "CAS has solved the black box problem"
- "Glass House AI is validated"
- any claim about behavior, activations, or causal effect

## Next Step

Stage 6.3 should capture Pythia activations for the full fixture using the
already-tested focus-token extraction helper. After capture, the next honest
gate is a full role-bound probe evaluation with text baselines and paired
statistics, not a marketing claim.
