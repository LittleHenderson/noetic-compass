# Dashboard Idea Atlas casing audit — 2026-05-13

**Status:** Reconnaissance only. No files moved, renamed, or deleted. Recommendations only.
**Trigger:** Codex audit `2026-05-13` for commit `f3f59fa` flagged a casing split between
`dashboard/src/components/IdeaAtlas/` and `dashboard/src/components/idea-atlas/` as risky
before serious Atlas work.
**Repo path note:** the dashboard lives at
`noetic-compass-scaffold/noetic-compass/dashboard/`. All paths below are relative to that
dashboard root unless prefixed `repo-root:`.

---

## 1. Goal

Codex flagged that two directories with the same name in different cases
(`IdeaAtlas/` PascalCase and `idea-atlas/` kebab-case) coexist under
`dashboard/src/components/`. On Windows the filesystem is case-insensitive but Git is
case-sensitive, so this kind of split is invisible locally and only breaks on
case-sensitive filesystems (Linux CI, Mac with case-sensitive APFS, Docker images) or
on case-sensitive bundler lookups.

This audit answers three questions:

1. What is actually in each directory and what does it do?
2. Are the two directories duplicates, partial overlap, or unrelated work that just
   shares a name?
3. Which casing should win, and what is the safe order of operations to clean it up?

The headline finding up front: **the two directories are NOT duplicates**. They hold
different code with different purposes. The lowercase `idea-atlas/` is the actually
shipped, route-wired Sprint-1/2/3 Atlas UI. The PascalCase `IdeaAtlas/` is an
uncommitted scaffold that introduces a different (toggle + reactflow + stub) Atlas
direction and has zero importers. The cleanup is not a rename — it is a decision
about which Atlas direction is canonical, and an alignment of the leftover directory's
casing to match.

---

## 2. Inventory

### 2a. `dashboard/src/components/IdeaAtlas/` (PascalCase, UNTRACKED in git)

All 7 files are untracked. `git status` reports the entire directory as untracked. No
file in this directory has ever been committed.

| File | Bytes | Last commit | Purpose |
|---|---:|---|---|
| `IdeaAtlasView.tsx` | 6928 | — (untracked) | Skeleton view renderer; lists Idea-node summaries inside an `InfiniteCanvas` wrapper. Documents reactflow integration plan in comments. |
| `DiagramView.tsx` | 5951 | — (untracked) | Skeleton renderer for the compiler-derived typed CAS diagram (state nodes, clusters, relations). Pairs with `IdeaAtlasView` as the other half of an atlas/diagram toggle. |
| `InfiniteCanvas.tsx` | 4616 | — (untracked) | Pan/zoom canvas wrapper. Comments document the intent to back this with `reactflow`; currently a placeholder div. |
| `ViewToggle.tsx` | 4427 | — (untracked) | Two-button tab control that switches between the atlas view and the diagram view. |
| `types.ts` | 8178 | — (untracked) | TypeScript types mirroring `cas-native/atlas/idea_atlas.py` and the compiler `diagram` field. Includes `IdeaAtlas`, `IdeaNode`, `IdeaEdge`, `CasDiagram`, `DiagramNode`, `GenerationTrace`, `CasPrediction`, `AtlasViewMode`, etc. |
| `stubs.ts` | 3176 | — (untracked) | Stub fixture data (`STUB_ATLAS`, `STUB_DIAGRAM`, `STUB_TRACE`, `STUB_CORRESPONDENCE`) for testing the UI without a backend. |
| `index.ts` | 1351 | — (untracked) | Barrel file re-exporting the views, the stubs, and the types. Suggests an `@/components/IdeaAtlas` import alias (the alias is not configured in `tsconfig.app.json`). |

Filesystem mtimes: all files last modified `May 4-6, 2026`. Directory created
`May 4, 2026`.

Self-contained: the only inter-file imports within this directory are
`IdeaAtlasView -> ./InfiniteCanvas`, `IdeaAtlasView -> ./types`,
`DiagramView -> ./InfiniteCanvas`, `DiagramView -> ./types`,
`InfiniteCanvas -> ./types`, `ViewToggle -> ./types`, `stubs -> ./types`, plus the
re-exports in `index.ts`. Nothing from this directory imports anything outside it.

### 2b. `dashboard/src/components/idea-atlas/` (kebab-case, TRACKED in git)

All 4 files are tracked. First introduced 2026-04-27 in commit `32dff45`
(`feat(idea-atlas): /idea-atlas page + sidebar entry + capture/list UI`).

| File | Bytes | Last commit | Purpose |
|---|---:|---|---|
| `GraphView.tsx` | 12414 | `0504aa8` (2026-04-27) | Hand-rolled SVG force-directed graph (charge + link + center forces, 220 ticks). Renders nodes and edges from an `Idea[]`/`Edge[]` model. Used by `IdeaAtlasPage` in GRAPH mode. |
| `InversionModal.tsx` | 9743 | `4ad6ad0` (2026-04-27) | Sprint 3 modal that lets the user pick an inversion axis (N/W/F/E/S/A/P), calls `POST /idea_atlas/invert`, and commits the inverted CAS expression as a new idea. |
| `NodeDetailPanel.tsx` | 9010 | `c2c5cc7` (2026-04-27) | Sliding right-side panel that shows an idea's original text, CAS expression, timestamp, AST, and a small CAS structure diagram fetched via `/notation/compile`. Wires Invert and Delete actions. |
| `useRippleAnimation.ts` | 3085 | `4ad6ad0` (2026-04-27) | Hook that injects a `@keyframes idea-atlas-ripple` stylesheet and exposes a per-id class accessor for a brief pulse when a target idea changes. |

Directory mtime: `April 27, 2026`.

This directory was developed in Sprints 1-3 across three commits: `32dff45` (Sprint 1
page + sidebar), `3a03f35` (Sprint 2 D3 force graph + detail panel), `4ad6ad0`
(Sprint 3 InversionModal + ripple hook), with a polish pass in `0504aa8`. Followup
`c2c5cc7` added voice capture + CAS Structure preview to `NodeDetailPanel`.

---

## 3. Reference map

### 3a. Importers that reach into `IdeaAtlas/` (PascalCase)

No external file imports anything from `dashboard/src/components/IdeaAtlas/`. The
barrel `index.ts` is never consumed.

Documentation mentions (non-code references):

| Referrer | Line | Form |
|---|---:|---|
| `dashboard/src/components/IdeaAtlas/index.ts` | 12 | Comment: `import ... from '@/components/IdeaAtlas';` (illustrative; the `@` alias is not configured) |
| `cas-native/atlas/idea_atlas.py` | 19 | Docstring: ``dashboard/src/components/IdeaAtlas/types.ts`` mirrors this schema |
| `cas-native/inference/atlas_adapter.py` | 3 | Docstring: refers to `dashboard/src/components/IdeaAtlas/` as part of the shipped Idea Atlas surface |

The two Python docstrings appear to be documentation drift — they point at the
PascalCase directory as if it were the shipped surface, but in fact the route-wired
shipped surface is the lowercase directory.

### 3b. Importers that reach into `idea-atlas/` (kebab-case)

| Referrer | Line | Form |
|---|---:|---|
| `dashboard/src/pages/IdeaAtlasPage.tsx` | 4 | `import { GraphView } from '../components/idea-atlas/GraphView';` |
| `dashboard/src/pages/IdeaAtlasPage.tsx` | 5 | `import { NodeDetailPanel } from '../components/idea-atlas/NodeDetailPanel';` |
| `dashboard/src/pages/IdeaAtlasPage.tsx` | 6 | `import { InversionModal } from '../components/idea-atlas/InversionModal';` |
| `dashboard/src/pages/IdeaAtlasPage.tsx` | 7 | `import { useRippleAnimation } from '../components/idea-atlas/useRippleAnimation';` |
| `dashboard/src/App.tsx` | 23, 62 | Lazy-imports `IdeaAtlasPage` and mounts the `/idea-atlas` route (kebab-case URL, unrelated to filesystem casing but consistent). |
| `dashboard/src/components/layout/Sidebar.tsx` | 23 | Navigation entry pointing to the `/idea-atlas` route. |
| `docs/working/exposure_button_traceability_spec.md` (in `noetic-compass-scaffold/noetic-compass/docs/`) | 48 | Spec text: `dashboard/src/components/idea-atlas/GraphView.tsx (already built).` |
| `dashboard/src/components/IdeaAtlas/InfiniteCanvas.tsx` | 17-21 | Comment in the PascalCase scaffold acknowledging the older `idea-atlas/GraphView.tsx` and flagging it as a future migration target. |

### 3c. Cross-casing references in import lines

There are **zero** real code imports that target the PascalCase directory. Every
import statement that names the components/* path uses lowercase `idea-atlas/`.

This means a Linux/Mac case-sensitive build of the current repo would compile fine
without the PascalCase directory existing at all — it is dead code on disk that has
never been linked into the bundle.

---

## 4. Content comparison

There is **no file-by-file overlap**. The two directories were not even attempting to
build the same thing. The differences:

| Concern | `IdeaAtlas/` (PascalCase) | `idea-atlas/` (kebab-case) |
|---|---|---|
| Renderer | Skeleton, plans to use `reactflow` | Hand-rolled SVG with home-grown force simulation |
| Data model | Mirrors `cas-native/atlas/idea_atlas.py` (`IdeaNode`, `IdeaEdge`, `IdeaAtlas`) plus compiler `CasDiagram` | Local `Idea` / `Edge` interfaces defined inline in `GraphView.tsx` and `InversionModal.tsx` (no shared schema file) |
| Toggle pattern | Atlas/Diagram dual-view via `ViewToggle` + `InfiniteCanvas` | List/Graph toggle implemented inside the page (`IdeaAtlasPage.tsx`) |
| Inversion UI | Not present in the scaffold | `InversionModal.tsx` (full 7-axis picker + API call) |
| Stub fixtures | Yes (`stubs.ts`) | No |
| Animations | Static | `useRippleAnimation` keyframe hook |
| Live route | Not wired | Wired at `App.tsx:62` to `/idea-atlas` |
| Reactflow dependency | Comments require `npm install reactflow` | Not required |
| Git status | Untracked (never committed) | Tracked (5 commits across April 27, 2026) |

No filenames collide between the two directories, so there is no "which copy wins"
question on individual files — they are disjoint sets.

The semantic overlap is conceptual: both directories aspire to be "the Idea Atlas UI
under `components/`". They embody two different design directions for that surface,
written by different agents at different times, with no merge point.

---

## 5. Build-system check

Three pieces of build configuration are relevant:

1. **`dashboard/tsconfig.app.json`** — TypeScript config. `moduleResolution` is
   `"bundler"`, `include` is `["src"]`. No `paths` aliases are defined; the
   `@/components/IdeaAtlas` form in the `index.ts` comment is aspirational, not
   functional. TypeScript will pick up files only if they are imported through a
   relative path that resolves successfully.
2. **`dashboard/vite.config.ts`** — Vite config. No custom resolver or alias for the
   `components/` directory. Vite resolves modules through Rollup, which on Linux is
   strictly case-sensitive. On Windows and default Mac (case-insensitive APFS),
   Rollup will follow the case used in the `import` statement; if the import string
   says `idea-atlas/GraphView`, that is what is resolved.
3. **`dashboard/package.json`** — No `files` glob, no workspace configuration that
   would pull in the PascalCase directory. Build script is `tsc -b && vite build`;
   neither step reaches into directories that are not imported.

Conclusion: today's bundler does NOT silently pick up the PascalCase directory.
Because nothing imports it, Vite/Rollup never see it. Today's build behaviour is
identical on Windows, Mac, and Linux: the PascalCase directory is dead code on disk.

The casing risk Codex flagged is therefore a future-facing risk, not a live build
break. It bites if and when:

- A new import is added by hand that uses `IdeaAtlas/...` casing on Windows and
  ships to Linux CI (Linux build fails with "Cannot find module").
- A future merge of the PascalCase scaffold into the live import graph happens
  without first deciding which casing to keep; whichever casing the build settles on
  may not match what some developer typed in another file.
- A `paths` alias is added to `tsconfig.app.json` that maps `@/components/*` and a
  future file imports `@/components/IdeaAtlas`. On Linux that would resolve the
  PascalCase directory; on Windows it would also resolve the lowercase one through
  case-insensitive lookup, hiding the bug until CI runs.

---

## 6. Recommended canonical casing

**Recommended choice: keep `idea-atlas/` (kebab-case) as canonical. Move the
PascalCase scaffold's content into the same kebab-case directory, or stage it under a
clearly named sibling, before any new code is added against it.**

Reasoning:

- **Route alignment.** The user-facing URL is `/idea-atlas` (kebab-case) — see
  `dashboard/src/App.tsx:62` and `dashboard/src/components/layout/Sidebar.tsx:23`.
  Matching the directory to the route is the lowest-surprise option for any future
  reader.
- **Existing dashboard convention.** Every other multi-file component directory under
  `dashboard/src/components/` is lowercase or kebab-case: `charts/`, `config/`,
  `layout/`, `shared/`. The PascalCase `IdeaAtlas/` is the only exception. Single-
  file components at this level are PascalCase (e.g., `RadialArchitectureDisplay.tsx`),
  but directories are lowercase. Keeping the PascalCase directory would make it the
  odd one out.
- **Real importers, real history.** Every existing import statement uses
  `idea-atlas/`. The lowercase directory has 5 commits and is wired into the live
  route. The PascalCase directory has no commits and no importers.
- **Git case-sensitivity hazard direction.** When two casings exist in the working
  tree and only one is tracked, picking the tracked one minimises the chance of a
  later `git mv` accidentally creating a second tracked-but-shadowed entry. The
  lowercase directory is already what Git "sees"; aligning the scaffold to that
  casing keeps the casing single-valued in the index.

The scaffold's *content* is still valuable: the typed schema in
`IdeaAtlas/types.ts`, the stub fixtures in `stubs.ts`, the toggle/canvas pattern in
`ViewToggle.tsx`/`InfiniteCanvas.tsx`, and the schema-mirroring contract with
`cas-native/atlas/idea_atlas.py` should not be thrown away. The recommendation is
about *where they live*, not whether they live.

---

## 7. Cleanup plan

This is a recommendation. No commands have been executed. Run them in the order
shown after the user/Codex have approved a casing decision.

There are two reasonable shapes for the cleanup. Pick one; do not interleave.

### Option A (recommended) — merge PascalCase content into lowercase directory

Step 1. **Decision artefact.** Land a short ADR or decision note under
`docs/working/agent_exchange/decisions.md` (or wherever the agent exchange protocol
puts decisions) that fixes the canonical casing as `idea-atlas/` and points
collaborators at this audit. No code change in this step.

Step 2. **Stage the move locally.** From `noetic-compass-scaffold/noetic-compass/`,
move each PascalCase scaffold file under the lowercase directory. On Windows, casing
changes need `--force` because the filesystem treats the names as identical:

```
git mv --force \
  dashboard/src/components/IdeaAtlas/IdeaAtlasView.tsx \
  dashboard/src/components/idea-atlas/IdeaAtlasView.tsx
git mv --force \
  dashboard/src/components/IdeaAtlas/DiagramView.tsx \
  dashboard/src/components/idea-atlas/DiagramView.tsx
git mv --force \
  dashboard/src/components/IdeaAtlas/InfiniteCanvas.tsx \
  dashboard/src/components/idea-atlas/InfiniteCanvas.tsx
git mv --force \
  dashboard/src/components/IdeaAtlas/ViewToggle.tsx \
  dashboard/src/components/idea-atlas/ViewToggle.tsx
git mv --force \
  dashboard/src/components/IdeaAtlas/types.ts \
  dashboard/src/components/idea-atlas/types.ts
git mv --force \
  dashboard/src/components/IdeaAtlas/stubs.ts \
  dashboard/src/components/idea-atlas/stubs.ts
git mv --force \
  dashboard/src/components/IdeaAtlas/index.ts \
  dashboard/src/components/idea-atlas/index.ts
```

Caveat: because the PascalCase files are currently **untracked**, the `git mv` calls
above will not produce a clean rename — `git mv` on an untracked source falls back to
"copy then add". Equivalent two-step alternative:

```
mv dashboard/src/components/IdeaAtlas/* dashboard/src/components/idea-atlas/
rmdir dashboard/src/components/IdeaAtlas
git add dashboard/src/components/idea-atlas/IdeaAtlasView.tsx \
        dashboard/src/components/idea-atlas/DiagramView.tsx \
        dashboard/src/components/idea-atlas/InfiniteCanvas.tsx \
        dashboard/src/components/idea-atlas/ViewToggle.tsx \
        dashboard/src/components/idea-atlas/types.ts \
        dashboard/src/components/idea-atlas/stubs.ts \
        dashboard/src/components/idea-atlas/index.ts
```

Because the source files were never tracked, no history is being rewritten and no
case-only rename is necessary. The PascalCase directory simply disappears after the
last file moves.

Step 3. **Resolve the only internal collision.** `idea-atlas/` does not have a file
named `index.ts`; the scaffold's `index.ts` lands cleanly. None of the other
filenames collide either. No content merge is needed.

Step 4. **Fix the two documentation drifts in Python.** Update the doc strings that
point at the PascalCase path:

- `cas-native/atlas/idea_atlas.py:19` — change
  `dashboard/src/components/IdeaAtlas/types.ts` to
  `dashboard/src/components/idea-atlas/types.ts`.
- `cas-native/inference/atlas_adapter.py:3` — change
  `dashboard/src/components/IdeaAtlas/` to
  `dashboard/src/components/idea-atlas/`.

These are docstring-only edits in Python files. They do not change behaviour. They
should ride in the same PR as the move so the cleanup is one self-consistent unit.

Step 5. **Fix the barrel's example import.** The moved
`idea-atlas/index.ts` JSDoc currently advertises
`import ... from '@/components/IdeaAtlas';`. Either:

- Leave the barrel with a corrected example
  (`import ... from '@/components/idea-atlas';`), and accept that the `@` alias is
  still aspirational; or
- Remove the example until the alias is actually configured in `tsconfig.app.json`.

This is a comment-only change in the barrel file.

Step 6. **Decide the new file imports** that bridge the two pre-existing surfaces.
None of the existing lowercase files (`GraphView`, `InversionModal`,
`NodeDetailPanel`, `useRippleAnimation`) need import changes — they did not refer to
the PascalCase scaffold at all. The new scaffold files (`IdeaAtlasView`,
`DiagramView`, `InfiniteCanvas`, `ViewToggle`, `types`, `stubs`) already use relative
`./` imports that survive the move unchanged.

Step 7. **Validate.** From `dashboard/`:

```
npm run lint
npm run build
npm test
```

`tsc -b` will fail loudly if any case-only resolution issue remains. CI on Linux is
the authoritative case-sensitivity check.

Step 8. **Rollback strategy.** If `npm run build` fails after Step 2, revert with
`git restore --staged --worktree dashboard/src/components/idea-atlas/` to drop the
newly added files; the PascalCase originals will need to be restored from a working
copy backup taken before the `mv` (since they were never tracked, Git cannot bring
them back on its own). Take the backup before running Step 2.

### Option B — explicitly archive the PascalCase scaffold

If the user decides the lowercase Sprint-1/2/3 Atlas is the only Atlas direction and
the PascalCase scaffold should be set aside without bringing its content into the
live tree:

1. Move the PascalCase directory out of `dashboard/src/components/` into a holding
   area such as `docs/design/idea_atlas_v2_scaffold/` or
   `noetic-compass-scaffold/noetic-compass/dashboard/_design/idea-atlas-v2/`.
2. Leave a one-line `dashboard/src/components/idea-atlas/README.md` pointer at the
   archived design so future agents do not re-invent it.
3. Update the two Python docstrings (Step 4 above) to point at the live lowercase
   directory.
4. Do NOT delete the scaffold files outright; the `types.ts` schema mirroring the
   Python data model is the most-likely-needed artefact and should remain readable
   somewhere in the repo.

Option B is correct if the scaffold's design (toggle + reactflow + typed schema) is
considered out of scope for the near-term Atlas build. Option A is correct if the
scaffold's content is in scope and the only blocker is the casing.

The user/Codex should decide between Option A and Option B. Both options eliminate
the casing split.

---

## 8. Risk assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Linux CI build break from a future import using the PascalCase casing | Medium today and rising as the Atlas gets built out | Build red on CI | Doing the cleanup before serious Atlas work (Codex's stated reason for flagging this) |
| Loss of the PascalCase scaffold's content (typed schema + stubs) if files are deleted instead of moved | Low if the plan is followed | Schema work would have to be redone | Take a working-copy backup of `IdeaAtlas/` before the `mv`. Files are untracked so Git cannot restore them |
| Wrong casing chosen and then changed again later | Low | One follow-up PR | The Section 6 rationale should be reviewed by the user/Codex before any move happens |
| Live `/idea-atlas` route breaks | Very low under Option A; zero under Option B | High if it happens | The live route imports only from `idea-atlas/`. Option A keeps that directory and only adds the scaffold files alongside; the four existing files are not touched |
| Python docstring drift left in place | Low risk to behaviour, medium risk to future reader confusion | Future agents mis-cite paths | Fix in the same PR (Step 4 above) |
| TypeScript path alias `@/components/IdeaAtlas` is added later and resolves on Windows but not on Linux | Low if Option A is taken (alias would now resolve to `idea-atlas`) | Build red on CI | Whichever casing is canonical, add the alias against that casing only |
| Case-only rename gotcha if anyone tries to convert the *tracked* `idea-atlas/` directory to a different casing | Not applicable in either Option above; flagged for completeness | Hidden duplicate-tracking in Git | If the user later wants to rename `idea-atlas/` itself, use `git mv --force` plus a tracked intermediate filename to force the index update |

Blast radius is small. The live Atlas surface uses only the lowercase directory.
Nothing in the bundle currently depends on the PascalCase directory. The cleanup is
disruptive only if Option A's `mv` step is run without a working-copy backup of the
untracked scaffold files.

---

## 9. Suggested PR order

Both options are small enough to fit in a single PR if the user prefers minimum
overhead.

### Option A as a single PR
1. Move the seven PascalCase files into `idea-atlas/`.
2. Delete the now-empty `IdeaAtlas/` directory.
3. Update the two Python docstrings.
4. Update the moved `idea-atlas/index.ts` JSDoc example string (kebab-case).
5. Run `npm run lint && npm run build && npm test` from `dashboard/`.
6. Commit message:
   `dashboard: align Idea Atlas directory casing on idea-atlas/`.

### Option B as a single PR
1. Move the PascalCase directory into the chosen archive location.
2. Update the two Python docstrings.
3. Add a one-line `idea-atlas/README.md` pointer at the archived design.
4. Run the dashboard lint/build/test triad.
5. Commit message:
   `dashboard: archive v2 IdeaAtlas scaffold, lock idea-atlas/ as canonical`.

If the user prefers separation, the move (Step 1-2) is one PR and the docstring +
README touches (Step 3-4) are a follow-up; the docstring fixes do not block the move.
Single-PR is cleaner because the docstrings drift back to "current truth" only after
the move lands.

---

## 10. Open questions to surface before any cleanup PR ships

1. **Which option does the user want?** Option A (merge scaffold into live directory)
   or Option B (archive scaffold)? This audit cannot answer that on its own because
   it depends on whether the toggle + reactflow + typed-schema scaffold direction is
   still in scope for the near-term Atlas.
2. **Should the typed `types.ts` schema be promoted to a shared substrate before any
   merge?** Codex's audit doc
   (`docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md` Section
   "Required First Artifact") proposes a `dashboard/src/lib/casGraph/` shared
   substrate. If that lands first, the scaffold's `types.ts` may belong under
   `lib/casGraph/types.ts` rather than under either Atlas component directory. This
   would make Option A's move target wrong.
3. **Does the user want the `@/components/*` path alias configured now?** The
   PascalCase scaffold's barrel already advertises an `@/components/IdeaAtlas` import
   style, but no alias is configured in `tsconfig.app.json`. If the alias is added,
   every import in the dashboard becomes simultaneously eligible for case-sensitive
   alias resolution, which raises the stakes of getting the casing decision right
   the first time.
4. **Are the two Python docstring drifts the only Python-side references?** This
   audit searched the dashboard, `api/`, and `cas-native/`. If there is a `docs/`
   page that cites the PascalCase path verbatim and gets included in printed
   documentation, the docstring fix should extend to that page too. The only doc
   page found was `noetic-compass-scaffold/noetic-compass/docs/working/exposure_button_traceability_spec.md:48`
   and it already cites the *lowercase* path; no action there.
5. **Confirm that `cas-native/atlas/idea_atlas.py` is the schema source of truth and
   the scaffold's `types.ts` mirrors it.** The docstring claim is "lock-step";
   nothing in this audit verified field-by-field that the TypeScript and Python
   stayed in sync after the PascalCase scaffold landed on May 4. Worth checking in
   the merge PR.

---

## 11. Summary

The PascalCase `IdeaAtlas/` directory is an uncommitted, never-imported scaffold for
a second Atlas direction (reactflow + atlas/diagram toggle + typed schema mirrored
from Python). The kebab-case `idea-atlas/` directory is the live, route-wired
Sprint-1/2/3 Atlas (hand-rolled SVG force graph + node detail panel + inversion
modal). The two share no file names and no importers. The casing split is currently
dead code, not a live build break, but it becomes a live break the moment the
scaffold gets wired into the import graph on a case-sensitive filesystem.

Canonical casing: **`idea-atlas/` (kebab-case)** — matches the route, matches the
sibling directory convention, matches the entire commit history.

Cleanup: move the seven untracked scaffold files into the lowercase directory
(Option A) or archive them out of `components/` (Option B). In either case, fix the
two Python docstring drifts (`cas-native/atlas/idea_atlas.py:19` and
`cas-native/inference/atlas_adapter.py:3`). Run the dashboard lint/build/test triad
before merging.

Open questions in Section 10 should be answered by the user or Codex before the
cleanup PR is opened.
