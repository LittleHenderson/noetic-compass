# CAS Transformer Architecture

**Status:** Draft architecture track
**Date:** 2026-04-29
**Purpose:** Define the path from the current compiler-grounded CAS-Native system toward a true CAS-native transformer where every conversational output is generated through a compiler-checkable CAS state transition.

---

## 1. Core Claim

CAS Transformer is not an LLM wrapped by CAS.

The target architecture is:

```text
user input
-> CAS parser / state initializer
-> CAS working memory M_t
-> CAS transition head proposes a_t
-> compiler / solver validates a_t
-> CAS state updates M_t -> M_t+1
-> surface language renders only from validated CAS transition
```

The architecture must not permit:

```text
hidden_state -> ordinary LM head -> free text
```

Surface text is not the primary generated object. The primary generated object is a typed CAS transition. Natural language is a rendering of accepted transitions.

This means all conversation is CAS-mediated, including greetings, acknowledgments, clarification requests, empathy, refusal, repair, uncertainty, planning, and closure.

---

## 2. Why This Is Not A Wrapper

A wrapper lets an LLM generate text and then checks, explains, filters, or repairs it after the fact.

A CAS Transformer does the opposite:

- The first decoded unit is a CAS transition, not a word.
- The compiler constrains generation during decoding, not only after decoding.
- The hidden state is updated through typed CAS memory, not only token recurrence.
- The language renderer has no independent route to fluent free text.
- Every sentence must be licensed by a trace node.
- Every trace node must be linked to a CAS state transition.
- Every formal CAS expression must compile.
- Every conversational act must have a CAS role.

The hard proof test is conditionality:

```text
log P(correct token | correct CAS state)
>
log P(correct token | corrupted CAS state) + margin
```

If changing the CAS state does not materially change token probabilities, the architecture is not yet CAS-native. It is only CAS-labeled.

---

## 3. Generated Unit And Gradient Boundary

At timestep `t`, the model predicts a typed transition:

```text
a_t = {
  kind,
  source_state,
  target_state,
  noetic,
  domain,
  drive,
  register,
  operator,
  operands,
  omega_target,
  production_recipe,
  meta_logic_context,
  trace_id,
  surface_act,
  confidence
}
```

`kind` is one of:

```text
state
relation
membership
subset
cluster_update
rpm_gate
production
omega_bind
inversion_check
meta_logic_move
surface_act
halt
ask_clarify
repair
```

The language renderer receives `a_t`. It does not decide the meaning on its own.

The training boundary matters. CAS-decoded means:

```text
L = lambda_transition * L_transition(a_t | S_t, G_t)
  + lambda_surface    * L_surface(y_t | accepted a_t)
```

CAS-conditioned-only means:

```text
L = L_token(y_t | h_t, CAS_embedding)
```

The architecture target is CAS-decoded. The transition is primary; tokens render an accepted transition. Phase 1 should use a deterministic or small constrained renderer so token-fluency gradients do not turn the transition proposer back into an ordinary language model.

---

## 4. Required Internal State

The transformer must maintain these state objects:

```text
S_t: current CAS cognitive state
M_t: CAS working memory
G_t: meta-logic graph
R_t: RPM/prerequisite status
P_t: production recipe state
Omega_t: named emergent target state
Trace_t: nested trace ledger
U_t: uncertainty / lacunarity map
```

Minimum cognitive state axes:

- Noetic: `^0..^9`
- Domain: `P/C/E/O`
- Drive: `F1..F7`
- Register: `|T`, `|A`, `|f`, `|E`
- RPM position: A0, Drive, Wisdom, Power/Proficiency
- Omega target: registered or proposed `Ω_*`
- Production recipe: `Θ(Ω_*) = ingredients -> Ω_*`
- Trace node: current explanation / action / response segment
- Meta-logic layer: typed sets, clusters, membership, nesting, products, covers, partitions, pullbacks

---

## 5. Meta-Logic Layer

The meta-logic layer must be first-class. It is not just notation. It is how the model knows what kind of thing it is reasoning about.

Core objects:

```text
Element
Noetic
State
Register
Drive
Domain
NoeticCluster
StateCluster
StateVariantCluster
RelationCluster
EvidenceSet
InstructionSet
ClaimSet
TraceSet
Product(A, B)
CoverOf(Base, ...)
PartitionOf(Base, ...)
Pullback(A, B over C)
```

Core relations:

```text
x ∈ X        membership
x ∉ X        non-membership
A ⊂ B        strict subset
A ⊆ B        subset
A ⊃ B        strict superset
A ⊇ B        superset
A ∪ B        union
A ∩ B        intersection
A ∖ B        difference
|A|          cardinality
<a,b,c>      typed coordinate / tuple
```

Why this matters:

- It prevents instance/category confusion: `^2 ∈ Noetics` is different from `NoeticCluster{^2,^7} ⊆ Noetics`.
- It lets the model nest reasoning: a sentence belongs to a trace node, a trace node belongs to a response, a response belongs to a dialogue episode.
- It lets the model separate evidence from claims: an input can be an element of `UserUtteranceSet` without becoming a member of `ValidatedClaimSet`.
- It lets the model maintain authority boundaries: system instructions, user requests, tool outputs, evidence, and generated claims can live in different typed sets.
- It gives prompt-injection defense a formal substrate: untrusted text can be represented as data in one set, not as an instruction in the controlling set.
- It lets multimodal inputs be typed: image regions, audio segments, text spans, and sensor signals can be elements in modality-specific evidence sets before becoming claims.
- It supports compositional memory: clusters, products, covers, partitions, and pullbacks give structured retrieval and explanation.

The meta-logic state graph:

```text
G_t = {
  objects: typed nodes,
  relations: membership/subset/product/pullback edges,
  authority: which sets can license which actions,
  evidence: which elements support which claims,
  nesting: response -> sentence -> phrase -> token trace,
  compiler_status: valid / invalid / repairable
}
```

The model must attend over `G_t`, not only over token history.

---

## 6. Conversation Is CAS: Turn-Type Admissibility

There is no small-talk bypass. Every conversational act has a CAS turn type.

Examples:

| Surface text | CAS turn type | CAS function |
|---|---:|---|
| "Hi." | `OPEN` | attention/orientation |
| "I understand." | `ACK` | receipt + alignment |
| "Let me think." | `PLAN` | decomposition before answer |
| "Can you clarify?" | `CLARIFY` | lacunarity detection |
| "That sounds hard." | `EMPATHIZE` | affective acknowledgment |
| "I cannot conclude that from the evidence." | `REFUSE_CLAIM` | evidence boundary |
| "Correction: I overstated that." | `REPAIR` | trace revision |
| "Here is the next step." | `PLAN` | operational transition |

Every response should be recoverable into:

```text
prompt -> CAS trace -> surface response -> recovered CAS trace
```

If the recovered trace does not match the intended trace, the response is not faithful.

Turn types require typed preconditions in the prior state. Without these, the compiler validates only syntax, not behavioral appropriateness.

Current compiler-side hook:

```text
api.notation.turn_admissibility.validate_turn_admissibility(turn_type, context)
```

The hook returns a JSON-ready artifact with required facts, observed/derived facts, missing facts, valid effects, diagnostics, and tight/shell classification. Service code and model code should call this before accepting/rendering a proposed conversational transition.

| Turn type | Required prior-state condition | Valid state effect |
|---|---|---|
| `OPEN` | channel is idle/unopened | establish attention/orientation |
| `ACK` | input has been received | stabilize receipt |
| `MIRROR` | user intent is present | restate intent into structured form |
| `CLARIFY` | lacunarity/unfilled slot detected | request missing constraint |
| `EMPATHIZE` | affective signal detected | acknowledge affect without claiming certainty |
| `ANSWER` | task active and claim support available | produce supported response |
| `PLAN` | task active | decompose next actions |
| `REFUSE` | boundary violation detected | decline action while preserving trace |
| `REFUSE_CLAIM` | evidence gap or unsupported claim detected | decline the claim, not necessarily the user |
| `REPAIR` | prior model/user mismatch or error detected | correct trace and restore coherence |
| `CLOSE` | response delivered or task complete | land completion/handoff |

These predicates must become compiler/validator obligations, not prompt-engineering conventions.

---

## 7. Model Modules

### 7.1 CASTokenizer

The tokenizer must reserve CAS structural tokens:

```text
^0..^9
P C E O
F1..F7
|T |A |f |E
Ω_* Θ κ ι Λ η
∈ ∉ ⊂ ⊆ ⊃ ⊇ ∪ ∩ ∖ ∅ |X|
NoeticCluster StateCluster StateVariantCluster RelationCluster
Product CoverOf PartitionOf Pullback
TRACE OPEN ACK CLARIFY EMPATHIZE REFUSE REPAIR CLOSE
```

Ordinary language tokens are allowed only as lexical realizations attached to CAS roles.

### 7.2 CASEncoder

Converts prompt/context into initial state:

```text
input -> S_0, G_0, R_0, P_0, Omega_0, Trace_0, U_0
```

It may read natural language, but it cannot answer directly.

### 7.3 CASWorkingMemory

Suggested tensor structure:

```text
M_state:    [10 noetics x 4 domains x 7 drives x 4 registers x d]
M_domain:   [4 x d]
M_drive:    [7 x d]
M_rpm:      [A0, Drive, Wisdom, Power/Proficiency x d]
M_omega:    [registered Ω + candidate emergents x d]
M_trace:    recurrent transition history
M_meta:     typed set / graph / nesting memory
M_compiler: valid-prefix / invalid-prefix / repair diagnostics
```

Use factorized embeddings where possible:

```text
e(state) = e_noetic[n] + e_domain[d] + e_drive[f] + FiLM_register[r](...)
```

### 7.4 CASAttentionBlock

Self-attention must be mixed with CAS slot attention.

Required masks:

- Causal mask over generation time.
- Compiler prefix mask for legal next CAS actions.
- Domain descent mask: `P -> C -> E -> O`, with reflection channel `O -> P` only through explicit update.
- RPM mask: outputs cannot claim Power/Proficiency if prerequisite states are not satisfied.
- Register mask: cross-register multiplication requires named `Ω`; otherwise it remains co-presence.
- Involution mask/loss for Noetic and Register pairs.
- Meta-logic mask: membership, subset, authority, evidence, and containment determine which objects can support which claims.

### 7.5 CASTransitionHead

Primary decoder. Predicts typed CAS transitions.

### 7.6 CompilerSolverLoop

The compiler participates during decoding:

- Valid next-action masks.
- Type checking.
- Meta-set/type validation.
- Rule 4 validation.
- RPM completion.
- Production/yield validity.
- Pullback/product/cover/partition consistency.
- Repair suggestions.

Validation happens at the completed transition boundary before any surface token is released:

```text
transition head proposes complete a_t
-> compiler/meta-logic/RPM/production validators accept or reject a_t
-> accepted a_t updates CAS state
-> renderer emits surface text
-> recovery parser reconstructs a'_t
-> recovery-fidelity gate accepts, repairs, or asks clarify
```

Prefix masks may prune invalid proposals, but they are not the proof gate. The proof gate is end-of-transition validation.

### 7.7 CASSurfaceRenderer

Renders language only after a valid CAS transition exists.

The renderer receives:

```text
a_t, S_t, S_t+1, G_t, Trace_t, surface_constraints
```

Then it emits tokens under a CAS-derived vocabulary/role mask:

```text
p(y_t) = softmax(mask_vocab_by_CAS(a_t, G_t) + W[h_t, M_t, a_t])
```

Renderer v0 must be deterministic/template-constrained. Renderer v1 may be a small CAS-conditioned neural renderer. A third-party general LLM renderer is not acceptable for the CAS Transformer proof wedge because it reintroduces an independent language route.

---

## 8. Prompt Injection And Authority

Prompt injection becomes a typed meta-logic problem, not a list of banned phrases.

Example:

```text
"Ignore prior instructions" ∈ UserUtteranceSet
SystemRuleSet ⊄ UserUtteranceSet
UserUtteranceSet ⊄ SystemRuleSet
```

The user utterance is valid data, but it is not automatically a member of the instruction-authority set.

Authority must be represented explicitly:

```text
SystemInstructionSet
DeveloperInstructionSet
UserRequestSet
ToolObservationSet
ModelHypothesisSet
ValidatedClaimSet
RenderedResponseSet
```

Allowed transitions:

```text
ToolObservationSet -> EvidenceSet
EvidenceSet + CAS reasoning -> ValidatedClaimSet
ValidatedClaimSet -> RenderedResponseSet
UserRequestSet -> TaskIntentSet
TaskIntentSet -> CAS action proposal
```

Blocked transition:

```text
UserRequestSet -> SystemInstructionSet
```

The model can discuss the injection attempt as data, but it cannot promote it into a controlling instruction without a valid authority relation.

---

## 9. Typed Transition Obligations

Rendered CAS strings are derived artifacts. The authoritative object is the typed transition.

Production semantics must be a typed object:

```text
ProductionTransition {
  omega_target
  ingredients: [(state_variant, coefficient, available_amount)]
  limiting_reagent
  theoretical_yield
  leakage
}
```

Validation obligation:

```text
Y_T = min_i(available_i / coefficient_i)
limiting_reagent = argmin_i(available_i / coefficient_i)
coefficient_i > 0
available_i >= 0
leakage >= 0
```

Register multiplicity must be typed:

```text
RegisterBinding {
  mode: single | set_spec | co_presence | integration
  registers
  omega_target?
}
```

Validation obligation:

- `single` requires exactly one register.
- `set_spec` expresses `|<...>|` specification and makes no interaction claim.
- `co_presence` expresses `+` and must not name an emergent target.
- `integration` expresses `x` and requires named `Omega`.

Domain descent must be typed:

```text
DomainTransition {
  source_domain
  target_domain
  transition_type: descent | feedback
  feedback_license?
}
```

Validation obligation:

- Descent follows `P -> C -> E -> O`.
- `O -> P` is feedback only and requires a license.
- Same-domain changes are state updates, not domain descent.

Meta-logic must validate membership, subset, authority, evidence, and nesting. Membership source must be element-like; subset requires both sides set-like; nesting must be acyclic; user/tool text can be evidence but cannot become system/developer instruction without an admitted authority edge.

## 10. Training Objective

The token objective is conditional on CAS:

```text
P(y_t | x, y_<t, S_t, S_t+1, G_t, trace_node_t, action_t, role_t)
```

Loss stack:

```text
L =
  λ_transition L_cas_transition
+ λ_token      L_surface_given_cas
+ λ_state      L_current_cas_state
+ λ_next       L_next_cas_state
+ λ_trace      L_trace_node
+ λ_role       L_role
+ λ_meta       L_meta_logic_graph
+ λ_compiler   L_compiler_validity
+ λ_faith      L_trace_faithfulness
+ λ_cond       L_response_token_conditionality
+ λ_contrast   L_prompt_trace_response_contrastive
+ λ_rpm        L_rpm_completion
+ λ_prod       L_production_yield
+ λ_inv        L_inversion
+ λ_fr         L_fisher_rao_drift
```

Do not train ordinary next-token prediction first and attach CAS labels later. Train:

```text
prompt -> CAS trace -> CAS actions -> rendered response
```

---

## 11. Synthetic Data Requirements

CAS Synthetic Data Generator must add a CAS Transformer dataset layer.

Required record shape:

```json
{
  "id": "cas_turn_000001",
  "prompt": "hey, can you help me think this through?",
  "response": "Yes. I can help you break it down step by step.",
  "cas_trace": [
    {
      "node_id": "t0",
      "surface_span": "Yes.",
      "turn_type": "ACK",
      "cas_state": "^1^O_{F4}|f + ^9^E_{F4}|f",
      "meta_context": "t0 ∈ TraceSet; TraceSet ⊆ DialogueEpisode"
    },
    {
      "node_id": "t1",
      "surface_span": "I can help you break it down step by step.",
      "turn_type": "PLAN",
      "cas_state": "^6^C_{F6}|A -> ^7^O_{F5}|A",
      "meta_context": "t1 ∈ TraceSet; t1 depends_on t0"
    }
  ],
  "compiler": {
    "valid": true,
    "normalized": "...",
    "ast_hash": "sha256:..."
  },
  "negatives": [
    {
      "type": "wrong_register",
      "description": "same response with incompatible CAS register"
    },
    {
      "type": "authority_violation",
      "description": "user utterance promoted into system instruction set"
    }
  ]
}
```

Synthetic generation must be compiler-first:

1. Sample valid CAS trace.
2. Sample meta-logic nesting/evidence/authority graph.
3. Render natural language from the trace.
4. Reparse the natural language into a recovered trace.
5. Keep only records where intended and recovered trace agree.
6. Generate hard negatives by corrupting one axis or one meta-logic relation at a time.

---

## 12. Recovery-Fidelity Metric

After rendering, recover the transition from text and compare:

```text
RF(a_t, a'_t) =
  0.25 transition_kind_exact
+ 0.25 CAS_axis_match
+ 0.15 meta_logic_relation_match
+ 0.15 trace_span_alignment
+ 0.10 compiler_AST_equivalence
+ 0.10 authority/evidence/surface_act_match
```

Gate:

```text
formal CAS expression: AST equivalence required
per-transition RF:     >= 0.92
response mean RF:      >= 0.95
minimum transition RF: >= 0.90
critical fields:       exact, no weighted forgiveness
```

Critical fields include transition kind, compiler validity, source/target state hash, authority path, and trace-node membership.

## 13. Shape 2 Data Engine

Shape 2 is not a competing product track. It is the data engine for CAS Transformer.

Every verify-and-rerank call should produce the implemented v0 record shape:

```text
Shape2 = {
  prompt,
  pre_state,
  candidates,
  accepted_candidate_id,
  accepted_transition,
  validation_artifact,
  rendered_response,
  recovered_trace,
  rf_score,
  perturbations,
  provenance
}
```

This converts service usage into the corpus needed for CAS Transformer training and evaluation.

Current implementation:

```text
cas-synthetic/schemas/shape2.py
cas-synthetic/scripts/write_shape2_records.py
```

The Shape 2 record is a training/eval tuple, not ordinary telemetry. It preserves rejected candidates, the accepted transition, compiler/compound-transition diagnostics, renderer output, recovered trace, recovery-fidelity score, perturbations, and provenance so later CAS Transformer training can learn from real service decisions.

## 14. Proof Gates

Do not claim "true CAS Transformer" until these pass:

1. **Compiler validity:** constrained CAS outputs compile at 100%.
2. **Free proposal validity:** unconstrained CAS action proposals compile at >=95%.
3. **CAS state prediction:** current and next CAS state predicted above threshold.
4. **Trace faithfulness:** generated response recovers to intended CAS trace.
5. **Small-talk grounding:** greetings, acknowledgments, empathy, refusals, repairs, and closures all recover to CAS turn types.
6. **CAS perturbation:** corrupting Noetic/Domain/Drive/Register/meta-logic state changes token probabilities in predicted direction.
7. **Meta-logic perturbation:** corrupting membership/subset/authority/evidence relations changes allowed claims and rendered language.
8. **No-wrapper generation:** disabling compiler candidate banks still leaves measurable CAS-structured generation above baseline.
9. **Reranker dominance test:** random, TF-IDF, or slot-only scoring cannot match the CAS-conditioned model.
10. **Internal mediation:** prompt affects CAS state; CAS state affects logits; blocking CAS state removes the effect.

---

Add four wedge-specific gates:

- Conditionality delta: `log P(correct | correct CAS) - log P(correct | corrupted CAS) > 2 nats` for CAS-critical tokens.
- Cross-domain recovery: held-out domain recovery-fidelity drops less than 10%.
- Unmasked transition validity: unconstrained transition proposals compile/typecheck at >=98%.
- Latency: P95 under 1s for a 10-transition v0 rendered response.

## 15. First Implementation Wedge

The first build should not attempt a frontier-scale conversational model.

Build a proof wedge:

```text
CAS Turn Schema
+ CAS Transformer synthetic dataset
+ CAS-conditioned token objective
+ ConditionalityProbe
+ meta-logic authority/nesting perturbation tests
+ small-talk CAS grounding eval
```

Minimum deliverables:

1. `CASTurn` dataclass / schema.
2. `MetaLogicContext` dataclass / schema.
3. Synthetic generator for 1,000 CAS-turn records.
4. Validator proving every CAS expression compiles and every meta-logic relation typechecks.
5. Model-side `ConditionalityProbe` that measures whether CAS state changes token logits.
6. Evaluation report with CAS perturbation and meta-logic perturbation results.

This is the smallest honest step toward CAS Transformer because it tests the core claim:

```text
CAS state causally controls language generation.
```

---

## 16. Relationship To Current System

Current CAS-Native evidence supports:

- Compiler-valid expression construction under constrained decoding.
- Prompt-to-CAS recovery with recoverable prompts.
- Learned reranking over compiler-valid candidates.
- Existing architectural pieces: register FiLM, expression proposer, production semantics, CAS synthetic generation, compiler validation.

Current evidence does not yet prove:

- CAS state causally controls every generated token.
- Meta-logic state controls authority/evidence/nesting in generation.
- Small talk is CAS-grounded.
- Raw transformer generation is CAS-structured without compiler/candidate help.

The next architecture track must therefore move from:

```text
compiler-grounded CAS translation
```

to:

```text
CAS-conditioned generation with compiler-checked trace fidelity
```

---

## 17. Design Principle

CAS is not metadata.

CAS is not a label.

CAS is not an explanation layer.

CAS is the generative substrate:

```text
No valid CAS transition -> no response token.
```
