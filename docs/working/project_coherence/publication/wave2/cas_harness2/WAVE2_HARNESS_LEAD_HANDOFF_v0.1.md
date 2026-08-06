# CAS Harness 2 Wave 2 Lead Handoff

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Base commit:** `c8635270ca6ba7c65504b4fda43cb42a89623015`

**Branch:** `codex/project-coherence-wave2-harness`

**Canon effect:** `NONE`

**Product-claim effect:** `NONE`

**Experimental result:** `NONE`

**Public disclosure:** `NOT AUTHORIZED`

## 1. Handoff outcome

This lane supplies a source-bound publication and specification delta for CAS
Harness 2. It reuses the existing Gate 5 preregistration, Evidence Packet v2,
review-matrix, adversarial-review, manifest, implementation, test, and history
artifacts. It does not recreate or amend them.

The package makes one central distinction explicit: implemented local
structural controls are not evidence of a joined experiment, hosted production
state, WORM retention, causal or scientific validity, product readiness,
licensing, canon admission, safety, or disclosure authority. Those conclusions
remain open unless and until their own exact evidence and qualified authority
exist.

The package contains no experimental data, no positive or negative target-model
finding, no safety conclusion, and no claim that CAS constructs have been
scientifically validated. Its publication value is architectural: it defines
what a future joined run must bind and what may and may not be inferred from
each evidence class.

## 2. Package contents

The lane contains eight files:

1. `CAS_HARNESS_2_EVIDENCE_GROUNDED_VALIDATION_DELTA_v0.1.md` — the substantial
   paper/specification delta, formal separation model, joined-run contract,
   threat model, claim-language rules, and publication sequence.
2. `WAVE2_HARNESS_CLAIM_THEOREM_CONTROL_MATRIX_v0.1.json` — exact mapping among
   candidate statements, inherited theorem boundaries, implemented controls,
   absent controls, evidence classes, allowed wording, and forbidden wording.
3. `WAVE2_HARNESS_EVIDENCE_MAP_v0.1.json` — evidence classes, exact bound source
   anchors, current local verifier receipt, evidence clusters, negative
   evidence, and minimum joined-run evidence.
4. `WAVE2_HARNESS_CITATION_LEDGER_v0.1.json` — primary external references and
   internal canonical or implementation sources, each with a narrow use and a
   non-inference boundary.
5. `WAVE2_HARNESS_UNRESOLVED_OBLIGATIONS_v0.1.json` — open editorial,
   engineering, scientific, security, WORM, product, licensing, safety, and
   disclosure obligations with closure evidence and prohibited shortcuts.
6. `WAVE2_HARNESS_SOURCE_INVENTORY_v0.1.json` — exact source paths, byte counts,
   SHA-256 values, Gate 5 role aggregates, product-boundary sources, and the
   read-only production-tracker snapshot.
7. `WAVE2_HARNESS_LEAD_HANDOFF_v0.1.md` — this integration and review handoff.
8. `WAVE2_HARNESS_ARTIFACT_MANIFEST_v0.1.json` — non-self-hashing manifest for
   the other seven files and package invariants.

The manifest deliberately excludes its own bytes. Any later edit to one of the
seven hashed artifacts invalidates the manifest and requires regeneration and
review. A merge, rebase, formatter, or line-ending conversion is an edit for
this purpose.

## 3. Source lock and inheritance

The package is based on commit
`c8635270ca6ba7c65504b4fda43cb42a89623015`. It inherits, but does not modify:

- the Project Coherence charter and shared claim, theorem, term, open/held, and
  disclosure registries;
- the Gate 4 manifest and its integration boundary;
- the Gate 5 specification, README, review matrix, adversarial review, artifact
  manifest, dependency receipts, history inventory, and recovered-history tree;
- the CAS Harness v2 kernel, its tests, the worker implementation and fixtures,
  and the Gate 5 verifier; and
- selected product, audit, provenance, retention, WORM, and acceptance modules
  used only to state cross-system boundaries.

The exact paths, byte counts, and hashes are in the source inventory. The
inventory also reproduces a deterministic aggregate for all 325 Gate 5
manifest records and per-role aggregates. These are source-identity evidence,
not new execution evidence.

The canonical production TODO was inspected under the production-readiness
skill as a read-only external tracker. This lane intentionally does not edit
that file because the assignment prohibits shared-tracker edits and the draft
does not change production status. Its external snapshot is time-indexed and
must be rechecked before any integration claim.

## 4. What current evidence supports

At the bound base, the existing Gate 5 verifier passed its local structural
suite and reported the following bounded receipt:

- 325 Gate 5 manifest artifacts;
- 296 syntax-checked Python files and 1,898 executable-shadow paths;
- 54 integrated Gate 4 artifacts;
- 11 claim records, all remaining Ring 4 and `NOT LICENSED`;
- 537 recovered-history files;
- 113 kernel tests plus 61 subtests;
- 364 worker tests, 32 numeric tests, and 76 API/fleet/launcher tests;
- 47 review criteria, including 22 required open boundaries; and
- a postflight rehash of the bound source set.

The exact local receipt is repository-local structural evidence. It supports
statements such as “the exact bounded verifier completed successfully” and
“the named local control exists and passed its declared regression.” It does
not support statements that a target scientific hypothesis passed, that a live
deployment matches the base, that executed model bytes were independently
authenticated, that an Evidence Packet was durably anchored under WORM policy,
or that a product, license, safety, canon, or disclosure gate is satisfied.

## 5. Implemented structural controls retained by the delta

The delta records the following controls as implemented only within their
repository-local scope:

- strict JSON parsing and schema validation;
- exact claim binding and rejection of absent or ambiguous claim identity;
- fixed sample, measurement, threshold, control, falsifier, and model bindings;
- append-only process-local amendment handling;
- process-local outcome-access chronology;
- exact artifact-byte resolution and digest checks;
- deterministic Evidence Packet v2 carrier construction;
- split arithmetic, vector assessment, and conservative aggregation rules;
- governance, role, and contradiction checks;
- rejection of Evidence Packet v1 downgrade paths;
- exact Pythia worker binding in the tested worker path;
- retained negative fixtures and recovered historical evidence; and
- deterministic Gate 5 manifest and verifier checks.

These are control propositions, not newly admitted mathematical theorems. The
matrix inherits the standard projector/Gram-kernel result only as an upstream
citation boundary and keeps the projector-capacity CAS transfer theorem open.
No theorem is added, upgraded, or admitted by this lane.

## 6. Boundaries that remain open

The following are deliberately not claimed:

- same-run authenticated executed-node identity;
- hermetic environment and dependency closure;
- complete vulnerability and supply-chain closure;
- trusted time, monotone ordering, replay prevention, and nonce one-use across
  the full protocol;
- exact-version WORM retention and independently verified anchor receipts;
- a transactionally joined preregistration, execution, outcome-access, packet,
  audit, and review run;
- valid target-model intervention evidence;
- independent numerical replay and held-out replication;
- construct validity, causal identification, generalization, clinical effect,
  or safety effect;
- live provider, deployment, account, billing, CRM, support, privacy,
  compliance, or incident readiness;
- product `ACCEPT` or launch readiness;
- claim licensing, canon admission, or public disclosure; and
- external specialist, legal, ethics, security, or editorial approval.

The retained worker negative evidence is especially important. An unattributed
or structurally invalid intervention receipt remains a negative boundary. It
must not be reframed as a successful causal intervention or silently replaced
with a fallback result.

## 7. Joined-run rule for future work

A future experimental receipt is eligible for review only if one authorized
transaction binds all of the following to exact identities:

1. the registered claim and allowed claim language;
2. the preregistration and every valid pre-access amendment;
3. sample, model, tokenizer, revision, code, dependency, container, hardware,
   and environment identities;
4. controls, falsifiers, measurements, thresholds, seeds, and split arithmetic;
5. trusted order for registration, amendments, execution, outcome access,
   packet construction, anchoring, and review;
6. raw inputs, activations or derived artifacts, logs, result tables, negative
   results, and exact artifact bytes;
7. Evidence Packet v2 bytes and durable exact-version retention evidence;
8. independent numerical replay and held-out replication; and
9. scoped human reviews for science, causal language, security, product,
   licensing, safety, and disclosure where applicable.

Missing identity, ordering, bytes, negative evidence, or required review makes
the corresponding conclusion ineligible. It cannot be repaired by a dashboard
label, a process-local clock, a later narrative, a generic storage receipt, or
a reviewer role that lacks the relevant authority.

## 8. Required cross-reviews

The lead editor should route the exact manifested package as follows:

- **Formal mathematics:** verify that control propositions CP-1 through CP-8
  are bounded executable statements and that theorem-language boundaries agree
  with the shared theorem ledger.
- **Category theory and semantics:** verify the separation among source,
  execution, evidence admission, scientific assessment, and authority; check
  that no semantic interpretation is inferred from a structural carrier.
- **Engineering and security:** review identity binding, hermeticity, trusted
  time, replay resistance, WORM semantics, supply-chain evidence, parser and
  schema attacks, and provider-specific assumptions.
- **Statistics and causal inference:** review controls, falsifiers, matched
  comparisons, split arithmetic, multiplicity, negative controls, causal
  language, replication, and stopping rules before any experiment is run.
- **Research governance and ethics:** review authorization, raw-data handling,
  model terms, privacy, safety, participant or institutional requirements, and
  claim-language scope.
- **Product, legal, and disclosure:** separately assess operational readiness,
  customer promises, licensing, branding, canon transition, and publication.

No reviewer should be asked to approve outside their scope, and no collection
of narrow approvals should be collapsed into a global `ACCEPT` verdict.

## 9. Integration order

The recommended dependency order is:

1. verify the manifest and every source hash on the integration commit;
2. reconcile notation and claim identifiers with all Wave 1 and Wave 2 lanes;
3. complete formal, semantic, engineering/security, and citation reviews;
4. resolve editorial conflicts and regenerate the package manifest;
5. obtain separate authorization for any experiment and freeze an exact run
   candidate;
6. execute one hermetic joined run only after all P0 pre-run obligations close;
7. retain positive and negative evidence and complete independent replay,
   replication, falsifier, and claim-language review; and
8. seek product, licensing, canon, safety, and disclosure decisions only through
   their separate authorities.

GPU capacity is not a blocker for this draft package. No RunPod resource was
used or needed. A later experimental run must be costed only after its exact
model, sample, instrumentation, retention, and replication plan is frozen; the
existence of account credit is not evidence that the run is authorized or that
its non-compute obligations are satisfied.

## 10. Lead-editor acceptance checklist

Before accepting this package into an integration branch, the lead editor must
confirm all of the following against exact bytes:

- all eight package files are present;
- the seven non-manifest files match the non-self-hashing manifest;
- every JSON file parses with duplicate keys rejected;
- all declared counts equal the actual array or object counts;
- all internal paths exist at the integration commit;
- all recorded internal and external-file hashes and byte counts still match;
- all matrix references resolve to a source, inherited control criterion,
  theorem, claim, or matrix entry;
- every external citation used in the paper appears in the citation ledger;
- every allowed claim remains narrower than its evidence class;
- every open obligation remains open unless exact closure evidence is added;
- the authoritative Gate 5 verifier still passes at the integration commit;
- the shared registries and production TODO have not been silently changed by
  this lane; and
- the package still reads `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD` with
  `NONE` as its experimental-result status.

If any item fails, the package remains held. A successful editorial integration
does not license the scientific claims, start an experiment, approve a product,
or authorize disclosure.

## 11. Final handoff state

The publication/specification delta is substantial and ready for bounded
internal adversarial review. It is not ready for external release, experimental
execution, scientific acceptance, product launch, licensing, canon admission,
or public disclosure.

**Final handoff status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`
