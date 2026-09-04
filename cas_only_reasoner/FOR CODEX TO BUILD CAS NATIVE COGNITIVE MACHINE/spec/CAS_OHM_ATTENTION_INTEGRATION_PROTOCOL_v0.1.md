# CAS-Ohm Attention Integration Protocol v0.1

## Native Attention Semantics, Neural Calibration, Cortex Diagnostics, and Generative Memory Retrieval

Status: **ADOPTED DESIGN DIRECTION / FOLLOW-ON CONTRACT / NOT INTEGRATED INTO CNCM-RRK RUNTIME 0.1.0**

Source: owner correction dated 2026-08-28, reconciled with the locally retained
`CAS_OHM_ATTENTION_PROTOCOL_v0.1.md`, the current CNCM authority contract, and
the three source PDFs listed in section 2.

This protocol supersedes the blunt design reading that CAS-Ohm must remain
outside the machine. It does **not** silently change the current v0.1 kernel,
issuer/capability matrix, scheduler, trace schema, proof rules, or commitment
rules. Runtime integration requires a separately versioned authority, KIR,
schema, implementation, and negative-test change.

Normative words `MUST`, `MUST NOT`, `SHOULD`, and `MAY` apply to any future
implementation claiming conformance to this protocol. A section explicitly
marked `PROPOSED` is not executable authority.

## 1. Revised architectural law

```text
CAS-Ohm governs flow.
CJTs govern transformation.
CAS-Sem governs meaning.
The verifier governs validity.
The commitment latch governs commitment.
The authority contract governs permission.
The trace preserves the evidence.
```

CAS-Ohm belongs inside the machine as a typed attention-flow,
resource-allocation, diagnostic, and tuning plane. It MUST NOT decide:

- whether a proposition is true;
- whether a word or semantic binding is correct;
- whether a proof is valid;
- whether a memory occurred;
- whether a branch may commit;
- whether an action is authorized;
- whether a patch, promotion, or self-modification is safe or permitted.

An attention reading is evidence about flow under a declared model. It is not
proof, truth, meaning, or permission.

## 2. Source basis and conflict disposition

The source set used by this protocol is:

| Source | Local identity | Relevant boundary |
|---|---|---|
| CAS PCBA Engineer | `book/CAS_PCBA_Engineer/CAS_PCBA_Engineer.pdf`, SHA-256 `f31584e628689115afba08c4686a1d07a28bbc2bfaf9103d3505f5177937372a` | PDF page 25/book page 7 describes the circuit/cognition relationship as a structural isomorphism and distinguishes topology from substrate-specific mathematics. |
| CAS-Ohm Quantification Guide | `cas_only_reasoner/CAS_Ohm_Quantification_Guide-1.pdf`, SHA-256 `89ae13c0a5d6208e328e9edc55f816609bb172076cc13093dccccf418145ce64` | Page 13 keeps attention local at each CJT stage, passes effects forward, and keeps gain distinct from local flow. Pages 15-17 supply ASOM, test-point, residual, and measure-diagnose-tune-retest patterns. |
| CAS-Ohm research paper v0.2 | `cas_only_reasoner/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf`, SHA-256 `21a34501a0db0c3c65f9cd6d3149ef16bb93db2a31d626affe726ff6e72d69bf` | Defines a profile-specific experimental neural response model, rejects physical/electrical/attention/causal overclaiming, requires typed quantities and disjoint held-out validation, makes residuals non-identifying, and keeps stateful behavior provisional. |

The apparent conflict is resolved by substrate typing. The native runtime may
define an exact computational flow law. The neural paper limits empirical
claims about an observed model. Neither licenses claims about biological
attention.

## 3. Three substrates and three execution modes

Substrate and execution mode are different fields. The three substrate claims
are:

| Substrate | Meaning of flow | Status |
|---|---|---|
| `NATIVE_COMPUTATIONAL` | A local typed activation/resource quantity whose semantics are defined by the runtime. | Exact by the versioned computational rule; not empirical telemetry. |
| `NEURAL_MODEL` | A measured activation projection or other registered quantity from one identified model profile. | Empirical, profile-specific, uncertain, and valid only under its calibration/held-out contract. |
| `HUMAN_BIOLOGICAL` | A proposed correspondence to attention in a human or biological brain. | Open research only; not admitted by the v0.1 stage-record schema. |

The admitted execution modes are:

| Mode | Required substrate | Meaning |
|---|---|---|
| `NATIVE_RUNTIME` | `NATIVE_COMPUTATIONAL` | Runtime-stage flow and resource accounting. |
| `NEURAL_PROFILE` | `NEURAL_MODEL` | Calibrated instrumented neural observation. |
| `MEMORY_RETRIEVAL` | `NATIVE_COMPUTATIONAL` | Proposed CAS-GEM allocation among eligible memory-candidate paths. |

Mode/substrate combinations are mutually exclusive. A native or memory record
MUST NOT carry a neural profile or neural-only units. A neural record MUST NOT
carry a memory-retrieval profile. Human/biological measurements require a later
protocol and cannot be encoded as either native or neural records.

The modes MUST NOT share units implicitly. A profile-specific bridge MAY be
declared as:

```text
I_attention_observed = H_profile(y_activation)
```

Without a registered `H_profile`, neural activation is not native CAS attention.
Neither quantity is automatically human attention.

## 4. Quantity type system and canonical encoding

Every numeric quantity MUST be carried in a typed envelope. Bare JSON numbers
are prohibited in the evidence record. Values use canonical decimal strings or
scaled integers; binary floating point MUST NOT enter authoritative CNCM state,
intents, identities, or hashes.

Each quantity envelope records at least:

- quantity kind;
- exact decimal value or explicit missing/censored state;
- unit identifier;
- measurement kind;
- method identifier;
- calibration-profile digest when applicable;
- declared/derived/observed status;
- uncertainty and confidence interval when applicable;
- sample size when applicable;
- raw evidence references;
- derivation-parent identities;
- missing or censoring reason.

Measurement kinds remain distinct:

```text
DESIGN_VALUE
INSTRUMENTED
RUNTIME_COUNTER
BEHAVIORAL_PROXY
MODEL_DERIVED
HUMAN_SCORE
LLM_SCORE
```

A derived value does not become instrumented because one parent was
instrumented. A score does not become telemetry because it appears beside a
measurement. Physical `volt`, `ampere`, and `ohm` unit aliases are forbidden for
native and neural CAS-Ohm quantities.

The v0.1 compatibility matrix is:

| Context | Permitted quantity/unit families | Permitted measurement kinds |
|---|---|---|
| Native runtime | Drive/native-drive, resistance/native-resistance, flow/native-attention, gain/effect/dimensionless, resource/resource-quanta | `DESIGN_VALUE`, `MODEL_DERIVED`, `RUNTIME_COUNTER` |
| Memory retrieval | Native Drive, retrieval-resistance, native-attention allocation, unit-interval allocation share | `DESIGN_VALUE`, `MODEL_DERIVED`, `RUNTIME_COUNTER` |
| Neural intervention | dose/`ALPHA`, activation/`ACTIVATION`, effective-resistance/`ALPHA_PER_ACTIVATION`, derived gain/residual | `DESIGN_VALUE` for authored dose, `INSTRUMENTED` for observations, `MODEL_DERIVED` for fits and residuals |

JSON Schema enforces the coarse mode/substrate/profile split. A deterministic
semantic validator MUST additionally enforce field-specific kind/unit/method
compatibility, exact arithmetic, and all cross-field equalities before a record
is admitted as conformance evidence.

## 5. Native Drive and resistance semantics

For a declared local native path:

```text
I_attention = V_drive / R_total
```

This equation is exact only because the runtime version defines its quantities,
units, arithmetic, topology, and rounding. It is not a universal law of thought.
`R_total` MUST be strictly positive.

A path MAY declare the following non-physical resistance categories:

```text
R_capability
R_policy
R_context
R_resource
R_specialized
```

Specialized subtypes MAY include:

```text
R_lexical
R_role_binding
R_reference
R_ambiguity
R_compute
R_distance
R_decay
R_interference
R_anchor_conflict
```

The subtype names refine the broader categories. They do not create new
physical quantities. Series addition is permitted only when the versioned
topology declares the components to be series-compatible with matching quantity
types and units. A displayed parent equivalent MUST NOT erase child test points.

For every complete native record, the semantic validator MUST reconstruct
`R_total` from the declared topology, prove `R_total > 0`, recompute
`I_pred = V_drive / R_total` under the frozen exact-arithmetic rule, and reject
any stored value that differs. If `delta_I` is present, it MUST equal
`I_obs - I_pred` exactly.

## 6. Scheduler allocation semantics

CAS-Ohm MAY govern native work allocation after a future KIR version admits the
plane. It MUST never widen the eligible set created by hard policy, capability,
budget, branch, RPM, or authority gates.

For each already eligible branch `i`:

```text
raw_attention_i = V_goal_i / R_branch_i
```

A conforming allocator MUST provide:

- a minimum exploration or fairness floor;
- a maximum per-branch ceiling;
- a deterministic total budget;
- exact normalized allocation;
- stable tie-breaking by canonical branch identity;
- a hard prohibition on converting attention rank into proof or commitment
  rank;
- a fallback allocation when all eligible flows are zero or missing.

The proposed clamped rule is:

```text
allocated_i = clamp(fairness_floor_i + proportional_share_i,
                    fairness_floor_i,
                    branch_ceiling_i)
```

Integer remainder assignment MUST use a frozen deterministic method, such as
largest remainder with canonical branch-ID tie-breaking. The sum of allocations
MUST equal the admitted tick budget. A high-current branch cannot monopolize the
Mind before alternatives receive their required exploration floor.

For each resource record, the semantic validator MUST prove
`fairness_floor <= allocated <= ceiling`, `consumed <= allocated`, and
`remaining_after = remaining_before - consumed`. Cohort validation, not one
record in isolation, proves total-budget conservation and the fairness floor for
every eligible branch.

For runtime 0.1.0 this section is contract-only. The existing scheduler remains
normative and MUST behave identically if every CAS-Ohm observer is removed.

The post-seal `CASOhmStageRecord` defined in section 8 is diagnostic evidence;
it MUST NOT be recycled as a scheduler command. Future flow governance requires
a separate, pre-schedule `AttentionAllocationPlan` contract bound to the sealed
input state, eligible-branch set, budget profile, exact allocation cohort, and
authority/KIR version. The scheduler may consume only that plan after the
allocator and authority gates in section 18 pass.

## 7. CJT flow, gain, and effect

Each CJT stage has separate local quantities:

```text
flow:        I_attention
transform:   beta
result:      effect_activation + effect_type
meaning:     CAS-Sem object evaluated by semantic/verifier contracts
```

Flow says how much typed work reached the stage. Gain says how the stage
transformed its input under one named gain profile. Effect says what the stage
produced. None is interchangeable.

In a cascade, the effect of stage `n` becomes the cause of stage `n+1`. Local
flow is measured independently at each stage; it is not one conserved
electrical current. Gain multiplication is allowed only under a declared,
compatible active-region profile. Fisher-Rao gain and local
Jacobian/projection gain remain separate profiles without a proved bridge.

Healthy flow with the wrong effect is a transformation or semantic fault, not
attention starvation. A conforming diagnostic MUST NOT respond by increasing
Drive merely because the output is wrong.

## 8. CNCM trace and component binding

A CAS-Ohm stage record is an append-only observation sidecar. For current CNCM
it is created only after a sealed `TraceEvent` and binds:

- run and runtime identities;
- trace event ID, logical tick, event hash, and trace digest;
- pre-state and post-state hashes;
- enabled and scheduled component identities;
- branch and goal identities;
- stage, board, and test-point identities where applicable;
- a stable component/CJT identity when one exists;
- topology identity/digest, combination rule, and referenced resistance-term
  identities for native records;
- compiler artifact and AST-node identities when a compiled component is being
  observed.

The record also carries a canonical payload digest, previous-chain digest,
sidecar-chain digest, retention-manifest digest, and verification status. Those
fields do not prove append-only storage by assertion: the sidecar verifier MUST
recompute the payload and chain hashes and verify retention before the record is
admitted as evidence.

With `H = SHA-256` and `C = CNCM_CANONICAL_JSON_V0.1`, the verifier computes:

```text
payload_digest = H(C(record with the entire integrity object omitted))
sidecar_chain_digest = H(C({
    previous_chain_digest,
    payload_digest
}))
```

The first record in a run uses `previous_chain_digest = null`; every later
record uses the preceding record's verified `sidecar_chain_digest`. Ordering is
by logical tick and then canonical record ID. The retention-manifest digest is
verified separately and is not inferred from the chain.

The current CNCM implementation has no canonical `CJT` runtime class or
compiler-AST-to-CJT binding. The existing `reasoning_engine` MUST NOT be
relabeled a CJT. Until those contracts exist, `binding_status` remains
`UNBOUND_COMPONENT` or `SUBSYSTEM_ONLY`.

The observer has no intent type, issuer capability, state-write path, proof
role, halt role, permission role, causal-identification role, memory-occurrence
role, or memory-write role. Removing or corrupting the sidecar MUST NOT alter
state, trace events, proof, conclusion, commitment, RPM behavior, or episodic
writes.

`semantic_outcome` is a borrowed result, not a CAS-Ohm judgment. Any value other
than `UNASSESSED` MUST bind the exact CAS-Sem or verifier contract version,
evaluation identity, and evidence digest that supplied it. CAS-Ohm may compare
that supplied classification with flow; it cannot create or revise it.

The contract-only wire shape is
`schemas/cas_ohm_stage_record.schema.json` with schema version
`cncm.cas-ohm-stage/0.1`.

## 9. RPM diagnostic binding

CAS-Ohm MAY bind an observation to a versioned `RPMFrame` and record its exact
`frame_id`, `goal_id`, `parent_goal_id`, `branch_id`, `target_foundation`,
`blocked_prerequisite`, `return_address`, `resume_stage`,
`expected_result_key`, and `depth`, plus a canonical frame digest, the observed
push/active-child/return phase, and local resource/flow measurements.

The observation MAY identify a low-flow or high-resistance neighborhood for
inspection. It MUST NOT invent D/W/P semantics, declare a prerequisite
satisfied, authorize `PUSH_RPM` or `RETURN_RPM`, or alter the exact resolver
proof. The existing RPM controller and transaction coordinator retain all
authority.

## 10. Cortex language-stage profiles

The intended diagnostic pipeline is:

```text
raw cortex output
-> schema validation
-> lexical grounding
-> role/content binding
-> semantic coherence
-> epistemic typing
-> kernel admission
```

Each stage MAY have a separate profile and test point.

- An invented word may raise `R_lexical`; a residual may rank lexical probes,
  but the grounding verifier identifies the actual failure.
- A passive-voice role reversal may have healthy flow and a wrong semantic
  effect; repair targets role binding, bias, rule, or topology rather than
  Drive.
- Increasing ambiguity may raise `R_reference` and `R_context`, lower the
  direct-answer allocation, and increase allocation to a clarification branch.

The external local precedent at
`cas_only_reasoner/CAS_CORTEX_v0.1/cortex/attention.py` is compute-only and
post-decision. It uses floating-point authored values and an external turn-trace
shape, so it is **not** a conforming CNCM KIR implementation or a substitute for
this wire contract. It MAY inform a later adapter after review.

## 11. Neural calibration and anti-circularity

`NEURAL_PROFILE` mode requires a calibration profile binding at least:

- exact model, checkpoint, tokenizer, weights, runtime, and dtype identities;
- code revision;
- layer, head, token position, hook site, and direction-vector identity;
- corpus manifest, rights, splits, seeds, and randomization;
- intervention coordinate and dose grid;
- full-scale method;
- fit and uncertainty methods;
- response-region rules, tolerances, controls, drift, expiry, and review state;
- a canonical profile digest.

The profile MUST declare that calibration and validation splits are disjoint
and that same-sample resistance reconstruction is prohibited. Those declarations
are necessary but not sufficient: a semantic validator MUST prove unequal
split identities, verify their manifests, bind every instrumented quantity's
calibration digest to the profile digest, and require a registered bridge before
native `I_attention_observed` is populated. Without a bridge the native-flow
field remains missing, even when neural activation was measured.

The model may use:

```text
y_activation_hat = alpha_dose / r_effective
```

only when `r_effective` has unit `alpha_per_activation`, carries uncertainty,
is fitted on a registered calibration split, and is evaluated on a disjoint
held-out split.

The same-sample construction is prohibited:

```text
r_same = alpha / y
y_hat = alpha / r_same
claim y_hat == y as validation
```

Software verification and empirical model validation remain separate.

## 12. Residuals, operating regions, and ASOM

For an admitted prediction:

```text
delta_I = I_obs - I_pred
```

A residual MAY rank follow-up probes. It cannot, from sign alone, identify a
hidden policy, bypass, opposition, cause, safety failure, or semantic defect.
Zero-compatible predictions and observations are censored under the registered
rule.

Operating region and semantic outcome are independent axes.

```text
operating_region:
    UNASSESSED | CUTOFF | ACTIVE | SATURATION | BREAKDOWN |
    NON_OHMIC | UNSTABLE

semantic_outcome:
    UNASSESSED | INTENDED | OPPOSITE | OFF_AXIS | UNKNOWN
```

ASOM is a mnemonic overlay only. `ACTIVE` does not imply `INTENDED`, and a flat
response has multiple possible causes. Diagnostics from stale, uncalibrated,
wrong-profile, cutoff, saturated, unstable, or semantically unassessed neural
records fail closed.

## 13. CAS-GEM retrieval-current model

For the proposed reconstructive-memory system:

```text
CuePacket                 = Cause
MemoryCapsule             = bias substrate
recall goal               = V_drive
candidate access limits   = R_retrieval
candidate work allocation = I_attention
reconstructed narrative   = Effect
```

One proposed decomposition is:

```text
R_retrieval_i = R_distance_i
              + R_decay_i
              + R_interference_i
              + R_anchor_conflict_i
              + R_policy_i
```

Interpretation remains bounded:

- one dominant eligible flow: prioritize that candidate for reconstruction;
- similar flows: preserve ambiguity or request another clue;
- all candidates below cutoff: return `NEEDS_INFORMATION`;
- high flow despite anchor conflict: flag saturation/model/topology probes;
- high flow with the wrong episode: classify semantic mismatch, not attention
  starvation.

For genuine alternative candidates with compatible endpoints, proposed
allocation weights are:

```text
w_i = I_i / sum(I_j)
```

`w_i` is a work-allocation share in the closed interval `[0,1]`, not posterior
truth probability. Exact-anchor conflicts, policy blocks, and verifier failures
remain hard gates: any one forces `eligible = false` and `w_i = 0`. The
allocation-cohort validator MUST prove that eligible sibling weights sum to one
under exact arithmetic, or all sum to zero when no candidate is eligible. Child
probes stay visible even when a parent equivalent is displayed.

The current CNCM exact `EpisodicRecord` and same-process exact-key recall remain
unchanged. CAS-GEM records stay outside the kernel until capsule, cue,
reconstruction, evidence, authenticated-import, and write-back contracts are
separately admitted.

## 14. Stateful retrieval-resistance extension

A future profile MAY declare:

```text
x_(t+1) = F_profile(x_t, input_t, observation_t, context_t; theta)
R_effective,t = G_profile(x_t; theta)
```

The state record must define initialization, update law, sampling interval,
reset behavior, drift, uncertainty, provenance, and versioning. It is admitted
only if it predicts held-out hysteresis or path dependence better than a matched
memoryless baseline.

Repeated reconstruction MUST NOT increase factual confidence without new
evidence or trusted correction. A generated recollection MUST NOT overwrite its
originating capsule. The word `memristive` remains a research analogy until the
specified held-out evidence is earned.

## 15. Held-out experiment program

| Experiment | Manipulation | Required separate outcomes |
|---|---|---|
| A - lexical resistance | known, rare, locally defined, invented, and misleading near-spelling terms | cortex activation, native gate flow, grounding correctness, commitment outcome |
| B - role binding | active, passive-equivalent, and role-reversed triplets | flow, role assignment, semantic correctness, operating region |
| C - ambiguity load line | progressively ambiguous references, context conflict, and missing referents | direct-answer allocation, clarification allocation, abstention, correctness |
| D - cortex scale | 0.5B, 1.5B, and 3B under one frozen hardware/profile battery | capability resistance, semantic gain, false commitment, latency/resource resistance, memory footprint |
| E - CAS-GEM cue strength | vague, distinctive, corroborating, and contradictory clues | retrieval rank, anchor conflict, ambiguity, unsupported-detail rate |
| F - history dependence | rehearsal, delay, conflict, and trusted correction schedules | stateful versus matched memoryless held-out prediction |

Negative outcomes, missingness, exclusions, cutoff, saturation, instability,
drift, and calibration failure MUST be retained.

## 16. Foundry visualization

A future Foundry view MAY show:

- Drive rails entering each eligible path;
- resistance decomposition without implying physical components;
- local attention flow at every test point;
- CJT gain and semantic effect as separate channels;
- branch fairness floor, allocation, consumption, and ceiling;
- RPM descent and return;
- competing memory-candidate allocations;
- residual rank and next-probe recommendations;
- verifier, commitment, and authority gates as visibly separate controls.

The visualization is an inspection surface. It cannot become evidence merely by
being visible, and it cannot authorize a state transition.

## 17. Local compiler and CAS-SDG boundary

The canonical local CAS compiler is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`

The canonical local CAS Synthetic Data Generator is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas-synthetic`

Future CAS-Ohm/CAS-GEM fixtures SHOULD use CAS-SDG for episodes, cues,
candidate branches, perturbations, and ground truth. Every embedded CAS
expression MUST independently pass the real compiler before the fixture is
called compiler-valid. Compiler success validates notation and declared static
semantics only; it does not establish memory truth, empirical validity, runtime
admission, or write authority.

The compiler and CAS-SDG remain external read-only dependencies until a
versioned adapter and artifact-digest boundary is implemented in this homebase.
No dependency is taken on the protected sibling `CAS_RRK_v0.1`.

## 18. Admission gates

The protocol progresses only through cumulative gates:

1. **Contract gate:** this protocol, the record schema, quantity/unit registry,
   and source disposition are frozen.
2. **Validator gate:** the stage-record shape validator, kind/unit compatibility
   validator, exact arithmetic validator, mode/profile validator, semantic-source
   binder, CAS-GEM hard-gate validator, and hash-chain verifier pass positive and
   negative vectors.
3. **Observer gate:** a deterministic sidecar binds to sealed trace events and
   removal invariance is proven.
4. **Native simulation gate:** exact arithmetic, topology checks, local-flow
   traces, cutoff/saturation fixtures, and deterministic replay pass.
5. **Allocator gate:** a distinct `AttentionAllocationPlan` schema exists and
   fairness, ceilings, conservation of allocated budget, stable tie-breaking,
   starvation controls, and removal/neutral-profile equivalence pass.
6. **CJT binding gate:** stable compiled component identities, test points,
   gain profiles, and semantic-effect references exist.
7. **Neural gate:** preregistered calibration, disjoint held-out validation,
   controls, uncertainty, drift, and negative-outcome retention pass.
8. **CAS-GEM gate:** cue/capsule/evidence contracts, hard-anchor enforcement,
   ambiguity behavior, false-detail controls, and memoryless/stateful ablations
   pass.
9. **Authority gate:** a new authority/KIR version explicitly admits only the
   intended allocation reads while retaining all truth, proof, meaning,
   commitment, memory-write, action, and self-modification prohibitions.

Passing an earlier gate grants no later capability or authority.

## 19. Current implementation boundary

For CNCM-RRK runtime 0.1.0:

- this protocol and `cncm.cas-ohm-stage/0.1` are contract artifacts only;
- no CAS-Ohm quantity or stage record is present in `MachineState`, `Intent`,
  `TraceEvent`, or `EvidencePacket`; the existing evidence flag
  `cas_ohm_runtime_authority = false` is only a negative boundary assertion;
- no CAS-Ohm semantic validator, sidecar-chain verifier, retained record, or
  `AttentionAllocationPlan` exists;
- the scheduler does not read CAS-Ohm;
- no CJT runtime identity is frozen;
- no neural calibration profile is admitted;
- no CAS-GEM retrieval path exists;
- no CAS-Ohm or CAS-GEM grade, empirical result, safety result, or authority is
  earned.

That boundary is deliberate. It records the corrected destination without
misrepresenting the bounded demonstrator that exists today.
