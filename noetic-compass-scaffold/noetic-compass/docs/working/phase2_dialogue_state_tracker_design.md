# Version B — Phase 2: Dialogue State Tracker (DST) Design

**Status:** initial design draft
**Owner:** Version B conversational track (DST sub-track)
**Decision date:** 2026-05-04 — drafted in parallel with Phase 1 SDG per `memory/project_version_b_conversational_plan.md` and the user's day-one parallel-execution ratification.
**Companion docs:**
- `docs/working/version_b_phase1_sdg_plan.md` — SDG schema this DST consumes
- `docs/working/exposure_button_traceability_spec.md` — Mode 1/3/5/7 cross-cutting requirements
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — canonical Noetic / Register / v7.6 / v7.7 semantics

---

## 0. Scope statement

The Dialogue State Tracker is a new architectural component layered **on top of**
the existing K=9 structured-prediction model (93.2% canonical, frozen as of
2026-05-04). The DST is responsible for everything the K=9 model does not do:

- maintain a per-turn cognitive state vector that **persists across turns**
- track cross-turn transitions (e.g., CO-8 / CO-9 chains over time)
- model the speaker (user vs assistant; demographic + tonal axes from Phase 1)
- store dialogue history at the structured-token level
- emit the per-turn trace artifacts the exposure button (modes 1, 3, 5, 7)
  reads from

DST does NOT modify K=9 weights, K=9 inference, or K=9 outputs. K=9 is treated
as a pure function `(text, attention_mask) -> StructuredPrediction + logits`.
DST consumes the per-axis logit distributions and the StructuredPrediction tuple
and turns them into a session-level state machine.

---

## 1. Architecture overview

DST sits between the K=9 model and the (future Phase 3) NL Generation Head.
Per-turn inference flow:

```
                       +------------------------------+
                       |        Session Buffer        |
                       |  (in-memory rolling window)  |
                       +------+-------------+---------+
                              ^             |
                              |             | prev-turn context
                              |             v
  user_text  +------------+   |   +-------------------+   +-------------------+
  --------->| K=9 frozen |---+-->| Dialogue State    |-->| (Phase 3) NL Gen  |
            | encoder +  |       | Tracker (DST)     |   |   Head            |
            | head       |       |                   |   +-------------------+
            +-----+------+       |  - state diff      |             |
                  |              |  - transition kind |             |
                  | hidden       |  - speaker model   |             v
                  | states +     |  - inversion scan  |        rendered_text
                  | per-axis     |  - trace assembly  |             +
                  | logits       +---------+----------+         trace record
                  |                        |
                  |                        v
                  |              +--------------------+
                  +------------->| Hook Capture Layer |
                                 | (sparse top-K)     |
                                 +--------------------+
                                          |
                                          v
                                    activation snapshot
                                    (Mode 7 substrate)
```

Key properties:

- **K=9 stays frozen.** All hooks register against existing named submodules.
  No graph edits. Phase 2 commits to never modifying the Phase 0/1 baseline.
- **DST is single-process, single-session.** Multi-tenant deployment lives at
  the API tier (Phase 6). Phase 2 ships a session-scoped Python object.
- **Trace is computed lazily but emitted eagerly.** Every turn produces a
  `TurnRecord` whose serialization is a first-class artifact, equal in status
  to the rendered text. This is the exposure-button non-negotiable.

### Inputs (per turn)

- `user_text` (str)
- `speaker` (`'user' | 'assistant'`) — DST is invoked once per utterance
  regardless of speaker; the assistant turn invocation is for state-tracking
  the model's own output, not for reading the user
- `conversation_id`, `turn_index` (int), `prev_turn_id` (str | None)
- optional `demographic_profile`, `tonal_profile` (Phase 1 axes; see
  `version_b_phase1_sdg_plan.md` T2/T3) — surfaced to Phase 5 coherence eval
- K=9 tensors: `hidden_states`, `attention_mask`, `axis_logits` dict
- session buffer (managed by DST itself; not a caller input)

### Outputs (per turn)

A single `TurnRecord` (Section 2 below) plus side effects:

- session buffer updated with the new TurnRecord
- session idea log updated with any new CAS expressions referenced
- inversion-scan running statistics updated
- sparse top-K activation snapshot captured for Mode 7

The TurnRecord is what downstream renders the exposure modes from. It is the
entire interface surface of the DST.

### Position in inference pipeline

Phase 0 baseline:    `text -> K=9 encoder -> head -> StructuredPrediction`
Phase 2 (this doc):  `text -> K=9 encoder -> head -> DST -> TurnRecord`
Phase 3 (later):     `text -> K=9 encoder -> head -> DST -> NL Gen Head -> (TurnRecord, rendered_text)`

DST is purely additive on Phase 0, and Phase 3 reads DST outputs to render. No
phase rewrites earlier phases.

---

## 2. State representation

The DST's primary persistent object is the **TurnRecord**. The session buffer
is `list[TurnRecord]` plus derived running aggregates.

### 2.1 TurnRecord (per-turn, immutable once written)

```
TurnRecord:
  # identity
  conversation_id        : str
  turn_index             : int           # 0-based
  turn_id                : str           # uuid4
  prev_turn_id           : str | None
  speaker                : 'user' | 'assistant'
  timestamp              : iso8601 str

  # raw I/O
  raw_input_text         : str           # the speaker's utterance verbatim
  raw_output_text        : str | None    # set only on assistant turns once
                                         # Phase 3 NL Gen Head exists

  # structured trace (matches exposure mode 3 stages)
  parsed_intent_cas      : str           # CAS expression form of input
  pre_state              : CognitiveState         # state BEFORE this turn
  applied_operators      : list[OperatorApplication]
                                         # ordered, with admissibility result
  post_state             : CognitiveState         # state AFTER this turn
  output_cas             : str | None             # the CAS form of reply
  compiler_validation    : CompilerResult         # ack | error + message

  # transition machinery
  transition_kind        : TransitionKind         # one of the 7; see Section 3
  transition_evidence    : dict[str, Any]         # diff that justified the kind

  # demographic + tonal axes (passthrough from Phase 1 input or inferred)
  demographic_profile    : DemographicProfile | None
  tonal_profile          : TonalProfile | None

  # K=9 axis logits + top-K alternatives (Mode 6 substrate)
  axis_distributions     : AxisDistributions      # per-axis softmax + topK

  # inversion scan deltas attributable to this turn (Mode 5 substrate)
  inversion_axis_values  : InversionAxisValues    # 7-axis; this-turn snapshot

  # network attribution pointer (Mode 7 substrate)
  activation_snapshot_ref: str | None             # opaque handle to sparse
                                                  # top-K capture; not the
                                                  # data itself, just a key
```

### 2.2 CognitiveState (the per-turn vector)

CognitiveState is the mathematical object the DST persists across turns. It
matches the `CognitiveStateData` shape consumed by
`dashboard/src/components/RadialArchitectureDisplay.tsx` (Mode 1 renderer)
**1:1 with no translation layer** — the DST output is literally what the
component reads.

```
CognitiveState:
  # 40 cognitive states = 10 Noetics x 4 Domains
  cells           : dict[(Noetic, Domain), float]
                    # 40 entries; values in open simplex S°_I = Delta39°
                    # invariant: all values > 0, sum to 1 (Correction 4)

  # 7 core drives, F1..F7
  drives          : dict[Drive, float]            # 7 entries, [0, 1]

  # 4 phenomenological registers, T/A/f/E
  registers       : dict[Register, float]         # 4 entries, [0, 1]

  # ActivationMap form (Noetic -> Domain -> Register -> intensity)
  # this is what RadialArchitectureDisplay actually reads; derived from
  # cells x registers per CAS v7.5 spec
  activation_map  : ActivationMap

  # lacunarity bookkeeping — global voids, pair voids, selective voids,
  # involution imbalances. Renders as the lacunarity layer in Mode 1.
  lacunarity      : LacunarityData

  # optional human-readable label, for the radial display alt-text
  label           : str | None
```

The `cells` field is the open-simplex vector (Correction 4). On every write,
the DST validates strict positivity and normalization with a small floor
(eps ~ 1e-9 then renormalize) — this is a hard invariant and the DST raises
on violation rather than silently coercing.

### 2.3 OperatorApplication

```
OperatorApplication:
  operator        : Operator              # CO-0..CO-9
  source_state    : CognitiveStateRef     # cell or compound
  target_state    : CognitiveStateRef
  admissible      : bool                  # is_admissible(operator, source, target)
  admissibility_reason : str              # human-readable
  generative_op   : '+' | 'x' | None      # v7.7 operator discipline (Clarif. 10)
  emergent_label  : str | None            # set iff generative_op == 'x' AND a
                                          # named emergent (Omega) is licensed
```

### 2.4 AxisDistributions (Mode 6 substrate)

```
AxisDistributions:
  noetic            : Distribution        # softmax over 10 Noetics, top-K alt list
  domain            : Distribution        # softmax over 4 Domains
  drive             : Distribution        # softmax over 7 Drives
  register          : Distribution        # softmax over 4 Registers
  transition_kind   : Distribution        # softmax over 7 transition kinds
  expression_family : Distribution        # softmax over expression families

  # K is 5 by default; configurable via DST init.
Distribution:
  probabilities     : list[float]
  top_k             : list[(label, prob, rationale)]
```

### 2.5 InversionAxisValues (Mode 5 substrate)

```
InversionAxisValues:
  N : float    # operator/Noetic involution imbalance
  W : float    # domain precedence violation (P > C > E > O)
  F : float    # drive pair imbalance (F1<->F7, F2<->F6, F3<->F5)
  E : float    # state-vector entropy deficit
  S : float    # sub-drive cross-domain variance
  A : float    # pathway RPM chain violation
  P : float    # compound (multiple axes simultaneously, derived)

  # threshold flags (set by Phase 2; thresholds tunable)
  flags : dict[InversionAxis, bool]
```

### 2.6 SessionBuffer (the rolling persistent state)

```
SessionBuffer:
  conversation_id   : str
  turns             : list[TurnRecord]            # in arrival order
  current_state     : CognitiveState              # = turns[-1].post_state
  idea_log          : list[Idea]                  # for Mode 2 atlas
  inversion_running : InversionRunningStats       # smoothed across turns
  speaker_models    : dict[str, SpeakerModel]
```

### 2.7 SpeakerModel (Phase 2 minimum)

Phase 2 ships a deliberately small speaker model: the speaker's accumulated
^5-substrate sketch, modeled as a smoothed average of that speaker's
post_states. The pedagogical scope of ^5 Female is "we are the sum of our
experiences" (CLAUDE.md, Clarification 5); the speaker model is the operational
analog at session granularity. NOT cross-session — that's Phase 5+ territory.

```
SpeakerModel:
  speaker_id            : str
  turn_count            : int
  ema_state             : CognitiveState  # exponentially moving average of speaker's
                                          # post_states; alpha = 0.3 by default
  demographic_profile   : DemographicProfile | None  # if known
  tonal_profile_running : TonalProfile | None        # smoothed from per-turn
```

---

## 3. Transition operators (model-side)

Phase 1 SDG plan T5 defines the seven transition kinds from the
**generator's** perspective: deterministic CAS-expression operations that
produce labeled multi-turn training data. Phase 2 implements them from the
**model's** perspective: detection of which transition fired between two
adjacent turn states.

The seven kinds (matching T5):

```
persist        : same cells, possibly different framing
refine         : tighten domain or register; cells become more concentrated
                 along an existing peak
pivot          : top-Noetic or top-cell changes; cells reweight to a new mode
integrate      : a named emergent state appears (Omega) under x operator
                 (CAS v7.7 cross-register integration)
escalate       : urgency tonal axis rises; cells unchanged, intensities scaled
descend        : urgency drops; cells unchanged, intensities scaled
name_emergent  : prerequisite primitives compose under x with an explicit
                 emergent result (CAS v7.7 Clarification 10 Section 6 case 3)
```

### 3.1 Detection signal: state diff

The DST computes a structured diff between `prev_post_state` and
`curr_post_state`:

```
StateDiff:
  cells_l1                : float                 # L1 distance over 40-cell
  cells_top_shift         : (Noetic, Domain) -> (Noetic, Domain) | None
                                                    # whose argmax moved
  cells_entropy_delta     : float                 # H(curr) - H(prev)
  drives_l1               : float
  drives_top_shift        : Drive -> Drive | None
  registers_l1            : float
  registers_top_shift     : Register -> Register | None
  fisher_rao_geodesic     : float                 # 2*arccos(sum sqrt(p*q))
                                                    # Correction 4 metric
  emergent_appeared       : bool                  # any new Omega in post
  named_emergent_label    : str | None
  urgency_delta           : float | None          # if tonal_profile available
```

The Fisher-Rao geodesic is the primary distance signal because the state
space is an open simplex (Correction 4). L1 stays as a cheap secondary.

### 3.2 Detection rules (deterministic, not learned)

Phase 2 ships rule-based detection. Learned detection is Phase 4 territory.

```
1. emergent_appeared and named_emergent_label is not None
   -> name_emergent

2. emergent_appeared and named_emergent_label is None
   -> integrate

3. cells_top_shift is not None AND involves Noetic change
   -> pivot

4. cells_top_shift is None AND fisher_rao_geodesic < EPS_PERSIST
   AND |urgency_delta| < EPS_URGENCY
   -> persist

5. cells_top_shift is None AND fisher_rao_geodesic < EPS_REFINE
   AND register_top_shift is not None
   AND cells_entropy_delta < 0
   -> refine

6. urgency_delta > +EPS_URGENCY AND cells_l1 < EPS_PERSIST
   -> escalate

7. urgency_delta < -EPS_URGENCY AND cells_l1 < EPS_PERSIST
   -> descend

8. otherwise
   -> pivot   (default; conservative — surfaces a real change)
```

Default thresholds (subject to tuning during Phase 4 curriculum):
```
EPS_PERSIST  = 0.02   # Fisher-Rao geodesic
EPS_REFINE   = 0.10
EPS_URGENCY  = 0.15   # urgency activation difference
```

### 3.3 Transition evidence

For every turn, the DST writes `transition_evidence` as a dict with the
StateDiff fields and the matched rule index. This is what the Mode 3 trace
renderer shows when the user expands the "transition" stage of a turn.

### 3.4 Disagreement with K=9's transition_kind head

K=9 already predicts a `transition_kind` per turn. The DST's
rule-based detection runs over actual cross-turn state changes; K=9's head
runs over single-turn structure prediction. These can disagree.

Phase 2 policy: **DST detection wins for the persisted TurnRecord field.**
K=9's prediction is preserved in `axis_distributions.transition_kind` as the
single-turn read; the agreed-on transition_kind is the cross-turn one. If
they disagree by more than a configurable threshold (default: any disagreement
where K=9 confidence > 0.7 and DST rule is `pivot` default fallback), the DST
emits a `transition_disagreement` flag in `transition_evidence`. Phase 5
coherence eval picks this up as a metric.

---

## 4. Storage strategy

Two storage tiers, recommended default explicit.

### 4.1 In-memory rolling buffer (DEFAULT, always on)

```
SessionBuffer kept entirely in process memory.
- turns: list[TurnRecord] capped at SESSION_MAX_TURNS (default 200)
- when capped, oldest non-anchor turns evict (anchor = turn_index 0 + last K)
- current_state always recomputable from turns[-1]
- idea_log: deduped by cas_expression hash, capped at SESSION_MAX_IDEAS (500)
```

Pros: zero serialization overhead; sub-ms read for Mode 1/3 panels.
Cons: lost on process restart; no cross-process replay.

### 4.2 On-disk per-session JSONL (DEFAULT for Mode 7 forensic, optional for others)

```
sessions/{conversation_id}/turns.jsonl    # one TurnRecord per line
sessions/{conversation_id}/ideas.jsonl    # one Idea per line, append-only
sessions/{conversation_id}/activations/{turn_id}.npz
                                          # sparse top-K activation snapshot
sessions/{conversation_id}/session.json   # metadata: started_at, speakers,
                                          # max_turn, demographic_profile
```

Schema reused from Phase 1 SDG (`level3_conversation.schema.json`) extended
with the Phase 2 additions: `pre_state`, `post_state`, `applied_operators`,
`inversion_axis_values`, `activation_snapshot_ref`.

Pros: forensic Mode 7 replay, multi-process Phase 6 deployment, audit log,
full reconstructability of any past trace.
Cons: ~5-50 KB per turn for the TurnRecord; ~200 KB per turn for the
sparse activation snapshot. Storage cost scales linearly per session.

### 4.3 Recommendation

**Phase 2 default: in-memory always; on-disk gated by a `persist_trace=True`
constructor flag, defaulting to True for any session where Mode 7 forensic
replay-on-demand is in scope.**

Rationale:
- The exposure-button spec is explicit (Mode 7, last paragraph): "Replay with
  full capture" is an existing user affordance; Phase 2 must not foreclose it.
- 5-50 KB per turn is small enough that disk persistence is the right
  default. Opting out is for ephemeral testing, not production.
- The activation snapshot is the largest cost. Phase 2 commits to sparse
  top-K (K=32) per layer per token, which the exposure spec already names
  as the storage strategy. Estimated 200 KB per turn matches that spec.
- Replay-on-demand keeps `(input_text, rng_state, model_version)` in the
  session.json so a future deeper-than-stored attribution can rerun K=9
  with full activation capture. Trade: 50-200 ms latency per replay vs the
  ~24 MB per turn that full storage would cost.

### 4.4 Tradeoffs at scale

For Phase 6 production:
- in-memory only: cheapest, no audit, no Mode 7 forensic
- in-memory + on-disk: default; suitable for single-tenant or per-tenant
  isolated deployments
- DB-backed (Postgres + S3 for activations): Phase 6 multi-tenant scale-out;
  out of scope for Phase 2 to design

Phase 2 ships an abstract `TraceStore` interface so Phase 6 can swap the
backing store without touching DST internals. Concrete implementation in
Phase 2: `JsonlTraceStore`, `InMemoryTraceStore`.

---

## 5. Trace emission contract

The TurnRecord serializes to JSON. DST produces the following data shapes
matched 1:1 to existing dashboard renderers — no translation layer required.

### 5.1 Mode 1 (Cognitive State) — RadialArchitectureDisplay.tsx

Direct emission of `CognitiveStateData`:

```
turn_record.post_state -> {
  activations    : ActivationMap,   # Noetic -> Domain -> Register -> number
  drives         : { F1..F7: number },
  lacunarity     : LacunarityData,
  label          : str | None
}
```

The exact field names and TS types come from
`dashboard/src/lib/mandala_types.ts`. DST writes those names verbatim. No
adapter, no rename, no shape change.

### 5.2 Mode 2 (Idea Atlas) — IdeaAtlasPage.tsx

DST emits, on each turn, any new ideas to `session.idea_log`. Idea shape
matches the existing TS interface verbatim:

```
Idea = {
  id            : str,
  text          : str,
  cas_expression: str | null,
  cas_english   : str | null,
  created_at    : iso8601 str,
  compile_error : str | null
}
```

Edges are computed by the existing backend `api/routes/idea_atlas.py` from
the idea log; DST does not produce edges itself (it's session-shared and
dashboard renders on demand).

### 5.3 Mode 3 (Per-Utterance Trace) — NEW renderer

DST emits the full TurnRecord. The new renderer (Phase 6) reads:

```
TurnRecord -> {
  user_text           : raw_input_text,
  parsed_intent_cas   : parsed_intent_cas,
  pre_state           : CognitiveStateData,
  applied_operators   : list[OperatorApplication],
  post_state          : CognitiveStateData,
  output_cas          : output_cas,
  compiler_validation : compiler_validation,
  rendered_text       : raw_output_text     # populated by Phase 3
}
```

This contract is locked. Phase 3's NL Generation Head MUST populate
`raw_output_text` and MUST NOT remove or modify any other field. The trace
is first-class; the rendered text is co-equal, not a replacement.

### 5.4 Mode 5 (Inversion Scan) — NEW renderer

Per turn, DST emits `inversion_axis_values`. Per session, the renderer
consumes the running aggregate:

```
inversion_running = SessionBuffer.inversion_running -> {
  axes        : { N|W|F|E|S|A|P : float },     # smoothed
  flags       : { axis : bool },
  history     : [{ turn_index, axes, flags }]  # all turns, for radar overlay
}
```

The 7-axis radar in Phase 6 reads `axes` for current and `history` for
recent-window comparison.

### 5.5 Mode 7 (Network Attribution) — NEW renderer

Per turn, DST emits `activation_snapshot_ref` (an opaque handle).
Resolution to the actual snapshot data is via `TraceStore.load_activations(ref)`,
returning:

```
ActivationSnapshot:
  layer_activations  : dict[layer_name, sparse_topk_tensor]
  attention_patterns : dict[layer_name, attention_thumb]
  per_token_topk     : dict[token_idx, list[(neuron_id, activation)]]
  rng_state          : opaque blob          # for replay
  model_version_hash : str                  # K=9 checkpoint id
```

The renderer reads layer names matched to CAS-named architectural components
when the K=9 successor (Phase 4 onward) lands — DomainDescentAttention,
PrerequisiteGateLayer, FractalAttentionHead, CognitiveToposReasoner. Phase 2
does NOT add these layers; it only stands up the hook capture infra so when
those layers exist, no architecture rework is needed.

### 5.6 No-translation invariant

The DST emits TS-typed JSON. The dashboard reads it. There is exactly one
schema definition per shape, lived in:

- `dashboard/src/lib/mandala_types.ts` — Mode 1 / state shapes
- `dashboard/src/pages/IdeaAtlasPage.tsx` (`Idea`, `AtlasEdge`) — Mode 2
- new `dashboard/src/lib/trace_types.ts` — Mode 3, 5, 7 (Phase 6 task)

Phase 2 adds a Python-side `cas_native/dst/trace_schema.py` that mirrors
those TS types. Round-trip JSON tests are CI-blocking.

---

## 6. Hook integration for Mode 7

Mode 7 (Network Attribution) is the densest exposure surface and the one
most easily broken by upstream architecture decisions. Phase 2 lays the
foundation; Phase 5+ research builds on it.

### 6.1 Hook attachment points

PyTorch forward hooks register against named submodules of K=9 at DST
construction time, before any inference call. The DST owns the hook
lifecycle: register on first turn, unregister on session close.

```
HookRegistry.attach(model, layer_filter)
  for name, module in model.named_modules():
    if layer_filter(name, module):
      handle = module.register_forward_hook(_capture_hook(name))
      handles.append((name, handle))
```

Phase 2 ships a default `layer_filter` covering:
- the K=9 encoder's transformer blocks (every block, attention + MLP)
- the StructuredPredictionHead's `backbone` Sequential
- every per-axis head (`turn_type_head`, `noetic_head`, etc., from
  `cas-native/model/structured_prediction.py`)

When Phase 4+ adds CAS-named architectural components
(DomainDescentAttention, PrerequisiteGateLayer, FractalAttentionHead,
CognitiveToposReasoner), the same registry mechanism picks them up by name
match — no DST code changes required.

### 6.2 Capture hook semantics

```
def _capture_hook(layer_name):
  def hook(module, input, output):
    if not session.capturing:
      return
    snapshot = sparse_topk(output, k=session.topk_k)   # default K=32
    session.layer_buffer[layer_name] = snapshot
  return hook
```

Per-token top-K storage: for each token position, record the K most-active
neurons and their activation values. Sparse representation (indices +
values), not dense tensor. Estimated ~200 KB per turn per the exposure spec.

### 6.3 Hook lifecycle and idempotency

- Hooks are registered exactly once per (DST instance, model instance) pair.
- DST `__enter__` registers, DST `__exit__` (or explicit `close()`)
  unregisters every handle, even on exception.
- Re-attaching to a model that already has a DST raises (no double capture).
- A `session.capturing` flag gates whether hooks actually write — defaults
  True; can be flipped False for benchmark runs that want pure inference
  latency measurements.

### 6.4 Phase 5+ sparse autoencoder track

The exposure spec (Mode 7 last paragraph) commits a Phase 5+ research
track: train sparse autoencoders on the locked Phase 6 model's captured
activations to discover interpretable features, label features in
CAS-aligned terms.

Phase 2's contribution: capture infra that produces SAE-ready training
data without architectural rework. Specifically:

- captured activations stored in shape SAEs expect (token_position,
  neuron_index, activation_value); not aggregated, not dense
- per-turn provenance preserved (TurnRecord links snapshot -> input text +
  CAS state); SAE training pipeline can subset by Noetic/Domain/Drive
- model_version_hash stored with every snapshot, so SAE training is reproducible
  across K=9 checkpoint versions

The SAE itself is NOT Phase 2 work. Phase 2's claim is that Phase 5+ can
do that work without retraining or re-instrumenting the model.

---

## 7. What this design does NOT do

Explicit non-goals to prevent scope drift:

1. **Multi-turn training curriculum (Phase 4).** DST does not produce
   training-time loss signals. Phase 4 will read DST traces during
   curriculum-driven training, but Phase 2 is inference-time only.

2. **NL Generation Head (Phase 3).** DST does not render text. The
   `raw_output_text` field is reserved and populated by Phase 3 once that
   component exists. Until then, assistant TurnRecords carry None there.

3. **Coherence eval metrics (Phase 5).** DST emits the substrate (trace
   records, transition disagreements, recipe slots) that Phase 5 metrics
   read. Phase 2 does not implement the metrics.

4. **K=9 model changes.** DST is read-only on K=9. No fine-tuning, no
   weight updates, no architectural edits. K=9 is treated as a stable
   pure function for Phase 2's lifetime.

5. **Cross-session memory.** SpeakerModel is per-session. Cross-session
   ^5-substrate accumulation (the "we are the sum of our experiences" full
   pedagogical scope) is Phase 5+ research territory, requires separate
   privacy/IP review per CLAUDE.md.

6. **Real-time inversion alerts as UI.** DST emits inversion axis values
   per turn; Phase 6's UI surface decides when an alert renders. DST
   does not push notifications, does not own the UI thread.

7. **Production recipe inference (Mode 4).** DST records when an outcome-
   naming utterance occurs and stores the CAS interpretation, but recipe
   instantiation Theta(Omega) is a CAS v7.6 operation that Phase 4+ adds
   as model capability. Phase 2 reserves a `recipe_ref` field on
   TurnRecord, populated by None.

8. **Demographic axis enforcement.** DST passes demographic_profile and
   tonal_profile through from input to TurnRecord. The robustness
   guarantee (CAS expression invariance under axis change) is enforced by
   Phase 1 SDG eval gate (T7), not by DST.

---

## 8. Open questions

Flagged for user judgment before Phase 2 implementation begins:

1. **Speaker model EMA alpha (default 0.3).** Higher alpha makes the
   speaker model react faster to recent turns; lower alpha makes it more
   stable. 0.3 is a guess from typical chat-session lengths (10-50 turns).
   Want a default, want it tuned, or want it adaptive?

2. **Transition rule fallback to `pivot`.** Current rule 8 in Section 3.2
   makes any unmatched diff a `pivot`. Alternative: emit a new
   `unclassified` kind, surface it to Phase 4 curriculum as a labeling
   gap. Risk: `unclassified` makes downstream renderers handle a 9th case
   they were not designed for.

3. **Fisher-Rao thresholds (EPS_PERSIST=0.02, EPS_REFINE=0.10).** These
   are pre-data guesses. Real values calibrate against Phase 1 multi-turn
   corpus once T5 ships. Phase 2 ships the rules with provisional values;
   Phase 4 retunes. OK to merge with provisional values?

4. **DST vs K=9 transition disagreement policy.** Currently the DST wins.
   Alternative: emit both, let Phase 5 eval pick. Phase 5 will eval either
   way; the question is which is the canonical TurnRecord field. Sticking
   with DST-wins makes the persisted record reflect cross-turn truth, which
   matches the cross-turn state-tracking thesis. Confirm?

5. **On-disk trace store: JSONL vs Parquet.** JSONL is human-debuggable,
   matches Phase 1 SDG corpus format, and supports streaming append.
   Parquet is denser and faster for analytics but harder to inspect. Phase
   2 default proposes JSONL; flip to Parquet if Phase 5 eval queries get
   slow. OK with JSONL default?

6. **Sparse top-K K value.** Exposure spec says K~=32. Confirm 32 as
   default, or push higher (64) for safer SAE training data? Cost is
   linear in K — 32 -> ~200 KB per turn, 64 -> ~400 KB.

7. **Session buffer cap (SESSION_MAX_TURNS=200).** Long-conversation
   sessions (think: extended pedagogical sessions) could exceed this.
   When capped, eviction policy is "keep turn 0 + last K". Alternative:
   keep all turns to disk, only evict from in-memory hot buffer. Slight
   memory savings vs. complexity. Default for Phase 2?

8. **Mode 5 inversion-scan compute budget.** Exposure spec Section 6
   flags this as an open question. Phase 2 assumes per-turn compute is
   cheap (axis math is O(40+7+4) per state). If the smoothing window
   becomes large, cost grows. Phase 2 default: window = full session,
   smoothing alpha = 0.4. Confirm?

9. **TraceStore interface scope.** Phase 2 ships JsonlTraceStore +
   InMemoryTraceStore. DB-backed store (for Phase 6 multi-tenant) is
   explicitly Phase 6 work. Confirm DST should NOT design the DB schema
   in Phase 2? (My read: yes, defer; design with DST consumers in
   mind, not as a Phase 2 deliverable.)

10. **Hook attachment timing.** DST registers hooks at construction
    (per-session). Alternative: register on first turn, unregister on
    session close. Construction-time attach is simpler; session-close
    detach is required either way. Confirm construction-time attach as
    default?

---

## 9. Acceptance criteria for Phase 2 completion

A draft list to anchor Phase 2 PRs against this design:

1. `cas_native/dst/` module exists with TraceStore interface,
   InMemoryTraceStore, JsonlTraceStore implementations.
2. `DialogueStateTracker` class accepts a frozen K=9 model + tokenizer +
   TraceStore at construction; manages session lifecycle via
   context-manager protocol.
3. Per turn, DST produces a TurnRecord whose JSON serialization round-trips
   through `dashboard/src/lib/mandala_types.ts` types without adapter.
4. Mode 1 (RadialArchitectureDisplay) renders against a real DST output
   for a 5-turn pilot conversation, with no mock data.
5. Mode 5 inversion-axis values populated for every turn; running
   smoothed aggregate matches a hand-computed reference on a fixture
   conversation.
6. Hook capture infrastructure attaches against current K=9 named
   submodules, captures sparse top-K activations for at least one layer,
   serializes to .npz under the on-disk store.
7. Mode 7 replay-on-demand: given a stored TurnRecord with
   `activation_snapshot_ref`, the DST can rerun K=9 on the captured input
   with full activation capture and produce a dense activation tensor.
   Tested end-to-end on a single fixture turn.
8. Test coverage >= 85% on `cas_native/dst/`. Property-based test:
   for any TurnRecord, `pre_state.cells` and `post_state.cells` satisfy
   open-simplex invariants (Correction 4: all values > 0, sum == 1).
9. Documentation: this design doc + a `cas_native/dst/README.md` with
   minimal usage example.

---

## 10. Sequencing relative to Phase 1

Phase 1 SDG and Phase 2 DST run in parallel from day one (user ratified
2026-05-04). Touchpoints:

- Phase 1 T2/T3 (demographic + tonal axis schemas) feed DST's
  `DemographicProfile` / `TonalProfile` types. DST's types pin to Phase 1's
  closed vocabularies. Coordination point: Phase 1 T2/T3 lock vocabularies
  before Phase 2 DST type module merges.
- Phase 1 T5 (multi-turn coherence labels) defines the seven transition
  kinds used in Section 3 above. They are already defined identically;
  no coordination needed beyond keeping them in sync if T5 changes.
- Phase 1 T7 (demographic-robustness eval gate) is the upstream
  invariant that DST's `axis_distributions` must respect — same CAS
  expression under demographic axis change should produce same K=9
  distribution. DST does not enforce this; Phase 1 does. DST surfaces
  any drift via `inversion_axis_values` to Phase 5 eval.

Phase 2 has zero GPU dependency. Hook infrastructure runs on the same
CPU-bound process as the frozen K=9 inference path, and capture is amortized
inside the existing forward pass.

---

## 11. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DST transition rules disagree with K=9 head systematically, surfacing as eval noise in Phase 5 | Medium | Medium | Section 3.4 disagreement-flag + retune thresholds in Phase 4 |
| Open-simplex invariant violations (cells with 0 or NaN) propagate from K=9 logits | Low | High | DST validates strictly on every state write; raises rather than silently coercing |
| Sparse top-K capture costs more than 200 KB per turn at long sequences | Medium | Low | Per-token K is fixed at 32; cost scales with sequence length, not unboundedly. Cap at SESSION_MAX_TURNS evicts old activations from hot store. |
| Hook double-attach if DST is reused across model instances | Low | Medium | Idempotency check raises on re-attach; context-manager pattern enforces single-use |
| TurnRecord JSON shape drifts from TS types | Medium | High | Round-trip JSON tests CI-blocking; single-source-of-truth field rename PR pattern (TS first, Python mirror in same PR) |
| Replay-on-demand reproducibility fails because RNG state was not captured | Low | High | Replay test in acceptance criteria #7; failure = fix before merging Phase 2 |
| `pivot` fallback rule swallows real `unclassified` patterns, hiding labeling gaps | Medium | Medium | Phase 4 curriculum includes a labeled-coverage metric over transition_kind distribution; if `pivot` rate exceeds threshold, surface for relabeling |
| Phase 6 wants a DB-backed TraceStore that DST didn't anticipate in interface design | Low | Low | TraceStore interface ships as abstract base class; both InMemory and JSONL implementations exercise the interface; DB store should fit |

---

## 12. Critical files for Phase 2 implementation

- `noetic-compass-scaffold/noetic-compass/cas-native/dst/__init__.py` (new)
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/trace_schema.py` (new) — Python mirror of TS types
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/state.py` (new) — CognitiveState, SessionBuffer, SpeakerModel
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/transitions.py` (new) — StateDiff, transition rules
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/inversions.py` (new) — 7-axis scanner per turn
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/hooks.py` (new) — HookRegistry, sparse top-K capture
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/store.py` (new) — TraceStore + InMemory + JSONL
- `noetic-compass-scaffold/noetic-compass/cas-native/dst/tracker.py` (new) — DialogueStateTracker class
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/test_dst_*.py` (new) — coverage per module
- `noetic-compass-scaffold/noetic-compass/dashboard/src/lib/mandala_types.ts` (existing) — Mode 1 contract
- `noetic-compass-scaffold/noetic-compass/dashboard/src/pages/IdeaAtlasPage.tsx` (existing) — Mode 2 contract
- `noetic-compass-scaffold/noetic-compass/cas-native/model/structured_prediction.py` (existing) — K=9 surface

No file in the existing K=9 baseline is modified by Phase 2.
