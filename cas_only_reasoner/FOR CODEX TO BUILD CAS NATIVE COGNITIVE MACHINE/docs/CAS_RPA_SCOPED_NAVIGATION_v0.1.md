# Declared-structure navigation v0.1

**2026-09-22 follow-up:** The new CAS-Ohm atlas applies the same contains-only
inspection rules to checked board/stage/resistor/calculation records and adds
coordinates plus saved views. See [current scope and usage](CAS_RPA_OHM_ATLAS_20260922.md).
The compound-runtime adapter and its saved evidence described below are unchanged.

The user's proposed acceptance behavior is useful and concrete: enter a saved
procedure, enter its declared parts, then return through breadcrumbs while the
actual execution-state identity stays fixed. This extension implements that
inspection behavior for the retained compound-runtime 0.5 evidence format.
Final test and browser status belongs in `records/rpa_scoped_001/STATUS.md`.

## Relationship to the accepted baseline

The earlier compound and cube deliveries remain unchanged. Their radial layout
and focus controls do not establish entry into a node's internal structure.
This new adapter and renderer have separate filenames and a new document schema,
`cncm.rpa-scoped-compound-view/0.1`. They do not modify a runtime registry,
installed procedure, journal, execution state, or the original display document.

`scoped_from_journal` first invokes the existing compound adapter with the
caller's supplied genesis, ingress digests and expected journal digest. That
adapter reconstructs the saved execution before projection. `scoped_projection`
can also extend an existing display document. Its document hash binds content;
it does not identify the author or authorize execution. The reproduction helper
separately pins accepted source documents to the prior receipt.

## Declared interiors

- A retained call program contains its one or two declared primitive calls,
  its exact pinned primitive, and separately labeled retained evidence records.
- Each call contains its three declared input bindings. A binding names an
  original input slot or the first call's result, `r0`; it does not execute it.
- A primitive contains the six instructions present in its retained artifact.
- An evidence record can be inspected with its complete retained body. No
  undisclosed children or fabricated execution steps are added to a leaf.

The adapter reconstructs the program and primitive artifacts before deriving
their internal parts. It rejects displayed step identities, input slots,
instruction identities or dependency pins that disagree with those artifacts.
It copies the source document so callers cannot mutate their original through
an alias in the returned extension.

Only directed `contains_part` relationships permit entry. `refines_state`,
`reachable_via`, overlap and shared-idea references do not become containment.
The evidence-bundle projection is labeled as evidence organization, separately
from the calls or instructions that make up the procedure itself.

## Interaction and invariants

Inspect reads a record without changing depth. Enter replaces the local map
with the selected child's direct declared interior. Breadcrumbs preserve the
path used to get there. A path is bounded to 32 nodes, refuses cycles, and is
bound to one exact snapshot. A leaf has no Enter action. Returning to the loaded
state resets inspection, not execution.

The local flower and ordinary declared dependency graph contain the same direct
children and containment links at each scope. Paging limits visible cards to
eight without omitting entries from the selector. Smaller screens show the same
scope as a vertical layout. Exact node fields, relationship records and evidence
remain inspectable. All page operations are offline.

The immutable execution-state ID/hash, source content, inspection scope and
selected record have different roles. Tests and browser checks compare them
before and after navigation. A change in inspection scope cannot count as a
transition, installation, returned child result, completed task or learning.

## Evidence limits and remaining work

The exact ten accepted compound inputs have no assigned `profile40` values and
no overlap certificates. The four accepted cube documents were also checked
separately and have no assigned profiles or overlap certificates. These are
observations about those packages, not a claim about every CAS artifact.

This extension does not implement ALR/Fisher–Rao geometry, CAS-Ohm routing, the
complete component board, recursive reasoning or learning. Declared-graph parity
tests establish inspection consistency, not a performance advantage. Runtime
versions with different declared structures require their own versioned adapter;
the separate derived-memory 0.6 runtime is not silently treated as 0.5 input.
The wider CNCM charter remains open.
