# CAS-RPA cube implementation v0.1

Status: **PURE_BRIDGE_IMPLEMENTED; FINAL_CHECKPOINT_ACCEPTANCE_PENDING**.

This is a separate checkpoint prepared after compound viewer checkpoint
`d0308d86d27c66b4d8ba657528dfa2ac95a906cb`. The new adapter has local conformance
evidence. Final source-bound acceptance, viewer verification and publication are
separate gates. The historical
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
Further review caught Python bool/int/float aliases in wire reconstruction and
cross-lesson teacher/learner joins. The pre-fix adapter bytes remain in
`records/rpa_cube_001/_scratch/rpa_cube_adapter_pre_scalar_fix.py`; their SHA-256 is
`129bcf8876a1489841e97b3161ef9d5751bc08884e7915e70b661f5b3c4e3275`.
The current fixed source passed **57 tests plus six subtests** in 31.43 seconds,
recorded locally in `records/rpa_cube_001/_scratch/draft_006.xml` (SHA-256
`8907f53b38c01d4f072a9aca60f41d2d405c822489735bf440f7aa44388d6d6e`).
The 306 unique view/assistance compilations matched the existing compiler and
were repeated in a fresh process with model, tensor and provider imports blocked.

The scratch acceptance run also passed: 306 compiler comparisons, 129 focus
checks, 420 equal-budget graph comparisons, 20 refusal probes and 31 actual project
imports bound to unchanged source bytes. All 24 retained artifacts were reread and
matched. Its local receipt is
`records/rpa_cube_001/_scratch/acceptance_candidate_001/receipt.json` (SHA-256
`a9ff8f684909ce63dd379679d89b04bf3df55b4e0badd60be54bd8a2ad9fa7b4`).
These ignored scratch records are preliminary local evidence; the final versioned
acceptance and publication must bind their own promoted tool and document bytes.

## Acceptance helper

`tools/reproduce_cube_rpa.py` writes only to a new direct child directory of
`records/rpa_cube_001`. It never overwrites evidence. It records the running helper and source
bytes before importing project code, then verifies each actual project import
against those bytes at completion. It also binds the implementation/design
documents and renderer as review inputs; listing these files is not a claim that
their behavior was executed. `--bind-input` adds further project files to this
before/after byte check. The helper itself must remain byte-identical throughout
execution. The pinned adapter hash is
`00d4bdd06109dfa3324da548b37d5b10c6b117256d95f98eb875aa95938e1e62`.

The helper saves three actual inspector documents; 306 learner inputs, teacher
sidecars and bindings in separate files; compiler comparisons; exact cube/face/
branch/mapping identities; 129 focus checks; 420 equal-budget ordinary-graph/RPA
traversal checks; a source-bound rewired hypothesis; paging and target-isolation
records; explicit refusals; a cache-identity regression; actual module identities;
and a receipt covering every produced artifact. Observation ID and time must be
supplied explicitly. Failures retain a traceback and cannot be overwritten by a
later successful run.

The promoted helper adds explicit refusals for catalog bool/int/float aliases,
numeric false provenance, resealed cursor size aliases, cross-joined teacher and
learner IDs, and mismatched teacher answer/index pairs. It also retains a fully
coherent resealed false reference to demonstrate the teacher agreement helper's
limited trust boundary. That helper can prove local consistency while the
supplied reference is wrong about the source.

`bridge_api_call_attempts` counts calls to the bridge API, including refusals
before reaching the frozen teacher compiler. This is not a count of completed
compilations, a compute measurement or evidence of learner work. The 306 matched
comparison count refers separately to successful graph-derived preparations.

No model, tensor, provider, optimizer, learner, action executor or deployment is
invoked. No new learned competence, layout advantage, causal inference, training
benefit or completion of the broader CNCM vision is claimed.
