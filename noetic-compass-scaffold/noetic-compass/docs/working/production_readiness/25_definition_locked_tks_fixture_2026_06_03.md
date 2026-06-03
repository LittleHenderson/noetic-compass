# Definition-Locked TKS/CAS Fixture Evidence - 2026-06-03

**Status: BUILT, source-locked, and test-guarded.** A definition-derived
fixture now exists for the next 40E / F28 probe pass. It is an input dataset,
not a model run and not a verdict.

This was built in response to the audit finding that the Condition-3 comparator
used CAS 40E fixture labels and a non-CAS `NC28` control, but did not directly
test the locked TKS/CAS definitions of the 40 Elements and 28 Foundations.

## Locked Sources Used

```text
docs/reference/tks_owner_locked_definitions_20260603.json
conversation:user_provided_tks_definitions_2026_06_03
docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md
```

The repo now contains a locked source file:

```text
C:\tmp\evidence-merge\docs\reference\tks_owner_locked_definitions_20260603.json
```

That file contains the owner-provided TKS `A1-D10` 40 Element definitions and
the owner-provided TKS `1a-7d` 28 Foundation definitions supplied on
2026-06-03. The fixture generator reads that file as the authority. It no longer
uses the CAS v7.5 `Drive x Register` translation key as the F28 source.

The CAS foundational clarification file is used only to map element numbers to
canonical noetic names such as `Mind`, `Positive`, `Negative`, `Vibration`,
`Female`, `Male`, `Rhythm`, `Above/Cause`, `Below/Effect`, and `Idea`.

## Generated Artifacts

Repo directory:

```text
docs/working/definition_locked_tks_mtc_20260603
```

Archive directory:

```text
D:\tksCAS-archive\definition_locked_tks_mtc_20260603
```

Files:

```text
canonical_tks_cas_axis_definitions_20260603.json
definition_locked_tks40_f28_fixture_20260603.json
definition_locked_tks40_f28_fixture_20260603.jsonl
definition_locked_tks40_f28_manifest_20260603.json
README.md
```

Generator:

```text
live-trace-worker/scripts/build_definition_locked_tks_fixture.py
```

Locked source file:

```text
docs/reference/tks_owner_locked_definitions_20260603.json
```

## Counts

```text
rows: 816
40E rows: 480
F28 rows: 336
40E classes: 40
F28 classes: 28
variants per class: 12
train/test per class: 8/4
```

## Validation

The fixture loads through the live repo's `probe_dataset_common` capture loader:

```text
loaded 816
element_classes 40 minmax 12 12
foundation_classes 28 minmax 12 12
sample_elements ['A1', 'A10', 'A2'] ['D7', 'D8', 'D9']
sample_foundations ['1a', '1b', '1c'] ['7b', '7c', '7d']
split_balance_bad [] count 0
```

Regression tests now pin this behavior:

```text
pytest -q tests\test_definition_locked_tks_fixture.py
5 passed
```

Those tests fail if:

- the locked source file is missing the owner-provided TKS definitions;
- the generator stops being source-driven;
- the committed fixture drifts from the source file;
- the live loader fails to preserve `A1-D10` and `1a-7d` labels;
- someone substitutes fallback labels such as `^1|P` or `F1|T`.

## Archive Hashes

```text
docs/reference/tks_owner_locked_definitions_20260603.json
A124302ED93C7B8571B24A5CDF14433ADF904EB94FD65895C6FD25FAE58E28A0

canonical_tks_cas_axis_definitions_20260603.json
A124302ED93C7B8571B24A5CDF14433ADF904EB94FD65895C6FD25FAE58E28A0

definition_locked_tks40_f28_fixture_20260603.json
812B4A73C2C4C70C36C52500897E8A7AFABB29430E2F93EB06823A2AD38BB1BF

definition_locked_tks40_f28_fixture_20260603.jsonl
23141C91D0A136B9129016E9D663B13BC03419788105F6C80AD801B4A7DD40DC

definition_locked_tks40_f28_manifest_20260603.json
1C3A01AF1E7E10F6BECC0DB34110943AF3957F3A830F2952592A28630DE08503

README.md
F034A281B71413BBF61375401346A455A3544DD3D6D8DF416834EE0BCE46FB94
```

## Claim Boundary

This closes the missing fixture-build step only. It does not run GPT-NeoX-20B,
does not run Pythia-160M, does not emit `PASS`, `GREY`, `FALSIFY`, or
`BLOCKED`, and does not change the Pythia-160M packet from
`FLAG_FOR_HUMAN_REVIEW`.
