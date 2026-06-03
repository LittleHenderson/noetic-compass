# MTC Pre-Registration Amendment A1 - Frozen Approval Record - 2026-06-03

**Status: FROZEN BY FOUNDER APPROVAL for the Condition-3 comparator run.**

Founder approval signal:

```text
VGO
```

Approval time:

```text
2026-06-03
```

This freezes the A1 amendment for the next engineering comparator run. It does
not claim Object-Lock retention for this prereg document: the currently shipped
Object-Lock anchor route handles registry-backed Evidence Packets, not arbitrary
methodology documents, and this session has no local AWS/Object-Lock credentials.
Any result that cites this amendment must therefore say **founder-approved and
hash/git frozen**, not WORM-retained, unless a later object-lock copy is made.

## Amends

```text
cas_harness_matched_taxonomy_control_prereg_20260530.md
```

Original A1 draft:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_mtc_prereg_amendment_A1_DRAFT_20260603.md
```

## Scope

MTC.1 instrument fixture only.

Unchanged:

- GPT-NeoX-20B substrate.
- H-MTC-1..4 hypotheses.
- Controls A/B/C/D.
- Probe family.
- Frozen split logic.
- Flat and nested lacunarity scoring.
- Pre-registered margins.
- BLOCK-don't-weaken rule.
- Decision vocabulary: `PASS`, `GREY`, `FALSIFY`, `BLOCKED`.

Changed:

- The MTC.1 fixture moves from the abstract A/B prompt fixture, which could not
  carry a balanced coherent non-CAS taxonomy, to the Condition-3 topical-scenario
  fixture.

## Reason

The original abstract Stage 9 / Foundation fixtures were ineligible for the
matched-taxonomy comparator: materializing NC40 against those abstract prompts
covered only 142 of 2,560 required train rows. Under prereg rule 4, the honest
result is `BLOCKED`, not a weakened comparator.

The earlier 20B MTC `FALSIFY` result is also not reused here because it came from
the quarantined dual-labeled fixture. It remains a fixture artifact, not a valid
CAS-specificity decision.

## Frozen Instrument

Condition-3 topical-scenario fixture:

```text
docs/working/mtc_matched_taxonomy_20260530/mtc_condition3_topical_scenarios_20260531.jsonl
```

Replacement-pod capture archive:

```text
D:\tksCAS-archive\condition3_mtc_capture_20260603
```

Captured activation dataset:

```text
D:\tksCAS-archive\condition3_mtc_capture_20260603\condition3_gptneox20b_activations.npz
SHA256 8A98216CD1D4DC5168FE56F46B22B46FF59FDF534FACE17B86ACF1AEC33987F1
```

## Integrity Conditions

1. The comparator must use the captured Condition-3 GPT-NeoX-20B activation NPZ
   from `D:\tksCAS-archive\condition3_mtc_capture_20260603`.
2. The row-level matched-taxonomy manifest must derive rival labels only from
   `control_semantic` fields, not from CAS labels.
3. The comparator result must preserve `PASS`, `GREY`, `FALSIFY`, or `BLOCKED`
   exactly as emitted.
4. A `PASS` here would be a 20B MTC.1 result only. It would not by itself turn
   the Pythia-160M WORM-retained packet into `ACCEPT`.
5. A `GREY`, `FALSIFY`, or `BLOCKED` result leaves the Pythia-160M packet at
   `FLAG_FOR_HUMAN_REVIEW`.
6. Because this prereg freeze is not Object-Lock retained, any later public
   claim must disclose that boundary unless an object-locked copy is made.

## Frozen Text From A1 Draft

MTC.1 is run on the Condition-3 topical-scenarios instrument:

- Fixture: `docs/working/mtc_matched_taxonomy_20260530/mtc_condition3_topical_scenarios_20260531.jsonl`
  with 1,440 rows, 40 elements balanced at 36 each, and train/test 720/720.
- Manifest/views: `mtc_condition3_topical_scenarios_20260531_manifest.json`,
  `mtc_condition3_capture_view_20260531.json`,
  `control_c_nc28_balanced_view_20260531.json`.
- Design intent: real CAS meaning carried in ordinary scenarios with an
  orthogonal topic/frame scaffold, so NC40/NC28 assign from non-CAS prompt
  content without reading any CAS field.
- Local readiness: Surface Gate PASS, Fixture-Eligibility ELIGIBLE, and
  Meaning-Preservation PASS as recorded in the A1 draft. The
  Meaning-Preservation gate was self-rated and should be independently hardened
  before any external claim-bearing `PASS` is published.

The comparator may now run as an engineering result under this frozen A1 record.
