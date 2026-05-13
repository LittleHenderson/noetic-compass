# Mode 7 Traceability — Design for Candidate E Stage 3 Chat REPL

**Date:** 2026-05-13
**Status:** Design doc. No code yet. Pending Codex audit + user "go" before any wiring work.
**Scope:** This doc specifies WHAT the Mode 7 trace surfaces for each chat turn, WHERE the data is sourced from in existing CAS-Native code, and HOW it appears in the chat REPL. A sibling doc, `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md`, consumes the trace-dict contract defined here.

---

## 1. Goal

Mode 7 — "Network Attribution / Mechanistic Trace" — is a per-utterance exposure surface. For every reply the Candidate E Stage 3 model emits in the chat REPL, the user (or an auditor) can ask: **"How did you get this answer from my prompt?"** Mode 7 answers by walking the chain: raw user text → BPE tokens → CAS prefix → encoder Δ°₃₉ trajectory → decoder hidden states → per-position slot-type decision + pointer-copy distribution → admissibility checks → post-processed output tokens → rendered text.

Without this surface, the model is a black box. With it, every reply walks back to its origin, and a wrong answer is a *diagnosable* wrong answer rather than a "the model just said that" wrong answer. This is the architectural spine of the product, not an optional debug feature. The Stage 3 chat REPL is the first surface where end users (Wakil, Codex, eventually a wider review pool) interact with a free-decoding CAS-Native model; if Mode 7 is not on for the first session, the surface that distinguishes Noetic Compass from a wrapper-around-base-model goes invisible.

---

## 2. The seven exposure modes — where Mode 7 sits

Per `project_exposure_button_traceability.md`, the exposure button surfaces seven modes. Recap in order:

1. **Cognitive State Exposure** — current 10×4 Cognitive State grid, 7 Drives, 4 Registers. Rendered as the Radial Architecture Display.
2. **Idea Atlas Exposure** — force-directed graph of every CAS expression encountered in the session.
3. **Per-Utterance Trace** — for one utterance: user_text → parsed_intent_CAS → applied_operator(s) → admissibility_check → output_CAS → rendered_text.
4. **Production Recipe Exposure** — when an outcome Ω is named, surface `Θ(Ω) = a₁X₁ + a₂X₂ + … → Ω` with limiting reagent, theoretical yield, observed yield, η, leakage.
5. **Inversion Scan Exposure** — 7-axis inversion scanner verdict across the conversation.
6. **Counterfactual Exposure** — top-K alternative CAS interpretations the model considered and why each scored lower.
7. **Network Attribution / Mechanistic Trace** — neural-substrate trace: embedding → encoder layers → simplex trajectory → decoder layers → per-head decisions → pointer-copy attribution → output tokens.

**This doc specifies Mode 7 only.** Modes 1, 3, 4, 5, and 6 are sibling surfaces consumed by the same chat REPL but designed separately. Mode 7 is the *deepest* surface — it is the substrate against which the other modes can be cross-checked (e.g., Mode 3's "applied_operator" claim can be verified against Mode 7's slot-type decisions; Mode 6's "alternatives considered" can be derived from Mode 7's top-K LM logits).

The Stage 3 chat REPL ships with Mode 7 on by default. Modes 1, 3, 4, 5, 6 are follow-on; they read from the same per-turn trace dict that Mode 7 owns.

---

## 3. The data Mode 7 surfaces

For each user-model turn, Mode 7 captures and exposes five layers. Each layer has a specific data source in existing code.

### 3.1 Input layer

| Field | Source | Notes |
|---|---|---|
| `raw_user_text` | Chat REPL input | Verbatim before any rewrite. |
| `rewrite_applied` | `cas_native/inference/rewrite_shim.py::rewrite_to_training_surface` | If the input was rewritten to training-surface English, both pre- and post-rewrite text are kept. |
| `cas_signal_detected` | `cas_native/inference/rewrite_shim.py::detect_cas_signal` | Whether the input contained CAS notation. |
| `bpe_tokens` | `cas_native/training/tokenizer.py::HybridCASTokenizer` | List of `(token_str, token_id)` pairs after tokenization. |
| `cas_prefix_ids` | Constructed by the chat REPL's CAS-prefix builder for conditioning the decoder. Same field the `cas_prefix_mask` change (commit `2530d1b`) made dominant for conditioning. | If the input did not include a CAS prefix, this is empty. |
| `cas_prefix_mask` | Same | Indicates which positions of the decoder input came from the CAS prefix vs the user text. |
| `prompt_template` | Chat REPL routing decision (`cas_native/inference/cas_routing.py::route_by_compilability`) | One of `cas_to_english`, `invalid_to_explanation`, conversational fallback. |

### 3.2 CAS state layer (Δ°₃₉ trajectory and marginals)

The encoder produces a per-source-token point on the open probability simplex Δ°₃₉ (40 strictly positive probabilities summing to 1). Source: `cas_native/model/simplex_encoder.py::SimplexEncoder.forward`, output keys `source_hidden` and `simplex_trajectory`. Verified at `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py:1-100`.

| Field | Shape | Source | Notes |
|---|---|---|---|
| `simplex_trajectory` | `(L_src, 40)` | encoder output | One Δ°₃₉ point per source token. The 40 cells index the 10 Noetics × 4 Domains. |
| `simplex_pooled` | `(40,)` | mean over source positions, masked by padding | Already computed inside `TypedFiberDecoder.forward` at `typed_fiber_decoder.py:325-331` for the phrase-bias path; expose it. |
| `noetic_marginal` | `(10,)` | sum the 4 domains for each Noetic from `simplex_pooled` | `typed_fiber_decoder.py:331` already does this as `pooled_noetic`. |
| `domain_marginal` | `(4,)` | sum the 10 Noetics for each Domain | Cheap reshape. Not currently computed but trivially derivable. |
| `dominant_noetic` | int 0–9 | `argmax(noetic_marginal)` | Same as the `k_star` used for phrase-bias indexing. |
| `dominant_domain` | str in {P, C, E, O} | `argmax(domain_marginal)` | Pure derivation. |
| `drive_marginal` | `(7,)` | Not yet computed by the encoder. **Open question.** Either (a) read off an aux Drive head if one exists on the trunk, or (b) derive from per-token slot-type decisions where a `DRIVE_LETTER` slot fired. | Drive is the 7-axis F1–F7 motivational architecture. See §10 Open Questions. |
| `register_marginal` | `(4,)` | Same pattern as Drive — Register is the v7.5 axis (T/A/f/E). | Same open question. See §10. |

Per Correction 4 in `CLAUDE.md`, every entry of the simplex trajectory must have `p_k > 0`. The trace dict carries a validation flag `simplex_open_simplex_valid: bool` and a `min_pk` value so an out-of-domain run is visibly flagged.

### 3.3 Activation layer (per-layer hidden states)

| Field | Shape | Source | Notes |
|---|---|---|---|
| `encoder_layer_norms` | `(n_layers,)` of L2 norms | summarized from `source_hidden` and per-layer hooks | Encoder is 4 layers per `SimplexEncoderConfig`. Hook the four `_EncoderBlock` outputs via the existing `cas_native.model.activation_hooks::register_named_hooks` machinery. |
| `decoder_layer_norms` | `(n_layers, L_out)` of L2 norms or means | per-decoder-block hooks on `_DecoderBlock` | Decoder is 6 layers per `TypedFiberDecoderConfig`. Hook output of each block. |
| `decoder_hidden_state_final` | `(L_out, d_model)` summary | `outputs["decoder_hidden_state"]` from `TypedFiberDecoder.forward` at `typed_fiber_decoder.py:304-366` | Already in the returned dict. Carry as L2/mean/max-abs summary, not the full tensor, in the default trace. |
| `attention_entropy_per_layer` | `(n_decoder_layers,)` | derived from each block's `_CrossAttention` softmax | Requires modest hook addition: capture pre-softmax `scores` from cross-attn returns. The final block already returns `copy_scores` for free; the first five blocks currently drop them. |

The `activation_hooks.py` infrastructure already exists and is class-name-allowlist driven (`CAS_ALIGNED_CLASS_NAMES`). The Stage 3 model classes — `SimplexEncoder`, `TypedFiberDecoder`, `_DecoderBlock` — are NOT in that allow-list as of 2026-05-04 (the list was sized for the structured-prediction architecture, not the simplex MVP). **Smallest hook needed:** extend `CAS_ALIGNED_CLASS_NAMES` to include `SimplexEncoder`, `TypedFiberDecoder`, `_EncoderBlock`, `_DecoderBlock`. No layer-class changes; the existing hook-attachment helper is plug-compatible.

### 3.4 Attribution layer (pointer-copy + slot-type per output position)

This is the load-bearing layer for Stage 3. The Candidate E decoder is a pointer-generator with slot-typed copy/generate; every output position decides between LM emission and pointer-copy from a source position. Source: `cas_native/model/typed_fiber_decoder.py:200-366`.

| Field | Shape | Source | Notes |
|---|---|---|---|
| `lm_logits_top5_per_position` | `(L_out, 5, 2)` of `(token_id, prob)` | softmax of `outputs["lm_logits"]` | `typed_fiber_decoder.py:305`. |
| `slot_type_decision_per_position` | `(L_out,)` int in 0–8 | argmax of `outputs["slot_type_logits"]` | `typed_fiber_decoder.py:306`. 9 slot types: CONNECTIVE / OMEGA / STAGE_VAR / COEFFICIENT / REGISTER_LETTER / DOMAIN_LETTER / DRIVE_LETTER / FRACTAL_K_LITERAL / NOETIC_PHRASE. See `typed_fiber_decoder.py:31-41`. |
| `slot_type_confidence_per_position` | `(L_out,)` float | softmax max of `slot_type_logits` | Useful for finding low-confidence slot decisions. |
| `p_copy_top5_per_position` | `(L_out, 5, 2)` of `(src_position, prob)` | `outputs["p_copy"]` top-5 | `typed_fiber_decoder.py:315`. |
| `p_copy_entropy_per_position` | `(L_out,)` float | Shannon entropy of `p_copy[t, :]` | Low entropy = peaked attribution to one source token; high entropy = diffuse / unsure. |
| `copy_source_indices` | `(L_out,)` int16 | `outputs["copy_source_indices"]` | `typed_fiber_decoder.py:351`. -1 at non-typed positions; argmax_j p_copy(j) at typed positions. |
| `phrase_bias_active_per_position` | `(L_out,)` bool | derived from `slot_type_probs[..., NOETIC_PHRASE]` > 0.5 | The `noetic_phrase_gate` factor at `typed_fiber_decoder.py:344`. Surfaces when the phrase-bias path influenced the LM. |

Per-position attribution is the closest analogue this architecture has to "which input token caused this output token?" — it is *not* attention rollout over the full forward pass; it is the explicit pointer-copy attention from the final decoder block (`typed_fiber_decoder.py:192-194`). That is a strictly stronger signal than rollout for the copy-shaped tokens (OMEGA, STAGE_VAR, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL) because the architecture *guarantees* those tokens are emitted by the pointer mechanism. For CONNECTIVE and NOETIC_PHRASE tokens, attribution falls back to the LM-head logits, which is a weaker but still useful signal.

### 3.5 Admissibility layer

Per `CLAUDE.md` Correction 1, each operator CO-k has an admissibility relation Dk ⊆ I × I specifying valid (source, target) pairs. The CAS-engine Rust crate at `cas-engine/src/ontology/` is the authoritative implementation. Found via grep at `cas-engine/src/ontology/operators.rs`, `cas-engine/src/validation/`. There is also Python-side admissibility logic in `cas-native/model/typed_fiber_decoder.py:48` (`COPY_ALLOWED_SLOT_IDS`) and `cas-native/inference/cas_routing.py` (compilability gate).

| Field | Source | Notes |
|---|---|---|
| `output_compiles` | `api.notation::compile_expression` invoked on a candidate CAS interpretation of the output | Boolean. Authoritative compiler verdict. |
| `compile_artifact` | Same | Carries the compiled IR + diagnostic positions when it fails. |
| `admissibility_violations` | List of `(operator, source_state, target_state, reason)` | From the compile artifact's typecheck/admissibility stage. Maps to `cas_routing.py::_STAGE_PREFIX_TO_ERROR_CLASS["typecheck"] = "admissibility"`. |
| `copy_slot_admissibility_per_position` | `(L_out,)` bool | For each output position: was the chosen slot_type in `COPY_ALLOWED_SLOT_IDS` *and* was `p_copy` argmax pointed at a source position whose `src_token_type` matched the chosen slot? | Catches the failure mode where the model emitted an "OMEGA" slot but the pointer pointed at a non-Ω source token. |
| `rpm_chain_check` | From the compile artifact | For RPM expressions: which A0 → Dn → Wn → Pn → Outcome links are satisfied; which are missing. Section-retraction direction per CLAUDE.md Correction 2. |

**State of the wire-up:** the `cas-engine` Rust admissibility lives behind a Python binding at `cas-native/validation/rust_bridge.py`. The `compile_expression` Python wrapper at `api/notation/compiler.py` already exists and is called by `cas_routing.py`. The plumbing for "ask the compiler what was admissible" exists; the trace builder needs to call it once per output and record the verdict + diagnostics. No new bridge work.

### 3.6 Output layer (post-processing + final text)

| Field | Source | Notes |
|---|---|---|
| `raw_decoded_tokens` | Argmax of `lm_logits` over `L_out` positions, gated by slot_type | The pre-postprocessing free-decode output. |
| `raw_decoded_text` | BPE detokenization of raw_decoded_tokens | Verbatim, before any repair. |
| `identifier_repair_log` | `cas_native/inference/identifier_repair.py` | Which Ω names, coefficients, and let-binding stage IDs were substituted in. |
| `cas_routing_decision` | `cas_native/inference/cas_routing.py::RoutingDecision` | The compilability-gate verdict that drove prompt template selection. |
| `rpm_repair_log`, `meta_logic_repair_log`, `fractal_repair_log` | sibling repair modules in `cas_native/inference/` | Any post-decode repairs applied. |
| `generation_cleanup_diff` | `cas_native/inference/generation_cleanup.py` | Final cosmetic cleanup (whitespace, casing). |
| `final_rendered_text` | Output of the full post-processing pipeline | What the user sees in the REPL. |

The diff between `raw_decoded_text` and `final_rendered_text` is itself a Mode 7 surface: how much of the answer the user is seeing came from the model versus from post-processing repairs. Heavy repair = the model did not source-ground; the answer should be flagged.

---

## 4. The trace dict contract

This is the schema the chat REPL integration consumes. The chat REPL plan (`docs/working/chat_repl_stage3_integration_plan_2026_05_13.md`) treats this as a typed dict / dataclass with a single constructor `build_mode_7_trace(...)`.

```python
{
  "schema_version": "mode_7_trace.v1",
  "trace_id": "<uuid4>",
  "id": "<uuid4>",                       # object-traceability: this trace object's id
  "created_at": "<iso8601>",
  "parent_ids": ["<session_id>", "<turn_id>"],
  "source": "stage3_chat_repl",
  "model_checkpoint_id": "<sha or run_dir name>",
  "model_code_version": "<git sha>",

  "input": {
    "raw_user_text": str,
    "rewrite_applied": bool,
    "rewritten_text": str | None,
    "cas_signal_detected": bool,
    "bpe_tokens": [{"token_id": int, "token_str": str}, ...],
    "cas_prefix_ids": [int, ...],
    "cas_prefix_mask": [bool, ...],
    "prompt_template": "cas_to_english" | "invalid_to_explanation" | "conversational" | ...
  },

  "encoder": {
    "n_source_tokens": int,
    "simplex_trajectory_summary": {
      # Full (L_src, 40) tensor is too big for default trace; surface a summary.
      "mean": [float] * 40,
      "max": [float] * 40,
      "argmax_state_per_position": [int] * L_src,   # 0..39
      "entropy_per_position": [float] * L_src
    },
    "simplex_pooled": [float] * 40,
    "noetic_marginal": [float] * 10,
    "domain_marginal": [float] * 4,
    "drive_marginal": [float] * 7 | None,           # None until aux head lands; see §10
    "register_marginal": [float] * 4 | None,        # None until aux head lands
    "dominant_noetic": int,                          # 0..9
    "dominant_domain": "P" | "C" | "E" | "O",
    "dominant_drive": "F1".."F7" | None,
    "dominant_register": "T" | "A" | "f" | "E" | None,
    "simplex_open_simplex_valid": bool,
    "min_pk": float,
    "encoder_layer_l2": [float] * 4
  },

  "decoder_per_position": [
    {
      "position": int,                              # 0..L_out-1
      "decoded_token_id": int,
      "decoded_token_str": str,
      "slot_type": "CONNECTIVE" | "OMEGA" | "STAGE_VAR" | "COEFFICIENT"
                 | "REGISTER_LETTER" | "DOMAIN_LETTER" | "DRIVE_LETTER"
                 | "FRACTAL_K_LITERAL" | "NOETIC_PHRASE",
      "slot_type_confidence": float,
      "lm_logits_top5": [(int, float)] * 5,         # (token_id, prob)
      "p_copy_top5": [(int, float)] * 5,            # (src_position, prob)
      "p_copy_entropy": float,
      "copy_source_index": int,                     # -1 if non-typed; else src position
      "phrase_bias_active": bool,
      "decoder_hidden_l2": float,
      "layer_l2": [float] * 6                       # one per decoder block
    },
    ...
  ],

  "admissibility": {
    "output_compiles": bool,
    "compile_error_class": str | None,              # "parse" | "admissibility" | "rpm" | None
    "compile_error_message": str | None,
    "violations": [
      {"operator": str, "source": str, "target": str, "reason": str},
      ...
    ],
    "copy_slot_admissibility_pass_count": int,
    "copy_slot_admissibility_fail_positions": [int, ...],
    "rpm_chain_check": {
      "chain_required": bool,
      "satisfied_links": ["A0", "Dn", ...],
      "missing_links": ["Wn", ...]
    } | None
  },

  "output": {
    "raw_decoded_tokens": [int, ...],
    "raw_decoded_text": str,
    "identifier_repair_log": {
      "omega_substitutions": [(str, str), ...],     # (replaced, with)
      "coefficient_substitutions": [(str, str), ...],
      "let_var_substitutions": [(str, str), ...]
    },
    "cas_routing_decision": {
      "task_type": str,
      "compiled": bool,
      "error_class": str | None
    },
    "rpm_repair_applied": bool,
    "meta_logic_repair_applied": bool,
    "fractal_repair_applied": bool,
    "final_rendered_text": str,
    "post_processing_changed_text": bool
  },

  "summary": {
    "dominant_noetic_name": "Idea" | "Mind" | "Positive" | "Negative" | "Vibration"
                          | "Female" | "Male" | "Rhythm" | "Above/Cause" | "Below/Effect",
    "dominant_domain_name": "Principled" | "Cognitive" | "Evaluative" | "Operational",
    "free_decode_recovery_self_score": float,       # Stage 3 identifier_recovery_rate-style
    "trace_warnings": [str, ...],                    # e.g. "post_processing_heavy_repair"
    "trace_size_bytes": int
  },

  "timing_ms": {
    "tokenize": float,
    "encoder_forward": float,
    "decoder_forward": float,
    "compile_check": float,
    "post_process": float,
    "trace_build": float,
    "total": float
  }
}
```

Notes on contract:

- All fields under `decoder_per_position` are per-output-position arrays of the same length `L_out`. Consumers can iterate or index uniformly.
- `simplex_trajectory_summary` is a summary by default. The full `(L_src, 40)` tensor is gated behind a `capture_level="raw"` flag (see §5) since it dominates the trace size budget.
- `drive_marginal` and `register_marginal` are `None` until aux Drive/Register heads land on the encoder trunk. The chat REPL UI must handle `None` gracefully (render "not yet computed" rather than zero).
- `parent_ids` always includes the session id and the turn id within the session. Per `feedback_object_traceability_required.md`: "Every object knows where it came from."
- `schema_version` is `"mode_7_trace.v1"` for Stage 3. Bump on any breaking change. The 2026-05-04 spec already used `mechanistic_trace.v1` for the structured-prediction classifier surface; this is a separate, sibling schema for the simplex-MVP generative architecture.

---

## 5. UI surface in the chat REPL

The Stage 3 REPL is the existing rich-driven console in `cas_native/inference/chat.py`. The Mode 7 surface there has three render modes, selected by a slash command:

### 5.1 Default mode: collapsed marker under each reply

After every model reply the REPL prints a single short line:

```
  [trace 7a3f… | ^2^C dominant | compiles ✓ | repair: 2 Ω substituted]
```

That is: the first 4 chars of the trace_id, the dominant Noetic+Domain in plain CAS notation, whether the output compiles, and a one-line repair summary. This is always on; the cost is one line per turn.

### 5.2 Expanded mode: `/trace` slash command

`/trace` (no arg) expands the trace for the *last* reply. `/trace <id>` expands a specific past reply. The expanded view renders the trace dict as five sections:

1. **Input** — raw text, rewrite shown if applied, BPE tokens, CAS prefix shown if non-empty.
2. **CAS state** — a bar chart of the 10 Noetic marginals; the dominant Noetic+Domain+Drive+Register in canonical CAS notation (`^2^C|A`, `F3|f`, etc.); a flag if `simplex_open_simplex_valid` is false.
3. **Decoder per position** — a table: position, decoded token, slot type, slot confidence, the top source position the pointer copied from (or `—` for non-copy slots), the LM top-1 fallback. Rows where copy admissibility failed are highlighted.
4. **Admissibility** — compile verdict, any violations listed by operator and stage. If RPM chain check ran, show satisfied/missing links.
5. **Output** — raw decoded text vs final rendered text, with diff. Identifier-repair substitutions listed.

All sections use canonical CAS notation. Noetic names match `CLAUDE.md` exactly: `^0 Idea`, `^1 Mind`, `^2 Positive`, `^3 Negative`, `^4 Vibration`, `^5 Female`, `^6 Male`, `^7 Rhythm`, `^8 Above/Cause`, `^9 Below/Effect`. Per `feedback_plain_language_no_jargon.md`, inline gloss where helpful (e.g. "^2 Positive (Idea the Mind is attracted to)"). No "mechanistic" / "load-bearing" / "modality" jargon in the user-facing labels.

### 5.3 Raw JSON dump: `/trace --json`

Emits the full trace dict to stdout as JSON. Used for piping into other tools, audit logs, replay. `/trace --json --raw` includes the full simplex trajectory `(L_src, 40)` tensor (the `capture_level="raw"` path; see §6).

### 5.4 Secondary surfaces (deferred)

- **Side panel HTML** — for the dashboard surface, the same JSON powers a `MechanisticTraceInspector.tsx`-style component (already specified in `docs/working/mode_7_network_tracer_spec_2026_05_04.md` §5.3 for the classifier; the simplex-MVP version is a parallel component).
- **Per-position attribution heatmap** — visual rendering of `p_copy` over source tokens, gated by output position. Deferred to a follow-on UI PR; the data is in the trace dict from day one.
- **Simplex trajectory ribbon** — per-position Δ°₃₉ as a stacked-bar over `L_src`. Visual only; deferred.

The CLI surface is the primary v1. Visual surfaces consume the same JSON. The slogan that holds: the trace is a first-class output, not an implementation detail — even when only the CLI is wired, the JSON contract is the artifact.

---

## 6. Implementation plan

Phased. Each phase has a single test gate, sized to the smallest unit that gives confidence. No phase requires retraining; all phases run against the already-trained Stage 3 checkpoint.

### Phase 1 — Trace dict schema + constructor (1–2 days)

- Land a `cas_native.trace.mode_7_trace` module with one dataclass + one constructor `build_mode_7_trace(...)` that takes the encoder/decoder outputs + post-processing logs + admissibility verdict and returns the dict.
- Smoke test: pass mock encoder/decoder outputs through the constructor, assert the schema matches.
- Gate: every field in §4 round-trips through `json.dumps` cleanly.

### Phase 2 — Encoder / decoder forward emit the raw tensors (0–1 day)

- Verify `TypedFiberDecoder.forward` already returns `lm_logits`, `slot_type_logits`, `p_copy`, `copy_source_indices`, `decoder_hidden_state`. (It does — `typed_fiber_decoder.py:361-367`.)
- Verify `SimplexEncoder.forward` returns `source_hidden` and `simplex_trajectory`. (It does — `simplex_encoder.py` per build-spec §2.1.)
- Add per-layer L2 norm hooks on `_EncoderBlock` and `_DecoderBlock` via the existing `cas_native.model.activation_hooks::register_named_hooks` infrastructure. Smallest change: extend `CAS_ALIGNED_CLASS_NAMES` in `activation_hooks.py:70-93` to include `"SimplexEncoder"`, `"TypedFiberDecoder"`, `"_EncoderBlock"`, `"_DecoderBlock"`. No layer-class changes.
- Gate: hook session attached around a single forward pass, assert one entry per encoder block + one per decoder block + one per model-top class.

### Phase 3 — Trace builder consumes raw tensors + post-processing decisions (1 day)

- Wire `build_mode_7_trace(...)` to the chat REPL inference path. The REPL's existing call into `generate_reply` (or its Stage 3 equivalent) needs to capture all the inputs Mode 7 needs and pass them to the builder.
- Wire admissibility: call `api.notation::compile_expression` on the output, capture the artifact, fill the admissibility section.
- Wire post-processing logs: identifier_repair, cas_routing, rpm_repair, meta_logic_repair, fractal_repair already log; expose their logs as return values from the post-processor pipeline rather than only side effects.
- Gate: REPL emits a real trace dict for a known prompt; manual inspection matches what the decoder actually did.

### Phase 4 — REPL UI: `/trace` slash command (0.5 day)

- Add the slash command, render the five sections of §5.2 using `rich`'s `Panel`, `Table`, and `Text`.
- Add the one-line marker under every reply per §5.1.
- Gate: a fresh chat session, three turns, each with a `/trace` and a `/trace --json`; outputs match the schema.

### Phase 5 — Admissibility deepening (1–2 days)

- The Phase 3 wire-up uses the Python compiler. The Rust admissibility relations (per CLAUDE.md Correction 1) are in `cas-engine/src/ontology/operators.rs` and friends. The Python bridge at `cas_native/validation/rust_bridge.py` is the existing path. Surface Rust-side admissibility violations in the trace when they are stricter / more informative than the Python compiler.
- Gate: a deliberately admissibility-violating CAS expression produces a trace where the Rust-side violation appears under `admissibility.violations`.

### Phase 6 — Persistence + replay (1 day)

- Each per-turn trace dict is appended to a per-session JSONL file `runs/<session_id>/traces.jsonl`. The chat REPL session id is the file name; each turn is one line.
- A separate one-off `replay_trace.py` script can load a trace by `trace_id` and re-render the §5.2 view without re-running the model.
- Gate: a finished session writes a JSONL file that loads cleanly and renders correctly.

Phases 1–4 ship the user-facing Mode 7 surface. Phase 5 is the admissibility deepening that earns the "every output knows whether it was admissible" claim. Phase 6 is the audit trail.

### Capture levels (mirrors the 2026-05-04 spec)

- `summary` — drop `decoder_per_position` entirely; keep encoder summary and admissibility. Used for batch traces where size matters.
- `full` — default. Everything in §4 except the raw `(L_src, 40)` simplex trajectory tensor (carried only as the summary).
- `raw` — `full` plus the full simplex trajectory + the full `lm_logits` and `p_copy` tensors. Used for interpretability research and the rare deep-dive replay.

---

## 7. Object traceability

Per `feedback_object_traceability_required.md`, every Mode 7 trace object carries:

- `id` — UUID4 for this trace record itself.
- `created_at` — ISO-8601 timestamp.
- `version` — `"mode_7_trace.v1"`.
- `parent_ids` — `[session_id, turn_id]`. The session is the chat session UUID; the turn is its position within the session.
- `source` — `"stage3_chat_repl"`.
- `trace_id` — UUID4 distinct from `id` because the same logical trace can be re-captured (e.g. on a forensic replay) under a new trace_id while preserving id continuity.
- `model_checkpoint_id` — the Stage 3 checkpoint path or SHA; pinned from the run manifest when the chat REPL loads weights.
- `model_code_version` — git SHA at REPL start.

Every other object Mode 7 produces (the per-position decoder records, the admissibility violations, the post-processing repair entries) carries an inline `parent_ids = [trace_id, ...]` link upward. The whole graph walks back to the session and to the checkpoint.

---

## 8. Data volume + perf budget

Stage 3 default: `L_out ≈ 192`, `L_src ≈ 128`.

Per-position record (summary form, with top-5 LM + top-5 p_copy + 6 layer L2s + slot decision):
- ~25 small floats / ints per position ≈ 200 bytes / position.
- × 192 positions ≈ 38 KB per turn for the per-position array.

Encoder summary:
- Simplex pooled (40), noetic marginal (10), domain (4), drive/register (7+4), argmax-per-position (192), entropy-per-position (192). ≈ 2.5 KB.

Admissibility + input + output sections: ≈ 5 KB (most of it is the raw_decoded_text + final_rendered_text).

**Default trace size: ~45 KB / turn.** A 50-turn session is ~2.25 MB on disk as JSONL. Memory-resident for the active session is fine.

`capture_level="raw"` blows up to ~1 MB / turn because of the full `(L_src, 40)` simplex trajectory + full `lm_logits` (192 × vocab_size × 4 bytes ≈ 38 MB at vocab=50k — gated even tighter or kept top-50 only). The raw mode is opt-in and persists to disk only on explicit `/trace --json --raw --save` invocation.

UI default: the one-line marker (§5.1) is on by default. The expanded `/trace` is opt-in. The full JSON dump is opt-in. This keeps the chat surface uncluttered while keeping the data fully available.

Latency budget per turn:
- Trace assembly: target <50 ms on top of generation.
- Compile-check (admissibility): the existing `compile_expression` runs in <10 ms for typical outputs.
- Per-position summarization (top-K, entropy): pure tensor ops on already-computed logits, <20 ms.
- JSON serialization: <10 ms.

Total Mode 7 overhead per turn: target <100 ms on top of generation. Generation itself is the dominant cost.

---

## 9. Privacy + safety

Mode 7 exposes internal state. Specific concerns:

- **Training-set echo.** If the model regurgitates a memorized training record, the per-position pointer-copy pattern + the bottleneck signature will show it. The trace surface should flag suspicious echo: a `summary.trace_warnings` entry `"possible_training_echo"` fires when the post-processing diff is small (the model produced the text directly) AND a nearest-neighbor lookup against training data scores above a threshold. The nearest-neighbor surface from `cas_native.trace.generation_trace::NearestNeighborIndex` is the existing primitive to reuse.
- **Identifier leakage.** Stage 3's hard safety gate is `cross_emission_count == 0` for source-swap pairs (per `docs/working/candidate_e/stage3_plan_2026_05_13.md` §5). Mode 7 should compute and surface the same check: if any `copy_source_index` in a turn points at a position from a *different* CAS expression than the conditioning one, flag it. This is the exact failure mode Stage 3 is built to detect; Mode 7 should never silently hide it.
- **No foreign-model fingerprints.** Per `feedback_no_foreign_architecture_cas_only.md`, the entire stack is CAS-native end-to-end. There is no TinyLlama / Qwen / GPT-2 / etc. residue to redact. The model code version surfaced in the trace is the project's own git SHA. If a foreign tokenizer or weight is ever introduced upstream, this section gets a redaction rule.
- **User text.** The raw user text is in the trace by default. For an audit trail intended to leave the local machine, the chat REPL should expose a `/trace --redact-user-text` flag that hashes the raw_user_text under SHA-256 before emission. Default for local sessions is no redaction; the user can read their own text.
- **CAS prefix content.** CAS prefixes are CAS notation, not private data; no redaction default.

The trace is a private development artifact in Stage 3. A future "share this trace with a reviewer" affordance would force the redaction-by-default flow. Out of scope for v1.

---

## 10. Open questions

These could not be resolved from existing code; the user (or Codex audit) decides:

1. **Drive and Register marginals on the encoder trunk.** The Δ°₃₉ simplex carries Noetic × Domain (40 cells) per the build-spec §2.1. Drive (F1–F7) and Register (T/A/f/E) are not surfaced as marginals from the trunk because they are not part of the 40-cell state space — they are orthogonal axes per `CLAUDE.md` v7.5/v7.7. Two paths to surface them in Mode 7:
   - **Path A — auxiliary heads on the trunk.** Add a Drive head and a Register head to the encoder trunk that read off the pooled `source_hidden`. Cheap (two small Linear layers), but adds parameters and would need fine-tuning training data. Not Stage 3.
   - **Path B — per-position slot-type derivation.** Aggregate over output positions where `slot_type == "DRIVE_LETTER"` or `slot_type == "REGISTER_LETTER"` to construct *observed* Drive/Register marginals from the generation itself. Requires no new parameters and uses only Stage 3 outputs, but only fires when the model emits those slot types.
   - Recommended: ship Path B for v1, leave `drive_marginal` / `register_marginal` as `None` when no slot fired. Path A is the right long-term answer once aux heads are in scope.

2. **Encoder per-layer hooks vs encoder-block hooks.** `SimplexEncoder` per build-spec §2.1 is a 4-layer pre-norm Transformer trunk plus a 2-layer mirror-descent tail. The trace currently calls for `encoder_layer_l2: [float] * 4`, which covers the trunk only. Should the trace also expose the tail's per-layer summary? The tail is what enforces the open-simplex projection; surfacing its L2 might catch projection-related failures. Recommended: include trunk and tail; rename to `encoder_l2_per_layer` (length 6).

3. **Trace persistence default.** §6 Phase 6 defaults to JSONL persistence per session. Should that be on by default in Stage 3, or behind a `--persist-traces` flag? Tradeoff: always-on gives full audit trail at 2–3 MB / session; opt-in keeps the local working directory clean. Recommended: always-on for Stage 3 development (the goal is to maximize evidence collection during the first real chat sessions); add a `--no-trace-persist` flag for later.

4. **Rust admissibility integration timing.** The Rust `cas-engine` admissibility is more complete than the Python compiler in some cases (per the `CLAUDE.md` Phase 1 spec). Phase 5 wires it. Should Phase 5 land in v1 or be deferred to v1.1? Recommended: defer to v1.1; Phase 3's Python-compiler verdict covers ~95% of admissibility cases that surface during normal chat, and Phase 5 is independent of the user-facing surface.

5. **What does "Mode 7 caught it" look like in a Stage 3 session?** The success criterion for the surface is operational: on the first chat session where the model emits a wrong copy (e.g. the swap-pair leakage Stage 3's `cross_emission_count` gate watches for), Mode 7 should flag the failure visibly in the one-line marker, not just buried in the JSON. The marker format in §5.1 is sized for compile + repair status; should it also surface the swap-pair / cross-emission flag inline? Recommended: yes — add a `swap_emission: clean` / `swap_emission: leaked` indicator to the marker line when the prompt came from a paired source. The pair-membership is known by the prompt builder; the cross-emission verdict is a fast computation from the trace.

---

**Document ends. No code changed by this doc.**
