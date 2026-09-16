# Cube and CAS-RPA bridge: review note

This is a separate, unpublished checkpoint prepared after compound viewer
checkpoint `d0308d86d27c66b4d8ba657528dfa2ac95a906cb`. The adapter is implemented;
its tests and this acceptance helper remain in scratch until final promotion. The historical
`docs/CAS_RPA_CUBE_INTEGRATION_v0.1.md` remains an unchanged design record.

## Implemented behavior

`cncm/rpa_cube_adapter.py` binds original bounded UTF-8 source bytes to both the
file SHA-256 and the canonical bundle digest. `CubeSourceReceipt` requires explicit
namespace and observation metadata, retains the bytes privately, and rechecks
them when a document or lesson is loaded. A receipt authenticates no person and
establishes no physical fact.

One complete source catalog retains the actual six-cube bundle. Its index keys
include source namespace, context, cube ID and revision. Canonical idea IDs exclude
presentation labels. Each selected presentation projects 43 nodes (one loaded
source state, six cubes, 36 faces) and 47 typed composition links, including all
five source `contains` branches. Face payloads, mappings, provenance and views
remain in the catalog once, with node references into that catalog.

All branch links remain `contains_part`. The graph-teaching operation
`REACHED_VIA` follows those structural links; it never creates an RPA
`reachable_via` execution event. Teacher witnesses name actual branch chains or
complete inventories. Why remains a structural teacher explanation; How remains
unsupported without an action contract.

Focus, paging and separately bound hypothetical graphs preserve the loaded
current state. Compiling while focused on a hypothesis still uses the explicitly
supplied complete base source. A hypothetical graph cannot commit a runtime
transition or replace the original source by being selected.

## Teaching boundary and identities

The existing unchanged compiler requires a teacher-shaped case because its
disclosure audit reads `correct`. The bridge derives that reference from the
authored graph, invokes the actual compiler, and then exports a closed learner
allowlist: `record_id`, `public`, and `encoded_options`. The answer, encoded
correct index, visibility diagnostics and supporting branch chains are saved in
a separate teacher sidecar. The public compilation entry point accepts no private
target. Compiler answers are not learner predictions.

The new input ID binds exact public bytes, ordered options and versioned encoding
context. A separate semantic question ID supports presentation comparisons. The
acceptance helper reproduces the legacy stale-ID case: renaming branch IDs changes
the public fact order while the old task ID and option order remain unchanged.
The new input ID changes. Optional model/checkpoint, tokenizer and encoder
digests are metadata only: `cache_identity_bound` does not claim cache readiness.

## Explicit limits and review fixes

- Only the complete `contains` presentation profile and guided/unassisted versions
  of LIST_PARTS, FIND_SHARED_PART and REACHED_VIA are supported. Partial graph
  views are refused because the frozen compiler ignores their `branch_refs` and
  would silently widen input. Partial correspondence coverage remains separate.
- Scored answers require declared complete inventory. Unknown and not-applicable
  faces preserve their own availability; unknown is not empty-complete.
- Private-target field names are rejected across the entire source, including
  context, views and provenance metadata. The frozen validator checked only cube
  nodes and branches.
- A partial face-five inventory must still be a unique subset of that cube's own
  outgoing branches. Foreign references are refused.
- Source reconstruction compares canonical JSON, so booleans cannot substitute
  for source integers and numeric zero cannot substitute for false. Cursor
  offsets and sizes require actual integers, even when the cursor is resealed.
- Teacher agreement checks matching input IDs, encoding identity and option/index
  coherence. It explicitly establishes only local consistency of the supplied
  export. To establish agreement with the source, recompile through the bounded
  source-backed document; hashes supplied by the caller do not authenticate it.
- The bridge rejects truncated prompts or option tags, including the frozen
  codec's 8,192-character prompt and 256-character tag truncation. Distinct
  choices cannot silently collapse to identical visible tags.
- Bounds: 8 MiB source, 12 MiB catalog, 24 MiB complete document, 2 MiB lesson,
  64 source cubes, 20 catalog rows per page, plus unchanged AtlasSnapshot limits
  of 512 nodes, 2,048 links and 8 MiB atlas JSON. Larger or unsupported inputs
  fail explicitly; deferred traversal is not evidence of absence.

Independent review discovered the target-metadata, truncation and partial-face
gaps. Initial failures remain in `draft_002.xml` and `adversarial_probe_*.txt`.
The corrected draft suite passed 45 tests in `draft_004.xml`; 306 unique
view/assistance compilations matched the existing compiler and were repeated in
a fresh process with model, tensor and provider imports blocked.

## Acceptance helper

`reproduce_cube_bridge.py` writes only to a new child directory of this scratch
folder. It never overwrites evidence. It records the running helper and source
bytes before importing project code, then verifies each actual project import
against those bytes at completion. The pinned adapter hash is
`00d4bdd06109dfa3324da548b37d5b10c6b117256d95f98eb875aa95938e1e62`.

The helper saves three actual inspector documents; 306 learner inputs, teacher
sidecars and bindings in separate files; compiler comparisons; exact cube/face/
branch/mapping identities; 129 focus checks; 420 equal-budget ordinary-graph/RPA
traversal checks; a source-bound rewired hypothesis; paging and target-isolation
records; explicit refusals; a cache-identity regression; actual module identities;
and a receipt covering every produced artifact. Observation ID and time must be
supplied explicitly. Failures retain a traceback and cannot be overwritten by a
later successful run.

No model, tensor, provider, optimizer, learner, action executor or deployment is
invoked. No new learned competence, layout advantage, causal inference, training
benefit or completion of the broader CNCM vision is claimed.
