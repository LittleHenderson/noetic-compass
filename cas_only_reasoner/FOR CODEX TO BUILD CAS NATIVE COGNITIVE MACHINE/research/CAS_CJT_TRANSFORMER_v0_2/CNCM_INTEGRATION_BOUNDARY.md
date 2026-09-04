# Deterministic CNCM integration boundary

Status: `IMPLEMENTED PROPOSAL-ONLY ADAPTER / NOT ADMITTED BY CURRENT CNCM`

The current `cncm` runtime remains version `0.1.0`. Neural CJT v0.2 does not
change its `MachineState`, KIR, proof rules, intent types, capability matrix,
transaction coordinator, memory boundary, or halt behavior.

“Authoritative Effect” inside Neural CJT v0.2 means authoritative only in the
isolated v0.2 research database. It does not mean a CNCM proposition, proof,
commitment, state change, memory occurrence, action, or halt.

## Implemented bridge

`ProposalOnlyCNCMBridge.translate` accepts only a typed `PublishedEffect` and
a read-only retained-evidence store. It reconstructs and checks:

1. the retained publication and its digest;
2. the source candidate Effect and its digest;
3. the independent verifier receipt and its exact candidate/Bias/model/
   operation bindings;
4. the authorized commit receipt and its publication list; and
5. the matching semantic payload, tensor reference, and provenance.

If every check passes, the bridge returns a frozen
`InertCNCMCandidateEnvelope` with:

```text
authority_status = INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM
authoritative = false
current_cncm_admitted = false
future_authority_revision = REQUIRED_BUT_UNASSIGNED
```

The envelope permits display as a non-authoritative candidate or review by a
future explicit authority revision. It cannot create a current CNCM object or
mutate either runtime.

```mermaid
flowchart LR
    PE[Retained Neural CJT PublishedEffect] --> B[ProposalOnlyCNCMBridge]
    ES[(Read-only candidate, verifier, and commit evidence)] --> B
    B --> IE[Frozen inert candidate envelope]
    IE -. no admission path in CNCM 0.1.0 .-> X[No CNCM state, proof, intent, memory, action, or halt]
```

`translate_optional(None)` returns `None`. This gives the host a clean
sever-the-neural-core path.

## Executable boundary evidence

- `tests/test_cncm_bridge.py::test_committed_effect_becomes_only_an_inert_future_candidate`
- `tests/test_cncm_bridge.py::test_absent_or_malicious_neural_core_cannot_change_deterministic_shell`
- `tests/test_cncm_bridge.py::test_uncommitted_or_untyped_effect_is_refused`
- `tests/test_cncm_bridge.py::test_forged_or_unretained_publication_is_refused`
- `tests/test_cncm_bridge.py::test_every_retained_authority_link_is_reconstructed_and_checked`
- `tests/test_cncm_bridge.py::test_bridge_source_has_no_current_cncm_import_or_privileged_construction`

The malicious-core test compares one deterministic CNCM fixture before and
after bridge use. It is strong negative evidence for this adapter path, not a
formal proof about every possible CNCM behavior.

The bridge source deliberately imports no current `cncm` module and constructs
none of `MachineState`, `ProofStep`, `Intent`, `CommitmentState`, or
`TraceEvent`.

## Permanent prohibitions

CAS-Ohm flow, neural output, decoder labels, learned confidence, operation
rank, memory similarity, or a self-issued result can never by themselves grant:

- semantic truth or meaning;
- proof validity;
- permission or policy bypass;
- commitment;
- authoritative CNCM memory or state write;
- protected modification;
- halt authority; or
- external action.

## Work required before real CNCM admission

A real integration remains a separate versioned project. At minimum it needs:

1. A new CNCM runtime, KIR, and authority-contract version.
2. Strict admitted schemas for neural requests, inert responses, evidence,
   verifier receipts, compute plans, and artifact references.
3. Explicit issuer/capability entries and negative tests for each forbidden
   privilege escalation.
4. A semantic admission rule that reconstructs any symbolic claim without
   trusting neural activation, confidence, or CAS-Ohm flow.
5. An admitted network scheduler and resource contract.
6. If fairness, exact global budget conservation, or removal invariance is
   required, a new allocator that implements and tests those properties. The
   current v0.2 top-route ceiling does not provide them.
7. Authenticated checkpoint, Bias, memory, and restore rules. Current SHA-256
   chains provide tamper evidence, not signatures, trusted identity, or WORM.
8. Broader sever, bypass, replay, corruption, and adversarial tests.
9. Held-out calibration and matched-baseline evidence before any neural
   CAS-Ohm profile is called admitted or advantageous.

Until a later authority decision closes these gates, the integration status is
`NOT_RUNTIME_INTEGRATED`.
