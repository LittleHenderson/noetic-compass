# CAS-RPA: offline CAS-Ohm atlas

This addition connects the real local PCBA checker and CAS-Ohm compiler to a
saved atlas and its offline viewer. It provides nested inspection, exact item
addresses, saved versions, explicit profile coordinates, and a comparison of
the declared R=4 design with a hypothetical R=6 alternative.

The displayed present is an explicitly **host-declared fixture**. No sensor,
live Helm state, board execution, learned result, or control permission is
provided.

## Reproduce and open

Run these commands in PowerShell:

~~~powershell
Set-Location -LiteralPath 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\codex-helm-data\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' tools/reproduce_rpa_ohm_atlas.py --out records/rpa_ohm_atlas_20260922/demo
~~~

Open the resulting file in a browser by double-clicking:

~~~text
records/rpa_ohm_atlas_20260922/demo/atlas.html
~~~

The HTML contains its data, styles and script. It needs no server or network.
Its content security policy blocks network connections. The Python reproducer
uses the existing local compiler/checker dependencies; it does not install
anything.

The output directory must resolve inside the existing CNCM homebase.
The default is the same demo directory shown above. Re-running replaces only
the five generated artifact names:

| File | Contents |
| --- | --- |
| declaration.json | Explicit source declarations and friendly display labels |
| atlas.json | Revalidated saved atlas, profiles, full sources and calculation receipts |
| atlas.html | Self-contained viewer, rendered through tools/render_rpa_view.py |
| verification.json | Checks actually executed by the reproducer, numerical results, addresses, navigation trace and source hashes |
| hashes.json | Byte counts and SHA-256 hashes for the other four artifacts |

The reproducer checks that its recorded implementation and source-page files
do not change while it runs. It reads generated files back after writing.
Its evidence does **not** claim that it ran pytest or exercised a browser.
The current machine's browser checks and broader test results are separate
verification records.

## Explore the saved designs

1. Select **Board · saved R=4 design** and choose **Inspect item**, then
   **Enter parts**. Continue through the stage and resistor. Inspect the flow
   calculation to see the compiler result and exact inputs.
2. Use the breadcrumbs or **Back** to return through the declared structure.
   **Present** returns to the project scope.
3. Inspect **Flow calculation · 12 / 6 = 2** to compare the hypothetical
   version. The recorded present remains the project fixture.
4. Change **Coordinate reference**. Only the coordinate chart changes.
   The selected item's identity, exact source and declared present remain fixed.
5. Open **Exact saved address**, choose **Put address in lookup**, and use
   **Find exact item**. Addresses bind the complete snapshot, node, permanent
   item ID, saved version and context.
6. Use **Save view**, **Download view**, **Open view file**, or the
   **Saved view link** to retain inspection, reference and breadcrumbs.
   A saved view from a different source snapshot is refused.

Flower and graph positions are display layouts. Coordinates mode uses two
selected components of the 39-dimensional chart. Screen proximity is not a
proof of equivalent state, reachable transition, attention flow or path cost.
The unprofiled note remains explicitly unassigned.

## Calculation and record boundaries

The R=4 board passes the checker's supported static subset. Its exact resistor
literal, the explicit drive value 12, the declared scale, and provenance
references enter the real CAS-Ohm path. The result is 3. The separately saved,
hypothetical R=6 board gives 2.

The adapter does not infer resistance units from CAS state symbols. It does
not infer series, parallel or total resistance. Each case retains:

- Full board source and its SHA-256.
- Exact selected resistor expression and compiler expression.
- Compiler/helper source identities.
- Exact quantity reports, declared scales, original references and formula
  lineage, replayed using the existing helper.
- PCBA check scope and the calculation's absence of measurement authority.

Loading an atlas reconstructs and compares the complete record, including
provenance and bindings. Replacing a report and merely recalculating the outer
hash cannot make it valid. Caller references remain unverified even when the
formula is consistent.

Permanent item IDs are caller-assigned identifiers, not authenticated global
registry entries. Different saved versions share their item identity and
retain separate node IDs and exact addresses. Equal profiles never merge
records. The exact address is meaningful for that complete saved snapshot;
a regenerated or changed snapshot has a different address.

The new wrapper uses the existing AtlasSnapshot schema. Its supported
relationships are declared **contains_part** and **references_same_idea**.
Containment enables entry into a declared interior; a shared-identity link
does not. Both are declared structure, not execution evidence. Navigation is
bounded to 32 nodes and cannot change the saved source.

## Profiles and mathematics

Every assigned profile contains 40 explicit, canonical, strictly positive
rational values whose exact sum is one. Its basis, ordering, origin and
reference must be supplied. CAS labels and full descriptions do not generate
profile values automatically. The demo deliberately supplies example profiles;
these are neither measurements nor probabilities of future outcomes.

Two explicitly named permutations are accepted:

- Canonical: **^0..^9 x P,C,E,O; row-major**.
- Alternate: **P,C,E,O x ^0..^9; domain-major**.

These reorder the same 40 labels. They do not map Domains to Registers,
Foundations, Drives or other CAS namespaces. The wrapper converts to canonical
order while retaining the original order declaration. Coordinate comparison
requires the same declared basis.

With positive profile \(p\), explicitly selected reference \(r\), and
denominator label **^9/O**, the 39 coordinates are:

\[
z_i=\log(p_i/p_{40})-\log(r_i/r_{40}),\qquad i=1,\ldots,39.
\]

The inverse uses that actual reference:

\[
w_i=r_i\exp(z_i)\quad(i<40),\qquad w_{40}=r_{40},\qquad
p_i=w_i/\sum_jw_j.
\]

The implementation uses bounded exact rational inputs and approximate
binary64 output with a stable inverse. It reports its numerical policy and
round-trip tolerance. It refuses unrepresentable boundary results instead of
clipping values or inventing a small positive value. Missing profiles remain
missing; a missing present profile never creates a uniform reference.

Changing reference changes only the chart:
\(z(p;q)=z(p;r)-z(q;r)\).
This is a coordinate chart, not an implemented Fisher–Rao distance or a
transition-cost model.

The source is *CAS_Recursive_Possibility_Atlas_v0_1.pdf*, pages 6–7 and 20–22,
SHA-256:

~~~text
e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab
~~~

The existing mathematical review is
[CAS_RPA_MATHEMATICAL_REVIEW.md](CAS_RPA_MATHEMATICAL_REVIEW.md).
Retained page images and text are in
[records/rpa_ohm_atlas_20260922/source_pages](../records/rpa_ohm_atlas_20260922/source_pages).
The reproducer hashes those retained pages and checks the historical PDF
identity record. It does not claim to reopen the PDF during each reproduction.

## Verification and remaining scope

The final verification ran **354 distinct tests**, all passing with no skips,
including actual Chrome interactions and existing atlas/Ohm regressions.
See the [verification record](../records/rpa_ohm_atlas_20260922/VERIFICATION.md)
for the exact test files, resolved failures and evidence.

The reproducer executes record replay, all exact-address lookups, distinct
saved versions, equal-profile identity preservation, nested navigation,
fixed-present inspection and reference changes, order permutation, centered
coordinates, inverse recovery, and R4/R6 calculation equality across the
PCBA/compiler/projection records. It labels the result
PASS_EXECUTED_DETERMINISTIC_CHECKS only after those checks succeed.

The focused Python checks can be run separately:

~~~powershell
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' -m pytest tests/test_rpa_ohm_atlas.py tests/test_rpa_coordinates.py tests/test_rpa_ohm_view.py -q
~~~

This completes the bounded local atlas connection for these saved records.
It does not add live Helm measurement or control, learning, general transition
generation, automatic profile assignment, a complete component board,
Fisher–Rao geometry, or a proof of full CAS-RPA or cognitive-machine completion.
