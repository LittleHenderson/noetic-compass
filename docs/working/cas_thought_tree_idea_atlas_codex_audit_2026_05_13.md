# CAS Thought Tree & Idea Atlas — Codex Audit

**Date:** 2026-05-13  
**Status:** Design handoff audited. No implementation authorized by this doc.

## Verdict

The direction is right: **Thought Tree and Idea Atlas should be separate UI
surfaces over one shared CAS graph substrate.** This is the correct product
shape for the proof-of-concept target:

- Thought Tree = follow one reasoning path.
- Idea Atlas = explore relationships across many thoughts.

The spec is good enough to guide planning, but **not yet build-ready**. The
first implementation step should be the shared substrate contract, not either
UI surface.

## Repo-Grounded Findings

Existing surfaces/assets found:

- `dashboard/src/pages/CompilerPage.tsx`
  - Already defines compiler diagram wire types, layout functions, and
    `DiagramPreview`.
  - This is currently too large to keep expanding directly.
- `dashboard/src/components/IdeaAtlas/`
  - Existing TypeScript Idea Atlas types and view components.
- `dashboard/src/components/idea-atlas/`
  - A second similarly named component directory exists.
  - This casing split is risky on Windows/macOS/Linux and should be cleaned up
    before serious Atlas work.
- `api/routes/idea_atlas.py`
  - Existing backend route surface, including the `/casivenize` path.
- `cas-native/atlas/idea_atlas.py`
  - Existing Python atlas model, but it is activation/prediction oriented.
  - It is not yet the canonical shared graph identity scheme described in the
    new spec.

## Main Build Risk

If we start by building `ThoughtTreeView.tsx` or a new force graph directly,
we will duplicate data logic and end up with two incompatible views.

The build should start with:

1. Shared graph schema.
2. Shared palette constants.
3. Shared CAS diagram extraction.
4. Then Thought Tree.
5. Then Idea Atlas.

## Required First Artifact

Create a shared substrate package before UI build:

`dashboard/src/lib/casGraph/`

Suggested files:

- `types.ts`
  - `CasGraphNode`
  - `CasGraphEdge`
  - `CasGraph`
  - `ThoughtTree`
  - `IdeaAtlasGraph`
- `identity.ts`
  - `makeNodeKey(kind, role, normalizedLabel, axisAttrs)`
  - `makeEdgeKey(sourceKey, targetKey, kind, label)`
  - stable normalization for CAS labels
- `palette.ts`
  - CAS Color v1.0 constants copied from the SGGS spec into code
- `fromCompilerDiagram.ts`
  - maps compiler diagram payloads into graph nodes/edges
- `fromStage3Trace.ts`
  - later maps Stage 3 / Mode 3 trace into graph nodes/edges

This lets Thought Tree, Idea Atlas, SGGS, paper exports, and trace overlays
share identity instead of inventing it independently.

## Scope Correction

Phase 1 as written is probably too broad if treated as one build:

- Thought Tree full node set
- Idea Atlas force graph
- search/filter
- SVG export
- accessibility
- shared extraction

Recommended Phase 1 should be split:

### Phase 1A — Substrate

- canonical graph types
- stable node/edge keys
- palette constants
- compiler diagram adapter
- small fixture set
- unit tests

### Phase 1B — Thought Tree v0

- static 2D tree
- root / commitment / sub-thought / validation node types
- expand/collapse
- keyboard navigation basics
- SVG export if cheap, otherwise export in Phase 1C

### Phase 1C — Idea Atlas v0

- 2D graph over the same `CasGraph`
- click/select detail panel
- search/filter
- simple SVG export

Live growth, rewind, slow motion, Mode 7 overlay, 3D SGGS, webcam gesture, and
large-scale persistence should remain Phase 2+.

## Specific Decisions

Codex recommendations for the open questions:

1. **Tree node card size**
   - Use fixed card widths with adaptive height up to a cap.
   - Keep layout stable; let detail panel show full content.

2. **Atlas force simulation tuning**
   - Start with deterministic seeded layout for tests.
   - Tune force parameters after real fixture data exists.

3. **Default visual density**
   - Default to calm mode.
   - Show major nodes first; minor register/drive nodes can be toggled.

4. **Session vs persistent default**
   - Default to session-only for privacy.
   - Let users explicitly save/persist an atlas.

5. **Mobile/tablet**
   - Full keyboard/mouse/touch parity for core actions.
   - Simplify dense graph controls on mobile; do not promise desktop parity for
     10k-node graphs.

6. **Color customization**
   - Lock CAS Color v1.0 as default/export palette.
   - Allow accessibility overrides locally, but exports default to locked
     palette unless the user opts out.

## Blockers Before UI Implementation

- The SGGS palette PDF must be turned into a concrete TypeScript constants
  file. "Palette lives in PDF" is not enough for implementation.
- Canonical identity needs exact normalization rules, not prose.
- The two Idea Atlas component directories need a naming decision.
- Backend persistence is explicitly out of spec, so Atlas v0 should use
  in-memory/session data until a storage schema lands.
- Thought Tree input source must be specified:
  - compiler diagram,
  - Stage 3 local smoke report,
  - Mode 3 trace,
  - or all via adapters.

## Relation to Current Stage 3 Work

This UI spec should not interrupt the current six-step Stage 3 integration
order.

Current immediate path remains:

1. Stage 3 local loader — done.
2. One-record smoke — done.
3. CAS-input CLI — next.
4. Chat REPL.
5. Mode 7 / trace.
6. Thought Tree / Idea Atlas can consume trace outputs once the trace schema is
   concrete.

The UI work becomes much easier after the CAS-input CLI and trace schema exist.

