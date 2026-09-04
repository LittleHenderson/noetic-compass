# CASformer-to-Neural-CJT roadmap

Status: `FIRST REASONING-TRANSISTOR MECHANISM MILESTONE REACHED`

The v0.2 milestone is the first integrated local mechanism prototype. The
larger CAS-native Transformer and CNCM brain remain a research program.

## Frozen v0.1 to v0.2 map

| Frozen CASformer v0.1 element | Implemented v0.2 use | Important boundary |
|---|---|---|
| Dense hidden tensor | Artifact-backed dense part of a typed `CausePacket` | The tensor is not the whole Cause |
| `CASControl.bias` | Materialized recurrent tensor from persistent `BiasState.memory` | Ordinary neural bias is not the six-part CJT Bias |
| Readiness scalar | Product of separately retained Desire, Wisdom, and Power values behind three hard status gates | Product profile is prototype-local, not canonical CAS semantics |
| `OhmicMultiheadAttention` | Differentiable current, allocation, and additive-logit attention inside one selected CJT | It does not choose truth or globally schedule CJTs |
| Relation IDs/operators | First relation-specific neural stage | v0.2 adds a second registered operation module and exact operation contract binding |
| `CJTRegionGate` | Cutoff/active/saturation/breakdown gate with separate semantic outcome | Region is not correctness |
| `telemetry.cjt_effect` | Sole neural source for the v0.2 candidate Effect | Residual/FFN block output is discarded as an Effect source |
| Standard or differential-conductance linear layers | Trainable operation and Bias-update modules | Positive rails are a parameter representation, not physical hardware proof |
| Caller feedback | Previous committed operating state and recurrent Bias artifact | Uncommitted feedback cannot become persistent state |
| Local trace telemetry | Input to a retained 11-phase transition record | SHA-256 is tamper evidence, not signature or WORM |
| No durable state authority | SQLite sole-writer state/model/memory/Effect store | Authority is local to the v0.2 research database |
| No external verifier/latch | Exact-bound independent verifier and network coordinator | Verifier is a narrow authored-target oracle, not a general truth engine |

## Completed v0.2 implementation stages

| Stage | Result | Executable evidence |
|---|---|---|
| 1. Contract layer | Strict types, schemas, operation identities, authority split, and phase contract | `tests/test_types_and_schemas.py`; `tests/test_public_api.py` |
| 2. Pure neural CJT | Gated candidate Effect, distinct operation modules, zero-flow behavior, optional positive rails | `tests/test_neural_core.py` |
| 3. Governed state | Artifacts, persistent Bias/memory, verifier, immutable intents, sole writer, and trace chain | `tests/test_persistence_coordinator_trace.py`; `tests/test_network_coordinator.py` |
| 4. Recursive tick | Exact 11 phases, Effect-to-Cause cascade, next-tick repair, and bounded controls | `tests/test_integrated_runtime.py::test_complete_four_cjt_reasoning_transistor` |
| 5. Governed learning | Staged gradient, exact allowlist, qualification, atomic checkpoint promotion, and unchanged active bytes on failure | `tests/test_governed_learning.py`; integrated test |
| 6. Integrated episode | A -> B -> C -> repair R -> resumed C, restart, changed output, invalid update refusal, and reconstruction | `tests/test_integrated_runtime.py::test_complete_four_cjt_reasoning_transistor`; `examples/complete_reasoning_transistor.py` |
| 7. Proposal-only CNCM boundary | Retained Effect becomes only a frozen inert future candidate | `tests/test_cncm_bridge.py` |

Release validation must pass the full v0.2 suite, install the built wheel in a
clean environment, and rerun the frozen v0.1 and current CNCM suites before a
release receipt is claimed.

## Next engineering stages

1. **Release and reproducibility** — finish clean wheel installation,
   dependency locking, cross-package regression, deterministic manifests, and
   a separately reviewed release receipt whose review provenance is stated.
2. **Network scheduler** — replace explicit host selection of one `cjt_id`
   with an admitted scheduler that can choose and budget several eligible CJTs
   without receiving write authority.
3. **Resource allocator** — decide whether CNCM requires fairness, exact global
   budget conservation, starvation bounds, and removal invariance; implement
   those rules instead of attributing them to the current top-route ceiling.
4. **Richer governed memory and repair** — add semantic/procedural retrieval,
   multi-branch repair, durable return values, branch rollback, and stronger
   recursion accounting. Add a separately authorized persistent-quarantine
   transition and, if needed, a bounded authoritative Published-Effect history
   without conflating it with candidate history. Follow
   `MEMORY_RESEARCH_PLAN.md`: wrap the current
   deterministic reader as M0, establish explicit branch-manager-issued chain
   tags as the audit baseline, and only then compare bounded propagation and
   true two-state oscillation. A new memory phase or trace field requires an
   explicit contract/schema version change.
5. **Semantic verification** — replace synthetic exact-label targets with
   domain-specific evidence and checkers that can justify typed claims. Neural
   confidence must remain non-authoritative.
6. **Transformer and language integration** — connect CJT state and authority
   to token generation, sequence training, language contracts, and an actual
   causal language-model loop. The current v0.2 runtime is a CJT network
   demonstrator, not a completed language model.
7. **Operation expansion** — qualify new operations through the extension
   mechanism and a separately governed ontology process. Do not relabel
   experimental `^2`, `^3`, or `^8` as canonical.
8. **CNCM admission** — create a new runtime/KIR/authority version and pass the
   gates in `CNCM_INTEGRATION_BOUNDARY.md`. Do not import this prototype into
   CNCM 0.1.0 as hidden authority.
9. **Security and durable evidence** — add authenticated identities,
   signatures, trusted time, access control, backup/recovery, and WORM or
   external anchoring if those properties are required.
10. **Scale and hardware study** — test concurrency, distributed execution,
    larger models, accelerator behavior, and any claimed resistance-hardware
    correspondence.

## Empirical program required before an advantage claim

The current demo uses synthetic labels, a hand-authored expected symbol, and a
small optimization objective. It shows that a guarded parameter change can
persist and alter later output. It does not show better learning or reasoning.

Any CAS-advantage study should be preregistered and compare against matched
ordinary-attention and ordinary-routing baselines with the same data,
parameter budget, optimizer budget, compute budget, seeds, stopping rules, and
evaluation set. It should report accuracy, calibration, abstention, repair
quality, compute, latency, stability, retention, and failure cases. A result
must be replicated before it changes the claim boundary.

Passing the local mechanism milestone grants no later capability or authority.

## Accepted memory comparison sequence

The owner-supplied pulsation and chain-tag addendum is accepted as design
input for a later, replaceable memory subsystem. It does not widen the v0.2
completion claim. Explicit chain tags preserve identity and provenance;
pulsation may later control relevance and timing inside a chain. Phase is not
authority, and neither mechanism is preferred until a matched comparison is
run. See `MEMORY_RESEARCH_PLAN.md` for the interface, stability rules, and
measurement plan.
