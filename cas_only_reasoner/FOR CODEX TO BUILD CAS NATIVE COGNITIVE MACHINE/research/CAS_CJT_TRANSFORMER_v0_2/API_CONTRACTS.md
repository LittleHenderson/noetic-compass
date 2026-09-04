# Neural CJT v0.2 API contracts

Status: `IMPLEMENTED AND COVERED BY PUBLIC API TESTS`

The package root provides lazy public exports. Typed contracts can be imported
without importing PyTorch or the frozen `casformer` dependency. Key surface
members and the documented entry-point signatures are checked by:

- `tests/test_public_api.py::test_version_and_declared_public_surface_are_stable`
- `tests/test_public_api.py::test_top_level_exports_are_the_objects_owned_by_their_modules`
- `tests/test_public_api.py::test_documented_entry_point_signatures_are_visible_at_package_root`
- `tests/test_public_api.py::test_lightweight_package_import_does_not_require_casformer`

## Core typed records

The main immutable wire records are available from `cas_cjt`:

```python
CausePacket
BiasState
CandidateEffect
PublishedEffect
OperationContract
VerifierReceipt
RepairFrame
RepairOutcome
StateUpdateIntent
ModelUpdateIntent
MemoryWriteIntent
CommitReceipt
PhaseRecord
TickTrace
TensorArtifactRef
```

Their JSON form rejects unknown or malformed fields through the bundled Draft
2020-12 schema. Authoritative JSON rejects floating-point values; neural
tensors live in content-addressed artifacts with dtype, shape, encoding, byte
count, and SHA-256 references.

## Neural and routing plane

```python
NeuralCJT(config)

NeuralCJT.forward(
    x,
    control,
    *,
    operation_id,
) -> NeuralCJTProposal

CASOhmRouter(compute_policy=None)
CASOhmRouter.route(inputs) -> CASOhmRoutingResult
```

`NeuralCJTProposal` contains a non-authoritative candidate tensor, proposed
Bias delta, execution mask, selected operation registration, and neural
telemetry. Neither class has a durable-store, verification, publication, or
commit method.

`CASOhmRoutingResult` keeps the candidate/effective masks, resistance,
conductance, current, relative flow allocation, attention allocation, total
current, and predeclared compute plan separate.

## Operation registry

```python
RegisteredOperationBank(config)

RegisteredOperationBank.register_operation(
    registration,
    module,
) -> OperationRegistration

RegisteredOperationBank.bind_contract(
    contract,
) -> OperationRegistration
```

An extension must use a unique non-canonical operation ID, relation index,
contract ID, and module instance. It cannot execute until its exact typed
`OperationContract` is bound. The built-in identities cannot be replaced.

## Network plane

```python
NeuralCJTNetwork(
    config,
    node_specs,
    *,
    topology=(),
)

NeuralCJTNetwork.select_candidates(cause) -> tuple[str, ...]
NeuralCJTNetwork.forward_node(cjt_id, x, control) -> NeuralCJTProposal
NeuralCJTNetwork.parameter_names_for_node(
    cjt_id,
    *,
    include_engine=False,
    include_bias_head=False,
) -> tuple[str, ...]
```

`select_candidates` performs deterministic operation and directed-edge
filtering. The host still chooses which returned `cjt_id` to run. This is not
an autonomous scheduler API.

## Verification plane

```python
IndependentVerifier(
    verifier_id,
    *,
    verifier_version=1,
    policy_id="cas.neural-cjt.exact-semantic-verifier/0.2",
)

IndependentVerifier.evaluate(
    cause,
    candidate,
    operation_contract,
    evidence,
    *,
    bias,
    operating_region=OperatingRegion.UNASSESSED,
) -> VerificationResult
```

The verifier is not a `torch.nn.Module` and has no store or commit handle. It
binds its receipt to the Cause, candidate, Bias revision, model digest,
operation contract, evidence identity, and region. Missing expected evidence
returns `UNASSESSED/ABSTAIN`; it cannot return `ACCEPT`.

## Integrated runtime

```python
NeuralCJTRuntime.create(
    path,
    *,
    config,
    node_specs,
    topology,
    seed=7,
    labels=None,
    model_id="cas-cjt-network-model",
) -> NeuralCJTRuntime

NeuralCJTRuntime.open(
    path,
    *,
    config,
    node_specs,
    topology,
    labels=None,
) -> NeuralCJTRuntime
```

`create` builds one network checkpoint, at least three persistent Biases, the
operation contracts, deterministic decoders, and a new SQLite authority head.
`open` reloads the exact checkpoint and refuses integrity or binding failure.
The caller must supply the same compatible architecture and decoder labels.

```python
runtime.make_input_cause(
    tensor,
    *,
    tick,
    content,
    goal_context,
    candidate_operation_ids=("^6",),
    cause_kind=CauseKind.IDEA,
    source="prototype:user-input",
    provenance=("prototype:local-input",),
    uncertainty_ppm=0,
    entity_bindings=(),
    relation_bindings=(),
    memory_refs=(),
    originating_modality=None,
) -> tuple[CausePacket, StoredArtifact]

runtime.cause_from_effect(
    published_effect_id,
    *,
    tick,
    candidate_operation_ids,
    goal_context,
) -> CausePacket
```

`cause_from_effect` is the normal cascade boundary. It verifies the retained
publication, commit receipt, trace, and tensor artifact before creating an
Effect-kind Cause.

```python
runtime.inference_tick(
    *,
    cause,
    cjt_id,
    expected_symbol,
    opposite_symbol=None,
    settings=None,
    supplied_artifacts=(),
    resume_repair_id=None,
    write_memory=True,
) -> InferenceTickResult
```

The result contains the pre/post Bias, candidate, verifier receipt, commit
receipt, optional publication, optional repair frame/subgoal, optional sealed
repair outcome, and materialized control record. Ticks must advance by exactly
one. Repair resumption uses `resume_repair_id` together with a Cause derived
from the committed repair Effect. An accepted resume atomically persists a
digest-bound `RepairOutcome`; there is no separate `resume_repair()` method in
v0.2.

```python
runtime.learning_tick(
    *,
    cause,
    cjt_id,
    expected_symbol,
    loss_fn,
    score_fn,
    opposite_symbol=None,
    settings=None,
    supplied_artifacts=(),
    allowed_parameter_names=None,
    parameter_group_ids=None,
    policy=None,
    regression_passed=False,
    resume_repair_id=None,
    write_memory=True,
) -> LearningTickResult
```

Learning requires an accepted inference result. It computes gradients on a
deep copy, limits changes to the named parameter bytes and admitted groups,
creates a candidate checkpoint, runs the supplied scoring functions, and asks
the coordinator to recheck and commit the batch. There is no active-model
`optimizer.step()` path.

The integrated v0.2 runtime admits only the exact default `LearningPolicy()`;
`policy=None` selects that policy and a different policy is rejected. The
coordinator recomputes the qualification arithmetic, retention decision,
decision conjunction, content-derived ID, and digest against that policy.

`loss_fn`, `score_fn`, and `regression_passed` are caller-supplied prototype
declarations. `regression_passed` defaults to `False`, so a caller must opt in
explicitly after running its stated regression check. The coordinator verifies
the receipt structure, arithmetic, checkpoint difference, and allowed scope;
it does not independently establish the scientific adequacy or independence of
those caller declarations. Learning is forbidden on the reserved `t+1` repair
subgoal tick.

## Sole-writer and persistence plane

```python
NetworkAtomicCoordinator(
    store,
    *,
    coordinator_id,
    authority_contract_id,
    runtime_id,
    software_digest,
    num_attention_heads,
    model_manifest_context,
    operation_contracts,
    decoder_contracts,
    permitted_topology_edges=(),
    trusted_evidence_sources=(),
    candidate_validator=None,
    parameter_scope_prefixes=None,
)

NetworkAtomicCoordinator.commit(
    batch,
    *,
    fault_at=None,
) -> CommitReceipt

NetworkAtomicCoordinator.restore_and_verify() -> NetworkRecoverySnapshot
```

`commit` validates the complete batch before one SQLite compare-and-swap
transaction. A mixed invalid batch cannot partially publish. `fault_at` is a
test-only failure-injection hook.

The coordinator receives complete trusted operation and decoder contracts,
not caller-supplied digest hints. It independently binds Cause eligibility,
topology, verifier identity and replay, decoder identity, runtime identity,
permissions, repair deltas, model qualification, control diagnostics, and the
candidate's control-binding provenance before any authoritative write. A
promoted model version must also carry the exact trusted network, config,
decoder-label, checkpoint, learning-tick, initiator, qualification, and changed
parameter manifest; unknown manifest or semantic-evidence fields are rejected.
Runtime v0.2 accepts only the four exact frozen operation contracts. State and
model intent IDs and rationale codes are recomputed, and each accepted or
repairing Bias successor must exactly match `advance_bias`; only a valid,
shape-bound recurrent tensor reference remains a neural proposal boundary. A
Bias with an open repair cannot accept ordinary work without the exact retained
repair outcome that closes it.

The module-level legacy `AtomicCoordinator` and `CommitBatch` are retained only
as a trusted single-Bias persistence and rollback compatibility harness. They
are not exported from the package root and are not an untrusted neural-CJT
proposal API. They reject `StateUpdateIntent`, `ModelUpdateIntent`/
model-version, and `RepairFrame` inputs; those semantic mutations use
`NetworkAtomicCoordinator` through `NeuralCJTRuntime`.

```python
SQLiteAtomicStore(path)
store.initialize(...)
store.reconstruct_transition(trace_id=None) -> dict
store.verify_integrity() -> bool
```

Application code should normally use `NeuralCJTRuntime.create/open` instead of
calling low-level store mutation methods. `SQLiteAtomicStore.commit` and
`AtomicWriteSet` are trusted coordinator-to-storage primitives: they provide
atomic persistence and mechanical row checks for a write set that
`NetworkAtomicCoordinator` has already authorized. They are not an untrusted
proposal API and do not replace its semantic validation. The supported neural
semantic mutation path is normally through `NeuralCJTRuntime`.

`reconstruct_transition`
returns the retained trace and its linked Causes, candidates, evidence,
receipts, intents, Effects, repairs, model records, memory records, and
artifacts. `verify_integrity()` semantically reconstructs every retained
transition, not only the active head, and validates nested Bias/model bindings
and transitive rollback origins. Integrity checking is tamper detection, not
cryptographic actor authentication or WORM storage.

## Proposal-only CNCM boundary

```python
ProposalOnlyCNCMBridge(adapter_id=BRIDGE_ADAPTER_ID)

ProposalOnlyCNCMBridge.translate(
    published_effect,
    *,
    store,
) -> InertCNCMCandidateEnvelope
```

The bridge accepts only a typed, retained `PublishedEffect` with a valid
candidate, verifier receipt, and commit receipt chain. Its frozen result says
`current_cncm_admitted=False` and provides no CNCM mutation method.

## Failure behavior

Malformed values raise the owning module's typed exception, such as
`ContractTypeError`, `RoutingError`, `VerificationError`,
`RuntimeContractError`, `LearningError`, `NetworkBatchRejected`, or
`PersistenceError`. A coordinator rejection adds a separate tamper-evident,
non-authoritative rejection audit and leaves the active cognitive head
unchanged. Reason codes such as `ZERO_FLOW`, `BREAKDOWN_REGION`,
`SEMANTIC_EVIDENCE_MISSING`, and `CHECKPOINT_PARAMETER_SCOPE_ESCAPE` remain
visible in receipts or audits.
