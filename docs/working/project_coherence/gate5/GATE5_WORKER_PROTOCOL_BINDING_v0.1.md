# Gate 5 worker-to-Harness-v2 protocol binding

Document status: `DRAFT / OPEN / NOT FROZEN`

Decision status: `OPEN / KEEP_OPEN`

Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`

Experimental execution status: `NOT_STARTED`

License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`

Live / product route status: `unavailable / not authorized`

Authority boundary: `PRIVATE RESEARCH ENGINEERING CANDIDATE ONLY`

This document specifies a bounded, fail-closed mapping between the current CAS
fleet-worker surfaces and the isolated Harness-v2 control kernel. It does not
authorize or report a RunPod job, admitted scientific GPU execution, experiment,
scientific result, canon change, product route, license decision, public
disclosure, or Gate 5 closure. Retained local GPU and joined mechanics are bound
by `GATE5_ENGINEERING_EXECUTION_RECONCILIATION_v0.1.json`; they do not change
this protocol's normative schema or authority. The fixed Gate 5 status above is
not changed by a passing local test, an authenticated HTTP callback, a content
hash, an Object-Lock receipt, or this
document.

## 1. Purpose and source boundary

The purpose of this binding is to remove an interface ambiguity recorded by
`G5-ENGINEERING-001`: the fleet launcher, lease, worker, receipt, and model
identity controls already exist, and the Harness-v2 preregistration and Evidence
Packet carriers already exist. The dark lifecycle successor and admitted
packaged adapter now give those surfaces one locally reviewable, locally tested
protocol. The adapter remains default-dark and does not admit live execution.

The current source surfaces are:

| Surface | Current source of truth | Relevant symbols |
|---|---|---|
| Harness-v2 exact JSON and artifact identities | `src/cas_harness_v2/_strict_json.py`, `src/cas_harness_v2/_validation.py` | `ArtifactRef`, strict loaders, canonical hashes |
| Preregistration, amendments, and outcome-access seal | `src/cas_harness_v2/preregistration.py` | `PreregistrationArtifact`, `PreregistrationChain`, `OutcomeAccessEvent` |
| Evidence Packet v2 | `src/cas_harness_v2/evidence_packet.py` | `EvidencePacketArtifact`, `load_evidence_packet`, `verify_evidence_packet` |
| Worker-protocol carriers | `src/cas_harness_v2/worker_protocol.py` | `WorkerAuthorizationArtifact`, `WorkerTerminalReceiptArtifact`, `load_worker_authorization`, `load_worker_terminal_receipt` |
| Tenant/audit/fleet/worker callback identity | `noetic-compass-scaffold/noetic-compass/api/services/fleet_service_auth.py` | `FleetServicePrincipal`, `FleetServiceBoundIntakeReceipt`, `FleetServiceAuthStore.authenticate_with_bound_intake_receipt`, `verify_authenticated_callback` |
| Fleet lease and receipt state | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_fleet_executor.py` | `FleetJobRecord`, `ActiveFleetJobLease`, `validate_active_fleet_job_lease`, `lease_next_job`, `submit_job_receipt` |
| API bridge into the exact protocol | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_worker_bridge.py` | typed principal/job/nonce-to-carrier bridge functions admitted by this candidate |
| Prospective lifecycle registry | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_run_lifecycle.py` | `DurableProspectiveRunLifecycle`, one-use transitions, hash-linked events, tenant reconciliation |
| Exact wrapper/orchestration seam | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_lifecycle_service.py` | `DarkHarnessV2LifecycleService`, exact wrapper replay, output/outcome/packet/nonreporting reconciliation |
| Default-dark API boundary | `noetic-compass-scaffold/noetic-compass/api/routes/cas_harness_v2_worker_protocol.py` | exact request-bound service authentication and private authorization/output/consume/terminal/packet/nonreporting/reconcile handlers excluded from OpenAPI |
| Worker lease and terminal callback | `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/fleet_worker.py` | `FleetJob`, `FleetJobExecutionResult`, `FleetApiClient`, `FleetWorkerDaemon` |
| Durable callback replay control | `noetic-compass-scaffold/noetic-compass/api/services/fleet_service_auth.py` | credential-scoped `fleet_service_nonce` rows in `StateStore` |
| Existing immutable packet repository | `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_evidence_object_store.py` | `EvidencePacketRepository`, `S3ObjectLockPacketBackend` |

If prose here disagrees with an exact loader, the exact loader wins. If a bridge
cannot establish every required equality from current source objects, it must
fail closed. It may not infer a missing identity, downgrade a mismatch to a
warning, or construct favorable evidence from absence.

## 2. Three non-interchangeable authorities

The protocol keeps three capabilities separate.

### 2.1 Callback authentication

`FleetServiceAuthStore.authenticate` verifies one HTTP attempt using a secret
credential, tenant scope, audit/fleet scope, optional worker scope, required
capability, application-clock freshness, and a durable credential-scoped
one-time callback nonce. Its successful result is a `FleetServicePrincipal`.

That principal proves only that the current API accepted one scoped machine
callback under its configured application trust boundary. It does not prove
that an experiment was prospectively authorized, that the underlying host or
model execution is independently attested, that the clock is trusted, or that
the caller is licensed to create a scientific or product claim.

### 2.2 Run authorization

A Harness-v2 run authorization is a separate exact-byte carrier. It binds one
sealed pre-outcome preregistration chain to one exact fleet assignment, the
lease-bound model facts, the preregistered model/code/environment identity set,
and one caller-declared 256-bit run nonce. This carrier is immutable once
execution may begin.

The authorization is prospective, so it does not contain a later callback
nonce. The strict kernel checks only the run nonce's declared profile,
base64url encoding, and length; it still does not authenticate issuance or
consumption. The lifecycle successor's default factory calls
`secrets.token_bytes(32)`, reserves the resulting digest before authorization
construction, releases the raw value only once, and uses a same-host
`StateStore` compare-and-swap for consumption. The constructor also accepts an
injected nonce factory, including deterministic test factories, and no admitted
runtime attests which callable supplied a particular nonce. That local control
does not alter the strict carrier's
`EXTERNAL_REQUIRED_NOT_PROVIDED` caveat and does not establish a multi-host,
host-loss-resistant, independently authenticated run authority.

### 2.3 Terminal receipt and outcome access

A terminal receipt is another exact-byte carrier. It records either success or
failure for the authorized run, binds the exact authorization digest, preserves
all produced/missing/error facts, and binds stable artifact identities. A
success carrier does not itself mean the scientific criteria passed. A failure
carrier is retained negative evidence and must never be erased by a retry.

The transport callback nonce is never a field of either worker carrier. Every
accepted dark-route request creates a durable authentication nonce row. For a
terminal submission only, the API bridge also places the complete
server-authored `FleetServiceNonceReceipt` in a separate callback-acceptance
wrapper and index that point to the immutable terminal storage identity. The
nonterminal route operations do not create that bridge wrapper. This separation
lets identical terminal bytes survive a transport retry made with a fresh HTTP
nonce without allowing the fresh nonce to rewrite worker evidence.

`PreregistrationChain.record_outcome_access` remains a distinct event. Outcome
access seals the pre-outcome chain and binds the execution-completion timestamp
plus an exact receipt artifact. It must occur only after terminal execution
facts exist. The successor reserves the untrusted access time in the lifecycle
store before mutating the process-local chain and then retains/replays an exact
wrapper. This is recoverable local ordering, not durable WORM authority;
independent append-only ordering remains open.

### 2.4 Exact executable worker-carrier schemas

`src/cas_harness_v2/worker_protocol.py` defines two closed schema labels:

| Artifact | Exact schema value | Exact loader |
|---|---|---|
| worker run authorization | `cas_harness_v2.worker_authorization.v1` | `load_worker_authorization(raw, *, chain)` |
| worker terminal receipt | `cas_harness_v2.worker_terminal_receipt.v1` | `load_worker_terminal_receipt(raw, *, authorization, chain)` |

The frozen public carriers are `WorkerAuthorizationArtifact` and
`WorkerTerminalReceiptArtifact`. Both snapshot exact bytes, digest, length,
closed payload, and bound artifact identities. The terminal loader requires the
already loaded exact authorization and the same exact preregistration chain; it
does not accept a caller's detached digest as a substitute for either carrier.

The authorization has the following exact semantic sections:

| Section | Exact fields and fixed meanings |
|---|---|
| `freshness` | `issued_at`, `expires_at`, `semantic=FRESHNESS_ONLY`, `trust=NOT_TRUSTED` |
| `preregistration_binding` | `base_artifact`, `pre_outcome_chain_sha256`, `claim_id`, `claim_record_sha256`, `protected_design_sha256` |
| `identity_binding` | `model_canonical_sha256`, `code_canonical_sha256`, `environment_canonical_sha256`, `combined_canonical_sha256` |
| `required_design` | closed control and falsifier rows, each binding its exact ID and canonical SHA-256 |
| `execution_mapping` | exact `fleet_id`, `job_id`, `audit_id`, `assigned_worker_id`, `layer_start`, `layer_end`, `shard_id`, ordered `assigned_methods`, ordered `expected_outputs`, and `lease_model{model_id,model_revision,model_artifact_manifest_path,model_artifact_manifest_sha256,execution_mode}` |
| `nonce_binding` | `run_nonce{value_b64url,profile=CALLER_DECLARED_CSPRNG_256_BIT,structural_assurance=LENGTH_AND_ENCODING_ONLY}` plus `durable_enforcement=EXTERNAL_REQUIRED_NOT_PROVIDED` |
| authority/governance | fixed limitations plus the unchanged preregistration Ring-4 governance boundary |

The terminal carrier repeats the exact preregistration, identity, required
design, execution, and run-nonce bindings; references the exact authorization
as an `ArtifactRef`; records its own freshness block; and contains one closed
`terminal` branch. A callback nonce field is an unknown field and is rejected.

`COMPLETED` requires
`produced_output_effect=DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED`, an
ordered produced-output row for every authorized output, no missing outputs,
and a null error. `FAILED` requires
`produced_output_effect=QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY`, a typed
error, and an exact ordered partition of the authorized output sequence between
`produced_outputs` and `missing_outputs`. Produced and missing names may not
overlap, disappear, appear twice, or depart from their authorization order.
Every produced artifact on a failed run is quarantined partial negative
evidence only; it is not partial success and may not be promoted to a favorable
outcome.

Both carriers require this exact authority block:

```text
scope                 = STRUCTURE_ONLY
authentication        = NOT_PROVIDED
durable_one_use       = NOT_PROVIDED
trusted_time          = NOT_PROVIDED
worm                  = NOT_PROVIDED
scientific_conclusion = NOT_ESTABLISHED
license               = NOT_GRANTED
product               = NOT_AUTHORIZED
disclosure            = HELD
```

These executable loaders provide structure, integrity, exact equality, and
negative-evidence preservation only. Their fixed limitations explicitly deny
authenticated execution, durable replay enforcement, trusted time, WORM
authority, science, license, product, disclosure, and canon authority.

## 3. Exact 1:1 identity mapping

No field in the left column may be silently substituted with a different field
from the same object. String equality is exact after the current loaders have
performed their own canonical validation; there is no fuzzy or case-insensitive
matching except where a loader explicitly says so.

### 3.1 `FleetServicePrincipal` to run-authorization identity

| Current principal field | Harness-v2 carrier meaning | Required rule |
|---|---|---|
| `credential_id` | server-side callback provenance | Compare to the nonce receipt and, for a terminal bridge submission only, retain it in the private callback-acceptance wrapper. The nonce-keyed terminal-acceptance index binds safe receipt digest/length facts; the stable terminal index does not. Nonterminal route operations retain the authentication row but have no bridge acceptance wrapper. It is not a strict-carrier field or signing authority. Never retain the secret or credential digest. |
| `tenant_id` | private storage tenant | Use as the `StateStore` and repository scope on every bridge operation. It is intentionally absent from the worker carrier and cannot be caller-selected. |
| `account_id` | immutable audit-owner provenance | Use only as server-derived private repository/index provenance. It is not a reviewer or executor identity. |
| `audit_id` | `execution_mapping.audit_id` | Must equal the server FleetJob snapshot, API path, terminal receipt's repeated mapping, and private repository scope. |
| `fleet_id` | `execution_mapping.fleet_id` | Must equal the server FleetJob snapshot and callback scope. Current service auth requires `fleet_id == audit_id`; the carrier preserves both semantic names. |
| `worker_id` | `execution_mapping.assigned_worker_id` | Must be non-null for `submit_receipt` and equal the current server FleetJob assigned worker and terminal receipt's repeated mapping. |
| `capabilities` | bridge acceptance condition | `persist_terminal_callback` requires `submit_receipt`. Capabilities are not copied into the strict carrier and never imply science, outcome access, publication, licensing, or disclosure authority. |

The earlier `authenticate_with_nonce_receipt` surface remains available to the
bridge. The default-dark HTTP boundary uses the stronger additive
`authenticate_with_bound_intake_receipt` surface. Its create-only v2 nonce row
atomically binds the successful callback to the server-observed HTTP method,
exact route path, job ID, deterministic prospective run ID, authorization
digest where required, and request-carrier digest and byte length. It returns a
`FleetServiceBoundIntakeReceipt` containing the same
`FleetServiceAuthenticatedCallback(principal, nonce_receipt)`. The receipt is
server-side transport evidence only; it never enters the earlier prospective
authorization or immutable terminal carrier:

| `FleetServiceNonceReceipt` field | API-acceptance destination | Required rule |
|---|---|---|
| `nonce_id` | durable authentication-row identity and, for terminal bridge submissions only, `server_callback_nonce_receipt.nonce_id` plus acceptance trace/index identity | Exact server-derived ID for the credential/raw-nonce pair. |
| `nonce_sha256`, `byte_length` | same-named safe digest/length facts | Preserve the exact uppercase digest and UTF-8 byte length from the validated durable row; never recompute them from caller-selected replacement text. |
| `credential_id`, `tenant_id`, `account_id`, `audit_id`, `fleet_id`, `worker_id`, `capabilities` | full authenticated receipt scope | Every value must exactly equal the corresponding `FleetServicePrincipal` value. The durable row preserves the full server-authored scope; the terminal bridge wrapper repeats it only for terminal acceptance. None is copied into a worker-authored nonce field. |
| `consumed_at`, `expires_at` | acceptance timing provenance | Preserve both with `time_semantic=FRESHNESS_ONLY_NOT_TRUSTED`; they remain application-clock facts, not trusted-time evidence. |
| bound intake method/path/job/run/authorization/carrier facts | v2 nonce-row request identity | Re-read and compare the exact server-observed request; the same nonce cannot authorize a different path, run, authorization digest, body digest, or body length. |

`consumed_nonce_receipt` must re-read and validate the durable nonce row,
including schema, record ID, complete principal scope, digest, length, parents,
and trace.
A missing, legacy, cross-principal, malformed, or storage-unavailable row fails
closed. The raw callback nonce, credential secret, and lease secret never enter
either strict carrier.

Because the bridge receives a callback carrier rather than the raw nonce, its
injected `verify_authenticated_callback` port must re-read that exact durable
row again and return the identical callback object before any carrier is
accepted. For terminal intake, the admitted adapter now also preserves the
enclosing `FleetServiceBoundIntakeReceipt` through the lifecycle, and the bridge
revalidates that exact receipt and its callback identity before persistence.
This proves a bounded HTTP-intake binding only; it is not model-execution
authentication, a signature, trusted time, or worker attestation.

The executor identity written into an Evidence Packet must not be fabricated
from `account_id`, `tenant_id`, or `credential_id`. The binding may preserve the
worker/principal identity as execution provenance, but `execution.executor_identity`
and any claim of person or organizational independence require a separately
admitted identity policy.

### 3.2 Fleet lease to run authorization

The strict authorization mirrors the current live `FleetJob` shape instead of
inventing a second scheduler vocabulary. Layer ranges remain ranges,
`assigned_methods` and `expected_outputs` remain ordered arrays, and the entire
lease-bound model tuple is repeated exactly. The root loader rejects missing,
extra, reordered, type-coerced, or drifted values. The current dark persistence
bridge still does not construct this carrier from a `FleetJob`; a separately
reviewed launcher adapter must perform the direct mapping below before the
default-dark route can be admitted or enabled.

The route derives its prospective `run_id` from `job_id`. The lifecycle derives
the registry `run_id` from `subject_id`, and the lifecycle service independently
requires `subject_id == authorization_id`. Consequently an admitted adapter
must enforce the joint identity contract
`job_id == subject_id == authorization_id` before calling either side. No
current packaged adapter performs or proves that equality, so matching route
and lifecycle run identities remain OPEN.

| `FleetJob` / `FleetJobRecord` field | Harness-v2 destination | Required rule |
|---|---|---|
| `job_id` | `execution_mapping.job_id` and authorization subject | Preserve exactly in authorization and terminal carriers; it must not be reused for another authorization digest. |
| principal `fleet_id` | `execution_mapping.fleet_id` | Server-derived fleet scope; current service auth requires it to equal the audit fleet. |
| `audit_id` | `execution_mapping.audit_id` | Exact equality with principal, API path, terminal receipt, and private repository scope. |
| `assigned_worker_id` | `execution_mapping.assigned_worker_id` | Exact equality with the non-null principal and request worker identities. |
| `layer_start`, `layer_end` | same-named integer fields | Preserve both exactly and require a valid ordered range. They are assignment facts, not proof of layer semantics. |
| `shard_id` | same-named field | Preserve exactly; no parser-derived shard index/count is introduced. |
| `assigned_methods` | same-named ordered array | Preserve every value and its order; no set conversion, sorting, first-value selection, or unassigned addition. |
| `expected_outputs` | same-named ordered array | Preserve every value and its order. Terminal completion must account for this exact sequence. |
| `model_id` | `execution_mapping.lease_model.model_id` | Preserve the lease value and require exact equality with `PreregistrationArtifact.payload.identities.model.model_id`. |
| `model_revision` | `execution_mapping.lease_model.model_revision` | Preserve the lowercase 40-character lease value and require equality with the preregistered revision. A branch, tag, abbreviation, or mutable alias is rejected. |
| `model_artifact_manifest_path` | `execution_mapping.lease_model.model_artifact_manifest_path` | Preserve the exact canonical absolute lease value. It is a worker locator and does not replace the accompanying digest or preregistered identities. |
| `model_artifact_manifest_sha256` | `execution_mapping.lease_model.model_artifact_manifest_sha256` | Preserve the exact lowercase 64-hex lease value. It binds the lease manifest identity but does not alone prove semantic equivalence to all preregistered artifacts. |
| `execution_mode` | `execution_mapping.lease_model.execution_mode` | Preserve exactly. `dry_run_control_plane` remains engineering-only and can never create scientific evidence; an admitted live protocol must require the reviewed real mode. |
| `status` | authorization precondition, not a carrier claim | Authorization creation requires the exact allowed preterminal state. A completed, failed, or expired assignment cannot mint a new authorization. |
| `lease_token` | ephemeral lease capability | Verify at the fleet transition boundary; never serialize it into preregistration, authorization, outcome-access, terminal, packet, logs, or Object-Lock objects. |
| `lease_expires_at` | application lease deadline | Enforce locally as an application-clock limit. It is not a trusted-time receipt and cannot establish prospective ordering. |

The preregistration carrier contributes the immutable `claim_id`, claim-record
digest, preregistration digest, protected-design digest, pre-outcome chain
digest, model/code/environment artifact identities, frozen controls,
falsifiers, thresholds, splits, uncertainty plan, wording ceiling, and Ring-4
governance block. The fleet lease contributes only the assignment and current
machine-execution facts listed above. The loader also recomputes canonical
hashes of the complete preregistered model/code/environment objects and requires
the fixed controls/falsifiers and governance block. Neither side may overwrite
the other.

### 3.3 Fleet terminal callback to terminal receipt

The current `FleetJobReceiptRequest` is not rich enough to author a strict
`WorkerTerminalReceiptArtifact` without additional admitted facts. It lacks
`worker_started_at`, `terminal_at`, typed error code/category/retryability, and
per-output exact `ArtifactRef` identities. Its fragment URI/payload does not
automatically supply those missing meanings. The current dark bridge therefore
accepts exact authorization and terminal-receipt bytes; it does not translate
the legacy request body or claim that a fleet receipt is already Harness-v2.

| Current callback/result field | Harness-v2 terminal meaning | Required rule |
|---|---|---|
| API path `audit_id` and `job_id` | terminal subject | Must equal the authorization and current lease. |
| `worker_id` | reporting worker | Must equal the principal and assignment. |
| `lease_token` | proof of current lease possession | Verify before terminal transition, then discard from retained carriers. |
| `job_status` | `terminal.status` | Map only `completed -> COMPLETED` and `failed -> FAILED`. No other value is accepted. |
| `execution_mode` | repeated `execution_mapping.lease_model.execution_mode` | The terminal carrier repeats the exact authorization mapping; any mode drift fails strict equality. |
| `produced_outputs` | ordered `terminal.produced_outputs[].output_name` plus exact `artifact` | `COMPLETED` requires every authorized output in exact order with its `ArtifactRef`. `FAILED` may retain the produced side of an exact ordered produced/missing partition, but every such artifact has the fixed quarantined-negative-evidence effect. Names alone are insufficient. |
| `missing_outputs` | ordered `terminal.missing_outputs` | `COMPLETED` requires none. `FAILED` requires the missing side of the exact ordered expected-output partition; together the two lists must cover every expected name exactly once. |
| `evidence_packet_fragment_ref` | possible locator for separately verified exact artifact bytes | The strict receipt does not accept a fragment URI in place of per-output `ArtifactRef` rows. Recompute and verify exact bytes before mapping; a self-reported URI is not authority. |
| `evidence_packet_fragment_payload` | possible source for exact output/failure artifacts | Bind the original retained bytes, length, digest, IDs, and media types. Re-serializing an unretained mapping does not prove worker-emitted byte identity. |
| `error_message` | `terminal.error.message` for `FAILED` | Preserve the bounded secret-safe text, but `code`, closed `category`, and `retryable` are also required and are absent from the legacy request. They may not be guessed from prose. |
| worker real-model attestation | execution/model artifact evidence | Must pass the existing model/revision/manifest/local-files-only/post-load-reverified/trust-remote-code/use-safetensors checks and then be carried as an exact artifact identity. |
| worker/application start and terminal timestamps | `freshness.worker_started_at` / `terminal_at` | These facts are missing from the legacy receipt and must be supplied by the admitted worker carrier. They use `FRESHNESS_ONLY / NOT_TRUSTED`; `terminal_at` later maps to packet completion and outcome-access completion. |

A strict failed terminal error has exact keys `code`, `category`, `message`,
and `retryable`. `code` is a normalized machine ID; `message` is bounded to
4,000 characters; `retryable` is an exact Boolean; and `category` is one of
`INPUT_REJECTED`, `EXECUTION_FAILED`, `RESOURCE_EXHAUSTED`, `CALLBACK_FAILED`,
or `INTERNAL_ERROR`. `retryable=true` describes an engineering disposition; it
does not authorize automatic replay after a possibly consumed run.

The `terminal.produced_output_effect` field is also closed. It must equal
`DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED` for `COMPLETED` and
`QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY` for `FAILED`. The latter applies
even when the failed receipt retains one or more exact output artifact refs.

The Evidence Packet `execution.authentication` block must remain
`UNAVAILABLE` or `PRESENT_UNAUTHENTICATED` under the current isolated kernel.
Successful `FleetServiceAuthStore` authentication is not, by itself, the
independently admitted execution trust root required for an `AUTHENTICATED`
scientific status.

### 3.4 Terminal receipt to outcome access and Evidence Packet carriers

| Terminal/authorization fact | Harness-v2 carrier |
|---|---|
| authorization exact bytes | stable authorization SHA-256 and byte length referenced by the terminal receipt and execution manifest |
| terminal exact bytes | `WorkerTerminalReceiptArtifact.outcome_access_receipt_ref` / `.artifact_ref`, accepted as the exact outcome-access receipt identity and later included in the packet artifact inventory |
| authorization preregistration digest | packet `claim_binding.preregistration_sha256` |
| authorization pre-outcome chain digest | the authorization-only canonical `cas_harness_v2.preregistration_chain.v1` identity with `outcome_access=null`; it is replayed structurally and is not copied into either later digest field |
| outcome-access sealed-pre-outcome digest | the distinct `cas_harness_v2.preregistration_pre_outcome_chain.v1` identity created by `PreregistrationChain.record_outcome_access` |
| final packet chain digest | packet `claim_binding.preregistration_chain_sha256`, computed from the final `cas_harness_v2.preregistration_chain.v1` identity after the outcome-access event is present |
| authorized run ID | packet `execution.run_id` |
| `worker_started_at` and `terminal_at` | packet `execution.started_at` / `completed_at`; `terminal_at` must equal outcome-access `execution_completed_at` |
| worker/executor provenance | packet `execution.executor_identity`, subject to the independent-identity caveat above |
| authorization plus terminal/artifact inventory | exact `execution.execution_manifest` artifact |
| verified callback/auth receipt artifact, if admitted | packet `execution.authentication.receipt` with `PRESENT_UNAUTHENTICATED`; no automatic status promotion |
| terminal outcome artifacts | packet `outcome_artifacts` and the appropriate scientific-evidence artifact references |
| failed or incomplete terminal state | retained run-registry record and negative evidence; it must not be represented as a favorable packet or silently excluded |

The public `load_worker_authorization` surface intentionally requires a
pre-outcome chain and remains forbidden after sealing. The terminal loader is
the narrow exception needed for immutable receipt idempotency: it privately
replays the exact authorization against the recomputed pre-outcome chain digest
and may accept an already sealed chain only when
`OutcomeAccessEvent.receipt == WorkerTerminalReceiptArtifact.artifact_ref` and
`OutcomeAccessEvent.execution_completed_at == terminal_at`. Any different
receipt reference, completion time, or chain binding fails closed. This does
not expose a public post-outcome authorization-loading capability and does not
permit new or changed terminal bytes after outcome access. The admitted dark
lifecycle/adapter tranche now authors that seal through the controller-only
route; the bridge's narrower sealed-safe replay port verifies the same retained
terminal afterward. A packaged reconciliation-report path now first replays the
strict per-run lifecycle and then binds its run head/artifact inventory to the
separately configured-scope lifecycle, context, Fleet-mapping, and bridge
report. Independent, provider-backed reconciliation that proves registry
completeness remains absent.

### 3.5 Admitted controller continuation envelopes

Three controller-only continuations are now exact, separate operations:

| Operation | Exact request schema | Required capability | Bounded effect |
|---|---|---|---|
| outcome seal | `cas_harness_v2.route_outcome_seal_request.v1` | `seal_outcome` | replays retained authorization/terminal facts, reserves one untrusted time observation, and records the exact outcome-access carrier |
| Packet attachment | `cas_harness_v2.route_packet_attachment_request.v1` | `attach_evidence_packet` | accepts Packet-v2 bytes plus Packet-specific dependency bodies only; server-owned chain, output, and terminal bodies are reloaded rather than resubmitted |
| explicit nonreporting | `cas_harness_v2.route_nonreporting_request.v1` | `record_nonreporting` | records a closed reason code and server-built negative/nonreporting envelope rather than manufacturing a favorable Packet |

The terminal response exposes the terminal receipt media type, byte length,
status, and terminal event digest needed by the exact outcome request. The
outcome response analogously exposes the outcome receipt media type, byte
length, outcome event digest, sealed-chain digest, and recorded untrusted time
needed by the next continuation. It does not expose the run nonce, lease token,
credential, retained chain bytes, output bodies, or internal lifecycle rows.

Outcome reservation is create-only and records the winning declared time plus
its source and untrusted assurance. Exact HTTP retries converge on that winning
reservation even when competing process-clock observations differ. Each
request still reconstructs a fresh local chain from retained server facts, so
this is not process/host-loss recovery, rollback resistance, or proof that no
earlier outcome access occurred.

After outcome access, a second create-only reservation arbitrates `PACKET`
versus `NONREPORTING`. It binds the exact request digest, dependency-plan
digest, parent lifecycle head, clock observation, planned final artifact, and
the closed nonreporting reason; Packet reservations require a null reason.
Finalization must echo those bindings and match the planned artifact and reason;
a losing or semantically changed branch cannot silently replace the winner.
Every new lifecycle event and complete replay must also preserve canonical
nondecreasing event time. After an event-first/index-second interruption, a
read may repair exactly one structurally verified pending successor; corrupt or
divergent successors fail closed. Packet and nonreporting events have exact
per-type detail shapes, and the complete indexed history plus reservations is
verified before any replay, append, repair-winner return, or fresh-success
return. A concurrent repair winner must index the exact pending event at the
winning sequence. Full verification checks each event record envelope; the
lifecycle, subject, nonce, and finalization envelopes; exact dependency and
profile bindings; and canonical event identities independently of untrusted
payload run IDs. A bounded fingerprint refresh makes stale reads, post-CAS
acknowledgements, simultaneous exact retries, and competing repairs converge
only on one fully verified stable tuple. Outcome and reporting reservations
enter that loop before existing-reservation replay or lifecycle-state inspection,
and each event record binds its exact tenant and canonical kind. This tested
compare-and-set and repair scope is local to the configured state substrate. Cross-host authority,
partial-write/orphan completeness, and independent ordering remain open.

Reconciliation retains
`cas_harness_v2.reconciliation_report_storage_wrapper.v2`. Its returned
receipt ID and SHA-256 identify the same wrapper bytes. That wrapper contains
the exact configured-scope report as an inner artifact and a separately hashed
strict-run binding covering the current lifecycle head, state, event count,
artifact inventory, and registry digest. The wrapper explicitly states that
snapshot atomicity, trusted time, off-registry execution absence, licensing,
and disclosure authority are not established.

The bridge does not calculate scientific metrics, choose threshold outcomes,
declare controls passed, or manufacture independent audit, replication, or
claim-review records. Those artifacts must come from their own admitted
implementations and identities.

## 4. State machine

The protocol state is monotone. Fleet and Harness state names remain distinct,
but the bridge permits only the transitions below.

This table is the target end-to-end integration state machine. The dark bridge
implements only its storage substate
`PERSISTING_RESEARCH_ONLY -> STORED_AND_REPLAYED_RESEARCH_ONLY`. The lower
lifecycle registry locally implements `AUTHORIZED`, `RUNNING`, five terminal
states, `OUTCOME_ACCESSED`, `PACKET_RECORDED`, and
`NONREPORTING_RECORDED`. The lifecycle service wires `SUCCESS`/`FAILURE`
terminalization plus typed server dispositions for `INDETERMINATE`, `REJECTED`,
and `EXPIRED`; the admitted worker adapter/router does not expose the latter
three paths.
Its `RUNNING` transition now invokes the exact process-local active-lease
validator through the admitted adapter and retains a digest-only lease fence.
The unavailable terminal-state and live/provider integration paths remain open
rather than being implied by the broader registry table.

| Protocol state | Required durable facts | Allowed next states |
|---|---|---|
| `UNBOUND` | preregistration chain and fleet assignment exist separately | `AUTHORIZED` or terminal `REJECTED_BINDING` evidence |
| `AUTHORIZED` | exact authorization carrier binds principal, chain, assignment, identities, run nonce, and local deadline | `RUNNING`, `EXPIRED_UNUSED`, or `REJECTED_BINDING` |
| `RUNNING` | one-use run authorization has been atomically consumed; admitted integration must also prove the exact lease generation is active | `TERMINAL_SUCCESS`, `TERMINAL_FAILURE`, or `TERMINAL_INDETERMINATE` |
| `EXPIRED_UNUSED` | authorization was not consumed before its application deadline | no execution transition; a successor requires a new job and authorization identity |
| `TERMINAL_SUCCESS` | exact terminal receipt, complete output accounting, and stable artifact identities | `OUTCOME_ACCESSED` and packet assembly |
| `TERMINAL_FAILURE` | exact failure receipt, complete negative facts, and any available failure artifacts | `OUTCOME_ACCESSED` only when outcomes were exposed; otherwise retained reconciliation |
| `TERMINAL_INDETERMINATE` | execution may have happened but the terminal outcome cannot be proven | quarantine and external reconciliation only; never automatic retry or success |
| `OUTCOME_ACCESSED` | exact outcome-access event seals the current pre-outcome chain and terminal completion | packet assembly; no amendment or second outcome-access event |
| `PACKET_RECORDED` | packet bytes, referenced bytes, terminal state, and event-bound local registry records reconcile; orphan/off-registry completeness remains open | independent audit/review only; no automatic claim promotion |
| `REJECTED_BINDING` | the mismatch/error and all available source identities are retained | corrected successor assignment only; never mutate the rejected carrier |

The current fleet state transition `queued|expired -> leased -> completed|failed`
is not sufficient by itself. In particular, a lease is not a prospective
Harness authorization, process-local `PreregistrationChain` state and one-host
SQLite are not independent WORM authority, and a completed fleet fragment is
not an Evidence Packet v2.

## 5. Error mapping

The bridge must map errors without losing the original class or turning missing
evidence into favorable evidence.

Private route handlers and an admitted packaged adapter now call the dark
lifecycle/bridge implementation for the bounded authorization, output,
consumption, terminal, outcome, Packet/nonreporting, and reconciliation paths.
Main still begins with a dark
service port and refuses enabled startup unless the exact packaged kernel,
adapter profile, shared state, immutable repository, and fleet-auth ports are
present. The HTTP statuses below describe that default-dark boundary and tested
adapter behavior; no provider-backed enabled startup has passed. The bridge
itself raises typed `ResearchWorkerBridgeBindingError`,
`ResearchWorkerBridgeConflict`, or `ResearchWorkerBridgePersistenceError` and
creates no HTTP or product result.

| Source error/fact | Protocol disposition | API effect |
|---|---|---|
| invalid/expired/revoked credential, stale timestamp, malformed or replayed callback nonce | callback authentication rejected | current generic `401`; do not reveal which credential check failed |
| valid credential with wrong tenant/audit/fleet/worker/capability | callback authorization rejected | current `403` |
| authentication storage unavailable | trust path unavailable | current `503`; never fall back to in-memory auth or customer Bearer identity |
| job/principal/preregistration/model/code/environment mismatch | `REJECTED_BINDING` | conflict/fail-closed response; no authorization carrier |
| expired lease or run authorization | `EXPIRED_UNUSED` when definitely unused | conflict; a new callback nonce cannot revive the run authorization |
| duplicate run-authorization consumption | replay rejection | conflict/authentication failure according to the admitted endpoint; no second execution |
| worker command timeout, nonzero exit, missing result, malformed result, or failed attestation | `TERMINAL_FAILURE` | preserve explicit error and missing outputs |
| provider/transport ambiguity after run consumption | `TERMINAL_INDETERMINATE` | quarantine; do not automatically rerun because doing so could create suppressed duplicate outcomes |
| exact terminal retry with a fresh HTTP callback nonce | return/reconcile the already stored immutable terminal identity and create/reconcile the separate authenticated acceptance record | idempotent terminal response only when every terminal byte identity is equal; the new POST attempt has its own nonce receipt |
| conflicting terminal retry | immutable conflict | reject and preserve both conflict metadata and the authoritative prior terminal identity |
| WORM write/index/re-read/receipt verification unavailable | storage authority unavailable | `503`/quarantine; no non-WORM fallback may claim the durable state |
| failed thresholds, controls, falsifiers, splits, audit, or replication | negative scientific evidence | packet remains loadable and ineligible/reported-negative as appropriate; never erase the run |

Free-form `error_message` text is retained as bounded evidence but is not the
protocol's sole machine error identity. The exact protocol carrier must also
include a closed error code/class so spelling changes cannot make conflicting
failures appear idempotent.

## 6. Nonce, lease, and retry rules

Three values serve different purposes and may never be aliased:

| Value | Issuer and scope | Consumption | Retention rule |
|---|---|---|---|
| callback nonce (`X-CAS-Service-Nonce`) | worker client; one credential and one exact HTTP attempt | atomically consumed after scope checks and bound to method/path/job/run/authorization/body identity | store only safe digest/provenance in the auth ledger; a terminal bridge submission additionally gets a separate acceptance wrapper/index, while nonterminal operations do not; it is forbidden in both worker carriers; a retry uses a fresh callback nonce |
| lease token | fleet executor; one exact active process-local lease generation | the admitted adapter passes it process-locally to the lifecycle's exact validator before consumption; the retained fence contains only its digest and generation facts | secret; never enter protocol carriers, packet artifacts, repository wrappers, logs, or responses after lease issuance; process-local lease state is not multi-host authority |
| `run_nonce.value_b64url` | lifecycle successor's default `secrets.token_bytes(32)` factory, or an injected and currently unattested callable; one proposed authorization/preregistration/job tuple | exact raw value is released once and same-host `StateStore` compare-and-swap admits one consumption | the value repeats in authorization and terminal carriers; only its digest is reserved before construction. Factory provenance is not attested, the strict carrier still says `EXTERNAL_REQUIRED_NOT_PROVIDED`, and replica/host-loss/independent authentication remain open |

The existing `fleet_service_nonce` compare-and-set proves callback replay
rejection for a configured `StateStore`, and the v2 receipt binds one exact
observed request. Separately, the lifecycle registry issues and consumes one
run nonce under its configured local backend. Neither proves that only one
experiment occurred outside the registry or that the registry survived host
loss. Reusing the callback nonce as a run nonce would make legitimate
multi-callback workers impossible and would still fail to record the complete
run lifecycle.

Idempotency is content identity, not repeated intent:

1. Creating the same authorization subject with the same exact carrier bytes
   may return the existing identity.
2. The same subject with different bytes is an immutable conflict.
3. Consuming an authorization is one-use even when the caller presents fresh
   callback credentials and a fresh callback nonce.
4. Before or after an exact outcome seal, an exact terminal retry authenticated
   with a fresh HTTP callback nonce may
   return the stored terminal receipt and create/reconcile a distinct
   per-attempt acceptance record; it does not change the terminal bytes.
5. A terminal retry with any different status, output accounting, mode,
   artifact identity, completion time, or error code is a conflict.
6. A failed or indeterminate run remains in the configured registry view and cannot be
   hidden by assigning its job ID or run nonce to a new favorable packet.

There are two different replay questions. Repeating a raw HTTP POST with the
same callback nonce is transport-attempt replay and is rejected before the
bridge because that nonce is durably one-use. Retrying the same immutable
terminal bytes after authenticating a new POST attempt with a fresh callback
nonce is terminal idempotency: the stable terminal wrapper converges on the
same content identity, while the acceptance wrapper/index binds the new full
server-authored nonce receipt to that terminal identity. A different terminal
status, byte sequence, output partition, artifact reference, completion time,
or error remains an immutable conflict. Neither path may silently author a
replacement carrier.

The bridge now has an explicit sealed-safe authorization replay port. It can
verify exact authorization and terminal bytes after sealing only when the
outcome event binds the same receipt and completion time; its public
authorization loader remains closed after outcome access. This closes the
previous pre-outcome-only implementation defect locally. It does not establish
an admitted post-seal HTTP service, independent replay, or live execution, so
`G5-ENGINEERING-001` remains open.

## 7. Time assurance

All current timestamps are application-clock facts unless a field is bound to
an independently verified trusted-time receipt.

`X-CAS-Service-Timestamp` is an integer epoch value used only for a bounded
freshness comparison in `FleetServiceAuthStore.authenticate`. `created_at`,
`updated_at`, `lease_expires_at`, fleet heartbeat times, authorization times,
execution start/completion, outcome access, and packet creation are currently
generated or checked by application processes. The strict Harness loaders
prove syntactic UTC form and declared ordering; they do not prove that the
clock was correct or that an event happened at that external time.

Within that declared, untrusted application-time profile, the exact loaders
still fail closed on internal contradictions: authorization issuance must
follow the latest preregistration/amendment; expiry must follow issuance;
worker start cannot precede issuance; terminal time cannot precede worker
start; and terminal time cannot exceed authorization expiry. These checks prove
consistency of the declared timeline, not external chronology.

Therefore:

- callback freshness must not be described as trusted time;
- lease expiry must not establish prospective preregistration;
- process-local ordering must not establish absence of prior outcome access;
- an S3 retention deadline proves only the provider-observed Object-Lock
  property represented by its exact receipt, not the truth of earlier worker
  timestamps; and
- `G5-TRUST-001` remains open until every relevant event is bound to an
  admitted, independently verified time authority.

## 8. Reuse of the existing Object-Lock repository

The Gate 5 integration should reuse, not duplicate, the current
`EvidencePacketRepository` and `S3ObjectLockPacketBackend` implementation for
private immutable persistence where their contract fits. That code already
separates immutable S3 bytes from a tenant-keyed `StateStore` index, uses
conditional creation, binds exact S3 `VersionId`, re-reads bytes, verifies
content hash, checks Object-Lock mode and retention deadline, and reconciles
concurrent identical writes while rejecting conflicting bytes.

Reuse has four constraints:

1. The existing `put_packet` contract canonicalizes a mapping and requires a
   `trace_id`. It is not automatically an opaque exact-byte repository for a
   preregistration, authorization, terminal receipt, or outcome-access carrier.
   A typed adapter must either preserve the exact admitted bytes or bind an
   explicit canonical envelope to the inner raw-byte digest and length.
2. Every operation must use the authenticated principal's `tenant_id` and the
   private Gate 5 namespace. A caller-supplied tenant or public namespace is
   forbidden.
3. The durable index and append chain are searchable integrity structures, but
   they do not independently prove trusted time, execution identity, complete
   run registration, or scientific truth.
4. Local/disabled storage, an object URL, a hash, a prose retention statement,
   or an unverified receipt can never be called WORM. Failure to obtain and
   revalidate the exact structured receipt must stop the durable transition.

The intended private storage sequence is:

1. store the exact preregistration/chain snapshot envelope;
2. create-only store the authorization carrier and register the run subject;
3. atomically consume the run authorization before execution;
4. create-only store the terminal carrier, including failure or indeterminate
   evidence;
5. store and seal the outcome-access carrier when outcomes become accessible;
6. create-only store Evidence Packet v2 and reconcile it against the configured
   run index; and
7. re-read and verify every exact version and structured retention receipt
   before reporting only the finite receipt-backed retention claim.

This sequence is a target contract, not a claim that `G5-TRUST-002` or
`G5-TRUST-004` is already closed.

### 8.1 Current dark persistence bridge

`ResearchOnlyHarnessV2WorkerBridge.persist_terminal_callback(...)` is the
bounded implemented seam in this candidate. Its arguments are exact
authorization bytes, exact terminal-receipt bytes, the exact pre-outcome
`PreregistrationChain`, and a server-derived
`FleetServiceAuthenticatedCallback`. Its constructor also requires an injected
`load_fleet_job_snapshot(tenant_id, audit_id, fleet_id, job_id)` port that must
return the exact `FleetJobSnapshot` type, plus an injected
`verify_authenticated_callback` port that re-reads the durable callback-nonce
row and an explicit sealed-safe authorization replay port for terminal
verification. The root Harness-v2 loaders are injected because the API package and
repository-root research kernel do not yet share a proven installation
boundary; the bridge does not copy or weaken the strict schemas. This injection
is nevertheless an unresolved deployment trust boundary. The bridge's
protocol/duck-typing checks can prove that returned objects retain the submitted
bytes and required fields, but they cannot attest that the callables came from
the reviewed root loader implementation or that their carrier classes have
strict root-kernel provenance. Both durable wrappers therefore fix
`loader_assurance=INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED`.

Before persistence, the bridge:

1. re-verifies the identical `FleetServiceAuthenticatedCallback` against its
   exact durable nonce row using the injected verifier;
2. snapshots and strict-loads both exact carriers, using the sealed-safe replay
   loader when the chain already has an outcome-access event;
3. verifies the loaders retained the submitted bytes, byte lengths, IDs, and
   uppercase SHA-256 identities;
4. requires `submit_receipt` in the principal capability tuple;
5. loads the current server-derived job snapshot under principal tenant/audit/
   fleet scope and authorization `job_id`;
6. compares the complete authorization `execution_mapping` byte-for-value
   projection with `FleetJobSnapshot.execution_mapping()`, including ordered
   methods/outputs and the lease model tuple;
7. compares authorization `audit_id`, `fleet_id`, and `assigned_worker_id` with
   the server-derived principal;
8. compares the complete durable nonce-receipt scope -- credential, tenant,
   account, audit, fleet, worker, and ordered capabilities -- with the exact
   authenticated principal;
9. requires the terminal receipt to bind the exact authorization SHA-256; and
10. keeps every callback-nonce fact outside both strict worker carriers.

`tenant_id`, `account_id`, and `credential_id` remain server-side storage
scope; they are not accepted as caller-selected strict-envelope claims. The
bridge reads a server snapshot rather than a worker-supplied `FleetJob`, and it
never receives or retains the lease token. It also does not translate the
legacy `FleetJobReceiptRequest`; exact terminal bytes must already exist.

`FleetJobSnapshot` carries the exact fleet/job/audit/assigned-worker IDs,
layer range, shard ID, ordered method/output tuples, model ID/revision, manifest
path/digest, and execution mode. Its lease manifest digest remains the exact
lowercase 64-hex value used by `FleetJob` and the strict authorization. The
bridge separately computes an uppercase canonical SHA-256 of the complete
snapshot mapping for its durable index and wrapper; that outer index digest
does not rewrite the inner lease value.

For stable terminal bytes, the bridge reserves a create-only tenant index under
`cas_harness_v2_worker_bridge_index` with state
`PERSISTING_RESEARCH_ONLY`, then writes a
`cas_harness_v2.worker_bridge_storage.v1` wrapper through the existing
`EvidencePacketRepository` in namespace
`research-only/harness-v2/worker-terminal`. The wrapper is explicitly labeled
`REPOSITORY_WRAPPER_NOT_AN_EVIDENCE_PACKET`. It carries base64 snapshots plus
exact hash/length identities for both source carriers, server scope, current
server FleetJob snapshot, loader-assurance caveat, and fixed non-authority
fields. It contains no callback-nonce fact. After that object reloads and strict
carrier replay succeeds, the bridge creates a second per-POST acceptance trace
and tenant index under `cas_harness_v2_worker_acceptance_index`, then writes
`cas_harness_v2.worker_callback_acceptance.v1` in
`research-only/harness-v2/worker-acceptance`. This separate wrapper points to
the exact terminal-storage identity and binds the complete authenticated scope,
the full server-authored `FleetServiceNonceReceipt`, the current server job
snapshot, fixed untrusted-time semantics, and the same loader-assurance caveat.
It is labeled `SERVER_CALLBACK_ACCEPTANCE_NOT_AN_EVIDENCE_PACKET`.

After terminal Object-Lock storage, the bridge reloads the exact repository
version, decodes and compares the original source bytes, replays both injected
strict-loader ports, stores and reloads the acceptance wrapper, and only then
finalizes both indices as `STORED_AND_REPLAYED_RESEARCH_ONLY`. Before or after
an exact outcome seal, terminal retries with fresh HTTP nonces converge on one terminal
object and distinct nonce-keyed acceptance records. A different
authorization/receipt binding
under the same authorization ID, or a different binding under the same
acceptance nonce identity, is an immutable conflict. A write, reload,
structured receipt, strict replay, index, or finalization failure remains
persisting/quarantined and cannot be returned as terminal success.

`ResearchWorkerBridgeResult` permanently reports
`execution_authentication=NOT_ESTABLISHED`, `trusted_time=NOT_ESTABLISHED`,
`run_nonce_issuance=NOT_ESTABLISHED`, `scientific_status=NOT_ESTABLISHED`,
`license_status=NOT LICENSED`, `product_status=NOT_ESTABLISHED`, and
`disclosure_authority=NOT_ESTABLISHED`. Its terminal field is explicitly
`declared_terminal_status`: it repeats only what the strict terminal carrier
declared and never upgrades that value to authenticated execution or scientific
assessment. It is a storage result, never a run, science, product, canon,
license, authorship, submission, or disclosure verdict.

The bridge alone still does not consume the strict `run_nonce`, create a full
lifecycle registry, call `record_outcome_access`, assemble
`EvidencePacketArtifact`, or ingest referenced output bodies. The surrounding
dark lifecycle successor supplies local versions of those functions while
retaining the bridge's narrow storage result. The packaged adapter now supplies
the bounded Fleet snapshot and active-lease seams, but independently attested
root-loader provenance, provider-backed startup, live Object-Lock authority,
and an authorized live route remain open.

### 8.2 Dark prospective lifecycle and HTTP boundary

`DurableProspectiveRunLifecycle` and `DarkHarnessV2LifecycleService` form the
new successor around the bridge. The word `Durable` is backend-qualified: with
`SqliteStateStore` the current evidence is close/reopen persistence for one
database file and compare-and-swap arbitration between two independent
connections to that file. It does not test a process crash, OS restart, power
loss, filesystem fault, or storage-device failure, and it explicitly does not
mean replication, host-loss survival, independent attestation, or WORM
authority.

The local transition sequence is:

1. create-only reserve the subject and the digest of a fresh run nonce before
   calling the injected authorization builder. The default factory is
   `secrets.token_bytes(32)`, but a caller can inject another callable and the
   current runtime does not attest factory provenance;
2. retain/reload the exact authorization wrapper, finalize its immutable
   binding, create the `AUTHORIZED` genesis event, and return the raw nonce only
   on the winning issuance call;
3. have the admitted adapter pass the raw lease capability process-locally to
   `validate_active_fleet_job_lease`, verify the exact current Fleet
   job/worker/model/token/expiry generation, and atomically move
   `AUTHORIZED -> RUNNING`. The server-built consumption-attempt envelope
   retains only safe digests and generation facts, never raw run, lease,
   callback, or credential secrets;
4. retain output bodies only while `RUNNING`, then have the lifecycle service
   accept a strict terminal carrier only by reloading the prior authorization.
   The HTTP route treats the terminal request body as opaque, while the admitted
   adapter invokes the strict lifecycle/bridge loaders and preserves the exact
   bound intake receipt through terminal persistence;
5. map the strict terminal carrier to `SUCCESS` or `FAILURE`, then reserve one
   stable untrusted outcome-access time before sealing the chain. The lower
   lifecycle registry and service also support typed server dispositions for
   `INDETERMINATE`, `REJECTED`, and `EXPIRED`, but the admitted worker
   adapter/router exposes no path that records those three states;
6. for a successful run, strict-load Packet v2, require exact terminal-output
   references, validate every supplied transitive body, rebuild the artifact
   registry, and run the kernel verifier before the first repository write.
   Repository writes then occur sequentially, so a dependency or Packet-storage
   failure after validation can leave earlier wrappers outside the lifecycle
   event chain. For a wired failed run, create a typed server-built
   `cas_harness_v2.nonreporting.v2` envelope instead of fabricating a Packet v2.
   Indeterminate nonreporting awaits the missing service path; and
7. replay the event hash chain and every event-bound authorization,
   consumption, terminal, outcome, and packet/nonreporting wrapper, together
   with packet-referenced dependency/output bytes, during tenant
   reconciliation. The service does not enumerate orphan or losing wrapper
   writes, nor every output retained while a run remains `RUNNING`.

Builder interruption is quarantined in the registry and
reconciliation-visible; it cannot recover or reissue the raw nonce. Exact
event-bound retries converge, conflicting bytes or operation facts fail, wired
failure/nonreporting evidence stays visible, and a packet cannot invent missing
scientific evidence. Registry-level indeterminate/rejected/expired states and
postvalidation orphan-wrapper enumeration remain unwired obligations. For an
entirely empty tenant view, registry reconciliation returns
`has_registered_runs=false`, all record counts zero, and
`all_runs_reporting_disposed=false`; an issue-free structural result over that
empty view does not prove that no off-registry execution occurred. Repository storage uses a
typed canonical wrapper containing base64 inner bytes plus their digest/length.
The current synthetic Object-Lock receipt applies to that wrapper object, not
the inner artifact directly, and therefore cannot establish independent WORM.

The private router defines exact-body handlers under
`/api/cas-harness/audit/distributed/session/{audit_id}/fleet/v2/job/{job_id}`.
It is default-false, excluded from OpenAPI, admits no query/compressed/oversized
or wrong-media-type body, has no customer-JWT fallback, and binds each consumed
callback nonce to the exact request method/path/job/run/authorization/body
identity. The admitted packaged adapter establishes strict terminal semantics,
transitive bound-intake verification, exact active-lease validation, joint
`job_id == subject_id == authorization_id` identity, and a controller-only
reconciliation-report path. Main initializes its service port to `None` and
fails enabled startup unless the byte-verified packaged kernel, exact admitted
adapter profile, shared state, immutable repository, and fleet-auth ports are
present. Local construction and startup-boundary tests pass, and the explicit
controller outcome/Packet/nonreporting adapters are regression tested. No
provider-backed enabled startup has passed. Thus the route remains default-
dark, unavailable as a live/product route, and not authorized for execution.

## 9. Fail-closed invariants

The root loaders, and the bridge only within its explicitly stated
injected-port boundary, must enforce all of the following:

- Exact schema keys only; no ignored extension fields.
- Root-kernel loaders require exact carrier types; no subclass or mapping
  look-alike bypass is accepted there. The bridge checks required attributes
  and exact bytes returned by injected ports but cannot attest their
  implementation or carrier-type provenance; that remains OPEN.
- Fresh replay of snapshotted bytes before any public state read.
- Exact claim, preregistration, protected-design, chain, audit, fleet, job,
  worker, model, revision, code, environment, assignment, and terminal binding.
- No caller-selected tenant, account owner, authority, trust root, reviewer,
  license, product, disclosure, or canon status.
- No customer JWT as a worker credential when service authentication is
  enabled; no in-memory authentication fallback when durable storage fails.
- No callback nonce reuse and no substitution of callback nonce, lease token,
  and run-authorization nonce.
- No callback nonce in authorization or terminal carrier bytes; every accepted
  route attempt has a bound durable authentication row, while only a terminal
  attempt traversing the bridge has the separate acceptance wrapper/index.
- No retained lease secret.
- No `dry_run_control_plane` receipt represented as real model execution or
  scientific evidence.
- No unknown, duplicated, overlapping, or silently missing outputs.
- No success carrier without exact result/artifact identities; no failure
  carrier without a bounded failure fact.
- No automatic retry after an indeterminate consumed run.
- Exact-terminal-byte idempotency across fresh authenticated HTTP nonces only;
  raw POST nonce replay and byte- or semantic-conflicting terminal retries fail.
- Negative, null, missing, failed, and indeterminate evidence remains visible
  when it is represented in the configured lifecycle record kinds. This does
  not claim complete discovery of off-registry executions, postvalidation
  orphan wrappers, or pending outputs.
- No packet assembly before outcome access seals the exact current chain.
- No post-outcome amendment.
- No packet hash, callback principal, fleet merge, or Object-Lock receipt may
  mint authentication, scientific eligibility, independent review, ACCEPT,
  canon, license, product, or disclosure authority.

## 10. Source and test evidence

The following existing tests are directly relevant but prove only their stated
local scope:

| Evidence | What it currently proves | What it does not prove |
|---|---|---|
| `tests/cas_harness_v2/test_research_control_kernel.py` | strict preregistration/chain/outcome-access/packet structure, exact-byte artifact identities, failure-preserving criteria, and fixed Ring-4 governance | live worker integration, durable trust, authenticated execution, external review, or science |
| `tests/cas_harness_v2/test_gate5_verifier_redteam.py` | adversarial loader/carrier/mutation boundaries admitted by the Gate 5 verifier | a trusted host, independent attestation, or live execution |
| `tests/cas_harness_v2/test_worker_protocol.py` | 35 focused tests plus 45 subtests cover exact authorization/terminal loading, current FleetJob-shaped mapping, lease model/preregistration equality, ordered output accounting, rejection of transport-nonce fields, structural run-nonce caveat, application-time bounds, completed/unassessed and failed/quarantined-partial effects, exact sealed-outcome replay constraints, fresh replay, collisions, prospective authorization construction, strict completed/failed terminal-receipt building and replay rejection, and immutable governance | launcher authorship, independently authenticated durable run consumption, trusted time, callback identity, Object Lock, live execution, or science |
| `noetic-compass-scaffold/noetic-compass/tests/test_fleet_service_auth.py::test_nonce_replay_and_concurrent_duplicates_have_exactly_one_winner` | one callback nonce has one successful durable compare-and-set consumer under local test storage | one-use research-run authorization or host-loss behavior |
| `noetic-compass-scaffold/noetic-compass/tests/test_fleet_service_auth.py::test_expiry_revocation_and_consumed_nonce_survive_sqlite_restart` | credential/revocation/callback-nonce state remains after closing and reopening a local SQLite file | process-crash, OS-restart, power-loss, shared-host loss, trusted time, or experiment-registry completeness |
| `noetic-compass-scaffold/noetic-compass/tests/test_fleet_service_auth.py::test_authenticated_callback_exposes_exact_durable_nonce_receipt_after_restart` | safe callback receipt re-read after close/reopen binds nonce row schema, ID, credential, uppercase digest, byte length, parent/trace scope, and local-file persistence | crash/OS-restart/power-loss durability, run-nonce issuance/consumption, trusted time, or execution attestation |
| `noetic-compass-scaffold/noetic-compass/tests/test_fleet_service_auth.py::test_tenant_audit_worker_and_capability_scopes_fail_closed` | callback tenant/audit/worker/capability mismatches are rejected | executor personhood, scientific role independence, or trusted execution |
| `noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_fleet_worker_daemon.py::test_service_credential_headers_are_scoped_and_use_fresh_nonces` | worker sends scoped headers and a fresh callback nonce per HTTP attempt | API-side trusted time or a run nonce |
| `noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_fleet_worker_daemon.py::test_command_executor_uses_only_lease_bound_identity_and_attested_result` | the command receives lease-bound model identity and rejects ambient substitutions | independently attested model execution or GPU numerical semantics |
| `noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_fleet_worker_daemon.py::test_fragment_ref_matches_api_fleet_executor_builder` | worker/API fragment-ref algorithms agree on tested mappings | immutable retention, semantic equivalence, or packet completeness |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_fleet_executor.py` | bounded fleet preparation, lease, receipt, fragment, model-attestation, merge, and readiness behavior | the Harness-v2 authorization/outcome-access protocol or science |
| `noetic-compass-scaffold/noetic-compass/tests/test_evidence_packet_object_store.py::test_packet_bytes_and_index_survive_restart_and_second_replica` | exact packet/index persistence over the test backend across restart/replica reconstruction | a live provider receipt or Harness-v2 carrier adapter |
| `noetic-compass-scaffold/noetic-compass/tests/test_evidence_packet_object_store.py::test_two_replicas_concurrently_create_one_packet_and_one_index` | concurrent identical packet creation converges in the tested repository | complete run registry or trusted external ordering |
| `noetic-compass-scaffold/noetic-compass/tests/test_evidence_packet_object_store.py::test_fleet_merge_publication_is_retry_and_concurrency_idempotent` | tested fleet publication retries converge without conflicting packet bytes | authorization consumption, negative-run completeness, or claim authority |
| `noetic-compass-scaffold/noetic-compass/tests/test_evidence_packet_object_store.py::test_packet_verify_detects_remote_byte_tampering` | remote byte drift from the durable index is detected | semantic correctness or an independent trust root |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_worker_bridge.py` | focused tests cover injected root-loader behavior; exact stable-carrier storage/reload; transitive bound-intake revalidation; separate callback acceptance and current FleetJob snapshot binding; same-terminal-byte idempotency across fresh nonces; nonce replay rejection; restart and concurrency convergence; scope/job substitutions; pending-on-Object-Lock-failure; sealed-safe retry; and no default loader or live route authority | an enabled live API route, independently attested loader provenance, provider-backed startup, trusted time, live S3/provider evidence, or science |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_run_lifecycle.py` | prospective reservation before nonce-bearing construction, raw nonce release once, same-file SQLite close/reopen and two-connection compare-and-swap behavior, one-use transitions, negative/nonreporting states, tamper detection, and tenant-visible reconciliation | crash/OS-restart/power-loss durability, host-loss or multi-host authority, attested nonce-factory provenance, WORM, absence of off-registry execution, or science |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_lifecycle_service.py` | exact wrapper reload, server-built consumption/nonreporting envelopes, retained output bodies, active-lease validation, sealed-safe terminal replay, outcome reservation, pre-write strict Packet-v2/transitive-artifact verification, event-bound local reconciliation, and preserved bridge failure classes | atomic multi-object Packet storage, absence of postvalidation orphan wrappers, wrapper-independent Object-Lock authority, trusted time, provider-backed execution, or science |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_worker_protocol_routes.py` | default-dark/OpenAPI-hidden routing, exact request-bound callback nonce rows, opaque-body media/size limits, no JWT fallback, and fail-start without an admitted service | provider-backed startup, reachable live execution, authenticated model execution, or product/public authority |
| `noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_worker_protocol_adapter.py`, `test_cas_harness_v2_reconciliation_report.py`, `test_cas_harness_v2_fleet_snapshot_loader.py`, and `test_cas_harness_v2_packaged_mirror.py` | exact packaged-adapter admission, issuance/current Fleet snapshot separation, joint identity, active-lease and terminal-intake binding, lifecycle replay, controller reconciliation reports, and byte-identical packaged kernel provenance within local tests | a joined provider-backed application startup, trusted time, independent WORM authority, live experiment, license, disclosure, canon, or product route |

Candidate-specific worker-protocol and bridge tests must additionally prove:

1. exact successful field mapping from principal, preregistration chain, and
   fleet job into the authorization carrier;
2. rejection of every single-field tenant/audit/fleet/job/worker/model/revision/
   manifest/mode/assignment/chain substitution;
3. exact success and failure terminal mappings;
4. preservation of the exact ordered produced/missing partition on failure,
   with every produced failure artifact quarantined as partial negative
   evidence;
5. rejection of unknown/overlapping outputs, mode drift, conflicting receipt,
   stale lease, wrong principal, and wrong chain;
6. callback-nonce/run-nonce/lease-token separation, strict-carrier transport
   nonce rejection, full acceptance-receipt scope, and secret absence;
7. same-terminal-byte idempotency across fresh HTTP nonces, per-attempt
   acceptance identity, raw nonce replay rejection, and conflicting-terminal
   retry rejection;
8. declared-time ordering without any trusted-time claim;
9. Ring-4 governance invariance and absence of enabled/admitted live, public,
   product, or disclosure routes;
10. authoritative Gate 5 manifest/verifier inclusion without changing the
    fixed open status; and
11. explicit non-attestation of injected loader provenance plus rejection of
    any claim that referenced output-artifact bodies were ingested or replayed.

Passing those tests can advance only the bounded mapping portion of
`G5-ENGINEERING-001`. Independent reproduction, authenticated and
host-loss-resistant run authority, trusted time, independent WORM binding,
proof that reconciliation covers every execution, live execution, and all
scientific/governance obligations remain separate.

## 11. Complete remaining Gate 5 OPEN obligations

This list is source-bound to the 25 open criteria in
`GATE5_REVIEW_MATRIX_v0.1.json`. A protocol candidate must not remove, rename,
or imply closure of any item without criterion-specific evidence and review.

| Criterion | Disposition | Remaining obligation after this bounded protocol draft |
|---|---|---|
| `G5-TRUST-001` | `OPEN_ENGINEERING` | Integrate and independently verify trusted time and bind every relevant event to an authenticated time receipt. Application freshness and declared UTC ordering are insufficient. |
| `G5-TRUST-002` | `OPEN_ENGINEERING` | Move the locally wrapped authorization/consumption/terminal/outcome/packet-or-nonreporting sequence under live independently controlled append-only/WORM authority; test rollback, replica, and host loss; bind independent verification receipts to inner exact bytes as well as wrappers. |
| `G5-TRUST-003` | `OPEN_ENGINEERING` | Replace the same-host server-nonce/SQLite candidate with an admitted, independently authenticated run authority whose atomic one-use consumption survives concurrency, replay, replicas, and host loss; keep it distinct from transport callback replay protection. |
| `G5-TRUST-004` | `OPEN_ENGINEERING` | Prove the tenant-visible lifecycle registry is complete against every authorized and executed run, amendment, failure, indeterminate outcome, packet, and nonreporting event across hosts; add independent anti-selective-reporting reconciliation. |
| `G5-TRUST-005` | `OPEN_GOVERNANCE` | Admit and independently audit a non-caller-selected execution trust root, signing policy, key custody, scope, rotation, revocation, and exact receipt verification. |
| `G5-TRUST-006` | `OPEN_GOVERNANCE` | Independently verify person, affiliation, conflict, qualification, organizational independence, authorization, and signing controls for executor, auditor, replication, and reviewer roles. |
| `G5-INTEGRATION-002` | `OPEN_ENGINEERING` | Close Gate 4 through its own semantic, scientific, independent-review, governance, and disclosure authorities, then bind an authorized successor without retroactively promoting this candidate. |
| `G5-ENGINEERING-001` | `OPEN_ENGINEERING` | Independently reproduce and provider-start the packaged root-kernel/lifecycle adapter, connect the admitted outcome/Packet/nonreporting tranche plus the remaining terminal-disposition and outcome-finalization-intent paths to an authorized live worker lane, then independently red-team the exact message, artifact, error, nonce, time, identity, persistence, and retry mappings. The tested default-dark adapter is a bounded software candidate, not closure. |
| `G5-ENGINEERING-002` | `OPEN_ENGINEERING` | Bind transient/dynamic import history and executed bytes; complete standard-library/test/native/descendant closure; cover files absent from distribution records; create an independently verified immutable snapshot; address privileged ABA and loader-alias races; independently reproduce and attest the candidate; compare admitted GPU outputs. |
| `G5-ENGINEERING-003` | `OPEN_SECURITY` | Remediate or explicitly disposition six vendor-confirmed/fix-deferred findings; reconcile the `dpkg` scanner/vendor conflict; retain scanner database/process evidence; independently rebuild/reproduce; run the admitted exact GPU loader/hook contract; obtain an independent security receipt. |
| `G5-ENGINEERING-005` | `OPEN_ENGINEERING` | Define typed artifact semantics, derivation/provenance identities, cross-run registry rules, and independent adjudication for byte-different semantic duplicates and relabeling. |
| `G5-ENGINEERING-006` | `OPEN_GOVERNANCE` | Admit a downstream authorization policy, inventory every `PacketAssessment` consumer, and independently prove that evidence states cannot mint capabilities or status changes. |
| `G5-SCIENCE-001` | `OPEN_EXTERNAL_VALIDATION` | After all pre-execution gates and explicit authorization, complete one exact-revision private Harness-v2 live experiment through the admitted protocol and preserve the full run without status promotion. |
| `G5-SCIENCE-002` | `OPEN_EXTERNAL_VALIDATION` | Obtain and resolve an independent statistical design and power-analysis review against stable artifact hashes before run authorization. |
| `G5-SCIENCE-003` | `OPEN_EXTERNAL_VALIDATION` | Execute the frozen matched-taxonomy, wrong-layer, clean-null, and selectivity controls; preserve failures; obtain independent numerical/scientific review before causal wording. |
| `G5-SCIENCE-004` | `OPEN_EXTERNAL_VALIDATION` | Commission a clean-room independent numerical implementation and reconcile every reported value and discrepancy against stable artifacts. |
| `G5-SCIENCE-005` | `OPEN_EXTERNAL_VALIDATION` | Complete and independently audit the held-out replication without modifying the result-bearing design or suppressing disagreement. |
| `G5-SCIENCE-006` | `OPEN_EXTERNAL_VALIDATION` | Conduct independent construct, causal-design, alternative-explanation, robustness, and scope review; retain noncausal private wording unless established. |
| `G5-SCIENCE-007` | `OPEN_EXTERNAL_VALIDATION` | Authenticate and independently review identity, affiliation, conflicts, custody, and methodological independence for all execution/audit/review roles. |
| `G5-SCIENCE-008` | `OPEN_EXTERNAL_VALIDATION` | Commission and resolve independent scientific, statistical, security, causal, and exact claim-language reviews against stable hashes. |
| `G5-SCIENCE-009` | `OPEN_EXTERNAL_VALIDATION` | Define the production numerical policy and independently reproduce eager/compiled, autocast/non-autocast, repeat-run, GPU/device, and production-hook cases under the digest-bound environment. |
| `G5-HISTORY-003` | `OPEN_ENGINEERING` | Recover additional historical dependencies/fixtures only through separately approved exact-source inventory; preserve the four model-free and 31 V1-worker failures; do not block v2 repair on historical executability. |
| `G5-GOV-001` | `OPEN_GOVERNANCE` | Evaluate and evidence every current production gate separately. Research protocol or science evidence cannot infer production readiness. |
| `G5-GOV-002` | `OPEN_GOVERNANCE` | Keep Gate 5 artifacts and claims held until explicit scoped owner and qualified-counsel authorization covers legal, patent, privacy, disclosure, and claim language. |
| `G5-GOV-003` | `OPEN_ENGINEERING` | After bytes and rights stabilize, produce and independently replay a private reproducibility package before any disclosure-filtered derivative is considered. |

## 12. Candidate disposition

The worker-protocol binding is viable as a bounded Gate 5 engineering
successor because it reuses current exact-byte Harness carriers, existing
tenant/audit/worker service authentication, existing model-bound fleet leases,
and the existing private Object-Lock repository rather than creating parallel
identity, nonce, or storage systems.

Its honest effect is narrower than Gate 5 closure: the current code and local
adversarial tests establish one explicit fail-closed bounded mapping between
the worker and kernel. Manifest rebinding, independent review, provider-backed
startup, and live authorization remain unfinished. The candidate cannot
establish independently authenticated or host-loss-resistant one-use research
execution, trusted time, WORM ordering, registry completeness beyond the
configured local store, authenticated science, external validation, license,
product readiness, canon, or disclosure authority.

The Gate 5 structural verifier can bind exact bytes, schemas, required status
language, and local regression outcomes. It cannot authenticate the substantive
truth of documentation or data, validate scientific interpretation, or turn a
structurally complete Packet into established science.

The `$107.00` RunPod balance is user-reported; no provider billing ledger or
balance receipt was inspected, no RunPod or paid job was launched, retained
local GPU provider calls were zero, and known spend for this tranche is `$0.00`.
No RunPod execution or funding action is required to author or locally verify
this protocol candidate. Any admitted scientific GPU job remains prohibited
until the pre-execution engineering, security, trust, protocol-freeze, budget,
and explicit-authorization gates are satisfied.
