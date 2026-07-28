# CAS Harness 0.33 to 1.00 Completion Roadmap

> ## HISTORICAL SNAPSHOT - NOT THE CURRENT CONTINUATION ROUTE
>
> This document was accurate at capture time. It is **not** the current execution frontier.
> Its canary status (`PRE_ANCHOR_FROZEN`, `WAITING_FOR_..._APPROVAL`, `NO_MODEL_OR_CUDA_EXECUTION`)
> is **superseded**: the technical canary **PASSED** on 2026-07-24, receiver-confirmed, at
> Attempt 11 (commit `f95cc610`), which earned **Gate 1** and moved the ladder to `0.38`
> (commit `194fec39`).
>
> **Read `docs/working/CAS_HARNESS_CURRENT_STATE.json` before acting on anything below.**
> Do not execute from this file.


Date: 2026-07-22

Status:
`ATTEMPT_5_PRE_ANCHOR_FROZEN / QUERY_UNSENT_BY_CONTROLLED_WORKFLOW / NO_TSA_RESPONSE_OR_RECEIPT_OBSERVED / WAITING_FOR_EXPLICIT_BYTE_SPECIFIC_TSA_APPROVAL / NO_OFFICIAL_MODEL_OR_CUDA_EXECUTION_ARTIFACTS / CURRENT_EVIDENCE_SCORE_0.33 / GATE_1_GPU_EXECUTION_OPEN / SHADOW / NONE / NOT_LICENSED`

This is an evidence-weighted planning rubric, not a percentage of code written
and not a promise that every research hypothesis will pass. A score increment
is earned only when its stated exit evidence independently verifies. Documents,
source code, narrow tests, plans, and receipt counts cannot substitute for live
evidence.

### 2026-07-23 verified Attempt 5 pre-anchor freeze checkpoint

Implementation preservation, remote prestage, fresh create-once identity,
independent PRE reverification, protocol, mapping, network plan, anchor
payload, and offline-verified RFC3161 query are complete for identity
`dd55bc73`. The independently rerun PRE verifier matched 16,351 runtime-file
records totaling 5,085,465,464 bytes and exited `0`. Setup identity
`eeec3ec7` is superseded and may never be resumed or reused.

The active candidate binds commit
`f72b89cd2ec574400ffe69ad7bd1540791fb73c3`, tree
`71c45fd5999b1d3f31636bbae8bd199d166ab2f5`, and parent
`be97bc7f76d1e9f5e501702660678d4af3081f5e`.

The exact 104-byte query has SHA-256
`e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846`.
The controlled Attempt 5 workflow has not transmitted it, and no TSA response
or receipt is present. No official model/CUDA artifacts or live model/CUDA
process were observed. Provider egress, TSA-side request, historical process,
and historical production-pod mutation logs are unavailable, so those
observations are not global historical proof.

The controlled workflow targeted only research pod `zp2s9pscgncn0b`;
production pod `hilj2rzs54gi06` was separately observed idle. The persistent
RunPod volume retained mode `0777`, so isolation relies on the dedicated
pod/container boundary and exact hashes, not host-level exclusive permissions.
The exact current remote continuity checker matches the frozen checker, while
historical executed-byte proof remains limited by unavailable immutable
file-history.

The evidence-boundary correction is 3946 bytes with SHA-256
`11b38c42f04b2613064ae4b76882afb8297d7c720ed08110d814e0b339626803`. It is a separate post-query governance addendum because
it changes interpretation only, not execution inputs; the final evidence
package and integrity anchor must bind it.

The self-excluding local `ARTIFACT_MANIFEST.json` now binds all 51 other
Attempt 5 package files totaling 40,119,563 bytes. The ordinal artifact-tree
SHA-256 is
`268d0cbc05f9b943dc0853727ecba47d5117f42b0ec3c3de3d8ea774cf10b60c`;
the 9,595-byte manifest SHA-256 is
`595ef472d14ad848f56f0e14699068d515be9c800140e96d9fbabca20f9458b5`.
An independent audit rehashed every entry and returned `PASS`.

A new direct read-only continuity check passed at `2026-07-23T08:04:21Z`.
It reverified the frozen repository, dependency, host/boot/machine/GPU, PRE,
query, empty-output, zero-compute-application, and run identities. Its
4,030-byte observation record has SHA-256
`7eaaeaf02bdc54a22d1c6c7010e3a5aaf17cd2936428c9c6658483bf0252550d`.
The query remains `UNSENT`, model/CUDA execution remains `NONE`, and the claim
boundary remains `SHADOW / NONE / NOT_LICENSED`. Both records are post-query
evidence that still require the final integrity anchor. Gate 1 remains `OPEN`,
and the score remains `0.33`.

## Plain answer

At `0.33`, CAS Harness has substantial research, product, evidence, and
fail-closed foundations, but the current new-design canary has not executed a
model or CUDA. At `1.00`, the project must demonstrate repeatable hidden-state
and activation probing, capability-scoped cross-architecture behavior, genuine
recoverable 300B-class execution, validated prompt-injection detection, bounded
steering and ablation, resolved CJT/J-Space/Bias/RPM/CAS-Ohm experiments,
authenticated workers, durable evidence and recovery, a usable customer
product, and independently defensible external claims.

`1.00` does not mean zero future bugs or that every future architecture is
already calibrated. It means the defined target is demonstrated, the adaptive
architecture-discovery path works, unsupported verdicts fail closed, and every
public claim is limited to the exact evidence that passed.

## Non-negotiable completion rules

1. Unknown models enter `DISCOVERY_CAPTURE`, adapter selection or generation,
   and canary diagnostics. Uncertainty blocks a customer verdict; it does not
   terminate the universality program.
2. Every model/revision/capability row is licensed separately. One successful
   Pythia run cannot license Qwen, OLMo, Llama, MoE, 20B, or 300B.
3. A negative but well-powered experiment resolves a hypothesis without
   licensing it. Optional modules that fail must be excluded from verdicts;
   the result must not be hidden or converted into success.
4. `FLAG_FOR_HUMAN_REVIEW` is never called `ACCEPT`.
5. Exact query approval applies only to those exact bytes. Attempt 1-4
   identities, queries, nonces, approvals, anchors, and remote roots may not be
   reused for Attempt 5.
6. No score moves because a plan, worker count, configuration flag, health
   endpoint, or small-model extrapolation says a capability should work.
7. Research evidence and customer-production acceptance remain separate until
   the final cross-lane release gate.
8. J-Space, CAS-Ohm, CJT, or RPM may be excluded if they add no validated
   incremental value. Prompt-injection detection and bounded steering/ablation
   are mandatory parts of the currently stated `1.00` target. A missing
   Pythia candidate pass blocks full Gate 3 credit; missing cross-family
   licensing blocks full Gate 4 credit and final `1.00`.

## 1:1 Metaphor Map

| Technical term | Plain-English meaning | Metaphor piece | Exact mapping |
|---|---|---|---|
| Probe/readout | A classifier measuring information in hidden states | Gauge | The gauge reads an internal signal; it does not prove the signal causes output. |
| Ablation/intervention | A controlled internal change | Circuit-breaker test | One circuit is changed to measure what downstream behavior changes. |
| Matched control | A fair same-budget comparison | Control lane | It tests whether CAS beats an equally sized non-CAS intervention. |
| Architecture adapter | Model-specific hook and tensor mapping | Adapter plug | The common Probe IR uses the correct plug for each model architecture. |
| Evidence Packet | The retained record of a run | Case file | It binds inputs, identities, raw evidence, controls, results, and verdict. |
| WORM/Object Lock | Retention that restricts changing evidence | Locked filing cabinet | `GOVERNANCE` has an override key; `COMPLIANCE` removes that ordinary operator bypass during retention. |
| Third-party witness | Independent timestamp or transparency service | Independent notary | It proves an external party saw a digest and helps detect replacement. |
| mTLS/workload identity | Cryptographic worker authentication | Employee badge | It proves which worker submitted a fragment, not that computation was honest. |
| Checkpoint/resume | Durable progress recovery | Save-game system | A failed worker resumes the frozen run without repeating completed work. |
| Release authority | Final evidence-bound human decision | Occupancy permit | It is issued only after technical, product, legal, and operational gates pass. |

## Evidence-weighted score ladder

The targets are cumulative. Parallel engineering may happen earlier, but a
score is awarded only when the relevant exit evidence has passed.

| Gate | Required outcome | Increment | Cumulative target |
|---|---|---:|---:|
| Current | Attempt 5 pre-anchor freeze and independent PRE reverification passed; controlled-workflow query unsent; no TSA receipt or official model/CUDA artifacts observed | — | `0.33` |
| 1 | Fresh Attempt 5 technical canary passes | `+0.05` | `0.38` |
| 2 | Small-model semantic authority, controls, uncertainty, and claim correction pass | `+0.08` | `0.46` |
| 3 | Joined Pythia program produces preregistered prompt-injection and steering/ablation candidate passes and resolves optional CJT/J-Space/RPM/CAS-Ohm components | `+0.10` | `0.56` |
| 4 | Required dense and MoE families pass held-out cross-architecture confirmation | `+0.09` | `0.65` |
| 5 | Distributed scale ladder culminates in a recoverable 300B/314B run | `+0.10` | `0.75` |
| 6 | Evidence, security, worker trust, storage, failover, and recovery become production-grade | `+0.10` | `0.85` |
| 7 | Customer product, billing, compliance, support, CRM, and launch gates pass | `+0.10` | `0.95` |
| 8 | Independent replication, nine authorities, and final release decision pass | `+0.05` | `1.00` |

## Dependency map

```text
Gate 1 -> Gate 2 -> Gate 3 -> Gate 4
   |
   +------> Gate 6A critical evidence/worker/recovery substrate
   |                         |
   |                         +------> Gate 5: 100B rehearsal and 300B run
   +------> Gate 6B remaining production hardening (parallel)
   +------> Gate 7 product/commercial/compliance (parallel)

Gates 2-7 -> Gate 8 independent acceptance and final release
```

## Gate 1 — Fresh Attempt 5 technical canary (`0.33 -> 0.38`)

1. **Completed 2026-07-23:** independently construct and reconstruct the
   canonical 31-file implementation manifest and complete Git bundle from
   clean commit `f72b89cd2ec574400ffe69ad7bd1540791fb73c3`. Preserve the
   separate ten-changed-file repair receipt as supplementary evidence.
2. **Completed:** remote Linux prestage rechecked the exact implementation,
   dependency/model inputs, OpenSSL 3 path, host/GPU capacity, and non-model
   guard conditions.
3. **Completed:** fresh identity `dd55bc73`, PRE, nonce-derived run ID,
   protocol, launch mapping, network plan, anchor payload, tool bindings, and
   empty execution boundaries were created and frozen. Setup identity
   `eeec3ec7` is superseded and never reusable.
4. **Completed offline:** the fresh RFC3161 query was generated, reconstructed,
   and decoded. It is exactly 104 bytes with SHA-256
   `e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846`.
5. **Current owner gate:** obtain exact byte-specific approval, recheck
   continuity, transmit once with retries disabled, verify the response, and
   freeze the anchor receipt and launch configuration.
6. Run Pythia-160M through the two-phase seccomp wrapper on an isolated GPU
   satisfying the exact `24_000_000_000`-byte observed-capacity gate.
7. Require phase-two TSYNC, post-guard CUDA proof, all 213 required artifacts,
   all 1,248 registered autograd calls, `IMMUTABLE_ENVIRONMENT_MATCH`, POST
   capture, off-pod recovery, and the independent receiver.

Exit requires the registered technical-canary pass and reconstruction of every
required artifact/count/hash. The exact frozen run must demonstrate the model,
CUDA, hooks, gradients/JVP/VJP path, and isolation controls.

Any mismatch produces only a complete fail-closed receipt with
`NO_SCIENTIFIC_CONCLUSION / NONE / NOT_LICENSED`. Another attempt requires a
new identity. A technical pass permits the scientific study; it does not
license prompt-injection detection, steering, universality, or 300B.

## Gate 2 — Small-model semantic and claims closure (`0.38 -> 0.46`)

1. Publish a model-by-revision-by-evidence-tier matrix reconciling every v1.0,
   v2.1, investor, engineering, and archived claim. Remove blanket six-model
   wording unless raw evidence supports the exact rows.
2. Complete the withdrawn-`ACCEPT` root-cause report without conflating
   defects. Separate the original verdict logic/record and absent or
   insufficient uniqueness/MTC gate; the later evidence that required
   withdrawal; and the later candidate-only revival plus anonymous-share
   bypass regressions. Tombstone every packet/read/share/export/anchor path and
   add regression tests preventing revival.
3. Obtain owner approval for a field-level semantic authority registry before
   claim-bearing A/B work. Bind native symbols, normalized indices, semantic
   definition IDs, source/crosswalk hashes, D3DA and A124 as separate versions,
   World-to-CAS-Domain and World-to-CAS-Register as separate mappings, and
   native F28 versus CAS Drive-by-Register. Mark Acquisition and algebra
   profiles `unavailable` until explicitly reconciled.
4. Run a same-model/revision/hook/split/budget/seed TKS definition experiment:
   original raw TKS; deployed byte-different payload; approved rich normalized
   definitions; compact CAS; coherent non-TKS ontology; shuffled/random nulls.
5. Preserve native TKS `A1-D10`, normalized indices, source hashes, crosswalks,
   and the D3DA/A124 semantic versions as distinct experimental subjects.
6. Report held-out results with confidence intervals, seed variation,
   clustered bootstrap where needed, calibration, error analysis, and raw
   artifact locations. Do not publish point estimates without uncertainty.
7. Run same-budget matched random, orthogonal, wrong-axis/layer/token,
   label-permuted, text, hash, and strong embedding baselines.
8. Replay the strongest saved Pythia/TKS fixtures through the current live
   Evidence Packet path without overwriting the historical record.

Exit requires exact model/revision/tier claim rows, `control_proof: present`
where controls ran, independently reproducible raw evidence, and a verdict
consistent with preregistered criteria. Mixed or negative results remain
`OPEN / NOT LICENSED`; criteria are not rewritten after outcomes are known.

## Gate 3 — Joined Pythia causal and behavioral closure (`0.46 -> 0.56`)

1. Correct the P0 output-control coordinate defect: 3,072-wide intermediate
   coordinates may not be applied to a 768-wide post-projection tensor.
   Invalid coordinates must fail closed.
2. Implement `CJT_JSPACE_OHM_JOINED_CANARY_V0` in a reconciliation worktree
   with a toy model, exact-hook and tensor-change guards, cleanup tests, raw
   artifact receipts, and an independent verifier.
3. Freeze the variable contract before data collection. `V_ext` is the
   controlled outside desire/stimulus/trigger; `C` is the cause-terminal value
   after `V_ext` enters the CJT; `B` is intended Bias and `b` is measured bias;
   `S_RPM` is the registered RPM stimulus/trace and `G_RPM` is its measured
   result; `I_internal` is the measured hidden-state response; `E` is the
   downstream output effect; and intervention dose `alpha` is not `V_ext`.
4. Freeze exactly one cause transduction before the run: either
   `C_EQUALS_I_AT_REGISTERED_TEST_POINT` or an explicit registered
   `C = T(V_ext, B)` function. Treat any later change as a new protocol.
5. Test `Delta V_ext = R_eff * Delta I_internal`, conditioned on `B`,
   `G_RPM`, and the preregistered operating region, against null, affine,
   saturating, Hill, and piecewise competitors on untouched data. Do not
   assume raw `V=IR`. Define `R_eff = 1/G_eff` only when the fitted nonzero
   slope is stable and its uncertainty interval excludes zero; otherwise
   report `R_eff: unavailable`.
6. Run a narrow GPU smoke, then preregister and timestamp the powered design.
   The base grid is `5 V_ext x 7 Bias x 9 RPM x 7 prompt groups = 2,205`
   cells per seed before replicates, layers, tokens, controls, and overload
   points. Power analysis sets the final workload.
7. Retain same-transaction hidden mediator and generated-output measurements.
   Compare ordinary hidden state, TKS/CAS probes, J-Space, CAS-Ohm, CJT/RPM,
   the joined system, and random/sham systems.
8. Prompt-injection validation must separate `INJECTION_PRESENT`,
   `INJECTION_RECOGNIZED`, `INJECTION_FOLLOWING_INTENT`, and
   `AUTHORITY_VIOLATION`; hold out attack/template/payload/source/language/
   encoding/long-context families; report FPR/FNR, AUPRC, calibration,
   worst-group recall, and clean utility.
9. Steering and ablation use signed multi-dose interventions plus sham,
   same-norm random, orthogonal, wrong-axis/sign/layer/token, and matched-rank
   controls. Measure target effect, utility, perplexity, refusal, toxicity,
   calibration, and unrelated capabilities.

Gate 3 can produce exact-Pythia candidate passes only. Prompt-injection
detection and steering/ablation must meet their preregistered criteria for
Gate 3 credit, but remain `NOT LICENSED` pending the named cross-family,
adaptive-attack, benign-utility, calibration, and independent-repeat evidence
in Gate 4. If CAS-Ohm, J-Space, CJT, or RPM adds no incremental value, retain
it as `NOT LICENSED` and exclude it from verdicts; the core harness may still
progress.

## Gate 4 — Adaptive cross-architecture universality (`0.56 -> 0.65`)

1. Stabilize a model-neutral Probe IR and adapter contract for hook discovery,
   shapes, token positions, interventions, gradients, cleanup, and receipts.
2. The minimum named coverage is one exact revision from each required family:
   Pythia/GPT-NeoX, Qwen, OLMo, Llama or Mistral, and one small MoE. MoE
   validation distinguishes router, selected/shared experts, active
   parameters, total weights, and rank ownership.
3. Every adapter passes no-hook equivalence, hook counts/shapes, signed capture,
   intended tensor change, invalid-coordinate rejection, finite difference
   versus JVP/VJP agreement, cleanup, and independent reconstruction.
4. Repeat source-locked semantic, prompt-injection, steering, ablation, and
   causal gates with architecture-family holdouts and untouched prompt
   families. Prompt-injection confirmation includes adaptive attacks, benign
   utility, calibration, worst-group analysis, and an independent repeat.
5. Repeat GPT-NeoX-20B with current definitions, controls, uncertainty, durable
   raw evidence, and verdict policy. Preserve positive readout/bridge and
   negative forward intervention as separate historical facts. This corrected
   20B repeat is a Gate 4 prerequisite consumed by the later scale ladder; it
   is not credited a second time in Gate 5.
6. Publish raw data and a capability matrix. Gate 4 may mark only exact
   `MODEL_CAPABILITY_LICENSED` rows whose model, revision, capability, protocol,
   and evidence tier passed. `UNIVERSALITY_LICENSED` remains unavailable until
   Gates 5, 6, and 8 also pass.
7. Award the full `+0.09` only when every required family and held-out-family
   contract passes. A failed or missing required family keeps Gate 4 partial
   and `OPEN`; it does not erase already earned exact-model licenses.

Universality is adaptive: any legally accessible open-weight model exposing
internal tensors can enter discovery and adapter work. It is not a claim that
one fixed hook already fits every possible model, and Gate 4 alone does not
license the project-wide universality claim.

## Gate 5 — Genuine recoverable 300B execution (`0.65 -> 0.75`)

Gate 5 may not begin its 100B or 300B executions until the Gate 6A critical
substrate has passed live tests: raw worker fragments, authenticated workers,
replay protection, durable checkpoints/resume, injected-fault recovery, and
independent reconstruction. A configured feature or narrow unit test does not
meet this prerequisite.

1. Replace scale-planner guesses with versioned measured hardware profiles,
   calibration residuals, and uncertainty. Document every multiplier.
2. Add MoE-aware total-versus-active parameter accounting; require real model
   config metadata for layer/expert maps; normalize precision/quantization
   inputs; fail closed when no memory-feasible plan exists; provide an explicit
   review path beyond the current 512-worker policy.
3. Implement true tensor, pipeline, and expert parallelism. A worker must not
   load the whole frontier model and then pretend assigned layers are a shard.
4. Store raw worker fragments and checkpointed merge state. Inject OOM, worker
   loss, rank loss, uploader failure, orchestrator restart, replay, and artifact
   corruption.
5. Run the scale ladder after consuming the corrected 20B Gate 4 result:
   optional 70B rehearsal, mandatory genuine 100B distributed rehearsal, then
   a pinned 300B/314B open-weight model.
6. The 300B run hashes every weight shard/config/tokenizer, binds topology and
   worker identities, captures hidden states and controlled interventions on
   owning ranks, meters memory/throughput/time/cost, resumes injected failures,
   retains off-host raw evidence, and passes an independent sample repeat.
7. If Grok-1 314B is the primary target, first qualify a JAX/Flax MoE adapter
   with router/expert semantics and registered projected-JVP/VJP approximation
   or reconstruction-error gates. If that path cannot pass, the owner must
   approve a different legally accessible 300B-class target; a dense adapter
   may not be relabeled as Grok support.

The planning starting point is approximately `8 x H200 141GB` or
`16 x H100 80GB`, subject to model, precision, active experts, context,
artifacts, and measured headroom. Provision it only after small-model, adapter,
storage, worker-trust, and 100B rehearsals pass. Passing licenses only the exact
300B model/revision/protocol and scale capability—not every 300B model.

## Gate 6 — Evidence, security, and recoverable operations (`0.75 -> 0.85`)

This track starts after Gate 1. Gate 6A is the critical subset named in Gate
5: raw fragments, cryptographic worker identity, replay protection, durable
checkpoints/resume, injected-fault recovery, and independent reconstruction.
Gate 6A must pass before the 100B rehearsal; Gate 6B contains the remaining
production hardening and runs in parallel with Gates 2-5.

1. Freeze one tenant/run/model/adapter/probe/TKS/worker/shard/artifact identity
   contract shared by queue, database, object store, WORM object, witness,
   worker receipt, and final packet.
2. Store hidden states, activations, logits, Jacobian/JVP artifacts,
   interventions, controls, fragments, and logs in versioned tenant-isolated
   object storage with conditional create, byte count, SHA-256, object version,
   layer/token/sample ranges, and independent reread.
3. Describe `GOVERNANCE` retention as operator-overridable and time-limited.
   For `1.00`, deploy non-bypassable `COMPLIANCE` retention or an independent
   Merkle-root transparency witness, preferably both, with customer export and
   reconciliation. A witness proves integrity/existence, not availability. If
   `COMPLIANCE` is absent, complete packets and raw evidence must also be
   independently or customer retained; product copy must say `GOVERNANCE` and
   `tamper-evident`, never permanent or operator-immutable.
4. Add fleet identity using private TLS/mTLS or equivalent short-lived workload
   credentials, scoped capabilities, live revocation and rotation, replay
   protection, signed result envelopes, and multi-replica enforcement.
   Equivalent credentials may not be a static shared token or server-only
   private TLS. Identity does not prove honest computation.
5. Build durable queue/resume/checkpointing with idempotent stages, monotonic
   fencing, no duplicate GPU charges/WORM appends, and visible `ORPHANED` or
   human-review outcomes for ambiguous external calls.
6. Deploy managed Postgres high availability plus encrypted backups and
   point-in-time recovery. Kill the primary during active leases and evidence
   publication; prove reconnection, fencing, resume, and restoration into an
   empty environment with measured RPO/RTO.
7. Independently recompute claim-bearing shards on redundant workers. Use a
   preregistered disagreement policy; mismatches quarantine workers and produce
   `FLAG_FOR_HUMAN_REVIEW`.
8. Keep private-weight upload disabled until dedicated ephemeral tenant
   workers, per-tenant keys/prefixes, deny-by-default egress, JIT/MFA operator
   access, telemetry allowlists, teardown, crypto-shred, residency, retention,
   and exfiltration red-team tests pass.
9. Add complete observability and real alert/incident drills for worker
   compromise, weight exfiltration, database loss, corrupt artifacts,
   WORM/witness outage, leaked credentials, and a stuck expensive GPU job.
10. Add cryptographic algorithm agility and expert review. Do not call SHA-512
    or SHA-3 alone quantum-resistant; post-quantum signatures/timestamps are a
    separate evidence and standards decision.

Full Gate 6 credit requires live adversarial evidence, including real alert
delivery and acknowledgement, deliberate escalation, named incident
participation, failover/restore, and evidence recovery. Code, configuration,
or simulated receipt counts alone leave the gate `OPEN`.

## Gate 7 — Customer product and public operation (`0.85 -> 0.95`)

This track also starts after Gate 1 and runs in parallel.

1. Start from a fresh clean current-`master` worktree. Inventory old launch
   branches as integrated, obsolete, selectively ported, or reimplemented; do
   not merge stale branches wholesale.
2. Finish durable accounts, organizations/workspaces, sessions, revocation,
   disabled-account checks, server-side RBAC, tenant enforcement, privileged
   roles, security headers/CORS, audit logs, and separate worker identity.
   Eliminate any shared frontend mint secret or paywall bypass; authorization
   decisions are server-only. Save and prove recovery of a permanent owner
   credential, remove `NC_ACCOUNT_BOOTSTRAP_SECRET`, prove first-owner
   bootstrap remains closed afterward, and prove ordinary owner authentication
   still works.
3. Enforce atomic server-side quotas by tenant, plan, model lane, GPU budget,
   concurrency, runtime, and storage.
4. Ship a CAS Harness-branded flow: login; select model/revision; connect key,
   endpoint, or worker; run; see progress/failure; open the proof ladder; view,
   verify, download, and share the packet; read FAQ/tooltips without raw JSON.
5. Prove the full hosted journey on the exact protected/deployed SHA: real
   Pythia audit, truthful terminal verdict, download hash,
   `/verify overall: all_match`, share/revoke, foreign-tenant isolation, and
   restart persistence. Before publishing this authority or any acceptance
   authority, require a fresh fixed-15-minute authorization from an
   authenticated permanent owner and retain its bound receipt.
6. Establish live Stripe plans only after pricing, tax, trial, refund,
   cancellation, and overage decisions. Close with one consenting payer path:
   Checkout, signed webhooks, durable event-to-entitlement lineage, metered
   audit, invoice/receipt, cancellation, repair, reactivation, and restart
   recovery. Fail-closed tests cover webhook replay and out-of-order delivery;
   inactive, canceled, past-due, expired, future, missing, malformed, or
   incoherent periods; failed payment and refund; and tenant, customer, plan,
   price, or metadata drift. Contradictory provider state must quarantine or
   revoke an existing grant until explicitly repaired.
7. Publish counsel-approved Privacy, Terms/beta agreement, DPA, subprocessors,
   retention/WORM disclosure, data-rights workflow, security policy, incident
   plan, vendor register, no-certification statement, and support/security
   contacts. Test access/export/correction/deletion workflows.
8. Activate a real CRM lifecycle: a consenting lead reaches Airtable with a
   real `external_id`; owner, notes, next action, NDA, packet-sent, deal value,
   and follow-up states survive restart. Prove support/security message receipt.
9. Run internal production smoke, invite-only private alpha, paid NDA beta, and
   public launch in order with preregistered reliability, security, support,
   and claim-honesty thresholds.
10. Reach SOC 2 readiness through a control matrix, MFA, access reviews, change
    records, incident exercise, vendor reviews, security training, monitoring
    evidence, and an independent gap assessment. Do not claim certification
    unless an auditor issues the report.

A small-model scoped beta may launch earlier only with prominent boundaries:
invite-only, public open-weight models, single trusted worker, capped spend, no
private weights, exact `GOVERNANCE` retention disclosure, customer export,
tenant isolation/support/alerts, and unresolved claims routed to
`FLAG_FOR_HUMAN_REVIEW`. That beta is not the `1.00` universal product.

## Gate 8 — Independent acceptance and release (`0.95 -> 1.00`)

1. Publish a model/revision/capability/evidence-tier matrix with raw-data
   locations, immutable hashes, held-out splits, seeds, uncertainty, matched
   controls, failures, missingness, and exact license status.
2. Commission independent scientific reproduction of claim-bearing small,
   cross-architecture, and 300B samples; security red-team/penetration testing;
   and restore/failover/evidence-reconstruction review.
3. Prepare an Amazon/engineering packet prominently including the withdrawn
   `ACCEPT` root cause, regression proof, Governance-versus-Compliance truth,
   exact model coverage, negative results, and no blanket claim beyond passed
   rows.
4. Before publishing `root_ci_protected_deploy` or assembling the release
   candidate, obtain a fresh pinned signed root-CI/deploy receipt bound to the
   exact protected source SHA and live deployment identity. If that receipt
   expires, or source/deployment changes before release, refresh and reverify
   it before proceeding.
5. Publish current authorities for exactly nine customer-production gates:
   `runtime_worm`, `root_ci_protected_deploy`, `hosted_customer_journey`,
   `accounts_billing`, `legal_publication_approval`, `support_crm`,
   `incident_tabletop`, `alert_delivery`, and `claim_honesty`.
6. Create a separate final `release_decision` binding all nine authority hashes,
   a fresh signed root receipt, exact protected source SHA, exact deployment
   identity, and authorized distinct-human approvals.

Only this convergence authorizes the production system to issue `ACCEPT` for
an individual Evidence Packet whose own scientific, integrity, and policy
gates pass; it does not pre-approve all packets. Any unresolved packet remains
`FLAG_FOR_HUMAN_REVIEW`. Any open release authority keeps release `OPEN`, score
`1.00` unavailable, and customer-production `ACCEPT` `NOT LICENSED`.

## Team and realistic sequencing

Minimum effective team:

1. Interpretability and ML research lead.
2. Experimental and statistical reviewer.
3. ML systems and distributed-compute engineer.
4. Security, SRE, and evidence engineer.
5. Full-stack product engineer.
6. Part-time qualified counsel or compliance advisor.
7. Independent red-team and reproduction reviewers.

AI agents can implement, test, document, and coordinate much of the work, but
they cannot fabricate legal approval, a real payer, incident responders, MFA,
provider identity, independent review, or the final release decision.

Planning-only critical-path estimate for a dedicated team, assuming available
GPUs and timely human/provider decisions:

| Period | Main work |
|---|---|
| Weeks 0-2 | Gate 1 Attempt 5 freeze and technical canary |
| Weeks 2-6 | Gate 2 claims/RCA/TKS A/B/controls; begin Gates 6 and 7 |
| Weeks 4-12 | Gate 3 joined runner, smoke, power analysis, Pythia pilot |
| Weeks 8-20 | Gate 4 dense/MoE adapters and cross-family replication |
| Weeks 12-28 | Gate 5 100B rehearsal and 300B cluster run |
| Weeks 2-24 in parallel | Gates 6-7 evidence/security/product/legal/beta |
| Final 2-6 weeks | Gate 8 independent replication and release |

This suggests roughly six to nine months for a staffed program, not a promise.
A solo, part-time, or provider-blocked program can take materially longer.
Scientific redesign after a negative result can also extend the path.

## Owner-only or human-owned decisions

The owner does not need to write the code. A qualified human must handle:

1. Exact byte-specific approval for each fresh external RFC3161 query.
2. Sign-in, MFA, CAPTCHA, provider recovery, and inaccessible secrets.
3. Saving/recovering the owner credential and approving identity architecture.
4. Model/cluster spending limits and procurement.
5. Retention/escrow, data use, pricing, tax, refunds, and commercial policy.
6. Qualified legal/privacy publication approval.
7. Named on-call, incident commander, tabletop participation, and support.
8. Distinct-human claim-honesty and final release approval.

## Immediate next 12 actions from 0.33

1. **Completed:** freeze the canonical 31-file Attempt 5 implementation manifest.
2. **Completed:** build the complete v2 single-head Git bundle.
3. **Completed:** independently reconstruct both in an empty checkout and
   verify all source/dependency bytes plus the complete worker suite.
4. **Completed:** remote isolated-GPU prestage passed without model or CUDA
   execution.
5. **Completed:** fresh `dd55bc73` identity, PRE, protocol, nonce, run ID,
   mapping, network plan, payload, and empty output boundary were frozen and
   independently reverified.
6. **Completed offline:** the exact 104-byte RFC3161 query was generated and
   reconstructed.
7. **Current owner gate:** approve SHA-256
   `e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846`
   for one transmission to DigiCert.
8. **Pending approval:** recheck continuity, transmit exactly once, verify the
   timestamp response, and freeze the anchor receipt and launch configuration.
9. Run the guarded Pythia-160M technical canary.
10. Recover POST/raw artifacts off-pod and run the independent receiver.
11. If it passes, begin TKS definition A/B and joined-runner implementation.
    If it fails, preserve the receipt, perform root-cause analysis, and create
    a new prospective identity without reusing the consumed identity.
12. In parallel, begin clean-`master` safety reconciliation, the universal
    evidence identity contract, accounts/RBAC/tenant isolation, and counsel/
    retention decision packages.

The current blocker is exact byte-specific owner approval. The query already
exists and is unsent. After approval, the first operator action is a fresh
continuity check followed by one no-retry transmission of those exact bytes.
Model/CUDA execution remains downstream of verified timestamp and anchor
construction.