# Stage 23.A.3 — Omega_* Enumeration

**Status:** `PREREGISTERED_FOUNDATION`
**Subject:** CAS Native (foundation layer only)
**Date:** 2026-05-20
**Builds on:** Stage 23.A.2 (`STAGE23_A_2_NOTATION_MAP_EXTENSION_20260519.md`)

## Scope

Stage 23.A.3 closes the explicit deferral from Stage 23.A.2: it places the **12 admitted Omega_\* emergent registers** on the canonical 2D notation map. The total primitive count grows from **157 → 169**. All additions remain in the **static foundation** layer — no model training, no learned parameter, no atlas-self-reading capability claimed.

## Source of truth

`cas-native/config/omega_registry.yaml` is the authoritative file. It contains 12 admitted entries (slots 0-11), each carrying `slot`, `name`, `appendix_i_ref`, `derivation`, `admission_date`. This stage uses **exactly** the 12 names and derivations in that file; no new Omega_\* names are invented here.

The hardcoded `EMERGENT_OMEGAS` tuple in `cas-native/atlas/notation_2d_map.py` mirrors the yaml file. Names are duplicated into Python (rather than loaded at module import) so the canonical layout payload stays deterministic across processes and machines. The yaml file remains the spec; the Python tuple is the deterministic shadow.

## Reversal of the 23.A.2 deferral

Stage 23.A.2 explicitly deferred this group:

> 12 Ω_\* emergent registers — suggested in the design review but no canonical enumeration exists in the repo. CAS v7.7 Clarification 10 introduces a single `Ω` slot for emergent-register results from cross-register integration (`(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`), but does not enumerate "12 specific Ω names." Inventing fixed positions for slots without canonical names would freeze unverified structure at the foundation layer — the worst possible failure mode. Add this primitive group in a future 23.A.3 ONLY when the 12 Ω names are defined and traceable to a source file.

`cas-native/config/omega_registry.yaml` is exactly that canonical enumeration. The yaml file is admitted as the authoritative source per its own header (`This file is the authoritative mapping from OmegaRegistry slot index to admitted Omega_* name`) and per `FULL_MANUSCRIPT.md` Appendix I Section 3 (Admitted Registry). The refusal condition has been satisfied. **Refusal reversed.**

## The 12 admitted Omega_* entries

| Slot | Name | Anchor Noetic | Derivation |
|---:|---|:---:|---|
| 0 | `Omega_presence` | `^1` | `(^1\|A × ^1\|E) = ^1\|Omega_presence` |
| 1 | `Omega_refusal` | `^3` | `(^3^P\|A × ^3^P\|f × ^3^P\|T) = ^3^P\|Omega_refusal` |
| 2 | `Omega_grounding` | `^2` | `(^2^C\|A × ^2^C\|f × ^2^C\|E) = ^2^C\|Omega_grounding` |
| 3 | `Omega_alignment` | `^5` | `(^5^P\|A × ^5^P\|f × ^5^P\|T) = ^5^P\|Omega_alignment` |
| 4 | `Omega_clarity` | `^1` | `(^1\|A × ^1\|f) = ^1\|Omega_clarity` |
| 5 | `Omega_resolve` | `^6` | `(^6^O\|A × ^6^O\|T) = ^6^O\|Omega_resolve` |
| 6 | `Omega_witness` | `^1` | `(^1\|A × ^1\|T × ^1\|E) = ^1\|Omega_witness` |
| 7 | `Omega_attunement` | `^4` | `(^4\|A × ^4\|f × ^4\|T × ^4\|E) = ^4\|Omega_attunement` |
| 8 | `Omega_genesis` | `^0` | `(^0\|A × ^0\|f × ^0\|T) = ^0\|Omega_genesis` |
| 9 | `Omega_cadence` | `^7` | `(^7\|A × ^7\|f × ^7\|E) = ^7\|Omega_cadence` |
| 10 | `Omega_invocation` | `^8` | `(^8\|A × ^8\|f × ^8\|T) = ^8\|Omega_invocation` |
| 11 | `Omega_landing` | `^9` | `(^9\|A × ^9\|f × ^9\|E) = ^9\|Omega_landing` |

The "anchor Noetic" is the Noetic on the LHS of each derivation — the Noetic from which the emergent register arises through cross-register integration (CAS v7.7 Clarification 10).

## Spatial-anchor design

Each Ω sits on a ring of radius **1.8** around the origin, at the angle of its anchor Noetic. The Noetic ring is radius 1.0, so an Ω at radius 1.8 is 0.8 units outside its anchor — visually and metrically "adjacent" to the anchor and unambiguously identified by direction.

| Constant | Value | Meaning |
|---|---:|---|
| `OMEGA_RADIUS` | 1.8 | Ring radius for emergent-register positions |
| `OMEGA_FAN_DEG` | 8.0 | Half-width of the angular fan when multiple Ω's share an anchor |

**Disambiguation when multiple Ω's share an anchor.** Three Ω's anchor on `^1` (slots 0, 4, 6 — `Omega_presence`, `Omega_clarity`, `Omega_witness`). They are fanned around the `^1` anchor angle (−90°) by `−OMEGA_FAN_DEG`, 0, `+OMEGA_FAN_DEG` respectively — so registry-slot order maps to angular order around the anchor. All other anchors carry exactly one Ω; their offset is 0.

The two design properties this yields:

1. Each Ω is **closer to its anchor Noetic than to any other Noetic** — verified by `test_every_omega_is_closer_to_its_anchor_noetic_than_to_any_other`.
2. No Ω **collides** with any of the 157 pre-existing primitives — verified by `test_no_omega_collides_with_any_other_primitive` and the global `test_no_collisions_across_full_169_primitive_set`.

The Ω ring sits in the annulus 1.0 < r ≤ 1.8 around the origin. This annulus is empty in the pre-existing 157-primitive layout (Drives at y = −1.5 are inside; Operations at y = 2.5 are outside; the Cognitive States grid is right of x = 3.0; Inversion Axes at x = −4.0). Collision verification is structural, not just empirical.

## Geometric properties enforced by tests

In addition to all Stage 23.A and 23.A.2 invariants:

| Property | Verified by |
|---|---|
| All 12 Ω names in `EMERGENT_OMEGAS` resolve to a position | `test_every_emergent_omega_has_a_position` |
| Each Ω is closer to its anchor Noetic than to any other Noetic | `test_every_omega_is_closer_to_its_anchor_noetic_than_to_any_other` |
| No Ω coordinate collides with any non-Ω primitive | `test_no_omega_collides_with_any_other_primitive` |
| Each Ω sits on the canonical 1.8-radius ring, outside the Noetic ring | `test_omega_radius_is_outside_noetic_ring` |
| `OMEGA_ANCHOR_NOETIC` matches the LHS Noetic of every yaml derivation | `test_omega_anchor_map_matches_registry_anchor_noetics` |
| **No coordinate collisions across all 169 primitives** | `test_no_collisions_across_full_169_primitive_set` |
| All **17** PrimitiveKind values are populated | `test_all_17_primitive_kinds_are_populated` |
| Layout payload primitive count is 169 | `test_canonical_layout_payload_has_required_shape` |
| Total primitive count from `all_positions()` is 169 | `test_stage_23_a_3_total_primitive_count_is_169` |

Total tests: **45 passing** (40 from 23.A / 23.A.2, 5 new for 23.A.3).

## Updated sub-stage sequencing

| Sub-stage | Scope | Status / When | Blocker |
|---|---|---|---|
| 23.A | Initial 65-primitive coordinate system | ✓ shipped | — |
| 23.A.2 | 92 additional primitives covering full CAS vocabulary | ✓ shipped | — |
| **23.A.3** | **12 admitted Ω_\* emergent registers (this stage)** | **✓ this commit** | — |
| 23.A.1 | Dashboard TypeScript adapter consuming the layout | follow-up (Agent A) | 23.A + 23.A.2 + 23.A.3 must land |
| 23.B | Trace-as-input encoder spec | post-v0 | v0 checkpoint required as ablation floor |
| 23.C | Atlas-conditioning during inference (read-back loop) | post-v0 | 23.B sign-off |
| 23.D | Atlas-conditioned training signal + eval | after 23.C | 23.C running end-to-end |

**Foundation work (23.A / 23.A.2 / 23.A.3) is not blocked by v0.** Only encoder/training work (23.B/C/D) is.

**169 is the final primitive count for foundation work.** This stage does not commit to a 23.A.4 — the omega_registry has 8 reserved slots for future admission, but reserved slots are not admitted, and reserved-slot positioning is not committed at this stage.

## Files in this stage

- `cas-native/atlas/notation_2d_map.py` — extended (12 new Ω constants + dispatch case + `emergent_omega` PrimitiveKind)
- `cas-native/atlas/tests/test_notation_2d_map.py` — extended (5 new property tests; existing count tests updated 157 → 169)
- `research/cas_probe/STAGE23_A_3_OMEGA_ENUMERATION_20260520.md` — this document
- `research/cas_probe/stage23_a_notation_2d_layout_20260519.json` — re-emitted with all 169 entries (layout filename retained; `layout_version` bumped to `stage23a3_notation_2d_layout_v3`)

## Files explicitly NOT touched in this stage

- `cas-native/config/omega_registry.yaml` — read-only source of truth; mirrored, not edited
- `dashboard/src/lib/notation2DMap.ts` — owned by Agent A (Stage 23.A.1)
- `research/cas_probe/STAGE23_B_*.md` — owned by Agent C
- `tools/visualize_notation_map.py` — owned by Agent D

## Out-of-scope claims (must not be claimed by Stage 23.A.3)

Same boundary as Stage 23.A / 23.A.2:

- **Not** "CAS Native reads the atlas."
- **Not** "The 2D map improves model performance."
- **Not** "These spatial relationships are optimal for encoder attention."
- **Not** "The 8 reserved Ω slots are positioned" — they are not, and will not be until they are admitted to `omega_registry.yaml`.

Stage 23.A.3 is exactly one thing: 12 more deterministic 2D positions, anchored to canonical-source Ω names, with collision and anchor-proximity invariants enforced by tests.
