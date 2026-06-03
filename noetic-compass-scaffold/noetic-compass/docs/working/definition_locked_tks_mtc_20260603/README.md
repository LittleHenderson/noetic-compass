# Definition-Locked TKS/CAS MTC Fixture - 2026-06-03

Status: built as an input fixture, not a verdict.

This directory contains the first definition-locked fixture for the next
matched-taxonomy / uniqueness pass. It is intentionally sourced from the locked
CAS/TKS definition documents instead of the Condition-3 topical scenario text.

## Contents

- `canonical_tks_cas_axis_definitions_20260603.json` - source definitions and
  source paths.
- `definition_locked_tks40_f28_fixture_20260603.json` - one JSON document with
  all rows.
- `definition_locked_tks40_f28_fixture_20260603.jsonl` - JSONL view of the same
  rows.
- `definition_locked_tks40_f28_manifest_20260603.json` - label counts and row
  label manifest.

## Counts

```text
rows: 816
40E rows: 480
F28 rows: 336
variants per class: 12
train/test per class: 8/4
```

## Honesty Boundary

The 10 Noetic definitions are verbatim canonical from
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.

The 40E state labels are generated as `Noetic x Domain`.

The F28 labels are generated as `Drive x Register`, following the current CAS
v7.5 translation key in `docs/reference/tks_28_foundations_translation_key.md`.
That reference explicitly says the original TKS 28 Foundations source
population remains pending. Therefore this fixture locks the current CAS
Drive/Register translation layer; it does not claim the full original TKS 28
Foundation prose has been recovered.

Run the generator to refresh hashes printed to stdout.
