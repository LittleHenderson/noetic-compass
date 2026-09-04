# CAS Core Ontology v0.1

Status: **required Phase 0 contract candidate — OPEN**

This artifact freezes only the identifiers, type separations, and semantic
dispositions supported by the named Phase 0 sources. It does not supply missing
Foundation meanings, Foundation-to-Drive mappings, Prime Desire identity,
D/W/P sufficiency rules, or executable meanings for open Noetics. It does not
declare Phase 0 closed.

Normative terms `MUST`, `MUST NOT`, and `OPEN` apply only to the bounded
CNCM-RRK v0.1 contract.

## 1. Authority basis and scope

This contract is constrained by:

- `cas_reasoner.txt:37-49`, which supplies the seven CAS Drive labels and
  explicitly distinguishes those rails from TKS Foundations;
- `cas_reasoner.txt:12564-12628`, especially the required artifact list at
  lines 12570-12580, the decisions to freeze at lines 12582-12610, the
  association/deduction distinction at lines 12612-12614, and the Phase 0 exit
  gate at lines 12616-12628;
- `OPEN_QUESTIONS.md`, whose `OPEN-SEMANTICS` rule forbids deriving behavior
  from an invented meaning;
- `NON_GOALS.md`, which bounds the implemented reference kernel;
- `docs/COMPILER_RUNTIME_BOUNDARY.md`, `spec/CAS_KERNEL_IR_v0.1.md`, and
  `spec/CONFORMANCE_PLAN_v0.1.md`, which describe the currently admitted packet,
  IR, execution, evidence, and test boundaries.

This document records no source-precedence rule beyond those sources. A future
semantic decision becomes normative only through a versioned change to the
authority manifest and every affected contract.

## 2. Frozen type ledger

| Type or role | Frozen members or identity rule | v0.1 semantic and execution status |
|---|---|---|
| `NoeticCoordinate` | Exactly `^0`, `^1`, `^2`, `^3`, `^4`, `^5`, `^6`, `^7`, `^8`, and `^9`. | Membership is frozen. The executable status is limited by Section 3. |
| `DomainCoordinate` | Exactly `P`, `C`, `E`, and `O`. | Identifier membership is frozen. Substantive stability criteria remain `OPEN-SEMANTICS` under OS-007. |
| `RegisterCoordinate` | Exactly `T`, `A`, `f`, and `E`. | Identifier membership is frozen. Transfer, leakage, persistence, packet fields, and executable behavior remain `OPEN-SEMANTICS` under OS-006. |
| `CASDrive` | Exactly `F1 Unity`, `F2 Wisdom`, `F3 Vitality`, `F4 Connection`, `F5 Agency`, `F6 Structure`, and `F7 Purpose`. | Membership and these source-supplied labels are frozen. This remains a namespace distinct from every TKS Foundation namespace; no Foundation mapping, weight, priority, or proof authority follows from a Drive label. |
| `TKSFoundation` | Opaque references `TF1` through `TF7`, as scoped by OS-001. | Meanings, names, precedence, and goal-generation behavior are `OPEN-SEMANTICS`. A reference confers no truth, evidence, priority, or runtime authority. |
| `TKSSubFoundation` | Opaque references `TF1a` through `TF7d`, as scoped by OS-002. | The 28 identifiers MUST remain separately typed goal and consequence channels. Definitions, World mappings, consequences, and weights are `OPEN-SEMANTICS`. |
| `PrimeDesireRoot` | Exactly one canonical identifier is required. | **OPEN:** the named sources do not supply that identifier. No placeholder or implementation-local value is canonical. |
| `DWPPrerequisite` | The prerequisite-state coordinates are `D`, `W`, and `P`. | They are not aliases for Drive, flow, or resistance. Sufficiency, assessors, evidence, packet fields, calculation, and routing are `OPEN-SEMANTICS` under OS-004 and are absent from v0.1 execution. |
| CAS-Ohm | Contract-only observation role in runtime 0.1.0; adopted follow-on native attention-flow and resource-allocation plane. | It MUST NOT be truth, meaning, proof, validity, commitment, permission, memory-occurrence/write, state-mutation, halt, causal-identification, action, or self-modification authority; a physical law; or an identifying causal diagnostic. The current scheduler does not read it. A later scheduler may consume only a distinct pre-schedule allocation plan after the versioned gates in `CAS_OHM_ATTENTION_INTEGRATION_PROTOCOL_v0.1.md` pass. |

`TKSFoundation` and `TKSSubFoundation` are not `CASDrive`. Shared numbers,
letters, display labels, ordinal positions, or storage encodings MUST NOT create
an identity, subtype, cast, or default mapping between those types.

The letter `P` occurring in `DomainCoordinate` and the letter `P` occurring in
`DWPPrerequisite` belong to different types. Their spelling MUST NOT create an
alias.

## 3. Noetic reasoning distinction

The source-level distinction is frozen as follows:

1. `^8` is associative triggering: it may surface another idea.
2. Association alone is not deduction, authoritative support, or proof.
3. Step-by-step deduction requires `^6` decomposition followed by `^9`
   conclusion formation.

The implemented KIR realizes only the bounded form documented in
`CAS_KERNEL_IR_v0.1.md`:

- `^6` is represented by `RECORD_DECOMPOSITION`, not by an accepted
  `DECOMPOSE` proof step;
- `^8` candidate association is not executed; candidates are caller-declared;
- `^9` is represented by the conclusion in an exactly reconstructed proof
  step;
- `^0`-`^5` and `^7` are valid coordinates but remain non-executable
  `OPEN-SEMANTICS` operations.

The existence of inference enum labels such as `ASSOCIATE` or `DECOMPOSE` does
not grant proof authority. Only the proof operations admitted by the KIR may
occur in an accepted `DERIVE_PROPOSITION` proof.

## 4. Namespace and authority invariants

The following invariants are normative:

1. A structurally valid ontology identifier proves only membership in its
   declared type.
2. Identifier membership MUST NOT establish external truth, evidence quality,
   priority, commitment, deployment authority, mutation permission, or action
   authority.
3. A `TKSFoundation` may be carried only as the opaque optional Foundation
   reference admitted by the current packet contract. No behavior may be
   derived from its unresolved meaning.
4. A `TKSSubFoundation`, `DWPPrerequisite`, `DomainCoordinate`, or
   `RegisterCoordinate` has no executable packet or IR field unless a later
   versioned contract explicitly adds one.
5. An unknown identifier, an invalid cross-type use, or a construct requiring
   open semantics MUST fail closed or produce explicit abstention. It MUST NOT
   be repaired by guessing.
6. Compiler acceptance cannot add ontology meaning. Runtime validation cannot
   turn descriptive provenance into authentication.

## 5. Recorded dispositions and unresolved items

These are the bounded dispositions supported by the named sources:

| Issue | Disposition |
|---|---|
| Canonical Noetic range | Frozen as `^0` through `^9`; this does not make every coordinate executable. |
| `^8` association versus deduction | Distinct. Association cannot substitute for the `^6` decomposition / `^9` conclusion distinction. |
| TKS Foundations versus CAS Drives | Separate types and namespaces. Mapping remains `OPEN-SEMANTICS`; no default exists. |
| D/W/P name collision | D/W/P are prerequisite states, not aliases for Drive, flow, or resistance. Their sufficiency semantics remain open. |
| CAS-Ohm authority | No truth/proof/meaning/validity/commitment/permission/memory/state/halt/causal/action/self-modification authority. Runtime 0.1.0 is observation-contract only; a later version may admit bounded native flow/resource allocation without widening any hard authority gate. |

The following remain explicitly open and prevent this artifact from being a
complete semantic ontology:

- OS-001: seven TKS Foundation meanings;
- OS-002: 28 TKS Sub-Foundation meanings and World mappings;
- OS-003: Foundation-to-Drive adapter;
- OS-004: D/W/P sufficiency;
- OS-005: executable meanings for `^0`-`^5` and `^7`;
- OS-006: register transfer behavior;
- OS-007: substantive domain stability criteria;
- the canonical `PrimeDesireRoot` identifier, which is required but not supplied
  by the named sources.

The wider unresolved authority and engineering questions remain governed by
`OPEN_QUESTIONS.md`. This ledger is not evidence that every conflict in every
historical source has been enumerated or disposed.

## 6. Conformance obligations

A conforming v0.1 implementation and compiler boundary MUST demonstrate that:

- only the frozen members are accepted for each closed identifier set;
- a Foundation or Sub-Foundation reference cannot be accepted as a CAS Drive;
- no Foundation-to-Drive mapping is inferred from matching ordinals or labels;
- open ontology constructs do not change proof, comparison, commitment,
  learning, scheduling, or authority;
- `^8` association is not accepted as a proof of a conclusion;
- the KIR's bounded `^6` and `^9` realization remains exactly reconstructable;
- CAS-Ohm data cannot authorize truth, meaning, proof, validity, commitment,
  permission, memory occurrence/write, state mutation, halt, causal
  identification, action, or self-modification. In runtime 0.1.0 it also cannot
  alter scheduling or any state transition. A later allocator requires a
  distinct pre-schedule allocation plan and explicit authority/KIR revision and
  remains limited to eligible-work resource allocation.

Passing those checks proves only the covered structural separation. It does not
resolve any `OPEN-SEMANTICS` item.

## 7. Phase 0 gate status

This file satisfies the requirement to create a named ontology contract
candidate. It does **not** establish that every core term has a complete typed
meaning, that every source conflict has a recorded disposition, that the KIR or
goldens have received Phase 0 acceptance, or that the exit gate at
`cas_reasoner.txt:12616-12628` has closed. Phase 0 remains **OPEN**.
