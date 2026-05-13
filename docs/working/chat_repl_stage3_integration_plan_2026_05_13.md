# Chat REPL Stage 3 Integration Plan (2026-05-13)

**Status:** DRAFT v1 — for Codex audit + user "go". No code edits proposed yet.

**Owner trail:** Stage 3 checkpoint at `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt` (pod) cleared its locked gates per Codex `707249b` (2026-05-13T07:55Z): free-decode identifier recovery 0.7778 dev / 0.6439 held-out, swap `cross_emission_count = 0`. The "next move" Codex named is wiring this checkpoint into the chat REPL with Mode 7 traceability visible per-utterance. This document is the file-by-file plan for doing that.

**Companion doc:** `docs/working/mode_7_traceability_design_2026_05_13.md` (being written in parallel) defines what Mode 7 surfaces consume. This plan defines the per-turn trace dict the REPL hands to that surface (§6).

**Glossary (used in plain language below):**
- *Free-decode* — the model generates each next token from its own previous tokens (deployment-like). Distinct from *teacher-forced (TF)*, where the gold prefix is fed in.
- *Greedy decode* — pick the highest-probability token at each step (no sampling). Stage 3 was trained with one-step scheduled sampling; at inference time we run plain greedy free-decode.
- *Identifier recovery* — does the generated text contain the right `stage[ADWP]\d+_\d+_\d{3,5}` identifier in the right position? This is the Stage 3 gate metric and the one piece of objective ground we can show the user.
- *Trace dict* — Python dict of structured fields a single turn produced. The thing Mode 7 surfaces consume. See §6 for the proposed shape.

## 1. Goal

The Stage 3 checkpoint generates CAS-grounded English text through free-decode greedy. The existing chat REPL at `noetic-compass-scaffold/noetic-compass/cas-native/inference/chat.py` was wired in the B-3 / B-4 era against a different model (K=9 classifier + a separate B-3 native generator). It does NOT load the simplex-MVP Stage 3 checkpoint and it does NOT decode through the simplex encoder/decoder path. Goal of this work is to land a chat surface where the user can:

1. Start the REPL on a local box.
2. Type a CAS prompt (or any English).
3. See the generated English reply, plus a structured trace surface for that single turn.
4. Iterate across multiple turns within a session, with the model picking up local context.

The success bar is "user can talk to the Stage 3 checkpoint and see the per-turn trace." It is NOT "this is a polished production chat product." Per §7, the human-review gate after Phase 2 is the load-bearing read.

## 2. What exists vs. what's missing — file-by-file audit

Audited files:

- `noetic-compass-scaffold/noetic-compass/cas-native/inference/chat.py` (1399 lines, B-4 era)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_cli.py` (the slash-command CLI entry)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/predict_cas.py` (K=9 predictor — NOT the Stage 3 model)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/native_nl_generate.py` (B-3 native-gen wrapper — NOT the Stage 3 model)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/ood_gate.py` (OOD routing)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/postprocessor.py` (identifier repair, jargon checks)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/routed_generate.py`, `identifier_repair.py`, `cas_routing.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py` (canonical Stage 3 load + decode reference)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py` (the `greedy_decode` / `decode_canary_pack` path)
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` (model factory: `build_simplex_mvp_model`, `SimplexTrainConfig`, `DEFAULT_LOSS_WEIGHTS`)
- `noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_checkpoint.py` (`load_checkpoint(...)`)
- `noetic-compass-scaffold/noetic-compass/cas-native/training/scheduled_sampling.py` (training-only — NOT used at inference)
- `noetic-compass-scaffold/noetic-compass/cas-native/trace/live_capture.py` (`LiveTrace` dataclass, K=9 only)
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/belief/test_chat_repl_wiring.py` (B-4-era smoke tests, K=9 surface)

Audit table (evidence level: *exists* = code present; *works* = unit-tested at last touch; *Stage-3-relevant* = will be reused for the new path):

| File | Today's state | Stage-3-relevant? | Action |
|---|---|---|---|
| `inference/chat.py` | Loads K=9 + B-3 native gen, has `/menu /sample /raw /beliefs /why /forget /trace /native` commands, OOD gate wired, BeliefStore wired, `LiveTrace` plumbed to `/trace` | Surface layer (REPL loop, banner, commands, rendering) — reuse | Add a new *load path* alongside the existing two, gated behind a flag. Do NOT remove K=9 / B-3 paths in this round — they still work for K=9 demos. |
| `inference/predict_cas.py` | K=9 structured-token classifier loader. NOT the simplex-MVP model. | No — different architecture | Leave untouched. |
| `inference/native_nl_generate.py` | B-3-era generator using `NLGenerationHead`. NOT the simplex-MVP decoder. | No — different architecture | Leave untouched. The forbidden-foreign-model rule does not apply here (B-3 was CAS-Native) but B-3 is a separate lineage from Stage 3. |
| `inference/ood_gate.py` | English-vs-CAS routing gate; consumes K=9 prediction dict | Partially. The gate's signature `route(prompt, k9_result)` is K=9-specific. A v1 OOD route was added on top of K=9 confidences. For Stage 3 we have NO K=9-style head outputs — we have free-decode text + the Stage 3 trace. | Phase 5 work. For now, gate is **bypassed** in the new path (CAS_PIPELINE always). Risk: this is an explicit deferral, see §8. |
| `inference/postprocessor.py` / `identifier_repair.py` / `cas_routing.py` | Identifier-repair + jargon checks. Stage 3 free-decode emits exact identifiers when copy succeeds. The repair functions are still useful as a defensive post-pass. | Possibly | Phase 5 work. Don't wire on the first round; Stage 3 dev recovery is 0.78 (= ~22% miss rate) — wiring repair may help, but only on hard evidence it doesn't degrade good outputs. |
| `evaluation/evaluate_candidate_e_stage2.py` | The canonical Stage 3 loader + decoder reference. `build_model_and_load` (lines 179-202) + `decode_records` (lines 205-229) define exactly the loading + decoding path the REPL needs to mirror. | Yes — reference | Use as the blueprint for the new `cas_native/inference/load_stage3_model.py` and `cas_native/inference/stage3_decoder.py` (proposed Phase 1/2 files; see §4). |
| `evaluation/sample_decoder.py` | `greedy_decode(...)` and `decode_canary_pack(...)`. Single-record path. Returns text + token_ids + slot_type_trace + optional per_token_trace. | Yes — reuse | Phase 1 reuses `greedy_decode` directly. No fork. |
| `training/train_simplex_mvp.py` | Defines `build_simplex_mvp_model`, `SimplexTrainConfig`, `DEFAULT_LOSS_WEIGHTS`. | Yes — import surface | Re-import the model factory from `cas_native.training.train_simplex_mvp` (the evaluator does this; the REPL will do the same). |
| `training/simplex_checkpoint.py` | `load_checkpoint(path, model, optimizer, map_location, strict, restore_rng)`. | Yes — import surface | Reuse. |
| `training/scheduled_sampling.py` | Training-time helper. | No — inference path does NOT call scheduled sampling | Leave untouched. The note added to the integration doc: scheduled sampling was a **training** technique; at inference we run plain greedy. |
| `trace/live_capture.py` | `LiveTrace` dataclass + `capture_live_trace(model, batch, ...)`. Built against the K=9 head architecture (heads have `argmax_label`, attribution computed on bottleneck dim). | Partially — schema is reusable; the existing `capture_live_trace` call site is K=9-specific. | Phase 4 work. Define a new `Stage3Trace` dataclass (or extend `LiveTrace` with optional Stage-3 fields) so the REPL has a typed trace surface. The dataclass shape is the contract with Mode 7. |
| `tests/belief/test_chat_repl_wiring.py` | Smokes K=9 imports. | No | Add NEW Stage 3 smoke tests in a sibling file `tests/inference/test_chat_repl_stage3_wiring.py`. Don't modify the K=9 tests. |

Evidence-level summary:
- *Code path exists* for K=9 chat REPL + Stage 3 evaluator + Stage 3 model factory.
- *Proven to work* for Stage 3 model loading + free-decode greedy at scale via the e3 evaluator (`stage_e3_20260513T043823Z` measurements).
- *NOT proven to work*: the Stage 3 model serving a single ad-hoc English prompt through a chat surface. The evaluator only takes structured `rpm_chain` records with `cas_prefix_ids` already supplied. A user free-form English prompt has no `cas_prefix_ids`. This is the load-bearing open question (§8 Q1).

## 3. Architecture — inference flow

The Stage 3 model expects a `SimplexCollator` batch (encoder input from `cas_prefix_ids`, decoder runs against that conditioning). The chat surface needs to give the model something to condition on. Two viable designs; the plan picks Design A for Phase 1-3 and revisits Design B at Phase 5 once we have human evidence.

```
                                       (Design A — eval-pack-mirroring)
USER PROMPT (English)
    │
    ▼
[Phase 5: OOD / route gate — deferred; CAS_PIPELINE always for now]
    │
    ▼
[CAS prefix construction]
    │   Option A1: hand the user the eval-pack record list; user picks an ID
    │             or types one of N seed prompts; we use that record's
    │             cas_prefix verbatim. (Phase 2 default.)
    │   Option A2: text-only prompt — synthesize an empty cas_prefix (the
    │             fail-closed all-PAD path that train_simplex_mvp.py:516-522
    │             already supports). Reply will be ungrounded; flagged.
    │
    ▼
[SimplexCollator] → batch dict (cas_prefix_ids, cas_prefix_mask, etc.)
    │
    ▼
[Stage 3 model.forward()  (encoder + typed-fiber decoder)]
    │
    ▼
[greedy_decode (sample_decoder.greedy_decode)] — free-decode greedy
    │   inputs: model, record, collator, tokenizer
    │   returns: text, token_ids, n_tokens_generated, hit_eos,
    │            slot_type_trace, [optional per_token_trace]
    │
    ▼
[Optional Phase 5: identifier_repair.repair(...)] — deferred
    │
    ▼
[Trace assembly] — see §6 for the dict shape
    │
    ▼
USER-FACING OUTPUT: generated_text + small trace summary
                    (Mode 7 surface consumes the full trace dict)
```

Important plain-language points:
- The chat REPL does NOT use scheduled sampling. Scheduled sampling was the training-time trick that taught the model to handle its own prefix. At inference time the model already has that capability; we just run greedy free-decode.
- The Stage 3 checkpoint expects a SOURCE (the `cas_prefix`) to copy identifiers from. For a free-form English prompt with no attached source, the model still runs through the fail-closed all-PAD path (`train_simplex_mvp.py` lines 516-522), but it has nothing to copy from. The reply will be CAS-grounded only when a CAS prefix is provided.
- Phase 2 will land Option A1 (pick from eval-pack records). This is honest about what the model was trained on. Option B (free-form English → synthesized CAS prefix) requires a separate piece of machinery (an NL-to-CAS step) that does NOT yet exist for Stage 3, and is left for §8 Q2.

## 4. Phased file-by-file plan

Each phase is independently shippable. Each phase has a single hard gate; if the gate fails, do not advance.

### Phase 1 — Checkpoint loading harness (no chat surface yet)

Estimated dev: 3-4 hours local, CPU.

**Files added:**
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/load_stage3_model.py` (new). Single public function `load_stage3_model(checkpoint_path, tokenizer_path, english_bpe_path, device, max_cas_prefix_len=192)` that returns a dict with keys `{"model", "tokenizer", "collator", "device", "max_cas_prefix_len"}`. Lift logic from `evaluate_candidate_e_stage2.build_model_and_load` (lines 179-202) plus the tokenizer + collator boilerplate from `main()` (lines 496-504). No CLI; pure library function.

**Files audited / not modified:**
- `training/train_simplex_mvp.py` — re-imported for `build_simplex_mvp_model`, `SimplexTrainConfig`, `DEFAULT_LOSS_WEIGHTS`.
- `training/simplex_checkpoint.py` — re-imported for `load_checkpoint`.

**Test gate (Phase 1 done):** new file `tests/inference/test_load_stage3_model.py`. CPU-only. Builds a tiny config (d_model=64, decoder_n_layers=2) to instantiate the model class, exercises the import path. Does NOT load the actual 384/4/6 production checkpoint in CI (too heavy for CI machines).

**Evidence level at gate-pass:** code path exists + import works. NOT proven to load the actual Stage 3 checkpoint until a local hand-run reads `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt` (which is a pod path — see §8 Q3 about how to materialize that checkpoint locally).

### Phase 2 — Single-prompt CLI smoke

Estimated dev: 3-5 hours local.

**Files added:**
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_decoder.py` (new). Public function `decode_one(prompt_record, model, collator, tokenizer, *, device, max_new_tokens=192) -> dict`. Wraps `sample_decoder.greedy_decode(...)` with the trace=True path on by default. Returns the decoded dict plus a stub `trace_dict` field shaped per §6 (the actual trace assembly lives in Phase 4; Phase 2 returns the minimum shape so callers can stop pretending and start consuming it).
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_cli_smoke.py` (new). Argparse CLI: `python stage3_cli_smoke.py --checkpoint ... --tokenizer ... --english-bpe ... --record-id ...` — picks one record from `rpm_copy_grounding_v2_dev.jsonl`, runs through `load_stage3_model + decode_one`, prints the generated text + a 6-line trace summary.

**Test gate (Phase 2 done):** running the CLI smoke against a real dev record on a developer's CPU box (1) does not crash, (2) prints the generated text within ~30s, (3) the text contains at least one identifier matching the bounded-regex `\bstage[ADWP]\d+_\d+_\d{3,5}\b`. The third check is a sanity test, not a quality test.

**Human review gate (load-bearing):** the user (or whoever is reviewing) reads 5-10 generated outputs across a stratified sample of categories and answers: *does the output read like CAS-grounded text the user might want to see in a chat?* This is the gate the B-4 audit (2026-05-07) failed; same gate applied here, before any more work. Per the user's memory `feedback_grade_samples_dont_hand_procedure.md`, this is grading, not procedure handing.

If the human review reads "this is incoherent" or "the output is gibberish" — STOP. Do not advance to Phase 3. The Stage 3 eval metrics measured identifier recovery (good — 0.78 dev, 0.64 held-out), they did NOT measure subjective text quality. We learn that here.

### Phase 3 — Multi-turn REPL with session state

Estimated dev: 4-6 hours local.

**Files modified:**
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/chat.py`. Add a new code path, gated by a new flag `--stage3 PATH` on the CLI and a runtime toggle `/stage3` command:
  - When `--stage3 PATH` is supplied at startup, `_load_with_spinner` is replaced by a Phase-1 `load_stage3_model(...)` call. The K=9 predictor is NOT loaded in this mode.
  - The REPL loop's "predict" branch (chat.py line 1309) is dispatched: if `stage3_loaded`, route through Phase-2 `decode_one`; else fall through to the existing K=9 + native-gen path.
  - Session state for the Stage 3 path: list of `(prompt, cas_prefix, generated_text, trace_dict)` tuples in memory. No persistence to disk in Phase 3.

**Files added:**
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_session.py` (new). `Stage3Session` class: holds the rolling turn history. Public methods `record_turn(prompt, prefix, generated, trace)`, `last_trace()`, `clear()`.

**Test gate (Phase 3 done):** automated smoke calls `Stage3Session` with three turns, asserts `last_trace()` returns the third turn's dict, `clear()` empties.

**Human review gate:** 5 conversations of 3-5 turns each. Does the model behave usefully across turns? Note that the Stage 3 checkpoint was NOT trained on multi-turn data — multi-turn behavior is emergent / accidental. If the multi-turn behavior is bad, do not panic; the gate is "does the *single-turn* generated text in turns 2-5 look approximately as good as in turn 1." If multi-turn meaningfully degrades single-turn quality, document and revisit.

**Risk callout:** multi-turn coherence may be poor. The Stage 3 corpus is single-turn rpm-copy records. This is an honest expected failure; don't oversell.

### Phase 4 — Trace dict construction + Mode 7 connection point

Estimated dev: 5-8 hours local.

**Files added:**
- `noetic-compass-scaffold/noetic-compass/cas-native/trace/stage3_trace.py` (new). Dataclass `Stage3Trace` with fields per §6. Helper function `assemble_stage3_trace(model, record, decode_result) -> Stage3Trace` that takes the `greedy_decode` output dict and assembles the full trace dict shape (Phase 2's stub gets replaced by the real call).
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_decoder.py`: updated to call `assemble_stage3_trace`.

**Files modified:**
- `chat.py`: the `/trace` command's display path (line 1297) needs to handle both `LiveTrace` (K=9) and `Stage3Trace` (new) types. Add a small dispatch on `isinstance`.

**Test gate (Phase 4 done):** `tests/trace/test_stage3_trace.py`. Asserts the trace dict has all fields in §6, fields have expected types, `to_dict()` is JSON-serializable.

**Mode 7 contract gate:** the `Stage3Trace.to_dict()` shape must satisfy what `docs/working/mode_7_traceability_design_2026_05_13.md` (sister doc) specifies for input. Phase 4 cannot land until that doc declares "this shape is sufficient." Coupling is explicit.

### Phase 5 — UI / formatting / OOD gate / refusal handling

Estimated dev: 6-10 hours local.

**Files modified:**
- `chat.py`: replace the canned "[gate: ...]" output in OOD-routed cases with a Stage-3-aware route. Today the gate consumes K=9 head confidences; for Stage 3, the gate needs different signal — likely identifier presence in input + a simple lexical regex on the prompt. The simplest viable rule: if the prompt does not contain a recognizable CAS substring (any of `\^\d`, `F\d`, `\|[TAfE]`, `→`, `Θ(`), route to a canned "I am the Stage 3 model; I generate CAS-grounded text only" reply, not the model. This is a stub, not the eventual product.
- `chat.py`: post-decode display formatting. Today the table renders `CAS PREDICTION` + `ENGLISH`. For Stage 3, rename the row labels to `CAS PREFIX` (the input source) + `GENERATED TEXT` (the model output). Add a `TRACE SUMMARY` row showing 2-3 high-signal fields (identifier-recovery sanity, free-decode path length).
- `chat.py`: optional `--repair` flag that routes Phase-1-output through `inference/identifier_repair.repair(...)` and `inference/postprocessor.postprocess(...)`. Off by default until Phase 5 human review confirms repair helps.

**Files added:** none expected, unless Mode 7 surface requires its own rendering helper.

**Test gate (Phase 5 done):** `tests/inference/test_stage3_repl_e2e.py`. End-to-end: loads a tiny model, feeds three sample prompts, asserts the full output (text + trace summary) is well-formed.

**Human review gate (final acceptance):** the user runs 15-20 ad-hoc conversations and answers: *would I show this to a stakeholder?* If no — log specific failure modes, don't land. If yes — Phase 5 closes the loop.

## 5. Inference path detail (file:line pointers, canonical user-facing flow)

For one user turn in the new `--stage3` mode:

1. `chat.py:1227` — `_read_prompt(console)` reads the line.
2. `chat.py:1309` — branch into the new Stage-3 path (Phase 3 dispatch).
3. New: `stage3_decoder.decode_one(prompt_record, model, collator, tokenizer, device, max_new_tokens=192)`.
4. Inside `decode_one`:
   - `SimplexCollator.__call__([record], device=device)` — same call site as `evaluate_candidate_e_stage2.py:268`.
   - `sample_decoder.greedy_decode(model, record, collator, tokenizer, device=device, max_new_tokens=192, trace=True)` — `sample_decoder.py:42`. Greedy free-decode, NOT scheduled sampling.
5. Build the `Stage3Trace` (Phase 4) from `greedy_decode`'s return dict (`text`, `token_ids`, `slot_type_trace`, `per_token_trace`).
6. Return `(generated_text, trace_dict)` to the REPL loop.
7. `chat.py:_render_turn` (existing) prints the user-facing table. Phase 5 updates row labels and adds a trace summary row.
8. Phase 4's `Stage3Session.record_turn(...)` stores the turn for `/trace` retrieval.

Decoding mode: **greedy free-decode, not scheduled sampling.** This is worth stating explicitly because (a) the training script is the only place scheduled sampling appears, and (b) the natural confusion is "Stage 3 was trained with scheduled sampling, do we keep it on at inference." No — scheduled sampling was teacher's-pet help during training; at inference the model decodes from its own outputs.

## 6. Trace contract — the `Stage3Trace` dict shape

This is the contract handed to the Mode 7 design doc. Sister doc may request edits; treat this as v0.1.

```python
@dataclass
class Stage3Trace:
    # === Inputs / identity ===
    input_text: str                              # user prompt as typed
    cas_prefix_text: str                         # source the model conditioned on
    record_id: str | None                        # eval-pack record id, when applicable
    schema_version: str                          # "stage3-trace-v0.1"
    created_at: str                              # ISO timestamp
    parent_ids: list[str]                        # session turn ancestry (multi-turn)

    # === Generated output ===
    generated_text: str                          # the model's reply
    generated_token_ids: list[int]               # tokenizer ids of generated tokens
    n_tokens_generated: int
    hit_eos: bool
    free_decode_path: list[dict]                 # per-token: {pos, chosen_id, chosen_str}

    # === Pre-state (encoder-side) ===
    pre_state: dict                              # encoder source_hidden summary
                                                 # {"l2_norm": float, "mean_abs": float,
                                                 #  "shape": [B, L_src, d_model]}

    # === User intent (deferred, Phase 5+) ===
    user_intent: dict | None                     # null for v0.1 — no intent classifier yet

    # === CAS transition steps (per-token slot routing) ===
    cas_transition_steps: list[dict]             # per-token:
                                                 #   {pos, slot_type_argmax, slot_type_top_prob,
                                                 #    slot_type_entropy, is_copy_eligible}

    # === Compiler validation (deferred, Phase 5+) ===
    compiler_validation: dict | None             # null v0.1 — would round-trip the generated
                                                 # text through cas-compiler. Hook here so Mode 7
                                                 # can render it once wired.

    # === Admissibility ===
    admissibility_result: dict                   # for Stage 3 v0.1: presence/absence of expected
                                                 # canonical identifiers from the prefix
                                                 # {"target_identifiers": [...], "recovered": [...],
                                                 #  "recovery_rate": float}

    # === Raw model summaries ===
    raw_lm_logits_summary: dict                  # {"mean_entropy_nats": float, "n_positions": int}
    copy_distribution_summary: dict              # {"mean_copy_entropy": float,
                                                 #  "n_high_confidence": int, "threshold": 0.5}
    slot_type_decisions: list[int]               # full slot_type_trace
    decode_timing_ms: dict                       # {"forward_ms": float, "decode_ms": float}

    # === Diagnostics ===
    diagnostics: dict                            # free-form: warnings, OOD-route info,
                                                 # repair-pass annotations
```

Notes on the shape:
- `pre_state` and `cas_transition_steps` mirror the names the user used in their `feedback_object_traceability_required.md` memory. Mode 7 surfaces should map directly.
- `compiler_validation` and `user_intent` are null in v0.1 with hooks present so wiring them later is additive, not invasive.
- Every field is JSON-serializable. `to_dict()` is the Mode 7 boundary.
- Per `feedback_object_traceability_required.md`: every Stage3Trace gets `record_id` (if from eval pack) + `created_at` + `schema_version` + `parent_ids`. The `parent_ids` field is the multi-turn ancestry.

## 7. Test plan

### Unit tests (per phase)

- Phase 1: `tests/inference/test_load_stage3_model.py` — tiny config, model factory smoke.
- Phase 2: `tests/inference/test_stage3_decode_one.py` — one record, mocked model, asserts return dict shape.
- Phase 3: `tests/inference/test_stage3_session.py` — `Stage3Session` state machine.
- Phase 4: `tests/trace/test_stage3_trace.py` — trace dict shape + JSON serializability.
- Phase 5: `tests/inference/test_stage3_repl_e2e.py` — full chat round trip on tiny model.

### CPU-only smoke (Phase 2 gate)

Mirror `evaluate_candidate_e_stage2.py --stage e3-baseline` invocation, but on CPU and with a single record:

```
python noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_cli_smoke.py \
  --checkpoint <local-checkpoint-path> \
  --tokenizer noetic-compass-scaffold/.../tokenizer.json \
  --english-bpe noetic-compass-scaffold/.../english_bpe.json \
  --record-id <one-from-rpm_copy_grounding_v2_dev.jsonl> \
  --device cpu \
  --max-new-tokens 192
```

Expected: generated text within ~30s on a developer CPU. NOT a quality check; a no-crash check.

### Human review checkpoint (after Phase 2)

Per the user's memory `feedback_samples_are_the_only_true_eval_for_cas_native.md`: read 5-10 samples directly. Specifically grade:

- Does the output contain the expected canonical identifier(s)?
- Does the output read like coherent English (not loop-text, not function-word salad)?
- Is there any obvious leakage (cross-emission of unrelated identifiers)?

If any of those three reads "no" on more than 1 of 10 samples, stop and report. Per `feedback_separate_evidence_levels_in_status.md`, do not advance to Phase 3 just because Phase 2 didn't crash.

## 8. Open questions

These are the items the audit cannot answer from the code alone. The user will resolve them before Phase 1 starts.

**Q1 — How does a free-form English prompt map to a `cas_prefix`?** The Stage 3 model expects a `cas_prefix_ids` input (encoder source). The eval pack records have this baked in. For an ad-hoc English user prompt typed at the REPL, three viable answers: (a) **eval-pack-only mode** — REPL only accepts a record id, not free-form text; honest, narrow; recommended for Phase 1-3. (b) **empty-prefix mode** — pass the all-PAD fail-closed source; reply will be ungrounded; risk of garbage; useful for "this is what the model does without source" demos. (c) **NL-to-CAS step** — wire a separate prompt-to-CAS prefix model; this does NOT exist yet for Stage 3 and is a separate project. Phase 1-3 default to (a); (b) is a small additional feature; (c) is deferred.

**Q2 — Does the Stage 3 checkpoint live at a local path on the user's box, or only on the pod?** The known artifact is `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt` (pod). Phase 1 needs a local copy or a documented download step before the smoke can run. The integration plan does NOT propose pod work — but downloading the checkpoint to local is not pod work. Surface this with the user; they may have already pulled it.

**Q3 — Is multi-turn behavior in-scope for the demo bar?** The Stage 3 corpus is single-turn. Multi-turn behavior is emergent. If multi-turn is required for the demo, Phase 3 risk increases. The plan assumes Phase 3 is best-effort and Phase 2 single-turn passing the human review is the actual demo bar. Confirm with the user.

**Q4 — What does "Mode 7 surface" actually render at v0.1?** Sister doc `docs/working/mode_7_traceability_design_2026_05_13.md` is being written in parallel. The trace dict shape in §6 is this plan's proposal; the sister doc may demand additions (e.g., per-layer activations, attention weight summaries). The two docs need to converge before Phase 4 lands. Flagged as a coupling, not a blocker.
