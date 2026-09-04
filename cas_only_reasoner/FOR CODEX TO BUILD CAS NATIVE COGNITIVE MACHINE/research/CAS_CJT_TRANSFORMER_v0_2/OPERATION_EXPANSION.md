# CJT operation registry and expansion path

Status: `FOUR BUILT-INS PLUS TESTED NEURAL-BANK EXTENSION / FULL CANONICAL VOCABULARY OPEN`

## Built-in operation identities

| Operation ID | Registered name | Relation index | Neural transform ID | Contract ID | v0.2 status |
|---|---|---:|---|---|---|
| `^6` | `decompose` | 0 | `cas.op.decompose.v1` | `cas.cjt.operation.^6.decompose/0.2` | `CANONICAL_ADMITTED` |
| `^2` | `experimental_attract` | 1 | `prototype.op.attract.v1` | `cas.cjt.operation.^2.attract.experimental/0.2` | `EXPERIMENTAL_OPEN_SEMANTICS` |
| `^3` | `experimental_avert` | 2 | `prototype.op.avert.v1` | `cas.cjt.operation.^3.avert.experimental/0.2` | `EXPERIMENTAL_OPEN_SEMANTICS` |
| `^8` | `experimental_trigger` | 3 | `prototype.op.trigger.v1` | `cas.cjt.operation.^8.trigger.experimental/0.2` | `EXPERIMENTAL_CONFLICTED_SEMANTICS` |

Only `^6` is canonical-admitted. The local names for `^2` and `^3` do not
establish canonical CAS meanings. The `^8` module produces an association
signal; it does not prove causation. The default verifier returns
`EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED` for all three experimental
operations, so they cannot publish an authoritative Effect.

The built-ins use different neural machinery:

- `^6`: two learned tanh views followed by a learned merge;
- `^2`: a learned direction multiplied by a sigmoid gate;
- `^3`: the negative of a learned direction multiplied by a sigmoid gate;
- `^8`: a learned source projection, GELU, and learned response projection.

## Current typed I/O contracts

| Operation | Accepted Cause kinds | Candidate effect kind |
|---|---|---|
| `^6` | `IDEA`, `PROPOSITION`, `EFFECT`, `RPM_SUBGOAL`, `TRAINING_EXPERIENCE` | `DECOMPOSITION_SIGNAL` |
| `^2` | `IDEA`, `EFFECT` | `ATTRACTION_SIGNAL` |
| `^3` | `IDEA`, `EFFECT` | `AVERSION_SIGNAL` |
| `^8` | `EVENT`, `EFFECT` | `ASSOCIATION_SIGNAL` |

Every candidate payload has exactly `operation_id`, `effect_kind`, and
`symbol`, plus a content-addressed tensor reference and provenance at the
record level.

## Operation contract

Each `OperationContract` binds:

```text
versioned contract and operation identity
ontology/admission status
accepted Cause kinds and schema versions
permitted evidence ports
neural transform identity
candidate Effect schema and kind
memory interface
readiness profile
legal actions and Bias paths
temporal transition law
verifier identity and configuration digest
plasticity groups
governance requirements
contract digest
```

An unknown operation, wrong Cause kind, mismatched relation channel, wrong
contract digest, or non-admitted experimental result fails before publication.

## Implemented neural-bank extension mechanism

`RegisteredOperationBank.register_operation(registration, module)` can add an
experimental operation when all of these are true:

- the operation ID, relation index, contract ID, and module instance are
  unique;
- the configured model has an unused relation channel;
- the name starts with `experimental_`;
- the extension does not claim `CANONICAL_ADMITTED`; and
- its module returns a finite tensor with the same shape, dtype, and device.

The module remains non-executable until
`RegisteredOperationBank.bind_contract(contract)` validates its exact
operation ID, name, ontology status, contract ID, and digest.

Executable evidence:

- `tests/test_neural_core.py::test_fifth_operation_requires_registration_and_exact_contract_binding`
- `tests/test_neural_core.py::test_extension_registration_cannot_override_builtins_or_relation_channels`
- `tests/test_neural_core.py::test_relation_contract_mismatch_fails_before_neural_execution`

The fifth-operation test adds an experimental `^9` module to a model configured
with five relation channels, proves it cannot run before exact contract
binding, and then executes it.

## Present limitation

Extension is generic at the neural operation-bank level, not yet at the full
`NeuralCJTRuntime.create` level. The runtime currently builds contracts through
the frozen four-operation `make_operation_contract` factory. A fifth operation
therefore still needs a versioned contract-provider and decoder-registration
API before it can participate in the durable inference, verifier, repair,
learning, and coordinator path without source changes.

The v0.2 coordinator enforces the frozen contracts through dedicated rules; it
does not interpret arbitrary new `temporal_transition_law` or
`governance_requirements` strings as executable policy. Those fields describe
and bind the four admitted implementations, but they are not a generic policy
language for extensions.

The current tests also do not show cross-version migration, operation removal,
mixed-operation learning, or canonical ontology admission.

## Path to a larger operation system

1. Freeze the source meaning, accepted inputs, outputs, and known conflicts.
2. Assign a new versioned ID without reusing an old meaning.
3. Define strict Cause, Effect, evidence, memory, temporal, verifier,
   plasticity, and authority contracts.
4. Add a runtime contract-provider and decoder-registration interface.
5. Register a distinct neural module and unused relation channel.
6. Add positive, negative, metamorphic, and adversarial fixtures.
7. Prove that zero flow, denial, mismatch, and breakdown stay closed.
8. Test full runtime publication, repair, learning, rollback, restart, and trace
   reconstruction for the new operation.
9. Test cross-operation cascades and parameter isolation.
10. Define registry-manifest versioning, migration, deprecation, and rollback.
11. Qualify the operation empirically against its declared purpose.
12. Admit it as canonical only through a separate ontology and authority
    decision.

The full canonical CAS operation vocabulary is not frozen in this package.
This document provides a tested extension seam and a precise path; it does not
invent a complete vocabulary or call experimental names canonical.
