# Definition-Locked TKS/CAS MTC Fixture - 2026-06-03

Status: built as an input fixture, not a verdict.

This directory contains the definition-locked fixture for the next
matched-taxonomy / uniqueness pass. It is sourced from the owner-provided TKS
40 Element and TKS 28 Foundation definitions supplied on 2026-06-03.

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

This is an input fixture. It is not a model capture, not a comparator result,
and not a CAS Harness `ACCEPT`.

The 40E rows are generated from explicit TKS Element definitions `A1` through
`D10`.

The F28 rows are generated from explicit TKS Foundation definitions `1a`
through `7d`.

The source text intentionally contains the TKS titles in many definitions. This
fixture therefore tests definition grounding and axis recovery from source
definitions; by itself it is not a blind semantic generalization proof.
