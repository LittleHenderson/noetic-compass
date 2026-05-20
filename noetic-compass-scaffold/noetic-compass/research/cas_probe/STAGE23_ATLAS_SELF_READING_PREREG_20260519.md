# Stage 23 — Atlas Self-Reading Architecture Pre-Registration

**Status:** `PREREGISTERED_FOUNDATION_ONLY`
**Subject:** CAS Native (not CAS Harness)
**Date:** 2026-05-19

## Scope

Stage 23 defines what it means for **CAS Native** to "see its own Idea Atlas and 2D notation map" during inference. It mirrors the Stage 22 preregistration discipline: lock the design boundary first, then deliver the smallest concrete artifact that the rest depends on. Speculative architecture work is named explicitly and deferred, not promised.

This stage scope is the **static foundation** only. The model-facing dynamic loop is deferred to numbered follow-ups.

## Naming Boundary

| Term | Meaning |
|---|---|
| `notation_2d_map` | Static canonical 2D coordinate system for CAS primitives. Same layout every time, regardless of model state. This stage. |
| `idea_atlas` | Dynamic per-run graph of thoughts as they form during inference. Already exists as JSON output (Atlas v0). Not modified in this stage. |
| `atlas_self_reading` | Future capability where CAS Native reads its own atlas as input during decode. Deferred to Stage 23.C, post-v0. |
| `notation_conditioning` | Future capability where CAS Native attends to 2D notation positions during decode. Deferred to Stage 23.C, post-v0. |

## Sub-Stage Sequencing

| Sub-stage | Scope | When | Blocker |
|---|---|---|---|
| **23.A** | `notation_2d_map.py` module + tests + emitted JSON layout artifact | This stage | None — purely declarative, no model |
| **23.A.1** | Dashboard-side TypeScript adapter consuming the layout | Follow-up, low effort | 23.A must land |
| **23.B** | Trace-as-input encoder spec — schema + dimensionality + which CAS-Native layer it feeds | Post-v0 design phase | v0 stable checkpoint required as ablation floor |
| **23.C** | Atlas-conditioning during inference — read-back loop + cross-attention head | Post-v0 implementation phase | 23.B sign-off |
| **23.D** | Atlas-conditioned training signal + eval — measurable claim that atlas-reading helps | After 23.C ships | 23.C running end-to-end |

Stage 23 (this preregistration) ships only **23.A**. Sub-stages 23.B / 23.C / 23.D are named here so that future work has a locked target and so this stage cannot silently expand into them.

## What 23.A Locks

1. **A canonical (x, y) position for every CAS primitive.**
   - 10 Noetics (CO-0 through CO-9)
   - 4 Domains (P, C, E, O)
   - 7 Drives (F1 through F7)
   - 4 Registers (T, A, f, E)
   - 40 Cognitive States (Noetic × Domain combinations)

2. **Geometric properties that encode CAS structure**, not arbitrary choices:
   - **Involution symmetry.** Noetic involution pairs (CO-2 ↔ CO-3, CO-5 ↔ CO-6, CO-8 ↔ CO-9) sit reflection-symmetric across the canvas origin. Drive involution pairs (F1 ↔ F7, F2 ↔ F6, F3 ↔ F5) likewise.
   - **Self-dual primitives** (CO-0, CO-1, CO-4, CO-7 for Noetics; F4 for Drives) sit on the symmetry axes.
   - **Domain precedence.** The P ≻ C ≻ E ≻ O total order is spatially layered (top-to-bottom or outermost-to-innermost), not interleaved.
   - **Position uniqueness.** No two primitives share a coordinate.

3. **Stable, deterministic API.** `get_position(primitive_id)` returns the same `(x, y)` for the same input across runs, processes, and machines. The layout is data, not configuration.

## Constraints (what 23.A does NOT do)

- Does not modify the existing `idea_atlas.py`, `thought_tree.py`, or any dashboard renderer.
- Does not introduce any tensor, neural network, or learned parameter. The 2D map is fixed geometry.
- Does not attempt to be a "good attention prior." That is a future research question (Stage 23.B/C) and depends on what the encoder needs.
- Does not assume any particular dashboard rendering. If existing renderers (CASBrainMap, MediumViewSubstructure) use different ad-hoc layouts, they remain working. The canonical map is the future single source of truth; migrations come later.

## Acceptance Criteria for 23.A

| Criterion | How verified |
|---|---|
| Every Noetic has a position | unit test |
| Every Domain has a position | unit test |
| Every Drive has a position | unit test |
| Every Register has a position | unit test |
| Every 40 Cognitive State has a position | unit test |
| Noetic involution pairs are reflection-symmetric across origin | unit test |
| Drive involution pairs are reflection-symmetric across origin | unit test |
| Self-dual Noetics (CO-0, CO-1, CO-4, CO-7) lie on a symmetry axis | unit test |
| Domain precedence is spatially monotone (P → C → E → O) | unit test |
| No two primitives share a coordinate | unit test |
| Layout is deterministic across calls | unit test |
| Canonical JSON artifact emitted and version-pinned | runner script |

## Out-of-scope claims (must not be claimed by Stage 23)

- "CAS Native reads the atlas." — false. Stage 23.A only ships the static map. The read-back loop is Stage 23.C.
- "The 2D map improves model performance." — false. Stage 23.A is foundational geometry; no training or eval is run.
- "The map is the optimal attention prior." — false. Optimality is an empirical question to be settled in Stage 23.D, not declared by fiat in 23.A.

## Connection to Stage 22 discipline

Stage 22 / 22.1 / 22.2 on the CAS Harness side established the pattern: lock the foundation, name what's measured vs not measured, defer speculative work explicitly. Stage 23 mirrors that pattern on the CAS Native side. The same discipline applies:

- Don't claim measurements you can't make.
- Don't bundle dynamic capabilities into a static spec.
- Don't let the prereg silently expand its own scope.

## Files committed in this stage

- `cas-native/atlas/notation_2d_map.py` — the canonical layout module
- `cas-native/atlas/tests/test_notation_2d_map.py` — property tests
- `research/cas_probe/STAGE23_ATLAS_SELF_READING_PREREG_20260519.md` — this document
- `research/cas_probe/stage23_a_notation_2d_layout_20260519.json` — emitted canonical layout artifact

## Next step after 23.A

Schedule **Stage 23.A.1** (dashboard adapter — small) and **Stage 23.B design phase** (encoder schema — requires v0 checkpoint). Do not start 23.B until v0 ships, by the same argument that gates Stage 22 ablations on existing frozen models.
