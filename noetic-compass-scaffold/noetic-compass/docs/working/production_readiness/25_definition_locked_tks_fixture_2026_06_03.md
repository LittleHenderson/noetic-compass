# Definition-Locked TKS/CAS Fixture Evidence - 2026-06-03

**Status: BUILT and schema-validated.** A definition-derived fixture now exists
for the next 40E / F28 probe pass. It is an input dataset, not a model run and
not a verdict.

This was built in response to the audit finding that the Condition-3 comparator
used CAS 40E fixture labels and a non-CAS `NC28` control, but did not directly
test the locked TKS/CAS definitions of the 40 Elements and 28 Foundations.

## Canonical Sources Used

```text
docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md
noetic-compass-scaffold/noetic-compass/CLAUDE.md
docs/reference/tks_28_foundations_translation_key.md
book/manuscript/Chapter_03_The_Four_Processing_Domains.md
```

The 10 Noetic definitions are verbatim canonical from
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.

The F28 lane uses the current CAS v7.5 `Drive x Register` translation key. The
translation-key document explicitly says the original TKS 28 Foundations source
population remains pending, so this fixture must be described as a
definition-locked CAS/TKS translation fixture, not as fully populated original
TKS 28 prose.

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
axes ['domain', 'drive', 'element', 'foundation', 'noetic', 'operator', 'register']
element_classes 40 minmax 12 12
foundation_classes 28 minmax 12 12
operator_classes 10 domain_classes 4 drive_classes 7 register_classes 4
split_balance_ok classes 68 train/test 8/4
```

## Archive Hashes

```text
canonical_tks_cas_axis_definitions_20260603.json
04122B2EDE0B37F3E714F20251D59C6BC6626592076CAC7FAA479281C5BE69C6

definition_locked_tks40_f28_fixture_20260603.json
E8C23AAEFE07E2A65AABD1F875655A3B524145476535FF26D2202D71FAC3871C

definition_locked_tks40_f28_fixture_20260603.jsonl
3D7A4BD5784CC224B97F204A6A06C49D887B74905E2897E0F852A196C42D4B58

definition_locked_tks40_f28_manifest_20260603.json
2F3C655784A3476DAFB203F1AF3C86ACB7E81ABAF78CAACFE3E7CB4268C2E489

README.md
D7786D4DC9D0E1CEA892700B5408F29944E7BECF52005C2F400CABC0CEFE77D1
```

## Claim Boundary

This closes the missing fixture-build step only. It does not run GPT-NeoX-20B,
does not run Pythia-160M, does not emit `PASS`, `GREY`, `FALSIFY`, or
`BLOCKED`, and does not change the Pythia-160M packet from
`FLAG_FOR_HUMAN_REVIEW`.

