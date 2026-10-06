# CAS Harness 2: Evidence-Grounded Validation of Structured Latent Representations

## Publication and specification delta v0.1

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Charter position:** working Paper 7

**Base commit:** `c8635270ca6ba7c65504b4fda43cb42a89623015`

**Gate 5 status:** `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`

**Experimental result status:** `NONE`

**Internal cross-review:** `OPEN`

**External specialist review:** `OPEN`

**Public disclosure:** `NOT AUTHORIZED`

This document is a source-bound delta over the existing Gate 5 specification,
review matrix, manifest, adversarial review, control kernel, and historical
recovery. It does not replace or amend any of those artifacts. It does not
authorize an experiment, certify hosted infrastructure, create an Evidence
Packet, establish a scientific result, license a claim, approve a product
route, make a safety finding, or authorize disclosure.

## Abstract

CAS Harness 2 is best understood as a separation architecture for research
claims. Its current implemented kernel can freeze a per-claim design, retain an
exact amendment chain, record process-local outcome access, resolve exact
artifact bytes, construct an Evidence Packet v2 carrier, and compute a vector
of conservative assessment axes. The kernel deliberately does not collapse
structural completeness, authenticated execution, reported numerical criteria,
scientific eligibility, independent audit, replication, claim-language review,
product status, licensing, and disclosure into one verdict.

This delta states the publication-level architecture and the missing joined-run
contract. It distinguishes five evidentiary layers that are frequently confused:
source presence, repository-local implementation evidence, externally hosted
machine observations, admitted experimental evidence, and human or institutional
authority. The current repository supports only bounded claims about the first
two layers. A mutable production dashboard reports additional hosted product
observations under different commits and authorities, but those observations
are not joined to the Gate 5 preregistration/outcome-access/Evidence Packet v2
protocol and are not evidence for the paper's scientific hypotheses.

The resulting program is viable without a new experiment today: its schemas,
control propositions, attack inventory, source identities, and open obligations
can be published internally as a rigorous draft. Empirical conclusions must
wait for one separately authorized, exact-revision, hermetic joined run followed
by independent numerical replay, held-out replication, falsifier review, and
external claim-language review.

## 1. Delta scope

The normative Gate 5 control kernel is already specified in
`HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md`. This paper
adds only the following publication-layer material:

1. a compact formal model of the control and authority separations;
2. a joined-run contract connecting a worker execution to the frozen kernel;
3. an evidence-state lattice that prevents hosted or local observations from
   being promoted into scientific or product conclusions;
4. an explicit relation between structured latent-representation hypotheses,
   controls, and permitted claim language;
5. a threat model for ordering, selective reporting, semantic relabeling,
   execution identity, and downstream authority confusion; and
6. a publication plan that retains negative results and preserves every
   `OPEN`, `NOT LICENSED`, and `HELD` boundary.

The delta is not a new schema version. Any future executable change belongs in
a successor Gate 5 specification and must pass its own review and manifest
process before this paper can describe it as implemented.

## 2. What CAS Harness 2 is and is not

CAS Harness 2 is a private research-control architecture for testing narrow,
predeclared hypotheses about structured latent representations. A hypothesis
may concern a projector profile, a layer-specific representation, an
intervention response, a matched control, a null behavior, or another registered
construct. The architecture is agnostic about whether the hypothesis is true.

CAS Harness 2 is not:

- an automatic claim-acceptance engine;
- a proof that latent coordinates represent cognition, safety, intent, or
  another noetic construct;
- a causal-attestation system;
- a product-readiness authority;
- a licensing authority;
- a safety, clinical, or regulatory certification system;
- a substitute for independent scientific review; or
- a disclosure or publication authorization channel.

The term *evidence-grounded* therefore means that every allowed statement must
name the exact evidence class supporting it and must preserve the associated
limits. It does not mean that current evidence establishes the target science.

## 3. Source and authority layers

The architecture uses the following noninterchangeable layers.

| Layer | Meaning | Current state | What it cannot establish |
|---|---|---|---|
| L0: source presence | A file, schema, test, or implementation exists at an exact byte identity. | `PRESENT` for the bound Gate 5 surface. | Correctness, execution, deployment, truth, or authority. |
| L1: local structural control | Bound code passes its stated repository-local regressions and verifier. | `PRESENT / LOCAL_UNATTESTED` for the recorded suites. | Authenticated execution, WORM, causality, scientific validity, or product readiness. |
| L2: hosted machine observation | A provider or deployed service reports a state under an exact external identity. | `EXTERNAL / TIME-INDEXED / NOT JOINED` in this delta. | Gate 5 experimental admission, independent trust, scientific truth, or human approval. |
| L3: joined protocol run | One authorized execution binds the frozen preregistration, worker, identities, outcome-access event, raw outcomes, and packet. | `NOT_STARTED`. | Replication, generalization, product readiness, licensing, or disclosure by itself. |
| L4: scientific validation | Independent numerical replay, controls, falsifiers, held-out replication, and specialist review agree within frozen rules. | `OPEN`. | Product, legal, licensing, safety, or disclosure authority. |
| L5: product and disclosure authority | Current product gates and qualified human decisions approve exact claims and exact release artifacts. | `OPEN / NOT LICENSED / HELD`. | Retroactive scientific truth or theorem admission. |

No upward edge in this table is automatic. In particular, L1 does not imply L2,
L2 does not imply L3, a favorable L3 result does not imply L4, and L4 does not
imply L5.

## 4. Formal control objects

The notation below is descriptive of the current software contract. It does not
assert a new mathematical theorem.

### 4.1 Exact-byte identity

For an admitted artifact with exact byte string \(b\), define

\[
I_{\mathrm{raw}}(b) = (\operatorname{SHA256}(b), |b|).
\]

An exact-byte identity detects a byte change when the digest or byte length no
longer agrees. It does not authenticate the producer, establish a trusted time,
or prove the artifact's semantics. SHA-256 is used here as an integrity digest;
digital signatures and trusted timestamps are different controls with different
security properties [E3] [E4] [E5].

For selected structured records, the kernel also computes a deterministic
canonical serialization before hashing. That serialization is an internal
profile, not a claim of RFC 8785 conformance. RFC 8785 is cited only as a
comparison showing why invariant representations matter for repeatable
cryptographic operations [E2].

### 4.2 Claim binding

Let a claim binding be

\[
C = (I_L, c_{id}, c_{text}, h_c),
\]

where \(I_L\) is the exact raw-byte identity of the current claim ledger,
\(c_{id}\) is one claim identifier, \(c_{text}\) is its exact text, and \(h_c\)
is the canonical hash of that claim record. A preregistration is invalid if any
of these components drift.

This construction binds a design to the wording under test. It does not make the
wording true or licensed.

### 4.3 Frozen design

Represent the protected preregistration design as

\[
P = (C,H,U,S,N,T,K,F,Q,J,W,G),
\]

where:

- \(H\) contains primary and null hypotheses, estimand, and direction;
- \(U\) contains measurement identifiers, kinds, operational definitions, and
  units;
- \(S\) contains confirmatory and held-out split identities and allocation
  rules;
- \(N\) contains target groups, enrolled/analyzed targets, and attrition bounds;
- \(T\) contains thresholds and decision effects;
- \(K\) contains matched-taxonomy, wrong-layer, clean-null, and any other
  preregistered controls;
- \(F\) contains falsifiers and consequences;
- \(Q\) contains uncertainty, multiplicity, permutation, seed, and grouping
  rules;
- \(J\) contains exact model, weights, tokenizer, code, analysis, dependency,
  runtime, container, and hardware identities;
- \(W\) contains permitted and forbidden claim wording; and
- \(G\) is the fixed governance block.

The current governance block is invariant:

```text
admission_ring       = 4
product_claim_status = NOT LICENSED
disclosure_status    = HELD
public_release       = false
product_route        = false
license_decision     = NONE
```

Preregistration separates confirmatory plans from later observations. The
registered-report and preregistration literature motivates that separation,
but does not validate this implementation or any CAS hypothesis [E14] [E15]
[E16].

### 4.4 Amendment chain

Let \(A_0=P\), and for each permitted pre-outcome amendment let

\[
A_k = (k,t_k,I_P,I_{A_{k-1}},\tau_k,\Delta_k).
\]

The implementation requires strictly advancing identifiers and timestamps,
exact predecessor binding, fresh replay, no cycle or skipped link, one optional
execution window, and at most 128 amendment links. The only amendment classes
are administrative clarification, execution-identity addition, and execution
window. No amendment field can replace hypotheses, units, splits, thresholds,
controls, falsifiers, uncertainty, wording, or governance.

This is a process-local sequence guard. It is not durable append-only storage
and does not prove that an earlier process did not inspect outcomes.

### 4.5 Outcome-access event

The process-local event

\[
O = (I_P,I_{A_n},t_{complete},t_{access},I_{receipt},h_{chain})
\]

seals the current chain, binds declared execution completion, and prevents later
amendment within the same validated chain instance. A durable scientific
protocol still requires externally trusted ordering, a nonce authority,
one-use consumption, replay rejection, and a complete run registry.

RFC 3161 provides a standardized trusted-time protocol and RFC 9162 provides a
Merkle-log design for append-only transparency in its certificate domain. They
are design references, not claims that CAS Harness currently implements either
standard [E5] [E6].

### 4.6 Artifact registry

Let \(\mathcal{R}\) map an artifact identifier to retained exact bytes and
their identity:

\[
\mathcal{R}(a)=(b_a,I_{raw}(b_a)).
\]

The current registry rejects missing identities, reused identities under
different artifact identifiers, and retained-byte mutation on replay. This
resolves exact byte identity only. It cannot decide that two byte-different
files have the same semantic content, that a media type is honest, or that one
artifact has been relabeled across separate packets. PROV-O is a useful external
vocabulary for entities, activities, agents, and derivations, but no PROV-O
conformance claim is made here [E7].

### 4.7 Evidence Packet v2

An Evidence Packet is represented abstractly as

\[
E=(C,P,A_{0:n},O,X,Y,M,K,F,S,Q,R_v),
\]

where \(X\) is the execution identity and manifest, \(Y\) is raw outcome
evidence, \(M\) is the reported metric set, and \(R_v\) contains available
audit, replication, and claim-review records. Every referenced artifact must
resolve to retained bytes.

For every split, the current loader requires exact disjoint accounting:

\[
n_{enrolled}=n_{analyzed}+n_{missing}+n_{excluded}.
\]

An arithmetically coherent underpowered or deviating run remains loadable as
negative evidence. It is marked ineligible rather than deleted.

### 4.8 Assessment vector

The current verifier computes a vector rather than one verdict:

\[
\alpha(E)=(s,a,c,e,n,r,q,g),
\]

with axes for structural completeness \(s\), execution authentication \(a\),
reported criteria \(c\), scientific eligibility \(e\), numerical audit \(n\),
replication \(r\), claim-language review \(q\), and governance \(g\).

The key non-escalation rule is:

\[
s=\texttt{COMPLETE}\;\not\Rightarrow\;a=\texttt{AUTHENTICATED},
\]

and

\[
c=\texttt{REPORTED\_CRITERIA\_MET}\;\not\Rightarrow\;
e=\texttt{ESTABLISHED}.
\]

The isolated kernel has no `AUTHENTICATED` execution path and caps an otherwise
eligible-looking packet at `NOT_ESTABLISHED`. Governance remains Ring 4,
`NOT LICENSED`, and `HELD` regardless of the reported metric direction.

## 5. Executable control propositions

The propositions below are bounded statements about the exact implementation.
They are not admitted TKS or Noetic Topos theorems.

### CP-1: strict-input proposition

RFC 8259 supplies the general JSON interoperability reference [E1]; the bound
kernel intentionally applies a narrower local profile and does not claim that
the RFC by itself supplies duplicate-key, semantic-schema, or resource-limit
controls.

For inputs accepted by the bound loaders, the parser has rejected the tested
duplicate-key, BOM, invalid UTF-8, JSON-float, nonfinite, oversized integer,
unsafe-surrogate, NUL, excessive tree, unknown-field, missing-field,
Boolean-as-integer, non-string-key, coercion-collision, and non-normalized-ID
cases.

Evidence class: repository-local implementation and regression tests.

Limit: the receipt does not prove absence of every parser defect or execution in
an independently attested interpreter.

### CP-2: claim/design binding proposition

For accepted preregistrations, the bound loader checks the exact claim-ledger
bytes, selected claim ID and text, canonical claim-record hash, protected design,
and fixed governance values.

Evidence class: repository-local implementation and regression tests.

Limit: the binding establishes identity and internal consistency, not truth,
scientific adequacy, ownership, or license.

### CP-3: bounded amendment proposition

For an accepted process-local chain, the current replay logic rejects the tested
cycles, skipped links, nonmonotone identifiers, protected-field replacements,
post-outcome amendments, duplicate execution windows, and a 129th link.

Evidence class: repository-local implementation and adversarial regressions.

Limit: rebuilding a fresh process can omit prior outcome access. Durable ordering
is `OPEN`.

### CP-4: negative-evidence retention proposition

For an arithmetically coherent packet, sample-size, group-floor, missing-row, or
excluded-row deviations remain representable and force the corresponding
criteria or eligibility axis to fail rather than making the packet disappear.

Evidence class: repository-local implementation and regression tests.

Limit: the software cannot prove that all runs were submitted or that raw rows
are authentic.

### CP-5: assessment non-escalation proposition

Within the current kernel's return contract, a structural or reported-criteria
state does not set authenticated execution, established science, a product
route, licensing, or disclosure approval.

Evidence class: repository-local implementation and regression tests.

Limit: downstream systems still require independent proof that they never treat
an assessment object as a capability token.

### CP-6: historical non-upgrade proposition

The current loader rejects all four repository-known Evidence Packet v1 labels
as ambiguous upgrades. A historical v1 packet can be cited as an exact source,
but missing prospective facts cannot be backfilled into v2.

Evidence class: repository-local implementation and adversarial tests.

Limit: this is a compatibility policy, not a scientific judgment about the
historical result.

### CP-7: intervention non-attribution proposition

The bound live-worker schema has no valid causal-success emission path. Even
when a tested intervention changes an activation and output, the receipt remains
`APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED`, is structurally invalid,
falls back to the paired unmodified baseline, and aborts the stream.

Evidence class: repository-local worker implementation, numeric red team, and
regressions.

Limit: no exact admitted GPU/autocast/compiled-hook run exists. The observation
does not establish coordinate semantics, selectivity, causality, utility, or
safety. Negative controls are relevant to detecting spurious causal
interpretation, but no general negative-control citation closes a CAS-specific
design [E17] [E20].

### CP-8: manifest-closure proposition

For the exact base commit, the integrated verifier binds 325 Gate 5 artifacts,
rehashes the 537-file historical recovery and transitive Gate 4 dependency,
checks repository-local executable shadows, reruns the declared suites, and
rehashes after subprocess execution.

Evidence class: current local verifier run on 2026-08-06 UTC.

Limit: the mutable host interpreter, installed packages, startup state,
hardlinks, reparse points, read-only snapshot, before/after ABA resistance,
same-run executed-node identity, and raw external build evidence remain open.

## 6. Current bounded implementation evidence

The current unchanged-base verifier completed in 204.9 seconds and reported:

- 325 hash-bound Gate 5 artifacts;
- 296 syntax-checked Python artifacts;
- 1,898 repository paths scanned for executable shadows before tests;
- integrated Gate 4 verification over 54 artifacts while Gate 4 remained open;
- 11 claim records, all Ring 4 and `NOT LICENSED`;
- 537 historical recovery files totaling 95,945,579 bytes;
- 113 Harness v2 tests plus 61 subtests;
- 364 complete-worker tests;
- 32 focused numerical red-team tests;
- 76 API, fleet-state, and launcher-identity tests;
- 47 Gate 5 review criteria and 22 required open boundaries; and
- postflight rehash of Gate 5, the historical recovery, and transitive Gate 4
  bytes.

This receipt is `LOCAL_UNATTESTED_HOST_REGRESSION`. It records that the exact
bounded repository checks reported `PASS` in this worktree. It is not a scientific experiment,
an authenticated execution, a causal result, a WORM receipt, independent
reproduction, product readiness, licensing, or disclosure approval.

## 7. Preserved adverse evidence

The architecture treats adverse chronology as evidence, not debris.

The retained historical recovery includes:

- a v3 LF/CRLF byte-identity inconsistency;
- a v3 wrong-layer ceiling failure;
- a v4 startup guard-name defect;
- a historical model-free receipt of 43 passed and 4 failed tests; and
- a restored v1 worker receipt of 31 failures caused by absent frozen fixture
  dependencies.

The current worker chronology also retains counterexamples involving:

- wrong intervention coordinate space;
- RNG-only output drift;
- nonfinite activations and outputs;
- dtype, shape, rank, device, and hook-cardinality mismatch;
- duplicate and partially invalid coordinates;
- malformed, Boolean, nonfinite, subnormal, and oversized gains;
- aliasing of caller and fallback outputs;
- hidden mutable model state after apparently stable controls; and
- post-validation mutation of a previously validated public receipt.

Repairs become bounded controls only when their reproducer remains in the test
surface. A repaired defect does not become evidence that the target scientific
hypothesis is true.

## 8. Joined-run contract

The central missing integration is a single transaction that joins the frozen
research-control kernel to one exact worker execution. The following is the
minimum proposed contract; it is not yet implemented as a Gate 5 admitted
protocol.

### 8.1 Pre-run admission record

Before any model load or outcome access, a run authority must atomically bind:

1. the exact preregistration bytes and final amendment-chain digest;
2. one unpredictable nonce and one-use run identifier;
3. the authorized execution window;
4. exact source commit and clean read-only snapshot identity;
5. exact container index, platform manifest, image config, dependency lock,
   model, weights, tokenizer, data, analysis, and hardware identities;
6. authenticated executor and independently controlled auditor identities;
7. all control and held-out split identities; and
8. the expected packet namespace and retention policy.

The authority must not be selected by the worker process itself.

### 8.2 Execution receipt

The execution receipt must be generated by the admitted runner and must bind:

- the consumed nonce and run identifier;
- the exact started and completed times from the chosen trust boundary;
- the actual executed source snapshot and container identity;
- the actual executed test or protocol node set in the same run;
- model and artifact hashes before and after load;
- runtime, hardware, precision, compilation, device, and RNG policy;
- every worker event and structural intervention receipt;
- raw result artifact identities;
- all abort, refusal, exclusion, missingness, and fault events; and
- the final execution disposition without scientific or product promotion.

Collect-only node IDs from one subprocess and pass summaries from another are
insufficient for this purpose.

### 8.3 Outcome-access transition

The first authorized unblinding operation must:

1. prove successful one-use nonce consumption;
2. bind the exact execution-completion receipt;
3. append the outcome-access event to durable protected storage;
4. reject replays and later design amendments;
5. expose all run identities to the anti-selective-reporting registry; and
6. retain a failure record if any step is unavailable or ambiguous.

### 8.4 Packet assembly

Packet assembly must operate on the frozen design and retained execution
artifacts. It must not accept caller-selected authoritative status. The packet
must include all registered splits, controls, falsifiers, deviations, audit
records, and negative outcomes. A packet hash is an integrity identity only.

### 8.5 Durable anchoring

When WORM retention is required, the joined protocol must retain and reverify
the exact object version, content digest, lock mode, original retention request,
observed retention floor, and future retain-until state. Amazon S3 Object Lock
documents different properties for governance and compliance modes; governance
mode may be bypassed by principals with the relevant permission [E13]. A
provider response therefore must not be generalized into an unqualified
immutability claim.

The repository contains source for S3 Object Lock write/readback and receipt
checks, and the mutable production tracker reports separate hosted product
observations. This paper does not join those observations to the Gate 5 run and
does not independently reverify the provider state. `G5-TRUST-002` remains
`OPEN_ENGINEERING`.

## 9. Structured latent-representation study profile

The first admitted study should test one narrow claim rather than the whole CAS
ontology.

### 9.1 Candidate question

A defensible candidate question has the form:

> For the exact registered model, revision, layer, token position, projector or
> coordinate definition, prompt taxonomy, intervention profile, and response
> measure, does the held-out response exceed its preregistered matched controls
> while satisfying every null, falsifier, uncertainty, and attrition rule?

This wording does not assume that the target is cognitive, causal, safe, useful,
or general across models.

### 9.2 Required splits

At minimum, the design must include:

- a construction or calibration partition used only before freeze;
- a confirmatory partition with group-aware allocation;
- a held-out replication partition unavailable to the primary executor until
  its authorized stage;
- explicit target groups and row counts; and
- disjoint missing and excluded row categories.

### 9.3 Required controls

The existing kernel requires three control families:

- matched-taxonomy controls, testing whether the result exceeds comparable
  nontarget structures;
- wrong-layer controls, testing whether a claimed layer-specific effect is
  actually nonspecific; and
- clean-null controls, testing whether the instrument produces apparent effects
  where none should be present.

Depending on the claim, the preregistration should also consider random
same-norm directions, label shuffles, wrong-token controls, prompt-group
holdouts, intervention-placebo controls, and repeated baseline stability.
Additional controls are not implied by the schema and must be registered
prospectively.

### 9.4 Falsifiers

Falsifiers must name consequences. Examples include:

- matched controls exceed the target effect;
- wrong-layer effects violate the frozen ceiling;
- clean-null behavior violates the frozen floor or ceiling;
- baseline outputs are not stable under the declared policy;
- coordinate or hook geometry differs from the registered profile;
- nonfinite or incomparable numerical states occur;
- the held-out replication disagrees beyond the registered tolerance; or
- an independent implementation cannot reproduce the reported number.

A falsifier result is evidence against the scoped hypothesis. It must not be
rewritten as a successful discovery.

### 9.5 Uncertainty and multiplicity

The design must state the estimand, grouping unit, confidence level,
multiplicity rule, resampling or permutation method, seeds, and any stopping
rule before outcomes are accessed. Exact power-analysis bytes can be bound by
the kernel, but statistical correctness remains subject to independent review.

### 9.6 Causal boundary

An intervention followed by an output change is not, by itself, evidence that
the intervention caused the change. RNG, hidden mutable state, hooks,
compilation, numerical precision, device differences, and nonspecific effects
are alternative explanations. The current worker intentionally emits an
unattributed state even after observing activation and output deltas.

Any future causal claim requires an explicit causal model, identification
assumptions, negative controls, intervention integrity, alternative-explanation
analysis, and independent review [E17] [E20]. CAS terminology must not replace
those requirements.

## 10. Supply-chain and execution environment

The Gate 5 successor candidate records exact source, lock, image, model, and
runtime identities. It reports a 73-distribution hash-bound lock, exact Pythia
five-file set, and a CPU-only offline canary. It also records locally observed
BuildKit SPDX and SLSA identifiers. SLSA defines provenance as verifiable
information about where, when, and how an artifact was produced, while in-toto
separates subject, predicate, envelope, and bundle layers [E8] [E9]. OCI defines
content-addressed image structures, and SPDX defines an interchange standard
for bill-of-materials information [E10] [E11].

Those standards clarify the target architecture. They do not turn the current
receipt into independently trusted provenance. The raw build history, SPDX,
SLSA, and scanner payloads were not retained in the repository. The package
scan completed with 3 medium and 4 low unfixed findings; the direct filesystem
scan remains incomplete. `G5-ENGINEERING-003` remains `OPEN_SECURITY`.

A future admitted runner must therefore:

1. retain the raw build, SBOM, provenance, and scanner payloads;
2. bind the source-to-image derivation under a non-tenant-selected trust root;
3. resolve or explicitly disposition every finding;
4. complete direct-filesystem coverage;
5. use a locked read-only snapshot with hardlink, reparse-point, cache,
   bytecode, native-extension, and ABA controls;
6. receipt the actual executed protocol nodes in the same run; and
7. obtain independent clean reproduction before live experimental authority.

## 11. Evidence Packet as provenance bundle, not verdict

Evidence Packet v2 should be interpreted as a bounded provenance-and-assessment
bundle. W3C PROV's distinction among entities, activities, and agents is useful
for future interoperable exports [E7]. FAIR principles motivate persistent
identification, metadata, interoperability, and reuse, while explicitly leaving
implementation choices open [E18].

The internal packet should remain stricter than any external export. A future
PROV or FAIR mapping must preserve:

- exact claim and design versions;
- raw-byte artifact identities;
- derivation and activity links;
- executor, auditor, reviewer, and replication roles;
- every negative or unavailable state;
- rights and disclosure restrictions;
- the difference between reported values and independently verified values;
- the difference between process-local order and trusted order; and
- the fact that `PacketAssessment` is data, not authority.

No external serialization may drop `NOT LICENSED`, `HELD`, a failed control, a
missing trust root, or an unavailable review merely to fit a simpler schema.

## 12. Product, hosted, WORM, and scientific separation

The repository contains substantial product-oriented CAS Harness source,
including audit sessions, worker access, evidence anchoring, object storage,
fleet execution, human attestations, and publication-authorization controls.
Source presence and local tests are legitimate L0/L1 evidence.

The canonical production tracker is a separate, mutable dashboard. Its current
snapshot reports time-indexed hosted machine and product-gate observations under
different deployment identities. This publication delta treats that tracker as
read-only context and does not reproduce its claims as current provider facts.
Even a verified hosted Object Lock receipt for a product Evidence Packet would
not prove that a Gate 5 scientific run used the frozen v2 design, and a
scientific packet would not prove current product readiness.

The product claim `CLM-HARNESS16-CURRENT-READINESS` remains Ring 4,
`NOT LICENSED`, and `HELD`. Historical Harness specifications or successful
research tests cannot satisfy current security, operations, account, billing,
quota, privacy, compliance, support, monitoring, incident, safety, licensing,
or disclosure gates.

## 13. Claim-language policy

### 13.1 Currently supportable wording

The paper may state:

- the exact bound repository implements the described control-kernel schemas;
- the current local verifier passed the stated bounded checks and test counts;
- the current kernel separates structural, authentication, numerical,
  scientific, review, and governance axes;
- coherent negative and underpowered packets remain representable;
- the current worker refuses to attribute an observed activation/output delta
  to the intervention;
- exact historical failures and attack reproductions are preserved; and
- the joined-run, trusted-ordering, scientific, product, licensing, and
  disclosure obligations remain open.

### 13.2 Prohibited wording

The paper must not state or imply:

- CAS Harness 2 has validated a structured latent representation;
- a projector, coordinate set, layer, token, or intervention represents a
  cognitive or noetic construct;
- the current worker proves a causal effect;
- the current test suites are authenticated or independently reproduced;
- an admitted GPU experiment has run;
- an Evidence Packet v2 scientific result exists;
- repository hashes are signatures, trusted timestamps, or WORM receipts;
- local S3-capable source proves a hosted bucket is correctly configured;
- product, clinical, safety, regulatory, or customer efficacy is established;
- any claim is `LICENSED`;
- any draft is accepted into canon; or
- public disclosure, authorship, submission, or peer review is authorized.

## 14. Review and replication plan

The lead editor should route stable hashes and the exact claim/control matrix to
separate reviewers.

### 14.1 Software and security review

Review strict parsing, raw-byte retention, chain replay, packet verification,
manifest closure, runner hermeticity, nonce consumption, WORM receipt semantics,
signature and key custody, and downstream authorization boundaries. NIST storage
guidance is relevant to authentication, authorization, configuration control,
data protection, isolation, restoration assurance, and encryption, but does not
certify this implementation [E12].

### 14.2 Statistical review

Review the exact estimand, effect size, variance assumptions, grouping,
multiplicity, attrition, power analysis, stopping rule, controls, and held-out
replication plan before authorization.

### 14.3 Causal and construct review

Review the construct definition, measurement validity, intervention target,
alternative explanations, negative controls, falsifiers, and generalization
limits. Reject terminology-based shortcuts.

### 14.4 Independent numerical replay

The independent implementation must start from exact raw inputs and reproduce
split accounting, metrics, thresholds, uncertainty, controls, falsifiers, and
summary fields. Shared helper code, shared mutable state, or a second call to
the same implementation is not independence.

### 14.5 Held-out replication

An independently controlled team must execute the frozen held-out design and
retain agreement, mixed, disagreement, and failure states. The National
Academies distinguishes computational reproducibility from obtaining consistent
results in a new study; the Harness packet should preserve that distinction
[E19].

### 14.6 Claim-language and disclosure review

Qualified reviewers must approve exact wording against exact artifacts. Owner,
legal, patent, privacy, licensing, and publication authorities remain separate.
No reviewer's silence counts as approval.

## 15. Publication result state

This draft reports no empirical result. It reports a control architecture and a
current bounded implementation receipt.

The scientifically correct result table is therefore:

| Question | Current result |
|---|---|
| Has an admitted Harness 2 experiment run? | `NO / NOT_STARTED` |
| Does an Evidence Packet v2 scientific result exist? | `NO` |
| Has execution been authenticated by an independent trust root? | `NO / OPEN` |
| Have registered controls passed on admitted evidence? | `NO RESULT` |
| Has independent numerical replay completed? | `NO / OPEN` |
| Has held-out replication completed? | `NO / OPEN` |
| Has a causal interpretation been established? | `NO / OPEN` |
| Has external specialist peer review accepted the work? | `NO / OPEN` |
| Is the claim licensed? | `NO / NOT LICENSED` |
| Is product readiness established by this paper? | `NO` |
| Is disclosure authorized? | `NO / HELD` |

## 16. Limitations

The current package has the following controlling limitations:

- no trusted clock, durable amendment/outcome ordering, nonce authority,
  replay registry, or anti-selective-reporting registry;
- no joined worker-to-kernel protocol;
- no independently attested hermetic runner;
- no same-run executed-node receipt;
- no retained raw build/SBOM/SLSA/scanner evidence;
- unresolved dependency/container security findings and an incomplete direct
  filesystem scan;
- no exact admitted GPU, autocast, compiled-hook, or multi-device receipt;
- no authenticated executor/auditor/reviewer identity or proven independence;
- no independent semantic review of data, labels, power, controls, artifacts,
  or claim language;
- no authorized live experiment;
- no independent numerical replay or held-out replication;
- no accepted causal, safety, utility, clinical, regulatory, or
  generalization conclusion;
- no downstream proof that packet assessments cannot mint authority;
- no current product-readiness decision from this research lane;
- no claim license, canon admission, authorship decision, or disclosure
  authorization; and
- no independent external review of this publication delta.

## 17. Minimum next sequence

The dependency-respecting sequence is:

1. cross-review this delta against the existing Gate 5 specification and exact
   matrix without editing the existing artifacts;
2. retain and hash-bind the raw build, SPDX, SLSA, and scanner payloads;
3. resolve or explicitly disposition all seven current scan findings and
   complete direct-filesystem coverage;
4. independently reproduce the exact candidate in a locked read-only runner;
5. specify and red-team the worker-to-kernel joined-run protocol;
6. materialize trusted time, nonce consumption, durable WORM ordering, and a
   complete run/packet registry;
7. obtain independent statistical, causal, construct, data-rights, security,
   and claim-language review of one exact preregistration;
8. obtain explicit, bounded authority for one private exact-revision run;
9. execute without changing the design, retain all negative evidence, and emit
   one Evidence Packet v2;
10. complete independent numerical replay and held-out replication;
11. resolve external specialist review; and
12. evaluate product, licensing, canon, and disclosure gates separately.

## 18. Conclusion

CAS Harness 2 is viable as a rigorous research-control and publication program
because the existing work already supplies a substantial exact-byte kernel,
adversarial chronology, manifest closure, worker safeguards, and a conservative
assessment vector. The next scientific advance is not another disconnected
paper or another local test count. It is the joined-run transaction that binds
one frozen claim to one authenticated execution and one complete packet while
preserving every failure and every authority boundary.

Until that transaction and its independent reviews exist, the strongest honest
conclusion is narrow: the bound repository implements and locally regression-
tests a serious control architecture for future structured-latent-
representation studies. The target empirical, causal, hosted, WORM,
scientific, safety, product, licensing, canon, and disclosure conclusions remain
`DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`.
