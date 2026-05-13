# CAS Trace Schema v0 — the contract between inference, chat REPL, Mode 7, and the Living Thought Atlas

**Date:** 2026-05-13
**Status:** Design doc. No code changed. This document locks the v0 trace dict shape so all downstream consumers (Mode 7 surface, Living Thought Atlas graph builder, audit artifacts) read from the same JSON.
**Companion docs:**
- `docs/working/mode_7_traceability_design_2026_05_13.md` — what the chat REPL surfaces to the user.
- `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md` — file-by-file plan for wiring Stage 3 into the chat REPL.
- `docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md` — Codex's audit of the Thought Tree / Idea Atlas UI substrate; defines the canonical node / edge identity scheme this schema must feed.

---

## 1. Goal

The CAS trace schema is one JSON dict produced for every model reply. It is the single artifact that flows from inference into:

1. The chat REPL (Step 5 of the Stage 3 integration order), which prints a one-line marker per reply and an expanded `/trace` view on demand.
2. The Mode 7 surface (Step 6), which walks the user through how the reply was assembled, position by position.
3. The Living Thought Atlas / Thought Tree (Step 7+), which turns the trace into nodes and edges on a shared `CasGraph` substrate.
4. Exportable proof artifacts for the pitch demo — every reply has a permanent, replayable record.

**v0 locks the shape.** Every downstream consumer reads the same dict; if a new consumer wants more, v1 adds fields without breaking v0 readers. Plain rule: **consumers MUST check `schema_version`; an unknown version is an error, not a best-effort parse.**

This schema is the Stage 3 sibling of the older `cas_native.trace.mechanistic` schema (the K=9 classifier era, version `mechanistic_trace.v1`). They live alongside each other. The K=9 schema is not modified by this doc.

---

## 2. Design principles

1. **Every node knows where it came from.** Per the user's memory `feedback_object_traceability_required.md`: every trace object — top-level dict, per-position decoder record, admissibility violation, repair-pass entry — carries `id`, `created_at`, `version`, `parent_ids`, `source`, `trace_id`. The whole graph walks back to the session and the checkpoint.

2. **Versioning is explicit.** Top-level `schema_version: "cas_trace_v0"`. Future versions bump the number. Migration policy in §8.

3. **JSON-serializable everywhere.** No tensors, no torch objects, no numpy types. Floats are Python floats, ints are Python ints. The dict round-trips through `json.dumps` / `json.loads` cleanly. Heavy tensors (full simplex trajectory, full LM logits) appear only as summaries; raw tensors are gated behind a `capture_level` flag.

4. **Plain field names where user-facing.** `dominant_noetic`, `final_rendered_text`, `output_compiles`. Internal fields (`copy_source_indices`, `p_copy_entropy`) keep technical names because they map directly to model output and confusion would cost more than it would save.

5. **Forward-compatible for the Atlas.** Living Thought Atlas features — ghost branches, Inversion Replay, infinite zoom — must be schema-extensible. v0 already includes top-K alternatives at every decision node so ghost branches can render. Replay-from-this-node (re-decode forward from a flipped axis) requires the model itself, not just the trace; v0 records the *facts*, v1+ records what would be needed to *re-run* from a saved point.

6. **Compatible with Codex's graph identity scheme.** Every schema field that should become a node or an edge in the Atlas has a defined mapping (§4). The Atlas does not invent identity; it reads it from this schema.

---

## 3. The schema

Top-level shape:

```json
{
  "schema_version": "cas_trace_v0",
  "id": "<uuid4>",
  "trace_id": "<uuid4>",
  "created_at": "<iso8601>",
  "parent_ids": ["<session_id>", "<turn_id>"],
  "source": "stage3_chat_repl",
  "model_checkpoint_id": "<sha or run_dir name>",
  "model_code_version": "<git sha>",
  "capture_level": "summary" | "full" | "raw",

  "input": { ... },
  "encoder": { ... },
  "decoder_per_position": [ ... ],
  "attribution": { ... },
  "admissibility": { ... },
  "output": { ... },
  "summary": { ... },
  "timing_ms": { ... }
}
```

### 3.1 Top-level identity fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | str | Always `"cas_trace_v0"` in v0. Required first check by every consumer. |
| `id` | str (UUID4) | Identity of this trace record. Stable; survives re-rendering. |
| `trace_id` | str (UUID4) | Distinct from `id`. Re-running the same trace dict (forensic replay) gets a fresh `trace_id` but preserves `id` continuity. |
| `created_at` | str (ISO-8601) | When the trace was assembled. UTC. |
| `parent_ids` | list[str] | `[session_id, turn_id]`. The session is the chat session UUID; the turn is its position within the session. |
| `source` | str | Producer name. `"stage3_chat_repl"` for Stage 3 chat sessions, `"stage3_local_smoke"` for the one-record smoke at `inference/stage3_local_smoke.py`, `"replay_trace"` for forensic replay. |
| `model_checkpoint_id` | str | The Stage 3 checkpoint path or SHA. Pinned from the run manifest when the chat REPL loads weights. |
| `model_code_version` | str | Git SHA at REPL startup. |
| `capture_level` | str | One of `"summary"` (per-position dropped), `"full"` (default — everything except raw tensors), `"raw"` (everything plus full simplex trajectory and full LM logits). See §6 for budget. |

### 3.2 `input` — what the user sent and how it got tokenized

| Field | Type | Source | Description |
|---|---|---|---|
| `raw_user_text` | str | Chat REPL input | Verbatim text the user typed. |
| `rewrite_applied` | bool | `cas_native/inference/rewrite_shim.py::rewrite_to_training_surface` | Whether the input was rewritten to the training-surface English style. |
| `rewritten_text` | str \| null | Same | The rewritten text if `rewrite_applied`, else null. |
| `cas_signal_detected` | bool | `cas_native/inference/rewrite_shim.py::detect_cas_signal` | Whether the input contained recognizable CAS notation. |
| `bpe_tokens` | list[{`token_id`: int, `token_str`: str}] | `cas_native/training/tokenizer.py::HybridCASTokenizer` | Tokenization of the (possibly rewritten) input. |
| `cas_prefix_ids` | list[int] | Chat REPL CAS-prefix builder; same path the collator at `cas_native/training/datasets/simplex_collator.py` uses | The CAS prefix the encoder will read. Empty if no CAS prefix was attached. |
| `cas_prefix_mask` | list[bool] | Same | Which positions of the encoder source came from the CAS prefix vs the user text. The mask the user-named commit `2530d1b` (cas_prefix_mask) made dominant. |
| `prompt_template` | str | `cas_native/inference/cas_routing.py::route_by_compilability` | One of `"cas_to_english"`, `"invalid_to_explanation"`, `"conversational"`, plus any future template name. |
| `prompt_record_id` | str \| null | When the prompt came from an eval pack record (Phase 2 of the REPL plan) | The record id for reproducibility. Null for free-form prompts. |

### 3.3 `encoder` — the Δ°₃₉ trajectory and its marginals

The encoder produces one point on the open probability simplex Δ°₃₉ (40 strictly positive probabilities summing to 1) per source-token position. Source: `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py` — the `SimplexEncoder.forward` return keys `source_hidden` and `simplex_trajectory`. The 40 cells index the 10 Noetics × 4 Domains.

| Field | Type | Source | Description |
|---|---|---|---|
| `n_source_tokens` | int | Length of `cas_prefix_ids` + user text after tokenization | Total encoder input length. |
| `simplex_trajectory_summary` | object | See sub-fields below | Compact summary of the per-position `(L_src, 40)` simplex trajectory. Full tensor only in `capture_level="raw"`. |
| `simplex_trajectory_summary.mean` | list[float] (length 40) | Mean across source positions, padding-masked | The average Δ°₃₉ point over the source. |
| `simplex_trajectory_summary.max` | list[float] (length 40) | Max across source positions | Where the encoder peaked on each state. |
| `simplex_trajectory_summary.argmax_state_per_position` | list[int] (length `L_src`) | `argmax_k simplex_trajectory[i, k]` for each source position `i` | Which of the 40 states each source token leaned toward most. |
| `simplex_trajectory_summary.entropy_per_position` | list[float] (length `L_src`) | Shannon entropy of `simplex_trajectory[i, :]` | Per-token uncertainty about which state. |
| `simplex_pooled` | list[float] (length 40) | `typed_fiber_decoder.py:325-331` already computes this for the phrase-bias path; expose it | Padding-masked mean. |
| `noetic_marginal` | list[float] (length 10) | Sum the 4 domains for each Noetic from `simplex_pooled` | `typed_fiber_decoder.py:331` already does this as `pooled_noetic`. |
| `domain_marginal` | list[float] (length 4) | Sum the 10 Noetics for each Domain from `simplex_pooled` | Cheap reshape. Not currently computed by the model; the trace builder computes it. |
| `drive_marginal` | list[float] (length 7) \| null | **Not produced by the encoder trunk.** Derived from per-position slot-type decisions where slot is `DRIVE_LETTER` (id 6) — aggregate copy-source token types into a 7-bin histogram. Null when no drive slot fired. | Path B from Mode 7 design §10. |
| `register_marginal` | list[float] (length 4) \| null | Same pattern — derived from positions where slot is `REGISTER_LETTER` (id 4) | Same caveat. |
| `dominant_noetic` | int (0-9) | `argmax(noetic_marginal)` | Canonical Noetic id. Maps to names below in `summary.dominant_noetic_name`. |
| `dominant_domain` | str | `argmax(domain_marginal)` mapped to letter | One of `"P"`, `"C"`, `"E"`, `"O"`. |
| `dominant_drive` | str \| null | `argmax(drive_marginal)` when not null | One of `"F1"`..`"F7"`. |
| `dominant_register` | str \| null | `argmax(register_marginal)` when not null | One of `"T"`, `"A"`, `"f"`, `"E"`. |
| `simplex_open_simplex_valid` | bool | Per Correction 4 in `CLAUDE.md`: every `p_k > 0` | False flags an out-of-domain run. |
| `min_pk` | float | Smallest `p_k` over the whole trajectory | Visible early-warning for boundary collapse. |
| `encoder_l2_per_layer` | list[float] | L2 norm of `_EncoderBlock` outputs (4 layers per `SimplexEncoderConfig`) plus the 2-layer mirror-descent tail = length 6 | Surfaced via `cas_native/model/activation_hooks.py`. As of 2026-05-04 the allow-list does NOT include `SimplexEncoder` / `_EncoderBlock`; the smallest hook is extending `CAS_ALIGNED_CLASS_NAMES`. v0 schema includes the field; if hooks aren't wired yet, populate with an empty list and add a `summary.trace_warnings` entry. |

### 3.4 `decoder_per_position` — one entry per output position

This is the load-bearing layer for Stage 3 and the Living Thought Atlas. The decoder is a pointer-generator: every output position decides between an LM emission and a pointer-copy from a source position. Source: `cas_native/model/typed_fiber_decoder.py:274-367` — the `TypedFiberDecoder.forward` return dict carries `lm_logits`, `slot_type_logits`, `p_copy`, `copy_source_indices`, `decoder_hidden_state`.

`decoder_per_position` is a list of length `L_out` (the number of decoded tokens). Each entry:

| Field | Type | Source | Description |
|---|---|---|---|
| `position` | int | Index `0..L_out-1` | Output position. |
| `id` | str (UUID4) | Generated at trace build | Stable id for this decoder-position object; used as a graph node key by the Atlas. |
| `parent_ids` | list[str] | `[trace_id]` | Walks back to the parent trace. |
| `decoded_token_id` | int | Greedy argmax of `lm_logits[position]`, possibly overridden by hard-typed-emission copy at `sample_decoder.py:187-223` | The id that was actually emitted. |
| `decoded_token_str` | str | BPE detokenization of `decoded_token_id` | The visible text fragment. |
| `slot_type` | str | `argmax(slot_type_logits[position])` mapped to name | One of `"CONNECTIVE"`, `"OMEGA"`, `"STAGE_VAR"`, `"COEFFICIENT"`, `"REGISTER_LETTER"`, `"DOMAIN_LETTER"`, `"DRIVE_LETTER"`, `"FRACTAL_K_LITERAL"`, `"NOETIC_PHRASE"`. The order is contract: `SLOT_TYPES` at `typed_fiber_decoder.py:31-41`. |
| `slot_type_id` | int | `argmax(slot_type_logits[position])` | The numeric slot id, 0-8. |
| `slot_type_confidence` | float | `softmax(slot_type_logits[position]).max()` | How peaked the slot decision was. Low confidence flags ambiguity. |
| `slot_type_top3` | list[{`slot_type`: str, `prob`: float}] | Top-3 entries of `softmax(slot_type_logits[position])` | Ghost-branch fuel for the Atlas. |
| `lm_logits_top5` | list[{`token_id`: int, `token_str`: str, `prob`: float}] | Top-5 of `softmax(lm_logits[position])` | The five tokens the LM most wanted to emit. The chosen one is usually but not always the top entry (hard-typed-emission can override). |
| `p_copy_top5` | list[{`src_position`: int, `prob`: float}] | Top-5 of `p_copy[position]` | The five source positions the pointer attended to. |
| `p_copy_entropy` | float | Shannon entropy of `p_copy[position, :]` | Low entropy = peaked attribution to one source token; high entropy = diffuse / unsure. |
| `copy_source_index` | int | `outputs["copy_source_indices"][position]` from `typed_fiber_decoder.py:351` | -1 at non-typed positions; argmax source position at typed positions. |
| `emission_route` | str | From `sample_decoder.py:224` `emission_route_trace` | `"lm"` or `"copy"`. Indicates which mechanism actually emitted the token. |
| `phrase_bias_active` | bool | `slot_type_probs[..., NOETIC_PHRASE] > 0.5` from `typed_fiber_decoder.py:344` | Whether the phrase-bias path mixed into the LM logits at this position. |
| `decoder_hidden_l2` | float | L2 norm of `decoder_hidden_state[position, :]` | Per-position activation magnitude summary. |
| `layer_l2` | list[float] | One per decoder block, length 6 per `TypedFiberDecoderConfig` | Per-layer hidden L2 at this output position. **Open**: requires the hook extension in §5; populate empty list with a warning if hooks aren't on. |

### 3.5 `attribution` — derived view of which source tokens caused which output tokens

`attribution` is a derived/condensed cousin of the per-position p_copy data, optimized for the Atlas to read without rebuilding it. It is computed by the trace builder from `decoder_per_position`, not the model.

| Field | Type | Description |
|---|---|---|
| `per_output_attribution` | list[object] (length `L_out`) | One row per output position. |
| `per_output_attribution[i].output_position` | int | Index. |
| `per_output_attribution[i].best_src_position` | int | `argmax(p_copy[i])`. -1 if non-copy slot. |
| `per_output_attribution[i].best_src_position_confidence` | float | `p_copy[i].max()`. |
| `per_output_attribution[i].best_src_token_str` | str \| null | BPE detokenization of `cas_prefix_ids[best_src_position]`. Null if -1. |
| `per_output_attribution[i].is_copy_slot` | bool | `slot_type` in {OMEGA, STAGE_VAR, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL}. |
| `cross_emission_count` | int | Number of output positions whose `best_src_position` points at a source-position from a *different* CAS expression than the conditioning one. The Stage 3 hard gate (`docs/working/candidate_e/stage3_plan_2026_05_13.md` §5). | 0 is clean. |
| `cross_emission_positions` | list[int] | The output positions, if any, that crossed. | Empty when clean. |

### 3.6 `admissibility` — does the output compile, and is each copy slot self-consistent?

Per `CLAUDE.md` Correction 1, each operator CO-k has an admissibility relation Dk specifying valid (source, target) pairs. The Python compiler at `api/notation/compiler.py` is the v0 authority. Rust admissibility at `cas-engine/src/ontology/operators.rs` is a v1.1 deepening (per Mode 7 §6 Phase 5).

| Field | Type | Source | Description |
|---|---|---|---|
| `output_is_cas` | bool | Trace builder — true when `cas_routing_decision.task_type` indicates a CAS-emitting template | Some replies are conversational; admissibility only applies to CAS output. |
| `output_compiles` | bool \| null | `api.notation::compile_expression(generated_text)` | Null if `output_is_cas` is false; else true / false. |
| `compile_error_class` | str \| null | From the compile artifact | `"parse"`, `"admissibility"`, `"rpm"`, or null. |
| `compile_error_message` | str \| null | Compiler diagnostic | Human-readable error. |
| `violations` | list[object] | From the compile artifact's typecheck/admissibility stage | Each entry: `{operator, source, target, reason}`. |
| `copy_slot_admissibility` | object | Trace builder | Per-position admissibility of the copy-source-slot match. |
| `copy_slot_admissibility.pass_count` | int | Sum of positions where chosen `slot_type` ∈ `COPY_ALLOWED_SLOT_IDS` AND copy source token's `src_token_type` matches | Hard-typed-emission's type-match guard, surfaced. |
| `copy_slot_admissibility.fail_positions` | list[int] | The output positions that failed the type-match check | Empty when clean. |
| `rpm_chain_check` | object \| null | When the compiled IR carries an RPM expression | Section-retraction direction per `CLAUDE.md` Correction 2. |
| `rpm_chain_check.chain_required` | bool | Compiler artifact | Whether RPM applies. |
| `rpm_chain_check.satisfied_links` | list[str] | e.g. `["A0", "D3"]` | Which prerequisites the trace satisfied. |
| `rpm_chain_check.missing_links` | list[str] | e.g. `["W3", "P3"]` | Which prerequisites are absent. |

### 3.7 `output` — what the user sees and what the post-processing pipeline did to get there

| Field | Type | Source | Description |
|---|---|---|---|
| `raw_decoded_tokens` | list[int] | The pre-postprocessing greedy output (`generated` in `sample_decoder.py:300`) | Argmax of `lm_logits` per position, possibly overridden by hard-typed-emission. |
| `raw_decoded_text` | str | BPE detokenization of `raw_decoded_tokens` (`sample_decoder.py:307`) | Verbatim model output before any repair. |
| `slot_type_trace` | list[int] | `sample_decoder.py:170` `slot_trace` | Per-position slot id, 0-8. Already returned by `decode_canary_pack`. |
| `emission_route_trace` | list[str] \| null | `sample_decoder.py:224` | Per-position `"lm"` or `"copy"`. Null when `hard_typed_emission=False`. |
| `identifier_repair_log` | object | `cas_native/inference/identifier_repair.py` | Identifier substitutions applied. |
| `identifier_repair_log.omega_substitutions` | list[[str, str]] | Replaced → with pairs | Ω-name fixes. |
| `identifier_repair_log.coefficient_substitutions` | list[[str, str]] | Same | Coefficient fixes. |
| `identifier_repair_log.let_var_substitutions` | list[[str, str]] | Same | Stage-var / let-var fixes. |
| `cas_routing_decision` | object | `cas_native/inference/cas_routing.py::RoutingDecision` | Compilability-gate verdict that selected the prompt template. |
| `cas_routing_decision.task_type` | str | Routing decision | One of `cas_to_english`, `invalid_to_explanation`, conversational, etc. |
| `cas_routing_decision.compiled` | bool | Routing decision | Whether the input compiled. |
| `cas_routing_decision.error_class` | str \| null | Routing decision | Compilation error class if any. |
| `rpm_repair_applied` | bool | `cas_native/inference/rpm_repair.py` if present | Whether RPM-chain repair fired. |
| `meta_logic_repair_applied` | bool | `cas_native/inference/meta_logic_repair.py` if present | Whether meta-logic repair fired. |
| `fractal_repair_applied` | bool | `cas_native/inference/fractal_repair.py` if present | Whether Cognitive Fractal repair fired. |
| `final_rendered_text` | str | Output of the full post-processing pipeline | What the user actually sees in the REPL. |
| `post_processing_changed_text` | bool | `raw_decoded_text != final_rendered_text` | A surface that distinguishes "model produced this verbatim" from "post-processing rescued it." |

### 3.8 `summary` — the high-level scalars the chat REPL marker line reads

| Field | Type | Description |
|---|---|---|
| `dominant_noetic_name` | str | Canonical name verbatim from `CLAUDE.md`: `"Idea"`, `"Mind"`, `"Positive"`, `"Negative"`, `"Vibration"`, `"Female"`, `"Male"`, `"Rhythm"`, `"Above/Cause"`, `"Below/Effect"`. |
| `dominant_domain_name` | str | `"Principled"`, `"Cognitive"`, `"Evaluative"`, `"Operational"`. |
| `dominant_drive_name` | str \| null | `"F1 Unity"`..`"F7 Purpose"` when drive marginal not null. |
| `dominant_register_name` | str \| null | `"Transcendent"`, `"Analytical"`, `"Affective"`, `"Embodied"` when register marginal not null. |
| `dominant_cas_notation` | str | Compact CAS notation, e.g. `"^2^C\|A"`. The marker line uses this. |
| `n_output_tokens` | int | Length of `decoder_per_position`. |
| `n_copy_emissions` | int | Count of positions with `emission_route == "copy"`. |
| `n_lm_emissions` | int | Count of positions with `emission_route == "lm"`. |
| `identifier_recovery_rate` | float \| null | The Stage 3 metric per `evaluate_candidate_e_stage2.py::per_record_recovery` when canonical identifiers are known | The same number the smoke prints. |
| `free_decode_confidence` | float | Mean of `slot_type_confidence` over `decoder_per_position` | Coarse "how sure was the model" scalar. |
| `cross_emission_clean` | bool | `attribution.cross_emission_count == 0` | The Stage 3 hard gate, surfaced. |
| `trace_warnings` | list[str] | Trace builder | Names of warnings raised during assembly. Canonical names: `"hooks_not_attached"`, `"possible_training_echo"`, `"post_processing_heavy_repair"`, `"cross_emission_leak"`, `"open_simplex_invalid"`, `"drive_marginal_unavailable"`. |
| `trace_size_bytes` | int | `len(json.dumps(trace))` after assembly | Memory-budget visibility. |

### 3.9 `timing_ms` — where the latency went

| Field | Type | Description |
|---|---|---|
| `tokenize` | float | Wall-clock ms to tokenize input. |
| `encoder_forward` | float | Encoder forward pass. |
| `decoder_forward` | float | Decoder forward pass (per-step accumulated). |
| `compile_check` | float | `compile_expression` invocation. |
| `post_process` | float | All repair / cleanup. |
| `trace_build` | float | Trace assembly itself. |
| `total` | float | End-to-end wall clock. |

---

## 4. Graph-identity mapping — schema → Living Thought Atlas nodes and edges

Codex's audit (`docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md`) locks the identity scheme: `node_key = kind + role + normalized_label + axis_attrs`; `edge_key = source_key + target_key + kind + label`. Every schema field that should appear in the Atlas has a defined mapping.

| Trace field | Becomes | `kind` | `role` | `normalized_label` | `axis_attrs` |
|---|---|---|---|---|---|
| Top-level `id` + `parent_ids` | A turn node | `Turn` | `turn` | `<turn_id>` | `{session_id, model_checkpoint_id, created_at}` |
| `input.bpe_tokens[i]` | A source-token node | `SourceToken` | `source_token` | `<token_str>` | `{position: i, token_id}` |
| `input.cas_prefix_ids[i]` (when `cas_prefix_mask[i]`) | A CAS-prefix-token node, subtype of SourceToken | `SourceToken` | `cas_prefix_token` | `<token_str>` | `{position: i, token_id}` |
| `encoder.dominant_noetic` (per-utterance) | A Noetic-marginal node | `NoeticMarginal` | `noetic_marginal_dominant` | `^<id> <Name>` | `{turn_id}` |
| `encoder.dominant_domain` | A Domain-marginal node | `DomainMarginal` | `domain_marginal_dominant` | `<letter>` | `{turn_id}` |
| `encoder.noetic_marginal[k]` for each k=0..9 | A Noetic-marginal node (10 total) | `NoeticMarginal` | `noetic_marginal` | `^<k>` | `{turn_id, weight: float}` |
| `encoder.domain_marginal[d]` for each d | A Domain-marginal node (4 total) | `DomainMarginal` | `domain_marginal` | `<letter>` | `{turn_id, weight}` |
| `decoder_per_position[t]` | A decoder-position node | `OutputPosition` | `<slot_type lowercased>` (e.g. `stage_var`, `omega`, `connective`) | `<decoded_token_str>` | `{position: t, slot_type, slot_type_confidence, emission_route}` |
| `decoder_per_position[t].slot_type_top3[k]` (k>0) | A ghost-slot-type node | `GhostSlotType` | `ghost_slot_type` | `<slot_type>` | `{position: t, rank: k, prob}` |
| `decoder_per_position[t].lm_logits_top5[k]` (k>0, when emission_route == "lm") | A ghost-token node (alternative the LM almost emitted) | `GhostToken` | `ghost_token_lm` | `<token_str>` | `{position: t, rank: k, prob}` |
| `decoder_per_position[t].p_copy_top5[k]` (when emission_route == "copy") | A ghost-source-edge from this position to a source token | edge | `ghost_copied_from` | label = `prob=<value>` | (edge axis_attrs: `{position: t, rank: k}`) |
| `attribution.per_output_attribution[t].best_src_position` (when `is_copy_slot`) | An edge from the OutputPosition node to the SourceToken node at that position | edge | `copied_from` | `prob=<confidence>` | (edge axis_attrs: `{output_position: t}`) |
| `admissibility.violations[v]` | A violation node | `AdmissibilityViolation` | `violation` | `<operator>:<source>→<target>` | `{reason}` |
| `admissibility.rpm_chain_check.missing_links[m]` | An RPM-gap node | `RpmGap` | `rpm_missing_link` | `<link name>` | `{turn_id}` |
| `output.identifier_repair_log.omega_substitutions[s]` | A repair-edge from the raw OutputPosition node to a corrected RepairedToken node | edge + node | `repaired_to` / `RepairedToken` | `<replacement>` | `{kind: omega}` |
| `summary.dominant_cas_notation` | The Cognitive State node for the whole turn | `CognitiveState` | `dominant_state` | `^<n>^<D>\|<R>` | `{turn_id}` |

The Atlas builder reads the trace dict, walks these rules, and emits its `CasGraph`. **The schema is the contract; the builder is one consumer.** A different consumer (e.g. paper-export, dashboard heatmap) is free to walk the same dict differently.

Two normalization rules from Codex's audit that this schema enforces:

1. **Stable per-trace position semantics.** A `SourceToken` node's `axis_attrs.position` is its position within *this turn's* encoder input. Across turns, position is not a stable identity. Cross-turn deduplication uses `normalized_label` (the token string), not position.

2. **Slot-type-as-role.** `OutputPosition` nodes role-distinguish by slot type. An `OMEGA`-role node and a `CONNECTIVE`-role node with the same `normalized_label` are different nodes. This matches Codex's "role" axis exactly.

---

## 5. Inversion Replay seam — where the trace lives in the bigger picture

Per `project_living_thought_atlas_flagship_2026_05_13.md`, **Inversion Replay** is a named flagship feature: take a decision node, flip a CAS axis (Noetic / Domain / Drive / Register / slot type), replay forward from that alternate commitment, render the ghost branch.

What v0 records that supports Inversion Replay:

- **Top-K at every decision node.** `slot_type_top3`, `lm_logits_top5`, `p_copy_top5` give the Atlas the *alternatives the model considered* without re-running the model. A "what if the slot had been COEFFICIENT instead of STAGE_VAR" view of one position can be rendered statically from these fields.
- **Cross-emission flags.** `attribution.cross_emission_count` and `cross_emission_positions` flag the exact decisions where the model leaked. These are natural Inversion-Replay entry points (the user clicks the flagged position to ask "what if it hadn't leaked").
- **Ghost branches without re-decoding.** Combined `slot_type_top3` + `lm_logits_top5` + `p_copy_top5` is enough to render single-position ghost branches as static alternatives. The Atlas can show "the model almost said X here" without invoking the model.

What v0 does NOT record but Inversion Replay v1+ will need:

- **Re-decoding from a chosen position.** "Flip a CAS axis on this node and re-decode from here forward" requires running the model with the rest of the prefix held and the flipped axis substituted in. That is a separate concern; the trace records WHAT happened, replay is a follow-on system. v1+ may add a `replay_seed_state` field (the decoder hidden state at the chosen position) so the Atlas server can pick up decoding from there, but v0 does not, because (a) the hidden state is heavy and (b) re-decoding is not yet wired.
- **Counterfactual scoring.** "How likely is the ghost branch vs the actual branch" — beyond the top-K probabilities — needs decoder runs. Defer.
- **Multi-position branch surgery.** Flipping one axis and propagating forward several steps requires re-decoding; same as above.

In short: **v0 makes single-position Inversion Replay visualizable statically; multi-step Inversion Replay is a v1+ system that re-uses v0's top-K data as the entry surface.**

---

## 6. Field-by-field source of truth — what code produces each field

The single most useful table in this doc for the Step 6 implementer.

| Schema field | Source location | Notes |
|---|---|---|
| `schema_version`, `id`, `trace_id`, `created_at` | Trace builder | UUID4 + `time.strftime`. |
| `parent_ids` | Chat REPL session manager | The session id is the chat session UUID; the turn id is its position-in-session. |
| `source` | Constant per caller | `"stage3_chat_repl"`, `"stage3_local_smoke"`, `"replay_trace"`. |
| `model_checkpoint_id` | Run manifest read at REPL startup | `noetic-compass-scaffold/.../inference/stage3_local_loader.py::load_stage3_local` already returns `bundle.hash_report`; reuse that. |
| `model_code_version` | `subprocess.check_output(["git", "rev-parse", "HEAD"])` at REPL startup | Cached for the session. |
| `capture_level` | REPL CLI flag or default `"full"` | Drives summarization choices in the builder. |
| `input.raw_user_text` | Chat REPL input read | Verbatim. |
| `input.rewrite_applied` / `rewritten_text` | `cas_native/inference/rewrite_shim.py::rewrite_to_training_surface` | Return-value capture. |
| `input.cas_signal_detected` | `cas_native/inference/rewrite_shim.py::detect_cas_signal` | Return value. |
| `input.bpe_tokens` | `cas_native/training/tokenizer.py::HybridCASTokenizer.encode` | Trace builder zips `token_ids` with `tokenizer.decode([tid])` per id. |
| `input.cas_prefix_ids` / `cas_prefix_mask` | `cas_native/training/datasets/simplex_collator.py::SimplexCollator.__call__` | The batch the collator produces; read its `cas_prefix_ids` and `cas_prefix_mask` fields. |
| `input.prompt_template` | `cas_native/inference/cas_routing.py::route_by_compilability` | Return value. |
| `input.prompt_record_id` | REPL Phase 2 record-picker | Null for free-form prompts. |
| `encoder.n_source_tokens` | `len(input.cas_prefix_ids)` | Trivial. |
| `encoder.simplex_trajectory_summary.*` | `SimplexEncoder.forward` returns `simplex_trajectory` at `simplex_encoder.py` (exact line numbers TBD when stage-1 skeleton lands); trace builder summarizes. | Mean / max / argmax / entropy are pure numpy. |
| `encoder.simplex_pooled` | Already computed at `typed_fiber_decoder.py:325-328`; expose it via the decoder return dict OR recompute in the trace builder from `simplex_trajectory` | Either works; recomputation is cheap. |
| `encoder.noetic_marginal` | Already computed at `typed_fiber_decoder.py:331` as `pooled_noetic`; expose it OR recompute | Trace builder owns either path. |
| `encoder.domain_marginal` | NOT currently computed by the model | Trace builder reshapes `simplex_pooled.view(4, 10).sum(dim=1)`. |
| `encoder.drive_marginal` / `register_marginal` | NOT produced by encoder trunk. **Open in §10.** Path B (Mode 7 design §10) derives from per-position slot-type histograms. | Null when no relevant slot fired. |
| `encoder.dominant_noetic` / `dominant_domain` | `argmax` over respective marginals | Pure derivation. |
| `encoder.dominant_drive` / `dominant_register` | `argmax` over marginals when not null | Pure derivation. |
| `encoder.simplex_open_simplex_valid` / `min_pk` | Trace builder iterates `simplex_trajectory` and checks every cell > 0 | Cheap. |
| `encoder.encoder_l2_per_layer` | Activation hooks on `_EncoderBlock` and the mirror-descent tail. **Requires extending `CAS_ALIGNED_CLASS_NAMES` in `cas_native/model/activation_hooks.py:70-93`.** | Without the extension, populate empty list and add `summary.trace_warnings: "hooks_not_attached"`. |
| `decoder_per_position[t].decoded_token_id` / `decoded_token_str` | `sample_decoder.py:300` `generated` list (the actual emitted ids), then `tokenizer.decode([tid])` | One per position. |
| `decoder_per_position[t].slot_type` / `slot_type_id` / `slot_type_confidence` / `slot_type_top3` | `outputs["slot_type_logits"]` from `typed_fiber_decoder.py:306` per position; softmax + top-3 | Cheap. |
| `decoder_per_position[t].lm_logits_top5` | `outputs["lm_logits"]` from `typed_fiber_decoder.py:305` per position; softmax + top-5 | Use `topk(5)`. |
| `decoder_per_position[t].p_copy_top5` / `p_copy_entropy` | `outputs["p_copy"]` from `typed_fiber_decoder.py:315` per position | `topk(5)` + Shannon entropy. |
| `decoder_per_position[t].copy_source_index` | `outputs["copy_source_indices"]` from `typed_fiber_decoder.py:351` per position | -1 at non-typed positions. |
| `decoder_per_position[t].emission_route` | `sample_decoder.py:224` `emission_route_trace[t]` | Available when `hard_typed_emission=True`; "lm" elsewhere. |
| `decoder_per_position[t].phrase_bias_active` | `softmax(slot_type_logits[t])[NOETIC_PHRASE] > 0.5` | Direct from `typed_fiber_decoder.py:344`. |
| `decoder_per_position[t].decoder_hidden_l2` | `outputs["decoder_hidden_state"]` from `typed_fiber_decoder.py:304`, L2 norm per position | Cheap. |
| `decoder_per_position[t].layer_l2` | Activation hooks on `_DecoderBlock`. **Same hook extension as encoder.** | Empty list + warning when not wired. |
| `attribution.per_output_attribution` | Trace builder derives from `decoder_per_position[*].p_copy_top5` and `copy_source_index` | Pure post-processing. |
| `attribution.cross_emission_count` / `cross_emission_positions` | Trace builder cross-checks each `best_src_position` against pair-membership data passed in from the prompt builder. Pair-membership for Stage 3 swap-pair records is in the eval pack record. | When prompt is free-form (no pair membership known), both fields are `0` / `[]` and a warning fires. |
| `admissibility.output_compiles` / `compile_error_class` / `compile_error_message` / `violations` | `api/notation/compiler.py::compile_expression(final_rendered_text)` invocation, captured artifact | Single function call per turn. |
| `admissibility.copy_slot_admissibility.*` | Trace builder iterates `decoder_per_position` and cross-checks `copy_source_index` against the source's `src_token_type` (collator output) | The type-match guard at `sample_decoder.py:202-209` is the reference logic. |
| `admissibility.rpm_chain_check.*` | From the compiler artifact's RPM stage when present | Null otherwise. |
| `output.raw_decoded_tokens` / `raw_decoded_text` | `sample_decoder.py:300` + `:307` | Direct. |
| `output.slot_type_trace` | `sample_decoder.py:170` `slot_trace` list | Already returned by `decode_canary_pack` (`sample_decoder.py:376-378`). |
| `output.emission_route_trace` | `sample_decoder.py:316` | Null when `hard_typed_emission=False`. |
| `output.identifier_repair_log.*` | `cas_native/inference/identifier_repair.py` repair-pass return | Surface as logs, not side effects. |
| `output.cas_routing_decision.*` | `cas_native/inference/cas_routing.py::RoutingDecision` | Return dict. |
| `output.rpm_repair_applied` / `meta_logic_repair_applied` / `fractal_repair_applied` | Sibling modules in `cas_native/inference/` | Boolean flags from each repair pass. |
| `output.final_rendered_text` | Output of the post-processing pipeline | Trace builder receives it from the caller. |
| `output.post_processing_changed_text` | `raw_decoded_text != final_rendered_text` | Trivial. |
| `summary.dominant_noetic_name` / `dominant_domain_name` / `dominant_drive_name` / `dominant_register_name` | Lookup against canonical name tables (Noetic from `CLAUDE.md`) | Pure mapping. |
| `summary.dominant_cas_notation` | `f"^{n}^{D}\|{R}"` where R may be absent | Compact CAS render. |
| `summary.n_output_tokens` / `n_copy_emissions` / `n_lm_emissions` | Counts over `decoder_per_position` | Cheap. |
| `summary.identifier_recovery_rate` | `evaluate_candidate_e_stage2.py::per_record_recovery(record, generated_text)` when canonical identifiers are known | Null for free-form prompts. The smoke at `inference/stage3_local_smoke.py` already uses it. |
| `summary.free_decode_confidence` | Mean of `slot_type_confidence` over `decoder_per_position` | Coarse. |
| `summary.cross_emission_clean` | `attribution.cross_emission_count == 0` | Boolean. |
| `summary.trace_warnings` | Trace builder appends warnings during assembly | Canonical names listed in §3.8. |
| `summary.trace_size_bytes` | `len(json.dumps(trace))` after assembly | Computed last. |
| `timing_ms.*` | `time.perf_counter()` deltas around each stage in the trace builder | Standard pattern. |

Where a field's source is unclear, this table says so. The big two open items are the activation hooks (§3.3 / §3.4) and the Drive / Register marginals (§3.3). Both are gracefully degraded — null or empty with a warning — when the upstream code path isn't wired.

---

## 7. What v0 explicitly does NOT include

Stated so future v1 / v2 designers don't think v0 forgot.

- **Per-layer activation hooks beyond `encoder_l2_per_layer` and `decoder_per_position[t].layer_l2`.** Full Mode 7 wants attention-entropy-per-layer and per-head attention weights. v0 ships the L2 summaries only; per-layer attention summaries land in v1.
- **Inversion Replay re-decoding seed.** v0 records what happened; it does not let the Atlas re-run the model from a chosen position with a flipped axis. That is a separate system, gated on v1+ work.
- **Per-Drive activation marginals from a dedicated head.** The encoder trunk does not produce them; v0 derives observed Drive marginals from slot-type histograms (Path B). A v1.1+ might add aux Drive / Register heads on the trunk (Path A).
- **Cross-session Atlas relations.** Per-turn trace is per-turn. The Atlas itself maintains cross-turn / cross-session graph identity by deduplicating on `normalized_label`. The trace does not store cross-session edges; the Atlas builder does.
- **Inversion Scan (Mode 5) and Production Recipe (Mode 4) exposure.** Those are sibling exposure modes per Mode 7 design §2. They will consume this trace dict and produce their own derived views. v0 does not bake them in.
- **Activation-pattern attribution / influence functions.** Heavy. Not in v0.
- **Nearest-neighbor lookups against training data (training echo detection).** The Mode 7 design §9 raises this; the existing `cas_native/trace/generation_trace.py::NearestNeighborIndex` is the primitive. v0 includes a warning slot (`summary.trace_warnings: "possible_training_echo"`) but does not bake the nearest-neighbor index into v0 trace assembly.

---

## 8. Versioning and migration

- **Top-level `schema_version: "cas_trace_v0"`.** Required check on every consumer.
- **Migration policy: hard.** A consumer that reads an unknown `schema_version` MUST raise an error. Silent best-effort parsing is forbidden because trace consumers (especially the Atlas) make claims to users — "this is the trace of your reply" — and silently parsing a future-format trace risks misleading downstream renders.
- **v0 → v1: additive only.** Adding new fields is fine; existing v0 fields must keep meaning. v0 readers can ignore unknown fields silently.
- **v1 → v2: may rename.** Bumping the major version signals that v0 / v1 readers must update or be locked out. Renaming `decoded_token_str` is a v2 move, not a v1 move.
- **Coexistence with the K=9 `mechanistic_trace.v1`.** The two schemas are siblings, not extensions of each other. A consumer that wants both reads `schema_version` first and dispatches. The Atlas Phase-1A substrate (`dashboard/src/lib/casGraph/fromStage3Trace.ts`) reads v0 only; a separate `fromMechanisticTrace.ts` reads the classifier-era schema if needed.

---

## 9. Example trace — small populated dict

Three-position output from a Stage 3 free-decode. Truncated and illustrative; field shapes match §3 exactly.

```json
{
  "schema_version": "cas_trace_v0",
  "id": "1f7a4d80-0010-4e29-9a6f-5b78b1c3a1aa",
  "trace_id": "ec2a1e63-7c5a-4f1b-8c4f-43c1c8d40fdc",
  "created_at": "2026-05-13T17:42:11Z",
  "parent_ids": [
    "session-7c4f-bb12-a019",
    "turn-0003"
  ],
  "source": "stage3_chat_repl",
  "model_checkpoint_id": "stage_e3_20260513T043823Z/ckpt_final.pt",
  "model_code_version": "707249b",
  "capture_level": "full",

  "input": {
    "raw_user_text": "Explain Θ(stageΩ_001) = 2*stageA1_001",
    "rewrite_applied": false,
    "rewritten_text": null,
    "cas_signal_detected": true,
    "bpe_tokens": [
      {"token_id": 14, "token_str": "Explain"},
      {"token_id": 8231, "token_str": " Θ"},
      {"token_id": 117, "token_str": "("},
      {"token_id": 4429, "token_str": "stageΩ_001"},
      {"token_id": 23, "token_str": ")"}
    ],
    "cas_prefix_ids": [2, 8231, 117, 4429, 23, 91, 207, 3],
    "cas_prefix_mask": [true, true, true, true, true, true, true, true],
    "prompt_template": "cas_to_english",
    "prompt_record_id": "rpm_v2_dev_0042"
  },

  "encoder": {
    "n_source_tokens": 8,
    "simplex_trajectory_summary": {
      "mean": [0.012, 0.014, 0.31, 0.018, 0.022, 0.045, 0.18, 0.011, 0.10, 0.012,
               0.013, 0.011, 0.16, 0.012, 0.014, 0.013, 0.012, 0.011, 0.013, 0.014,
               0.012, 0.013, 0.014, 0.012, 0.013, 0.011, 0.012, 0.013, 0.012, 0.014,
               0.012, 0.013, 0.014, 0.012, 0.013, 0.011, 0.012, 0.013, 0.012, 0.014],
      "max": [0.05, 0.06, 0.71, 0.04, 0.05, 0.08, 0.32, 0.03, 0.18, 0.03,
              0.03, 0.03, 0.34, 0.04, 0.03, 0.03, 0.03, 0.03, 0.03, 0.04,
              0.03, 0.03, 0.04, 0.03, 0.04, 0.03, 0.03, 0.04, 0.03, 0.04,
              0.03, 0.03, 0.04, 0.03, 0.04, 0.03, 0.03, 0.04, 0.03, 0.04],
      "argmax_state_per_position": [2, 2, 12, 2, 12, 2, 2, 2],
      "entropy_per_position": [3.42, 3.31, 2.18, 3.18, 2.27, 3.40, 3.05, 3.51]
    },
    "simplex_pooled": [0.012, 0.014, 0.31, 0.018, 0.022, 0.045, 0.18, 0.011, 0.10, 0.012,
                       0.013, 0.011, 0.16, 0.012, 0.014, 0.013, 0.012, 0.011, 0.013, 0.014,
                       0.012, 0.013, 0.014, 0.012, 0.013, 0.011, 0.012, 0.013, 0.012, 0.014,
                       0.012, 0.013, 0.014, 0.012, 0.013, 0.011, 0.012, 0.013, 0.012, 0.014],
    "noetic_marginal": [0.049, 0.051, 0.484, 0.054, 0.063, 0.069, 0.082, 0.048, 0.069, 0.051],
    "domain_marginal": [0.241, 0.358, 0.205, 0.196],
    "drive_marginal": null,
    "register_marginal": null,
    "dominant_noetic": 2,
    "dominant_domain": "C",
    "dominant_drive": null,
    "dominant_register": null,
    "simplex_open_simplex_valid": true,
    "min_pk": 0.0023,
    "encoder_l2_per_layer": [12.4, 13.1, 13.0, 12.7, 8.2, 7.9]
  },

  "decoder_per_position": [
    {
      "position": 0,
      "id": "pos-0-9c1a",
      "parent_ids": ["ec2a1e63-7c5a-4f1b-8c4f-43c1c8d40fdc"],
      "decoded_token_id": 412,
      "decoded_token_str": "The",
      "slot_type": "CONNECTIVE",
      "slot_type_id": 0,
      "slot_type_confidence": 0.93,
      "slot_type_top3": [
        {"slot_type": "CONNECTIVE", "prob": 0.93},
        {"slot_type": "NOETIC_PHRASE", "prob": 0.04},
        {"slot_type": "OMEGA", "prob": 0.01}
      ],
      "lm_logits_top5": [
        {"token_id": 412, "token_str": "The", "prob": 0.71},
        {"token_id": 1102, "token_str": "This", "prob": 0.12},
        {"token_id": 240, "token_str": "Here", "prob": 0.06},
        {"token_id": 6612, "token_str": "Recipe", "prob": 0.04},
        {"token_id": 919, "token_str": "Below", "prob": 0.02}
      ],
      "p_copy_top5": [
        {"src_position": 0, "prob": 0.31},
        {"src_position": 5, "prob": 0.22},
        {"src_position": 1, "prob": 0.18},
        {"src_position": 7, "prob": 0.11},
        {"src_position": 3, "prob": 0.08}
      ],
      "p_copy_entropy": 1.81,
      "copy_source_index": -1,
      "emission_route": "lm",
      "phrase_bias_active": false,
      "decoder_hidden_l2": 6.21,
      "layer_l2": [5.1, 5.6, 5.9, 6.0, 6.1, 6.2]
    },
    {
      "position": 1,
      "id": "pos-1-2b04",
      "parent_ids": ["ec2a1e63-7c5a-4f1b-8c4f-43c1c8d40fdc"],
      "decoded_token_id": 4429,
      "decoded_token_str": "stageΩ_001",
      "slot_type": "OMEGA",
      "slot_type_id": 1,
      "slot_type_confidence": 0.88,
      "slot_type_top3": [
        {"slot_type": "OMEGA", "prob": 0.88},
        {"slot_type": "STAGE_VAR", "prob": 0.07},
        {"slot_type": "CONNECTIVE", "prob": 0.03}
      ],
      "lm_logits_top5": [
        {"token_id": 4429, "token_str": "stageΩ_001", "prob": 0.41},
        {"token_id": 4521, "token_str": "stageΩ_002", "prob": 0.21},
        {"token_id": 990, "token_str": "Ω", "prob": 0.12},
        {"token_id": 4811, "token_str": "stageΩ_017", "prob": 0.06},
        {"token_id": 78, "token_str": ":", "prob": 0.03}
      ],
      "p_copy_top5": [
        {"src_position": 3, "prob": 0.94},
        {"src_position": 4, "prob": 0.03},
        {"src_position": 1, "prob": 0.02},
        {"src_position": 5, "prob": 0.005},
        {"src_position": 0, "prob": 0.002}
      ],
      "p_copy_entropy": 0.31,
      "copy_source_index": 3,
      "emission_route": "copy",
      "phrase_bias_active": false,
      "decoder_hidden_l2": 6.84,
      "layer_l2": [5.3, 5.8, 6.1, 6.3, 6.5, 6.6]
    },
    {
      "position": 2,
      "id": "pos-2-7f8c",
      "parent_ids": ["ec2a1e63-7c5a-4f1b-8c4f-43c1c8d40fdc"],
      "decoded_token_id": 6,
      "decoded_token_str": " stands",
      "slot_type": "NOETIC_PHRASE",
      "slot_type_id": 8,
      "slot_type_confidence": 0.74,
      "slot_type_top3": [
        {"slot_type": "NOETIC_PHRASE", "prob": 0.74},
        {"slot_type": "CONNECTIVE", "prob": 0.21},
        {"slot_type": "OMEGA", "prob": 0.03}
      ],
      "lm_logits_top5": [
        {"token_id": 6, "token_str": " stands", "prob": 0.41},
        {"token_id": 18, "token_str": " is", "prob": 0.28},
        {"token_id": 419, "token_str": " represents", "prob": 0.11},
        {"token_id": 22, "token_str": " denotes", "prob": 0.08},
        {"token_id": 53, "token_str": " names", "prob": 0.05}
      ],
      "p_copy_top5": [
        {"src_position": 7, "prob": 0.34},
        {"src_position": 3, "prob": 0.22},
        {"src_position": 1, "prob": 0.18},
        {"src_position": 5, "prob": 0.14},
        {"src_position": 0, "prob": 0.06}
      ],
      "p_copy_entropy": 1.62,
      "copy_source_index": -1,
      "emission_route": "lm",
      "phrase_bias_active": true,
      "decoder_hidden_l2": 6.51,
      "layer_l2": [5.2, 5.7, 6.0, 6.2, 6.4, 6.5]
    }
  ],

  "attribution": {
    "per_output_attribution": [
      {"output_position": 0, "best_src_position": -1, "best_src_position_confidence": 0.0, "best_src_token_str": null, "is_copy_slot": false},
      {"output_position": 1, "best_src_position": 3, "best_src_position_confidence": 0.94, "best_src_token_str": "stageΩ_001", "is_copy_slot": true},
      {"output_position": 2, "best_src_position": -1, "best_src_position_confidence": 0.0, "best_src_token_str": null, "is_copy_slot": false}
    ],
    "cross_emission_count": 0,
    "cross_emission_positions": []
  },

  "admissibility": {
    "output_is_cas": false,
    "output_compiles": null,
    "compile_error_class": null,
    "compile_error_message": null,
    "violations": [],
    "copy_slot_admissibility": {
      "pass_count": 1,
      "fail_positions": []
    },
    "rpm_chain_check": null
  },

  "output": {
    "raw_decoded_tokens": [412, 4429, 6],
    "raw_decoded_text": "The stageΩ_001 stands",
    "slot_type_trace": [0, 1, 8],
    "emission_route_trace": ["lm", "copy", "lm"],
    "identifier_repair_log": {
      "omega_substitutions": [],
      "coefficient_substitutions": [],
      "let_var_substitutions": []
    },
    "cas_routing_decision": {
      "task_type": "cas_to_english",
      "compiled": true,
      "error_class": null
    },
    "rpm_repair_applied": false,
    "meta_logic_repair_applied": false,
    "fractal_repair_applied": false,
    "final_rendered_text": "The stageΩ_001 stands",
    "post_processing_changed_text": false
  },

  "summary": {
    "dominant_noetic_name": "Positive",
    "dominant_domain_name": "Cognitive",
    "dominant_drive_name": null,
    "dominant_register_name": null,
    "dominant_cas_notation": "^2^C",
    "n_output_tokens": 3,
    "n_copy_emissions": 1,
    "n_lm_emissions": 2,
    "identifier_recovery_rate": 1.0,
    "free_decode_confidence": 0.85,
    "cross_emission_clean": true,
    "trace_warnings": [],
    "trace_size_bytes": 6128
  },

  "timing_ms": {
    "tokenize": 1.4,
    "encoder_forward": 18.2,
    "decoder_forward": 32.1,
    "compile_check": 0.0,
    "post_process": 0.6,
    "trace_build": 4.8,
    "total": 57.1
  }
}
```

The example is intentionally tiny (3 output positions). A real Stage 3 turn is more like 100-200 positions and ~45 KB; the structure is identical.

---

## 10. Open questions for the user / Codex to resolve

These are the items the schema cannot lock without an explicit decision. Recommended defaults are stated; flipping them is fine.

1. **Top-K — should K be 3 or 5 or both?** The schema currently uses `slot_type_top3`, `lm_logits_top5`, `p_copy_top5`. **Recommended:** keep slot at 3 (there are only 9 slot types so 3 is informative without being exhaustive) and LM/copy at 5 (Ghost Branches consume top-5 for the Atlas). **Alternative:** widen all three to top-10 for richer ghost-branch fuel at modest size cost (~50% size bump on the per-position record).

2. **Should `attribution.per_output_attribution` carry `p_copy_entropy` or just argmax?** The decoder-per-position record already has `p_copy_entropy`; carrying it again in `attribution` is redundant. **Recommended:** drop the duplicate; consumers wanting entropy read it from `decoder_per_position`. **Alternative:** carry it in `attribution` too if it simplifies the Atlas builder enough to be worth the duplication.

3. **Trace persistence default — where do traces live and when are they written?** Three options: (a) write every trace to `.tmp/traces/<session_id>/<turn_id>.json` (private, easy); (b) write a JSONL per session at `runs/<session_id>/traces.jsonl` (lighter on filesystem, replay-friendly); (c) keep in-memory only until `/trace --save`. **Recommended:** (b) — JSONL per session, always-on. Mode 7 design §10 Q3 came to the same conclusion. Adding `--no-trace-persist` for ad-hoc sessions later is cheap.

4. **Versioning of `trace_id` — random UUID4, content-hash, or timestamp+counter?** **Recommended:** UUID4. Content-hash makes ids reproducible across runs but a tiny semantic change (whitespace, model_code_version) shifts every id; timestamp+counter is fragile across replay. UUID4 + a separate `content_hash` field in v1+ if reproducibility matters.

5. **Encoder activation hooks — extend `CAS_ALIGNED_CLASS_NAMES` now or land v0 without `encoder_l2_per_layer` and `decoder_per_position[t].layer_l2`?** Mode 7 design §6 Phase 2 lists this as a small change. **Recommended:** extend the allow-list as part of Step 6 (Mode 7 wiring). The schema field is in v0; if hooks aren't attached yet, populate empty lists with `summary.trace_warnings: "hooks_not_attached"`. Consumers (Atlas, REPL `/trace`) handle the empty case gracefully.

6. **Drive and Register marginals on the encoder trunk (Mode 7 design §10 Q1).** v0 schema includes both as `null`-able fields. Path B (derive from slot-type histograms over output positions) requires no model changes; Path A (aux Drive / Register heads on the trunk) requires training. **Recommended:** ship Path B in v0; leave both fields null when no relevant slot fired; defer Path A to a later version after Stage 3 stabilizes.

7. **Cross-emission detection scope — only for prompts with known pair-membership, or universal?** Stage 3's hard gate is defined for swap-pair prompts. For free-form prompts, "cross-emission" is not well-defined. **Recommended:** populate `attribution.cross_emission_count` only when pair-membership is known (eval-pack records); else surface `0` and warn `"cross_emission_not_applicable"`. The Atlas should render the unknown case as "—" not as "clean."

8. **Should the trace include the full `raw_decoded_text` even when it's identical to `final_rendered_text`?** Cost is small (200-500 bytes); benefit is that consumers always have both, no special-case branching. **Recommended:** always include both verbatim; rely on `post_processing_changed_text` boolean for the quick check.

---

**Document ends. No code changed by this doc. This schema is the contract that the Step 6 implementation (Mode 7 + chat REPL wiring) targets, and the Atlas Phase 1A substrate (`dashboard/src/lib/casGraph/fromStage3Trace.ts`) reads.**
