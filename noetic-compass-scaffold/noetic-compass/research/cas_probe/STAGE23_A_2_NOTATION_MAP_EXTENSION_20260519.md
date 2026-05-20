# Stage 23.A.2 — Notation Map Extension

**Status:** `PREREGISTERED_FOUNDATION`
**Subject:** CAS Native (foundation layer only)
**Date:** 2026-05-19
**Builds on:** Stage 23.A (`STAGE23_ATLAS_SELF_READING_PREREG_20260519.md`)

## Scope

Stage 23.A.2 extends the canonical 2D notation map from 65 primitives to **157 primitives** by adding the remainder of the CAS primitive vocabulary. All additions remain in the **static foundation** layer — no model training, no learned parameter, no atlas-self-reading capability claimed.

This stage corrects the sub-stage sequencing table from the Stage 23 prereg: coordinate-system work is foundation, not post-v0. Only **23.B (encoder spec), 23.C (inference loop), 23.D (training + eval)** genuinely depend on a v0 checkpoint to ablate against. Adding more primitives to the map is 23.A-lineage and ships now.

## Naming Boundary

The boundary discipline from Stage 23.A holds. Canonical prefixed forms are used to avoid letter collisions:

| Group | Canonical id form | Example |
|---|---|---|
| Inversion Axis | `Inv:<axis>` | `Inv:N`, `Inv:P` |
| Foundation | `Fk^R` (Drive × Register) | `F1^T`, `F4^E` |
| RPM Pathway | bare `A0` / `Dk` / `Wk` / `Pk` | `A0`, `D3`, `W7`, `P5` |
| Operation | bare symbol | `×`, `÷`, `∘`, `+`, `−` |
| Production primitive | bare Greek letter | `Θ`, `Λ`, `η`, `κ`, `ι` |
| Set primitive | bare symbol or CamelCase | `∈`, `∪`, `NoeticCluster` |

The Inversion-Axis prefix `Inv:` is required because bare letters N/W/F/E/S/A/P all collide with Domain / Register / Drive / RPM-chain ids.

## What ships in 23.A.2 (92 primitives)

| Group | Count | Layout region | Source of truth |
|---|---:|---|---|
| Generative Operations | 5 | y=2.5 row above Noetic ring, x ∈ [-2, +2] | `CLAUDE.md` "5 CAS Generative Operators (× ÷ ∘ + −)" |
| Inversion Axes | 7 | x=-4 column, y ∈ [-1.5, +1.5] (`Inv:P` compound at y=0) | `CLAUDE.md` "7 Inversion Axes" |
| Foundations (Drive × Register) | 28 | 7×4 grid at y ∈ [3.0, 4.5], inherits Drive x | `CLAUDE.md` "28 Domain-Specific Drives" / `tks_28_foundations_translation_key.md` |
| Production primitives (Θ, Λ, η, κ, ι) | 5 | y=5.5 row above Foundations, x ∈ [-2, +2] | `CLAUDE.md` CAS v7.6 Clarification 9 |
| RPM chain (A0 + D1-7 + W1-7 + P1-7) | 22 | y ∈ [-9.5, -8.0] rows, A0 root then D/W/P descent | `CLAUDE.md` "22 Capability Pathways" |
| Set constructors | 4 | 2×2 cluster x ∈ [6, 7], y ∈ [0, 1] | `api/notation/compiler.py`, `dashboard/.../DiagramView.tsx` |
| Set relations (∈, ∉, ⊂, ⊆, ⊃, ⊇) | 6 | y=2.0 row, x ∈ [6, 8.5] | Standard math; used by compiler |
| Set operations (∪, ∩, ∖, ∅) | 4 | y=-1.0 row, x ∈ [6, 9] | Standard math; ∅ anchored "as origin" of subspace |
| Combinators (Product, CoverOf, PartitionOf, Pullback) | 4 | x=10 column, y ∈ [-1.5, +1.5] | Codex Phase-2 ship (per memory entry `cas_diagram_and_clusters`) |
| Authority sets | 5 | x=11 column, y ∈ [-2, +2] ordered by trust | `api/notation/turn_admissibility.py`, `cas-native/intent/level3_ingest.py` |
| Cardinality kinds (`Cardinality`, `OrderedTuple`) | 2 | x=12 column, y ∈ [-0.5, +0.5] | Form markers; any inner primitive can be wrapped |

Every primitive can be traced to a file the validator (me) confirmed exists in the repo.

## What is intentionally NOT shipped

- **12 Ω_* emergent registers** — suggested in the design review but no canonical enumeration exists in the repo. CAS v7.7 Clarification 10 introduces a single `Ω` slot for emergent-register results from cross-register integration (`(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`), but does not enumerate "12 specific Ω names." Inventing fixed positions for slots without canonical names would freeze unverified structure at the foundation layer — the worst possible failure mode. Add this primitive group in a future 23.A.3 ONLY when the 12 Ω names are defined and traceable to a source file.

- **"CAS Transformer paper Section 5" quote** — referenced in the design review but no file matching "CAS Transformer paper" exists in this repo. The Stage 21 paper draft (`PAPER_DRAFT_v0_*.md`) is the closest artifact and does not contain the quoted text. The claim "meta-logic must be first-class" is independently sound (and the meta-logic primitives ARE shipped in 23.A.2), but the citation is not propagated into the code or docs without a verifiable source.

## Geometric properties enforced by tests

In addition to the Stage 23.A invariants:

| Property | Verified by |
|---|---|
| Every Operation has a position | `test_every_operation_has_a_position` |
| × ↔ ÷ and + ↔ − are reflection-symmetric across x=0 | `test_operation_inverse_pairs_reflect_across_y_axis` |
| ∘ (compose) sits on the y-axis like a self-dual | `test_compose_operation_is_on_y_axis` |
| All 7 Inversion Axes have positions | `test_every_inversion_axis_has_a_position` |
| `Inv:P` (compound) sits at the column center (y=0) | `test_compound_inversion_axis_is_centered` |
| All 28 Foundations have positions | `test_every_foundation_has_a_position` |
| `Fk^R` inherits Drive Fk's x coordinate | `test_foundation_inherits_drive_x_and_register_y` |
| Foundations sharing a Register share a y row | `test_foundations_in_same_register_row_share_y` |
| All 5 Production primitives have positions | `test_every_production_primitive_has_a_position` |
| `A0 → Dn → Wn → Pn` chain is vertically monotone | `test_rpm_chain_d_w_p_rows_are_vertically_ordered` |
| Authority sets ordered by trust (System highest, Rendered lowest) | `test_authority_sets_ordered_by_trust` |
| **No coordinate collisions across all 157 primitives** | `test_no_collisions_across_full_157_primitive_set` |
| All 16 PrimitiveKind values are populated | `test_all_16_primitive_kinds_are_populated` |

Total tests: **40 passing** (18 from 23.A + 22 from 23.A.2).

## Updated sub-stage sequencing

Correcting the Stage 23 prereg's table:

| Sub-stage | Scope | Status / When | Blocker |
|---|---|---|---|
| 23.A | Initial 65-primitive coordinate system | ✓ shipped (commit `3cee982`) | — |
| **23.A.2** | **92 additional primitives covering full CAS vocabulary (this stage)** | **✓ this commit** | — |
| 23.A.3 (optional) | Enumerate Ω_* group IF canonical names are defined | future | requires canonical Ω_* list from project owners |
| 23.A.1 | Dashboard TypeScript adapter consuming the layout | follow-up | 23.A + 23.A.2 must land |
| 23.B | Trace-as-input encoder spec | post-v0 | v0 checkpoint required as ablation floor |
| 23.C | Atlas-conditioning during inference (read-back loop) | post-v0 | 23.B sign-off |
| 23.D | Atlas-conditioned training signal + eval | after 23.C | 23.C running end-to-end |

**Foundation work (23.A / 23.A.2 / 23.A.3) is not blocked by v0.** Only encoder/training work (23.B/C/D) is.

## Files in this stage

- `cas-native/atlas/notation_2d_map.py` — extended (92 new constants + dispatch cases)
- `cas-native/atlas/tests/test_notation_2d_map.py` — extended (22 new property tests)
- `research/cas_probe/STAGE23_A_2_NOTATION_MAP_EXTENSION_20260519.md` — this document
- `research/cas_probe/stage23_a_notation_2d_layout_20260519.json` — re-emitted with all 157 entries

## Out-of-scope claims (must not be claimed by Stage 23.A.2)

Same as Stage 23.A. Adding more primitives does not change the claim boundary:

- **Not** "CAS Native reads the atlas."
- **Not** "The 2D map improves model performance."
- **Not** "These spatial relationships are optimal for encoder attention."
- **Not** "The 12 Ω_* registers are positioned" — they're not, and won't be until canonical enumeration is supplied.
