# Independent final cube bridge review — resolution

Reviewed repaired adapter SHA-256:
`00d4bdd06109dfa3324da548b37d5b10c6b117256d95f98eb875aa95938e1e62`.

Status: no unresolved material finding remains within this bounded review.
Twelve final-review test methods and the earlier nine adversarial test methods
pass. This establishes the tested source/input/projection boundaries only, not
general security, complete CNCM acceptance, or learner competence.

The reviewer changed scratch probes and review notes only. Production source
repairs were made by the build agent. No learner construction, prediction,
training, provider call, or spending occurred. The fixed observation ID and
timestamp used by the probes are explicitly test fixture metadata, not measured
observation times or claims of an external event.

## Closed findings

- Reconstructed wire data now uses exact canonical JSON equality. Boolean,
  integer and floating-point aliases cannot alter bound cube records, provenance
  values, or source-path indices.
- Cursor offsets and limits require exact integer types. A resealed boolean or
  floating-point limit is refused.
- Teacher agreement requires shared learner/teacher record identity, recomputed
  public-input identity, consistent source revision and visibility identity,
  a valid integer option index, and equality between that option and the supplied
  teacher answer. Mixing valid records from two different lessons is refused.
- The prior review's source-private fields, option/prompt truncation, wrong partial
  face inventory, and silently widened partial view issues remain closed.

The pre-fix review notes and failed outputs are retained. In particular,
`final_review_effects_001.json` demonstrates that the old loader accepted a
record with a mismatched digest and a floating-point path that broke paging.
Those are historical failures, not results from the repaired adapter.

## Exact current evidence

- `final_review_probe_006.txt`: 12 final-review methods, zero failures/errors.
  It checks adapter hash before/after and verifies unchanged bytes.
- `adversarial_probe_006.txt`: 9 earlier adversarial methods, all passing.
  Adapter hash was reread after this run and matched the value above.
- `test_rpa_cube_final_review.py`: final independent probe source.
- `test_rpa_cube_adversarial.py`: earlier independent probe source.

The independent probes cover strict source JSON duplicate-key and nonfinite
number rejection; distinct file-byte/canonical-content identities; exact
catalog-to-source records and digests; cross-source cursor refusal; strict wire
and cursor scalar types; learner/teacher record and option-index joins; source
namespace separation; target-field exclusion; lossy option refusal; direct
inventory consistency; complete presentation coverage; and the six-cube
43-node/47-link containment-only projection.

Scratch modules install their import blocker for their standalone process.
They are review evidence, not ready to copy into a shared suite unchanged:
promotion must scope/restore the blocker and adjust scratch-relative paths.

## Integrity does not authenticate the source

Factory/loader integrity is relative to the externally supplied original bytes
and expected identities. The host supplies namespace, observation metadata and
revision. Matching hashes establish identity and reconstruction consistency;
they establish neither a trustworthy author nor true physical facts.

Use the source-bound factories or external-receipt loader for untrusted wire
input. Direct construction of the private-backed document object, or reading
its raw properties, is not a source-authentication interface.

Cursor checks bind a page to source content and exact range. They do not certify
who created the cursor or prove prior pages were visited. Explicit offsets permit
random access; a self-resealed cursor to another valid offset supplies no
evidence of complete inspection.

`check_teacher_target` now reports
`SUPPLIED_EXPORT_LOCAL_CONSISTENCY_ONLY`, `source_reconstructed=False`,
and `source_authenticity_established=False`. The final probe verifies those
exact values while changing a teacher reference to an existing distractor,
updating its option index, and resealing its digest. The coherent invented
reference is locally consistent, so agreement remains true. This is the expected
limit of a check without external source reconstruction. A source-grounded
answer requires fresh compilation against a document loaded from pinned source
bytes.

Supplied model/checkpoint/tokenizer/encoder IDs bind identity metadata only.
No actual encoder or cache capability was probed. The bridge prepares symbolic
teacher references and learner inputs; it does not establish a learner prediction,
learned transfer, causal execution, runtime advancement, or world truth.

