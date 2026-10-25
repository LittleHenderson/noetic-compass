# Confirmed Decisions

**Append-only.** A decision lands here ONLY when:
1. Codex sign-off in `codex_audit.md`
2. User confirms in chat
3. The decision is written here with `AUTHORIZED: yes` (or `AUTHORIZED: no` if explicitly rejected)

Format:

```
## YYYY-MM-DDThh:mmZ — <topic>

DECISION: <one-line decision>
AUTHORIZED: yes
RATIFIED-BY: user + codex
CONTEXT: <link/pointer to the relevant inbox/audit entries>

<optional further detail>

---
```

---

## 2026-05-13T18:25Z — Step 5B Minimal NL Front Door (Option C — heuristic + Stage 4 spec)

DECISION: Build Step 5B Option C — heuristic-pattern NL→CAS bridge now, Stage 4 training spec captured for the next pod run. Per Codex audits `8e0ae2d` (Traceability v0 first, Step 5B next) + `8997125` (Traceability v0 PASS, Step 5B awaiting explicit user go) + user chat "go" (2026-05-13T18:25Z).

Scope this entry:

Part 1 — Heuristic NL→CAS bridge (CODE):
1. New module `noetic-compass-scaffold/noetic-compass/cas-native/inference/nl_to_cas_v0.py`:
   - Public surface: `match_nl_to_cas(text) -> NLMatchResult | None`. Pure functions, rule-based, no model call.
   - Curated pattern table mapping constrained English to CAS expressions. Initial coverage per Codex's example set:
     - "explain a thought becoming action" → `^9^O` (Below/Effect, Operational)
     - "turn anger into CAS" → `^3^E|f` (Negative, Evaluative, Affective)
     - "what does this symbol mean" → triggers self-explainer symbol-legend topic
     - "give me a CAS chain for awareness leading to action" → `^1^C -> ^9^O`
     - "show me a simple CAS example" → canonical 2-stage RPM chain
     - "explain a decision in CAS" → `^8^P -> ^9^O` (cause/effect)
     - "explain a feeling in CAS" → `^4^E|f` (vibration in evaluative, affective)
     - Plus 8-10 more patterns from Codex's directive.
   - `NLMatchResult` dataclass: `{matched_pattern, cas_expression, explanation, confidence}`.
   - Discipline (mirrors plain_english "does not lie"): never invent a CAS expression. If no pattern matches, return None. The REPL then falls through to the existing bridge-text refusal.
2. REPL integration in `stage3_chat_repl.py`:
   - `classify_input` gains a fourth class: `nl_bridge_match` (when `nl_to_cas_v0.match_nl_to_cas` returns a non-None result).
   - `handle_turn` for that class: print "I read that as: `<CAS expression>`" + a one-line rationale + route the inferred CAS through the existing cas-explain pipeline so trace + Plain Mode + Thought Tree all attach normally.
   - When the user asks "explain anger" and the bridge maps to `^3^E|f`, they see BOTH the inferred CAS expression AND the model's Plain English explanation of that expression. Traceability is preserved end-to-end.
3. Tests in `tests/inference/test_nl_to_cas_v0.py` (~12-15) + REPL integration tests (~4-5).

Part 2 — Stage 4 training spec (DOC ONLY):
4. New doc `docs/working/stage4_minimal_nl_training_spec_2026_05_13.md`:
   - Target: 5K–25K curated examples on constrained prompt set per Codex's data-strategy memo (`feedback_cas_native_data_strategy_2026_05_13.md`).
   - Corpus sources hierarchy: own CAS data → compiler-synthetic → HF/Kaggle for style only. NO foreign-model distillation.
   - Curriculum tasks: english_to_cas (with the v0 heuristic as gold supervision), simple_chain_construction, symbol_query, depth_request_routing.
   - Training compute estimate (~$5-25K, ~1-2 weeks).
   - Gate criteria for Stage 4 promotion.
   - This doc is the spec the next pod training run consumes. NOT a training launch.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` (commit `8997125`, Traceability v0 PASS) + Codex chat ("Step 5B Option C is still the right NL path") + user chat "go" (2026-05-13T18:25Z).

BOUNDED SCOPE:
- Code: heuristic module + REPL integration + tests (~3 hrs work)
- Docs: Stage 4 training spec
- NO model retraining
- NO pod work
- NO Mode 7 visualization implementation
- NO Living Thought Atlas UI implementation
- NO Step 6 (Mode 7 full) or Step 7 (Atlas) code work

EXPLICITLY DEFERRED (Stage 4 training is its own AUTHORIZED entry, gated on Stage 4 spec doc audit + corpus engineering completion).

LIVING THOUGHT ATLAS FRAMING: the heuristic bridge IS the v0 NL surface. The trained NL bridge (Stage 4) supersedes it but the heuristic stays as a deterministic fast-path even after training, per Codex's "ship A now, B planned" guidance. Both feed the same Traceability v0 trace pipeline — every NL input becomes a CAS expression which becomes a full trace with Thought Tree.

---

## 2026-05-13T17:30Z — Traceability v0 (before Step 5B per Codex re-ordering)

DECISION: Build Traceability v0 BEFORE Step 5B (NL bridge). Per Codex audit `8e0ae2d` 2026-05-13: "traceability is the thing that makes CAS different... once trace v0 exists, every CAS answer and every future NL answer can show what CAS read / what the model generated / source references carried over / missed / slot pattern / confidence-warnings / Thought Tree JSON." Step 5B Option C remains the right NL path; it just comes after the trace backbone.

Scope this entry — Traceability v0:

1. New module `noetic-compass-scaffold/noetic-compass/cas-native/inference/traceability_v0.py`:
   - `build_v0_trace(report) -> dict[str, Any]` — pure function. Takes the cas-explain report (already has plain_english + identifiers + slot_summary) and produces the UI-ready trace dict.
   - 7 top-level sections per Codex's named field list: `schema_version` + `trace_id` + `created_at` (object-traceability per `feedback_object_traceability_required.md`), `input` (cas_expression + source_tokens), `output` (english + n_tokens), `copy` (copied / missed / coverage + per_identifier entries), `slot_trace` (length + counts_by_human_label + longest_stage_var_run + raw_trace), `confidence` (qualitative bands + caveats + structured warning_flags), `thought_tree` (root + node_count + edge_count, UI-consumable JSON).
   - Pure functions only. No model call. No new tensors. Consumes existing cas-explain output.
2. New module `inference/thought_tree.py`: tiny helper that builds the Thought Tree node-edge structure from copy + slot data. Public surface: `build_thought_tree(report) -> dict`. Separated so the eventual UI consumer can import it directly without the rest of traceability_v0.
3. REPL extension: add `/tree` slash command that dumps the Thought Tree JSON for the last turn.
4. cas-explain output dict gains `traceability_v0` sub-dict so saved `.tmp/cas_explain_*.json` files contain the full trace for UI consumption.
5. Tests in `tests/inference/test_traceability_v0.py` + `tests/inference/test_thought_tree.py`:
   - Each schema field populated from synthetic reports
   - Warning flags fire on correct structural conditions (low_coverage / no_identifiers_emitted / slow_decode)
   - Thought Tree node + edge counts are correct for known inputs
   - JSON round-trip cleanly (json.dumps → json.loads → same shape)
   - REPL `/tree` returns valid JSON

NOT in scope this entry (full Mode 7 territory):
- Per-position lm_logits / p_copy tensor dumps
- Activation hooks
- Simplex trajectory visualization
- Per-layer L2 dumps
- Inversion Replay alternates (ghost branches)
- Visual rendering (Living Thought Atlas UI)

NOT in scope this entry (Step 5B Option C — next):
- NL → CAS heuristic bridge (`nl_to_cas_v0.py`)
- Stage 4 corpus design

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13 (commit `8e0ae2d`, "Traceability v0 first. Then Step 5B NL bridge.") + user chat (2026-05-13T17:30Z, ratifies Codex's order).

BOUNDED SCOPE: pure-function additive code. The trace is built from already-computed fields in the cas-explain output. No new model plumbing. No Mode 7 wiring beyond what v0 enables.

LIVING THOUGHT ATLAS FRAMING: per memory `project_living_thought_atlas_flagship_2026_05_13.md`, the Atlas is the flagship presentation layer. Traceability v0 is the schema contract that flows trace data INTO the Atlas. Atlas implementation remains downstream.

---

## 2026-05-13T16:30Z — Step 5: CAS conversation shell (REPL) + Step 5B name reserved (Minimal NL Front Door)

DECISION: Build the first real CAS conversation shell as Step 5 of Codex's post-Stage-3 ordering. Plain English Mode is the default reply layer; technical layers behind slash commands; CAS self-explanation is folded into the REPL (not a separate `cas explain-cas` subcommand) per Codex's earlier audit. Free-form NL chat politely declines for now — that's Step 5B (Minimal NL Front Door), authorized by Codex's 2026-05-13 chat directive but NOT in this entry's scope.

Step 5 scope (this entry):

1. New module `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_chat_repl.py`:
   - Loads via `load_stage3_local()` from Step 2
   - Multi-turn loop with session state (history of explain reports + self-explainer level)
   - Input classifier: CAS expression / question about CAS itself / free-form NL
   - For CAS expressions: route through the existing `cas explain` pipeline; Plain Mode default
   - For CAS-self questions: route through new `cas_self_explainer` module (rule-based depth content: simple / stakeholder / user / builder / technical)
   - For free-form NL: polite refusal pointing user to one of the two supported paths (NL bridge is Step 5B work)
2. Slash commands: `/plain` `/technical` `/details` (alias for technical) `/all` `/trace` `/raw` `/deeper` `/simpler` `/help` `/clear` `/quit`
3. New module `cas_self_explainer.py`: rule-based content store. Public surface: `explain_cas(level, topic)` returns a `{text, example, metaphor, deeper, simpler}` dict. Topics: `what`, `why`, `problem`, `who-cares`, `demo-claim`, `symbol-legend`, `metaphor`, `example`. Five depth levels with example/metaphor populated at the low end.
4. CLI integration: new subcommand `cas chat-stage3` in `cas_cli.py`. Existing `cas chat` (B-4-era REPL) UNTOUCHED.
5. Tests in `tests/inference/test_stage3_chat_repl.py` + `tests/inference/test_cas_self_explainer.py`:
   - Input classifier on positive + negative examples
   - Each slash command dispatch
   - Plain mode is the default reply layer (regression pin)
   - Self-explainer depth graph is valid (simple → stakeholder → user → builder → technical, with deeper/simpler pointers wired)
   - Self-explainer "does not lie" gates: simple level always has metaphor; stakeholder level uses zero internal labels (STAGE_VAR, slot trace, Δ°₃₉ etc.); technical level uses canonical vocabulary verbatim
   - Heavy end-to-end test against real archive (skipped if absent)

Naming note (Codex 2026-05-13 chat): for demos, eventually rename to `cas chat` or `cas native`. For now, `cas chat-stage3` keeps old `cas chat` untouched. Surface this as a future rename ticket; do NOT touch the old REPL.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 1c54b5f (Plain English Mode PASS + Step 5 "ready after that wording patch") + Codex chat 2026-05-13 ("this is the right next build... go") + user chat (2026-05-13T16:30Z, this turn). Wording patch landed in commit `08238f3`.

BOUNDED SCOPE THIS ENTRY: code work in three new files (REPL + self-explainer + CLI subcommand wire-up). No touching of existing `chat.py` or `cas_cli.py:_cmd_chat`. No Mode 7 wired. No Living Thought Atlas. No pod work. No free-form NL bridging (Step 5B).

EXPLICITLY DEFERRED (Step 5B authorized in principle, NOT in this entry):
- Minimal NL Front Door: "Explain a thought becoming action." → small CAS expression. Constrained prompts only, not chat-GPT level. Per user 2026-05-13 chat directive. Will get its own AUTHORIZED entry after Step 5 lands and Codex audits.

CONTEXT: Codex's 6-step Plain English plan (point 4): "Make chat REPL use plain mode by default." All prior steps (1 max_cas_prefix_len reporting patch, 2 plain_english.py module, 3 cas explain flags) are committed and pushed. The wording patch (4th item Codex required pre-Step-5) landed in `08238f3`. Step 5 is the live conversation shell that the eventual visual UI sits on top of.

---

## 2026-05-13T16:00Z — The CAS Report (1T-parameter speculation round-table)

DECISION: Five-agent parallel round-table brainstorming a "1 TRILLION PARAMETER CAS Native" speculation document. Deliverable: `docs/working/cas_report_1T_parameter_speculation_2026_05_13.md`. Same five specialist vantage points the R&D pre-synthesis used (architecture / emergence / safety-and-traceability / compute-and-infra / stakeholder-strategic). Each agent produces a focused brief; Claude synthesizes into "The CAS Report."

AUTHORIZED: yes

RATIFIED-BY: user chat "put together a team of agent to form a round table brainstorming only concerning what could be 1TRILLION PARAMETER CAS Native Model likely look like and more importantly what would be it's emergent capabilities be this is the CAS REPORT" / "use your smartest agents" (2026-05-13T16:00Z). Speculative/pitch-supporting research, no code, no pod work.

BOUNDED SCOPE:
- Documentation only — single final doc + 5 specialist briefs as intermediate.
- No code changes. No pod work. No agent_exchange edits by agents (Claude owns those).
- Speculation must be honest: nobody has scaled CAS-Native architecture yet. Report flags what is known (Stage 3 at 150M) vs predicted (scaling curve) vs unknowable (frontier emergence).
- Output is meant to inform the Amazon-pitch path per memory `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md`. Same disciplined-claim posture: "this is what a 1T CAS-Native MIGHT look like and what it MIGHT do," not "we will build this."

NEXT GATED ACTION: agents fire in parallel; Claude synthesizes when all return.

CONTEXT: Codex's earlier trajectory table (Now → 100M → 300M → 1B → 7B → 10-30B → 70-100B → ?) tops out at 70-100B "with major compute help." 1T is the frontier-scale extrapolation. The user wants the visionary endpoint documented so the pitch can show "here's where this leads if it works." This is the CAS-Native equivalent of OpenAI's GPT-3 paper laying out what scaled transformers would look like — speculation grounded in the architecture, not in the model that's been built.

---

## 2026-05-13T15:30Z — Plain English Mode (Step 4.5): translator + `cas explain` defaults

DECISION: Plain English Mode becomes a first-class output mode baked into `cas explain` BEFORE Step 5 (chat REPL) starts, so the REPL inherits plain-by-default. Per Codex's 6-step plan:

Step 1 — `max_cas_prefix_len` reporting patch: DONE in commit `0762d20` (2026-05-13T15:15Z).

Step 2 — new module `noetic-compass-scaffold/noetic-compass/cas-native/inference/plain_english.py`. Pure functions, no model dependencies. Maps internal signals to human language:
- copied identifier → "the model carried this idea over"
- missing identifier → "the model missed this source idea"
- slot trace → "the model recognized this as a structured CAS name"
- low confidence → "the model is unsure here"
- cross emission → "the model may have mixed sources"
- numeric coverage → qualitative band ("strong" / "partial" / "weak")
- slot run length + counts → human pattern summary

Step 3 — extend `cas explain` CLI with output-mode flags:
- DEFAULT (no flag): `--plain` behavior. Three layers visible (Plain answer + What it means + collapsed "details available with --technical").
- `--plain` (explicit): same as default.
- `--technical`: full current technical output (slot trace, identifier breakdown with internal labels, etc.).
- `--json`: raw dict, unchanged.
- `--all`: all three layers, no collapse.

Output dict additions (forward-compatible — adds, doesn't break):
```json
"plain_english": {
  "short_answer": "...",       // one sentence
  "plain_meaning": "...",      // 1-3 sentences interpreting result
  "qualitative_coverage": "strong|partial|weak|none",
  "qualitative_slot_quality": "...",
  "confidence_caveat": null | "..."  // populated when confidence is uncertain
}
```

Translator is RULE-BASED in v0 — explicit mappings, no model call. Deterministic, audit-able, cheap. Future iteration could use the model itself for phrasing, but v0 keeps it as a deterministic shim so stakeholder-facing text never degrades from a generation glitch.

Test discipline (Codex's "plain mode does not lie" gate): every claim plain mode makes MUST be derivable from a verifiable field in the technical output. If an ID is missing, plain mode says so. If copy is clean, plain mode can say so. If confidence is unknown, plain mode does NOT claim certainty.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13 ("Plain English Mode should be the front door. Technical CAS should be the glass floor underneath it.") + user chat directive (2026-05-13T15:30Z) "we've to build a plain english mode into cas so users don't get lost in jargon" / approval of Codex's 6-step path.

BOUNDED SCOPE THIS ENTRY:
- `cas explain` CLI updates (Steps 2-3 of Codex's order)
- new `plain_english.py` module + tests
- regression pins on schema-level claims (plain mode does not lie)

NOT in this entry's scope (Step 4-6 of Codex's order — separate decisions):
- chat REPL adoption (Step 4 of Codex's order = our Step 5)
- Mode 7 / Living Thought Atlas consumption of plain layer
- model-generated plain phrasing (rule-based now)

User memory: aligns with `feedback_plain_language_no_jargon.md` ("talk like a person, not a paper"). This formalizes that feedback rule as a product mode.

---

## 2026-05-13T09:35Z — Step 4 of post-Stage-3 plan: `cas explain` subcommand + 2 parallel prep agents

DECISION: Codex audit on Step 3 PASSED (`4e7961c`) and answered "Step 4 should stay narrow: CAS expression in → English out, with recovered IDs / missing IDs / slot summary shown. No free chat yet." User chat "go" 2026-05-13T09:35Z authorizes Step 4 PLUS two adjacent parallel prep agents that surface info needed for Steps 5-7 without preempting them.

Three parallel agents launched in background:

1. **Agent A — Step 4 implementer (CODE WORK):** add `cas explain EXPR` subcommand to `noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_cli.py`. Reuses Step 2's `load_stage3_local()` + Step 3's decode path. Outputs: generated English, copied identifiers, missing identifiers, slot summary; `--json` flag for raw dict. Tests + hand-run + commit + push.

2. **Agent B — trace schema designer (DOCS ONLY):** write `docs/working/cas_trace_schema_v0_2026_05_13.md` proposing the canonical trace dict shape that flows inference → chat REPL → Mode 7 → Atlas. Locks the contract before Step 6 so all downstream consumers see the same shape. Reads Mode 7 design + chat REPL plan + existing trace plumbing.

3. **Agent C — dashboard casing auditor (RECONNAISSANCE ONLY):** Codex `f3f59fa` flagged `dashboard/src/components/IdeaAtlas/` AND `dashboard/src/components/idea-atlas/` both exist. Agent audits what's in each dir, what references each, writes `docs/working/dashboard_casing_audit_2026_05_13.md` with the recommended cleanup plan. NO file moves, NO refactor — proposal only.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T?Z (commit `4e7961c`, Step 3 PASS, "next is Step 4: CAS-input CLI" + answer that Step 4 should be narrow CAS→English) + user chat "authorize Step 4" / "put together your smartest ai agents working parallel in the background" (2026-05-13T09:35Z).

BOUNDED SCOPE PER AGENT:
- Agent A: code work strictly within `cas_cli.py` + `tests/inference/test_cas_cli_explain.py`. No changes to existing subcommands (notation, predict, chat, demo). No touching of `chat.py`. No CLI redesign. Subcommand registration only.
- Agent B: docs only. NO code changes. NO edits to `agent_exchange/`. Proposes schema; does not implement it.
- Agent C: read-only audit of dashboard/. NO file moves. NO renames. NO TS code changes. Recommendation doc only.

NO chat REPL touched. NO Mode 7 wired. NO Living Thought Atlas implementation. NO pod work.

CONTEXT: Step 3 smoke (`a653ae6`) confirmed the model loads + generates locally at 1.4s load + 6.1s decode for record 0 with 2/3 canonical recovery. Step 4 wraps that path in a CLI subcommand so users can hand a CAS expression to `cas explain` and get English back. After Step 4 lands and Codex audits, Step 5 (chat REPL wiring) is next.

LIVING THOUGHT ATLAS FRAMING: per memory `project_living_thought_atlas_flagship_2026_05_13.md` and Codex `f3f59fa`, the Atlas is the flagship presentation layer, not decoration. Engineering ordering protects the vision. Agent A advances Step 4 (the "engine"); Agents B + C advance prep work for Steps 6-7 (the "legibility layer") without preempting them.

---

## 2026-05-13T09:10Z — Step 3 of post-Stage-3 plan: one-record local smoke

DECISION: Build a deterministic single-record smoke harness that feeds the Stage 3 model (loaded from local archive via Step 2's `load_stage3_local()`) one known CAS record from the dev pack and confirms it produces Stage-3-shaped output on this machine.

Scope:
1. New file: `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_local_smoke.py`. Function `run_stage3_local_smoke(record_idx=0, dev_path=...)` returns a smoke report dict; CLI entrypoint prints it nicely.
2. Uses Step 2's loader for the model + tokenizer, the existing `SimplexCollator` for batching, the existing `decode_canary_pack` for free-decode, and the existing `per_record_recovery` for scoring. No new inference primitives.
3. Reads record at `--record-idx` (default 0) from `cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl`.
4. Saves a small JSON report at `.tmp/stage3_local_smoke_<ts>.json` (NOT committed; local-only).

Gates for "Step 3 success":
- Script runs without crash on CPU.
- Generated text is non-empty (length ≥ 1 token).
- ≥ 1 of the 4 canonical identifiers recovered on record 0 (loose check — a single record isn't a full eval).
- No NaN/Inf in any output tensor.
- Tokenizer round-trips cleanly (no UNK explosion).

Tests in `noetic-compass-scaffold/noetic-compass/cas-native/tests/inference/test_stage3_local_smoke.py`:
- Module imports cleanly (cheap).
- When archive present: end-to-end run with the smoke gates as assertions.
- Skipped when archive absent.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` (commit `5d153fc`, Step 2 PASS, "next move is Step 3: one-record local smoke test") + user chat "go" (2026-05-13T09:10Z).

BOUNDED SCOPE: local CPU only. One record, not a batch eval. No CLI surface (Step 4). No chat REPL touch (Step 5). No Mode 7 wiring (Step 6). No pod work.

CONTEXT: Step 2 (`14d7a6e`) shipped `load_stage3_local()` with hash gates. Step 3 confirms the loaded model can actually do inference on this machine — closes the loop from "can load" to "can generate." After this step, Codex audits the smoke result; if shape-correct, Step 4 (CAS-input CLI) is next.

---

## 2026-05-13T08:30Z — Step 2 of post-Stage-3 plan: local Stage 3 loader

DECISION: Build a hash-verifying local Stage 3 loader as the second step in Codex's 6-step post-Stage-3 ordering. Scope is intentionally narrow:

1. New file: `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_local_loader.py`. Public surface: `load_stage3_local()` (returns `Stage3LocalBundle` with `model`, `tokenizer`, `english_bpe_path`, `manifest`, `hash_report`) and `verify_archive()` (returns hash-verification report without loading the model — cheap pre-flight).
2. Constants pin the four load-bearing sha256 values from `checkpoint_archive_registry.md`: Stage 3 `ckpt_final.pt`, the ckpt's `manifest.json`, `tokenizer.json`, `english_bpe.json`. Tokenizer hash is also cross-checked against the embedded `tokenizer_info.*_sha256` in the loaded manifest (three-way verification).
3. Loud failure modes: missing file (RuntimeError naming the file), hash mismatch (RuntimeError naming expected vs actual), manifest cross-check fail (RuntimeError naming both sources), state_dict shape mismatch (caught from `load_checkpoint` with `strict=True`).
4. Tests in `noetic-compass-scaffold/noetic-compass/cas-native/tests/inference/test_stage3_local_loader.py`: happy path (skipped when archive absent), three failure-path tests via tempdir-with-bad-bytes, and source-level pins on the hash constants (so a refactor can't silently swap in a stale hash).
5. CPU smoke: hand-run `load_stage3_local()` against the actual `D:\tksCAS-archive\` archive, confirm no crash, model in eval mode, manifest parsed.

AUTHORIZED: yes

RATIFIED-BY: codex audit commit `c4a339b` ("Step 1 done. Next is Step 2: build the local Stage 3 loader. A script that loads the good checkpoint from D:\tksCAS-archive, verifies hashes, builds the model, and fails loudly if anything is missing or mismatched") + user chat "go" (2026-05-13T08:30Z).

BOUNDED SCOPE: local code only. No new model architecture. No pod work. No inference run beyond the one-time happy-path hand smoke at the end. No CLI surface (that's Step 4). No chat REPL touch (that's Step 5). No Mode 7 wiring (that's Step 6). After this step lands and Codex re-audits, Step 3 (one-record local smoke against a known eval-pack record) is next.

CONTEXT: Step 1 was Codex's audit of the checkpoint archive registry (commit `c4a339b`) which surfaced two corrections (torch version + line-ending MD5 clarification). Registry is now green. Step 2 builds the bridge from "files on disk" to "loaded model in memory" with hash gates so we can't silently load a corrupted or wrong checkpoint.

---

## 2026-05-13T07:45Z — E2c-continuation warm-start backup + Stage 3 code-commit pin

DECISION: Modified-Tier-3 reproducibility backup per Codex audit `ec32e14`. Two actions:

1. Back up the E2c-continuation checkpoint + small companion artifacts. This is the warm-start source for Stage 3 — if we ever need to retrain Stage 3 exactly, this is what `--load-model-from` must point at. Files: `ckpt_final.pt` (664 MB) + `ckpt_final.pt.manifest.json` + `trainer_manifest.json` + `trainer_log.jsonl` + `smoke_report.json`. sha256 verified pod ↔ local on all 5. Local archive: `D:\tksCAS-archive\stage_e2c_cont_20260513T002539Z\`.
2. Pin the exact Stage 3 code commit `e9a0b76161b63e647a6c88633ffcf1f692e06032` in `checkpoint_archive_registry.md`. This is the last code change before the Stage 3 training launch (04:38Z); the trainer + scheduled_sampling MD5s we verified at deploy time correspond to this commit. After this pin, "which code matches the trained Stage 3 checkpoint" is unambiguous.

Skipped (per Codex): training-corpus archive copy (already in repo at `cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl` — repo is canonical, archive copy would be neatness-only); ckpt_step_500.pt + ckpt_step_1000.pt from E2c-cont (Tier 4 forensic-replay, not strictly load-bearing for retrain).

After this backup: Stage 3 is fully retrainable from local archive alone — warm-start ckpt + identical training corpus (in repo) + identical code commit + identical hparams (in ckpt_final.pt.manifest.json) all available locally.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` and chat 2026-05-13 (commit `ec32e14`, "modified Tier 3: back up E2c-cont ckpt + pin commit hash; training corpus already in repo, no Tier 4 needed unless forensic replay") + user chat "go" (2026-05-13T07:45Z).

BOUNDED SCOPE: pod-read only on the 5 E2c-cont files. No training. No inference. No code changes. Same shape as 07:05Z + 07:25Z backups, third batch.

CONTEXT: Stage 3 backup (07:05Z) + tokenizer backup (07:25Z) covered "run the good model" reproducibility. This third backup closes "retrain from the same warm-start point" reproducibility. The full warm-start chain (b2 → e2a → e2b → e2c-first-run) remains pod-only — those are Tier 4 forensic insurance, ~2 GB combined, not authorized by this entry.

---

## 2026-05-13T07:25Z — Tokenizer artifact backup (closes inference-readiness gap)

DECISION: Back up the two load-bearing tokenizer artifacts that the trained Stage 3 checkpoint requires for inference but were not explicitly named in the 07:05Z backup scope: `tokenizer.json` (446 KB) and `english_bpe.json` (1.4 MB). Without these, the binary checkpoint is unusable for any local inference. Per Codex audit `a1e8132` ("the checkpoint alone is not enough to run inference. We also need local copies of: tokenizer.json, english_bpe.json").

Steps: scp both files pod → local archive at `D:\tksCAS-archive\stage6_v6_artifacts\` (preserves pod relative path under the archive root). sha256 verify both sides against the values already recorded in `checkpoint_archive_registry.md`. Update the registry doc with the local archive paths.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T??:??Z (commit `a1e8132`, "checkpoint alone is not enough to run inference") + user chat "go" (2026-05-13T07:25Z).

BOUNDED SCOPE: pod-read only for the two named tokenizer files. No checkpoint re-pull. No inference. No code changes. Same scope shape as the 07:05Z backup, narrower contents.

CONTEXT: 07:05Z backup of `ckpt_final.pt` + 4 companion files passed Codex audit (`a1e8132`). Codex flagged the residual gap: the registry doc lists tokenizer/BPE hashes but doesn't archive the files themselves. Phase 1 loader (per `chat_repl_stage3_integration_plan_2026_05_13.md`) will verify these files exist at startup and fail clearly if not; this backup is what those checks will succeed against. After this, the trained model can be loaded end-to-end from local archive alone — no pod dependency for inference reproduction.

---

## 2026-05-13T07:05Z — Stage 3 ckpt_final.pt backup from pod to local archive

DECISION: Copy the Stage 3 trained checkpoint (the current "good model") from pod to local archive BEFORE any integration code work begins. Per Codex: "Without that checkpoint, all the integration work has nothing reliable to load." Six steps:

1. scp `/workspace/tksCAS/stage_e3_20260513T043823Z/{ckpt_final.pt, ckpt_final.pt.manifest.json, trainer_manifest.json, trainer_log.jsonl, smoke_report.json}` pod → local.
2. Local archive: `D:\tksCAS-archive\stage_e3_20260513T043823Z\` (matches existing `D:\tksCAS-archive\v0_rc1` / `v1e_phase_c` convention). NOT committed to git — 664 MB binary doesn't belong in repo history.
3. `sha256sum` on pod and local; assert equal.
4. Write `docs/working/candidate_e/checkpoint_archive_registry.md` — local archive path + sha256 + pod source path + lineage (warm-start from E2c continuation, 1000 steps, schedule linear:0.0-0.5:1-1000) + brief metadata. Committed to git.
5. Inbox surface to Codex with hash verification result.
6. After Codex confirmation, integration work can proceed (Phase 1 of `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md`).

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` and chat 2026-05-13T08:55Z ("Yes. First priority. Before building REPL, Mode 7, or anything else, preserve the good checkpoint locally") + user chat "Go!!" (2026-05-13T07:05Z).

BOUNDED SCOPE: pod-read only. No training. No inference. No file modifications on pod. No commits of the binary checkpoint to git (only the registry doc that references it).

CONTEXT: Stage 3 trained checkpoint was produced by the 1000-step pod run at `decisions.md` 2026-05-13T04:25Z (commit `df22112`). Pod free-decode evaluation passed at `f3adfe9` (0.7778) and held-out pack at `f3adfe9` (0.6439, both gates clear). The risk Codex flagged: pod could be wiped, rented away, quota-cleaned, or accidentally deleted, in which case retraining costs ~$0.50 + 62 min and would reproduce the same architecture but not necessarily bit-identical weights (RNG paths in scheduled sampling depend on torch RNG state across forwards). Backing up costs ~2 min of scp.

---

## 2026-05-13T06:30Z — Stage 3 wrap-up + post-Stage-3 planning phase (docs only, no pod work)

DECISION: Three parallel agents produce three docs, no code changes, no pod work:

1. **Stage 3 wrap-up** — `docs/working/candidate_e/stage3_wrapup_2026_05_13.md` — comprehensive summary of the Candidate E journey from baseline through E2a/E2b/E2c/E2c-cont/e3-baseline/Stage-3-training/held-out. Headline numbers per stage, variant-honesty note (one-step SS, not full rollout), limitations + open questions, artifacts pointer.
2. **Chat REPL Stage 3 integration plan** — `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md` — file-by-file plan for wiring the Stage 3 checkpoint into the existing chat REPL flow. Inference path with Mode 7 trace surface. Gates / testing approach.
3. **Mode 7 traceability design** — `docs/working/mode_7_traceability_design_2026_05_13.md` — design for the load-bearing Network Attribution / Mechanistic Trace exposure surface. Connects input → CAS state → activations → admissibility → output. The differentiator Wakil flagged in Exposure Button memo.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T07:55Z (commit `707249b`, "next move: write the Stage 3 wrap-up, then start chat/REPL + Mode 7 traceability planning") + user chat "Put together a team... get this done all running parallel in the background" (2026-05-13T06:30Z).

BOUNDED SCOPE: documentation work only. No code changes. No pod work. No new training runs. No decisions.md / inbox edits by agents (Claude controls those). Agents produce one markdown doc each and return.

NEXT GATED ACTION: after all three docs land, Codex audits the plans; user "go" on which integration step to execute first.

CONTEXT: Codex's audit verdict at `707249b`: "Stage 3 is done for this loop. I do not recommend more GPU training right now. No higher ratio, no longer run, no DAgger. That would be tuning after a pass." Held-out eval result at `f3adfe9`: 0.6439 free-decode recovery + 0 cross-emission. Per Codex's locked branch (audit `6451411`): both conditions cleared → unblocks chat/REPL + traceability integration planning.

---

## 2026-05-13T06:05Z — Stage 3 held-out confirmation eval on test + swap-eval packs

DECISION: Run `evaluate_candidate_e_stage2.py --stage e3` against `stage_e3_20260513T043823Z/ckpt_final.pt` (the Stage 3 trained checkpoint) on held-out packs:

- Free-decode: `cas-synthetic/data/path_d/rpm_copy_grounding_v2_test.jsonl` (200 records, never seen by dev runs)
- Swap: `cas-synthetic/data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl` (100 records / 50 pairs, never seen by dev runs)

Codex named the swap-eval path correctly; this confirmation eval is held-out on BOTH dimensions, not partial. Same gates as the dev run: PRIMARY free-decode `aggregate_recovery_rate >= 0.50`, HARD SAFETY swap `total_cross_emission_count == 0`. Strong-pass annotation at `>= 0.70`. ~8 min, ~$0.05.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T07:30Z + file-path correction (commit `a33d92e`, "use cas-synthetic/data/eval/..."), audit `codex_audit.md` 2026-05-13T07:10Z (commit `6451411`, "next clean move is held-out confirmation eval"), and user chat "ok" (2026-05-13T05:55Z, given before the file-gap was discovered; the gap was a path issue not a substance issue, so the original "ok" stands per Codex's correction).

BOUNDED SCOPE: this authorizes ONE held-out eval run. Anything beyond — broader test packs, chat REPL integration planning, schedule changes, more training — requires a separate decision.

BRANCH ON RESULT (Codex 7:10Z): pass (≥ 0.50, cross_emission == 0) → "generalizes enough to start chat/REPL + traceability integration planning"; miss → diagnose dev/test divergence before any other move.

CONTEXT: Stage 3 dev result (commit `df22112`) hit 0.7778 free-decode recovery (strong pass) and 0 cross-emission on dev pack. This held-out run tests whether that generalizes. Same checkpoint, same evaluator, different (genuinely unseen) data. MD5-verified files in place on pod prior to launch: test pack `628a08929e6ce4595f7f4e60de364630`, swap-eval pack `0791b9db0b98dc3be49a7dd31834cbc2`.

---

## 2026-05-13T04:25Z — Stage 3 scheduled-sampling POD training run

DECISION: Run a 1000-step Stage 3 training on RunPod, warm-started from `stage_e2c_cont_20260513T002539Z/ckpt_final.pt`. Configuration:

- `--ablation e3` (inherits e2c loss weights; no new losses per locked scope).
- `--scheduled-sampling-schedule "linear:0.0-0.5:1-1000"` — linear ramp from `ratio=0.0` at step 1 to `ratio=0.5` at step 1000. Plan §6 spec (end at 0.5) applied proportionally to a 1000-step run.
- Identical hparams to E2c continuation: `--lr 1e-4 --batch-size 16 --weight-decay 1e-4 --grad-clip 1.0 --max-cas-prefix-len 192 --seed 1729`.
- Save final checkpoint + step-500 checkpoint.
- Corpus: `rpm_copy_grounding_v2_train.jsonl`. No corpus change (locked scope).
- Estimated cost / time: ~$0.50, ~90-100 min on RTX A6000 (2 forwards/step vs E2c's 1 forward/step → ~1.5-2× E2c continuation runtime).

AUTHORIZED: yes

RATIFIED-BY: codex re-audit `codex_audit.md` 2026-05-13T06:08Z (commit `a686b48`, "launch-eligible"; 23/23 + 81/81 tests pass, three re-audit blockers all patched in `e9a0b76`) + user chat "GO!" (2026-05-13T04:25Z).

BOUNDED SCOPE: this authorizes ONE Stage 3 training run + the post-training `--stage e3` evaluator measurement. Whether to continue training, scale to more steps, or pivot to DAgger requires a separate decision after the e3-mode eval result is read.

NEXT GATED ACTION: after the run completes, evaluate the resulting `ckpt_final.pt` with `--stage e3` (PRIMARY: free-decode `aggregate_recovery_rate >= 0.50`; HARD SAFETY: swap `total_cross_emission_count == 0`). Surface result for Codex audit + user "go" before any further pod work.

CONTEXT: e3-baseline result (commit `ef468d2`) showed 0.4412 free-decode recovery — middle branch per plan §2. Implementation in `dd07bdb`. Re-audit blocker patches in `e9a0b76`. Codex launch-eligibility verdict in `a686b48`. Plan v2 at `docs/working/candidate_e/stage3_plan_2026_05_13.md`.

---

## 2026-05-13T03:45Z — Stage 3 scheduled-sampling LOCAL build (no pod work)

DECISION: Implement scheduled sampling locally in the simplex MVP trainer, gated on the 7-step build list in Codex's 03:42Z audit ratification. Strictly bounded scope: (1) two-pass `forward_with_scheduled_sampling` (no-grad rollout → with-grad supervised forward), (2) trainer flags (`--scheduled-sampling-ratio` + schedule), (3) `--ablation e3` alias in `ABLATION_OVERRIDES`, (4) equivalence test at ratio=0 (gradients match TF path bit-for-bit), (5) self-feed unit test at ratio=1, (6) CPU smoke with `--ablation e3`, (7) Codex re-audit before any pod work.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T03:42Z (commit `f2da6eb`, "scheduled-sampling branch") + user chat "go" (2026-05-13T03:45Z).

EXPLICITLY NOT AUTHORIZED: no pod training, no Stage 3 launch, no DAgger, no new loss design beyond scheduled-sampling mechanics, no corpus expansion. Pod work requires a separate `decisions.md` entry after Codex re-audits the CPU smoke result.

CONTEXT: e3-baseline result at 0.4412 free-decode identifier recovery (270/612), 0 cross-emission, archived at `docs/working/candidate_e/eval_results/e3_baseline_*_20260513T030500Z.{md,json}` (commit `ef468d2`). Falls in middle branch per Stage 3 plan v2 §2 (0.30 < x < 0.50 = scheduled-sampling Stage 3 training is next move). Plan §6b specifies the implementation gates being adopted verbatim here.

---

## 2026-05-13T03:30Z — Stage 3 baseline measurement (e3-baseline) on E2c continuation checkpoint

DECISION: Run `evaluate_candidate_e_stage2.py --stage e3-baseline` against `stage_e2c_cont_20260513T002539Z/ckpt_final.pt` on pod. This is a decision-point measurement, NOT Stage 3 training authorization. Free-decode + swap eval, ~$0.05 / ~15 min, `overall_pass=True` regardless (informational mode). Outputs: `aggregate_recovery_rate` (free-decode identifier recovery) and `total_cross_emission_count`. Branch logic per Stage 3 plan v2 §2: `>= 0.50` → don't train Stage 3 yet, queue broader confirmation; `< 0.50` → build scheduled sampling locally; `< 0.30` → trigger redesign discussion.

AUTHORIZED: yes

RATIFIED-BY: codex audit `codex_audit.md` 2026-05-13T03:25Z (commit `f04cec1`, "no blockers"; verified gate threshold wiring, e3-baseline non-fail-exit, gate-dict naming, 26/26 tests) + user chat "go" (2026-05-13T03:30Z).

BOUNDED SCOPE: This authorization covers ONLY the baseline measurement. Stage 3 training (scheduled sampling, DAgger, or other) requires a separate decision after baseline result is read. Implementation commit `92cca6e` shipped evaluator modes + 8 regression pins; audit commit `f04cec1` ratifies.

CONTEXT: `inbox_claude.md` 2026-05-13T03:05Z entry surfaces commit `92cca6e` (implementation + tests) for audit. `codex_audit.md` f04cec1 entry confirms gate semantics correctly wired. `docs/working/candidate_e/stage3_plan_2026_05_13.md` §2 + §5b specifies the decision-point semantics. Per Codex Order B (audit 2026-05-13T02:36Z, commit `ee8dfa4`): step 5 of the 6-step sequence — implement → tests → surface for audit → user go → **run small pod baseline** → branch from result.

---

## 2026-05-12T17Z — Candidate E Stage 2c primary gate

DECISION: At `--stage e2c`, ONLY `tf_per_token_accuracy ≥ 0.70` is load-bearing. swap pair_pass_rate and TF identifier_recovery_rate are reported as informational diagnostics; they cannot fail the e2c run.

AUTHORIZED: yes

RATIFIED-BY: user + codex (audit verdict 2026-05-12 + user confirm "Launch")

CONTEXT: docs/working/candidate_e/stage2_launch_lock_2026_05_12.md §E2c evaluator section. Code: `evaluate_candidate_e_stage2.py` lines 869-878 (`if args.stage == "e2c": overall_pass = tf_per_token_gate_pass`). Tests pinned: `test_e2c_gate_only_per_token_load_bearing`, `test_e2b_gate_still_requires_both`.

---

## 2026-05-13T02:00Z — E2c continuation PASSES locked gate; Stage 3 unblocked for design

DECISION: E2c continuation (1000 steps from `stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt`) cleared the locked E2c gate. `tf_per_token_accuracy = 0.923` vs threshold 0.70 (pass margin 0.223). All E2c failure-mode metrics improved: exact spans 181→428, wrong_start 55→25, right_start_drift 412→195. Identifier recovery 0.279→0.660. Stage 3 (on-policy / DAgger) is now unblocked for design review ONLY — no Stage 3 pod launch until the Stage 3 plan + gates are written and audited.

AUTHORIZED: yes

RATIFIED-BY: user "go" (00:38Z authorized continuation + cleanup) + codex audit of E2c continuation PASS (`codex_audit.md` 2026-05-13T01:52Z) + user observation of agreement (chat, 02:00Z)

CONTEXT: `inbox_claude.md` 2026-05-13T02:00Z entry surfaces full trajectory. TF summary persisted at pod `/workspace/tksCAS/eval_e2c_cont_tf_only/tf_dev_summary.json`. Continuation ckpt at pod `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt` (664 MB). Codex's reframe of the next question: no longer "can the model learn source copy under TF?" (answered yes) — now "can the model keep that source copy behavior when generating on its own output?" That's the Stage 3 / DAgger question.

NEXT GATED ACTION: lock Stage 3 plan. No pod work until Stage 3 plan + gates audited.

---

## 2026-05-13T00:38Z — Pod quota cleanup before E2c continuation relaunch

DECISION: Delete the 6 stale stage7 candidate run dirs + 2 broader_b3_eval result dirs + 9 empty eval_e2c_* dust dirs from /workspace/tksCAS/ on pod. Frees ~20.4 GB to unblock E2c continuation training (which is failing due to user-quota exhaustion — Errno 122). Exact paths per cleanup manifest at `docs/working/candidate_e/pod_cleanup_manifest_2026_05_13.md`. NO WILDCARDS in destructive command per Codex safety requirement.

AUTHORIZED: yes

RATIFIED-BY: user "go" (chat, 00:38Z) + codex audit (00:33Z `codex_audit.md` Option 1 approval)

CONTEXT: Today's silent failures (E2c trainer crash at step 1000, all nohup launches with 0-byte logs, scp "close remote: Failure") all trace to user-quota exhaustion on pod. ~33 GB of training artifacts in /workspace/tksCAS/ vs quota ceiling. Codex listed the 4 KEEP dirs (b2 → e2a → e2b → e2c warm-start chain) and 6 DELETE dirs (falsified/superseded candidates). After deletion + quota verification, re-launch the already-authorized E2c continuation per the 00:20Z entry below.

---

## 2026-05-13T00:20Z — E2c continuation training (1000 more steps from ckpt_step_1000.pt)

DECISION: Run a 1000-step E2c continuation warm-started from `/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt`. Same corpus, same hparams, same E2c losses (span 1.0, contrastive_margin 0.5, coverage 0.1, start_anchor 2.0, anchor_contrastive 1.0, copy 0.5). Hold the 0.70 per_token_accuracy gate threshold (no metric drift). Hold the loss shape (don't design body-digit drift loss until after the continuation result).

AUTHORIZED: yes

RATIFIED-BY: user "go" (chat, 00:20Z) + codex audit (00:08Z `codex_audit.md` E2c continuation recommendation)

CONTEXT: E2c first run (`stage_e2c_anchor_20260512T192622Z`) FAILED gate at `tf_per_token_accuracy = 0.628` vs 0.70, but produced 45× lift on identifier recovery vs E2b. right_start_drift = 412/648 (63.6%) dominant; wrong_start only 55/648 (L_start_anchor working). Codex audit (00:08Z): "The jump from E2b to E2c is too large to call the objective exhausted after one 1000-step run." Eval after continuation will be TF-only (skip free-decode/swap to save the CPU-bound hours; load-bearing gate is TF per-token).

---

## 2026-05-12T21:35Z — E2c evaluator recovery via blocking SSH against ckpt_step_1000.pt

DECISION: Execute the E2c evaluator inline via blocking SSH against `/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt` (semantically equivalent to the missing ckpt_final.pt). No nohup/setsid/scp/heredoc/tmux. Run command shape per Codex audit 2026-05-12T21:28Z. Note explicitly in findings that ckpt_final.pt was not written.

AUTHORIZED: yes

RATIFIED-BY: user "go" (chat, 21:35Z) + codex audit (21:28Z)

CONTEXT: `codex_audit.md` 2026-05-12T21:28Z entry. `inbox_claude.md` 21:30Z ack. Pod-side process detach + scp failures forced blocking SSH approach. E2c trainer completed step 1000 cleanly; ckpt_final.pt skip was post-step observability failure, not training failure.

---

## 2026-05-12T15Z — Pod launch authorization protocol

DECISION: 5-step pre-launch checklist required before every pod launch — (1) sync files, (2) MD5-verify pod vs local, (3) resolve checkpoint path, (4) verify launch flags include `--max-cas-prefix-len 192` and correct `--ablation`, (5) confirm GPU idle. Both `AUTHORIZED: yes` here AND a "launch" / "go" chat message required. Either alone is not enough.

AUTHORIZED: yes

RATIFIED-BY: user (locked across E2a, E2b, E2c launches)

CONTEXT: docs/working/candidate_e/stage2_launch_lock_2026_05_12.md pre-launch checklist. Applied at E2a (commit 8ad6a3b), E2b (commit f53baca), E2c (commit cfcbc39).

---

## 2026-05-14T05:45Z — Mode 7 real-checkpoint upgrade (Render container)

DECISION: Queued for review. Render backend is live at https://noetic-compass-api.onrender.com (deploy `4787c2d` 2026-05-14T05:38Z, auto-deploy on every master push). Mode 7 SSE flows end-to-end with structurally-correct mechanistic payloads — but `activation_hooks.hook_status` reports all-false and diagnostics include `cas_native_predictor_run_dir_missing`, `stub_capture_no_model`, `stub_attribution_uniform`. Mode 7 is correctly falling into `_fallback_mechanistic_summary`.

This entry queues the option to upgrade Mode 7 from stub-numbers to real-model-numbers in production. NOT yet authorized — Codex to fill in scope/cost/source-checkpoint decision before user chat "go".

### Why this is queued, not auto-greenlit

- Production Mode 7 demo is **architecturally real** today (schema, UI, streaming, validators all correct). Stub numbers are a deliberate fallback the user accepted at SGGS-onboarding time.
- Real-numbers upgrade is **stakeholder-fidelity polish**, not a regression fix. Easy to defer until a stakeholder explicitly notices.
- Decision touches Render container shape (image size, persistent disk, or external blob fetch — all paid-tier tradeoffs).

### Source-checkpoint problem Codex needs to resolve first

Current Mode 7 predictor expects `/app/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/`. That run is:
- **Not in local archive `D:\tksCAS-archive\`** (verified by Claude 2026-05-14T05:45Z — paraphrase-v77fix folder absent)
- **Not on RunPod at `/workspace/tksCAS/.../runs/`** (verified by Claude via SSH same time — `grep -i paraphrase` returns nothing)
- **Older B3/K9 lineage** — pre-dates Stage 3 simplex MVP

Codex needs to pick the source checkpoint before this entry can be ratified. Three candidates:

| Option | Checkpoint | Pro | Con |
|---|---|---|---|
| **α** | Stage 3 simplex (`D:\tksCAS-archive\stage_e3_20260513T043823Z\ckpt_final.pt`) | Most advanced structural-prediction artifact; canonical for chat-stage3; 0.78/0.64 free-decode gates | Mode 7 mechanistic predictor was written for K=9/paraphrase architecture — likely requires `cas_native.trace.mechanistic` refactor to accept simplex-MVP shape. Not trivial. |
| **β** | Retrain a paraphrase-v77fix-shape model | Drop-in for current Mode 7 predictor | New training run (~$5-50 GPU spend); duplicates lineage user has already moved past |
| **γ** | Synthesize a tiny K=9-shape stub checkpoint | Cheapest; bypasses Lane 1 vs Lane 2 question | Worst signal — fake numbers dressed as real numbers; violates `feedback_separate_evidence_levels_in_status.md` (passes stub-numbers off as real) |

**Recommendation (Claude):** option α — refactor `cas_native.trace.mechanistic` to accept Stage 3 simplex shape. Investment in real interpretability infra, on the canonical checkpoint. ~4–8 hours of Codex pod work + Claude audit. Not eligible for option γ — stub-as-real is exactly the failure mode the user's memory bank guards against.

### Container delivery path

After source-checkpoint is picked, three delivery patterns for Render:

| Pattern | Implementation | Trade-off |
|---|---|---|
| **D1: Bake into image** | `COPY` checkpoint dir into `Dockerfile.api` before final stage | Image grows ~700 MB → 5-8 min builds (was 24 s on Railway). Auto-deploys slow proportionally. Git LFS or git-annex required since `.pt` files are too large for plain git. |
| **D2: Render persistent disk** | Standard plan supports disks; manually upload weights to a mounted disk, point Mode 7 predictor at the mount path | Image stays small; one-time upload via Render UI or SFTP; **need to repeat upload on every checkpoint refresh** |
| **D3: Container fetch on startup** | Lifecycle hook downloads checkpoint from an S3-compatible blob on container init | Cleanest separation of weights vs code; need a public-or-signed-URL bucket (R2 free tier works); cold-start gets +~30-60 s |

**Recommendation (Claude):** **D2** for the first cut (manual upload to Render disk; under user's control; no external infra), with D3 as a follow-on once a blob store is in place.

### Pre-flight checks before ratification

1. Codex picks α/β/γ for source checkpoint. If α: estimate refactor scope (`cas_native.trace.mechanistic` API surface).
2. Codex picks D1/D2/D3 for container delivery. If D2: confirm Render Standard persistent-disk pricing + Render UI upload mechanics. If D3: confirm a blob store target.
3. Smoke plan: after upgrade, the same end-to-end curl Claude ran 2026-05-14T05:45Z must show `activation_hooks.hook_status.*` all `true` AND diagnostics empty.

### Budget cap

Per-month delta from current state:
- D1: no monthly delta (paid in build minutes — Render Standard includes 500 build min/mo, current usage ~5 min)
- D2: +$1-3/mo for persistent disk (Render disk pricing: $0.25/GB/mo, ~5-10 GB needed)
- D3: ~$0/mo if Cloudflare R2 free tier (10 GB free egress)

GPU spend (only if option β picked): ~$5-50 for a retrain run.

### Gate criteria for promotion

1. Live end-to-end smoke (same curl as the 2026-05-14T05:45Z probe) shows `hook_status` all `true`.
2. Diagnostics list does NOT contain `cas_native_predictor_run_dir_missing`, `stub_capture_no_model`, or `stub_attribution_uniform`.
3. At least one captured `attention_heads[*].entropy` numeric value differs from the deterministic-stub value (proves real attention extraction, not stub).
4. `npx vitest run src/lib/sggs_stream.test.ts` still passes (selectors weren't broken by payload shape change).
5. User sample-reads 3-5 head_commit payloads from a live production stream and confirms numbers look like real model output, not stub.

### AUTHORIZED status

**AUTHORIZED: pending** — Codex must answer α/β/γ + D1/D2/D3 in this entry's appendix, then user chat "go" to ratify.

NOT in scope this entry:
- Any backend deploy changes (already auto-deploy on master push via blueprint)
- Lane A training (separate AUTHORIZED entry track per `codex_onboarding_2026_05_14.md` §10)
- SGGS Phase 2 live-witnessing wire-up (separate roadmap)

---

## 2026-05-14T15:00Z — Stage 4A pod launch (English → CAS Front Door v0)

DECISION: Stage 4A pod training of the Front Door v0 — train an English → CAS generation head on the 5,244-record Wave 2.5 + Wave 3 layer3 inverted corpus (`cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl`, sha256 `8ced4726bceae5176285a171d33ad6d9f3903c3047c240157fd51265ac3d2954`). Reuses the `train_native_nl_gen.py` real path (`NativeNLCollator` + `attach_nl_gen_head` + `forward_with_lm`). Post-training eval gated by `evaluate_stage4a.py` (commit `f273d36`) with the two Codex pre-launch locks below.

AUTHORIZED: yes

RATIFIED-BY: Codex audit `27236de` (evaluator + locks signed off) + user chat "go" 2026-05-14T15:15Z. Scope-of-go ratified: pre-flight smoke + full training + full-val eval `--limit 0` + sample read + immediate local backup on promote, exactly as written. No improvisation.

CONTEXT: User's refined data rule ratified 2026-05-14 — "Foreign questions can broaden CAS. Foreign answers cannot define CAS." Stage 4A is the CAS-native local-first anchor. Inverter adapter `cf4828d`. Real-data corpus smoke matched between Claude + Codex (loss_lm 10.141 → 10.095 on Codex's micro command). Evaluator landed `f273d36`, hardened against silent (0,0) division + permissive compile-validity bugs.

### Scope

| Param | Value |
|---|---|
| Pod | RunPod A6000 48GB (default) or A100 80GB (if A6000 unavailable) |
| Corpus | `cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl` (5,244 records, sha256 `8ced4726…`) |
| Tokenizer | `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json` |
| English BPE | `cas-synthetic/data/native_nl/english_bpe_50k_20260507.json` |
| Epochs | 3 |
| Batch size | 32 |
| Approx steps | 5,244 × 3 / 32 ≈ 491 |
| Wall-time estimate | 30–60 min on A6000 |
| LR / curriculum | trainer defaults (`--lr 2e-4`, β linear ramp `0.1 → 1.0` over 10K steps — short run stays near β=0.1) |
| Arch flags | `--d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 --head-n-layers 6 --head-n-heads 8` (trainer defaults; locked so eval `--d-model …` matches the trained checkpoint exactly) |
| `--use-cas-prefix` | OFF — Stage 4A inverter sets `cas_expression=""` deliberately (target leakage guard) |
| Budget cap | ≤ **$5** total GPU spend (kill-switch if exceeded) |

### Codex pre-launch locks (must be satisfied for the eval to count)

**Lock 1 — Full validation set.** Post-training eval must run with `--limit 0` (no cap). Expected ~262 records out of the deterministic 95/5 split. Default 50 is for iteration, not promotion.

**Lock 2 — Strict load.** `evaluate_stage4a.py` defaults to strict `load_state_dict`: any missing or unexpected key aborts the eval. The `--allow-load-mismatch` escape hatch must NOT be used for the promotion eval. Codex audit 27236de.

### Pod-side pre-flight smoke

Before the real run, run the Codex real-data micro smoke command on the pod (NOT `--smoke-test`). Same shape as Codex's `dbbce48` verification, swapped to CUDA:

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_native_nl_gen.py \
  --data-path cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_preflight_TS \
  --device cuda:0 --limit 8 --epochs 1 --batch-size 4 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8 \
  --train-log-every-steps 1 --beta-curriculum-steps 10 --seed 1729
```

Pre-flight passes if: corpus hash matches `8ced4726…`, `loss_lm` finite (not NaN), `mode=real`, 2 global steps, `training_complete` event emitted. Total time: ~2 min on A6000.

### Real training launch command

After pre-flight passes:

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_native_nl_gen.py \
  --data-path cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_v0_TS \
  --device cuda:0 --epochs 3 --batch-size 32 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8 \
  --lr 2e-4 --beta-curriculum-steps 10000 \
  --train-log-every-steps 20 --seed 42
```

### Eval gate after training (the four-rule check, calibrated for v0)

Run with `--limit 0` (full val split):

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_stage4a.py \
  --checkpoint /workspace/tksCAS/stage4a_v0_TS \
  --corpus cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_eval_v0_TS \
  --device cuda:0 --limit 0 --max-new-tokens 96 --sample-reads 12 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8
```

Promotion gates (v0, "did the model learn anything" floor — Codex to calibrate up/down after first numbers land):

| Gate | Floor | Source |
|---|---|---|
| TF per-token accuracy | ≥ 0.20 | Stage 4 spec §8 gate 1 analogue |
| Free-decode CAS validity rate | ≥ 0.50 | Stage 4 spec §8 gate 1 |
| Normalized recovery rate | ≥ 0.10 | covers minor whitespace variation |
| Per-grammar-category min validity | ≥ 0.25 in ≥ 7 of 10 buckets | catches bucket-skew failure |
| No silent load mismatch | n_missing == 0 AND n_unexpected == 0 | Lock 2 |
| Human sample read | user reads 12 samples; PASS = "this looks like a CAS-conditioned model trying to write CAS" | per `feedback_samples_are_the_only_true_eval_for_cas_native.md` |

Six measurements emitted regardless of gate state (gate is for promotion, not for the eval itself running).

### Kill-switch (during training)

Stop run + report failure if ANY of:
1. `loss_lm` NaN or +Inf at any logged step
2. `loss_lm` plateau > 50 steps (no decrease ≥ 1e-4)
3. Sample mode-collapse on mid-train sampling (if enabled) — i.e., greedy output repeats single token > 80% of sampled positions
4. Wall-time > 90 min OR GPU spend > $5

### Backup discipline (per `feedback_back_up_successful_runs_imperative.md`)

On successful eval pass: immediately scp the full run dir (model_final.pt + tokenizer.json + english_bpe.json + checkpoint_manifest.json + training_events.jsonl + eval report JSON + samples.jsonl) to `D:\tksCAS-archive\stage4a_v0_TS\`. Three independent sha256 confirmations. Do not wait for the demo to be needed.

### Push discipline

Commit + push the eval report + samples + a short eval findings doc immediately after the run lands. Per `feedback_push_immediately_after_commit.md`.

### Budget

| Item | Cap |
|---|---|
| Pre-flight smoke | ≤ $0.10 (A6000 ~ $0.80/hr × ~5 min) |
| Real run | ≤ $1.20 (A6000 × ~60 min) |
| Eval | ≤ $0.50 (A6000 × ~15 min on 262 records) |
| Buffer | ~$3.20 |
| **Hard cap** | **$5.00** |

### What is NOT in scope this entry

- Stage 4B external-question SDG pilot (separate AUTHORIZED entry — user-ratified to run in parallel per `feedback_parallelize_sdg_with_training.md`, but the pilot scope/budget/dataset pick still needs its own ratification).
- Stage 4C 70/30 mix retrain (post-Stage 4A; new AUTHORIZED entry once 4A baselines + 4B pilot land).
- Mode 7 real-checkpoint upgrade (separate entry above, 2026-05-14T05:45Z).
- Lane A conversational dialogue training (separate entry per `codex_onboarding_2026_05_14.md` §10).

### Provenance trail

- Corpus build: commit `cf4828d` (inverter adapter + corpus + manifest)
- Audit Track 1+2: commit `4c48e11` (pre-flight findings)
- Stage 4 spec: `docs/working/stage4_minimal_nl_training_spec_2026_05_13.md`
- Data rule refinement: `feedback_cas_native_data_strategy_2026_05_13.md` (foreign-questions-OK refinement)
- Codex Stage 4 directive: `codex_audit.md` 2026-05-14T00:??Z + 14:05Z + 27236de
- Evaluator: commit `f273d36`, strict-load patch this commit (next commit)
- Real-data micro-smoke (Claude verified): loss_lm 10.141 → 10.095, mode=real, 2 steps, matches Codex's numbers exactly.

### OUTCOME — 2026-05-14T16:45Z

Sequence ran to completion exactly as specified. **NOT promoted.** Mechanical gate failure on `normalized_recovery_rate` (0.000 < 0.10 floor). Human sample read: mode collapse onto `^3^O`-style high-frequency tokens regardless of input prompt. TF accuracy + validity gates passed strongly (3.6× and 1.8× respective floors).

Full findings + 12 sample reads: `docs/working/stage4a_v0_2026_05_14/FINDINGS.md`.

Run dir on pod: `/workspace/tksCAS/stage4a_v0_20260514T163737Z` (checkpoint `33bdaead-f171-4b5b-9bd9-68aecb872f7b`). Eval dir on pod: `/workspace/tksCAS/stage4a_eval_v0_20260514T164204Z`. Total cost ~$0.05 (well under $5 cap).

Diagnosis: β curriculum slow-ramp (β=0.140 at end-of-train) starved the LM head of gradient signal. Wave 2.5 prompts are templated-renderer output, contributing to encoder-side collapse.

Per the entry's "backup IF it promotes" condition, local-archive scp NOT executed. Codex review of next-lever sequence pending (`inbox_claude.md` 2026-05-14T16:45Z).

## 2026-05-14T17:00Z — Stage 4A v0.1 pod retrain (Lever A + B combined)

DECISION: Retrain Stage 4A on the same corpus + arch with two changes from v0: `--beta-curriculum-steps 200` (was 10000) and `--epochs 6` (was 3). LR unchanged at `2e-4`. Same locks: full-val eval `--limit 0`, strict load (`--allow-load-mismatch` forbidden), sample-read gate. **New diagnostic added per Codex directive `3b03207`:** generation diversity (`unique_output_ratio`, `mode_collapse_ratio`, top-5 modes) computed across the full val set so mode collapse is measured directly. Evaluator with diversity metric committed at `b030bf2`.

AUTHORIZED: yes

RATIFIED-BY: Codex audit `3b03207` (v0 rejection + v0.1 directive) + user chat "go" 2026-05-14T17:10Z. Scope-of-go ratified: pre-flight smoke + full training with `--epochs 6 --beta-curriculum-steps 200` + full-val eval `--limit 0` + sample read + immediate local backup on promote.

CONTEXT: Stage 4A v0 (entry above) produced clean training (loss_lm 10.07 → 0.91) but mode-collapsed at inference. Codex diagnosis: β curriculum was too slow for short runs — β reached only 0.140 of its 1.0 target, starving the LM head of gradient signal. Lever A (faster β ramp) + Lever B (more epochs) is the cheapest training-signal test; Codex defers Stage 4B until v0.1 result lands.

### Scope (deltas from v0 in **bold**)

| Param | v0 | v0.1 |
|---|---|---|
| Pod | A6000 48GB | **same** |
| Corpus | 5,244 records sha256 `8ced4726…` | **same** |
| Tokenizer + BPE | as v0 | **same** |
| Epochs | 3 | **6** |
| Batch size | 32 | **same** |
| Approx steps | 491 | **~984** |
| LR | 2e-4 | **same** |
| `--beta-curriculum-steps` | 10000 | **200** |
| Arch flags | d-model 512, 6/8 enc, 6/8 head | **same** |
| Wall-time estimate | 3 min observed | **~7 min** |
| Budget cap | ≤ $5 | **≤ $5** |

### Pre-flight smoke (unchanged)

Same Codex real-data micro command (`dbbce48` shape) on the pod with `--device cuda:0 --limit 8 --epochs 1 --batch-size 4`. Pass criteria identical: corpus hash matches `8ced4726…`, loss_lm finite, mode=real, 2 global steps, training_complete event emitted.

### Real training launch command (v0.1)

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_native_nl_gen.py \
  --data-path cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_v01_TS \
  --device cuda:0 --epochs 6 --batch-size 32 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8 \
  --lr 2e-4 --beta-curriculum-steps 200 \
  --train-log-every-steps 20 --seed 42
```

The only flag deltas from v0 are `--epochs 6` and `--beta-curriculum-steps 200`. Seed stays at 42 so the train/val split is identical to v0 → eval gates are directly comparable.

### Eval gate after training (full val, strict load, + diversity)

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_stage4a.py \
  --checkpoint /workspace/tksCAS/stage4a_v01_TS \
  --corpus cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_eval_v01_TS \
  --device cuda:0 --limit 0 --max-new-tokens 96 --sample-reads 12 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8
```

### Promotion gates (v0.1 — diversity gate added)

| Gate | Floor | v0 actual | Notes |
|---|---|---|---|
| TF per-token accuracy | ≥ 0.20 | 0.726 ✅ | unchanged |
| Free-decode CAS validity rate | ≥ 0.50 | 0.905 ✅ | unchanged |
| Normalized recovery rate | ≥ 0.10 | 0.000 ❌ | unchanged |
| Per-bucket validity ≥ 0.25 | ≥ 7/10 | 9/10 ✅ | unchanged |
| **Unique output ratio** | **≥ 0.40** | (not measured — added v0.1) | **NEW** — directly catches collapse |
| **Mode-collapse ratio** | **≤ 0.15** | (not measured — added v0.1) | **NEW** — single output ≤ 15% of total |
| No silent load mismatch | n_missing = 0 AND n_unexpected = 0 | 0/0 ✅ | unchanged |
| Human sample read | "looks like CAS-conditioned model trying to write CAS" | mode collapse ❌ | unchanged |

The diversity floors (0.40 unique / 0.15 collapse-cap) are first-cut values — Codex to calibrate after first v0.1 numbers if too strict / too loose. Both metrics are computed over normalized (whitespace-stripped) outputs so trivial spacing variations don't inflate diversity.

### Kill-switch (unchanged)

Stop run + report failure if ANY of:
1. `loss_lm` NaN or +Inf
2. `loss_lm` plateau > 50 steps (no decrease ≥ 1e-4)
3. Sample mode-collapse on `--sample-every-steps` (off this run)
4. Wall-time > 90 min OR GPU spend > $5

### Backup discipline

On successful eval pass (all 8 gates including diversity): immediately scp the full run dir to `D:\tksCAS-archive\stage4a_v01_TS\`. Three sha256 confirmations. Per `feedback_back_up_successful_runs_imperative.md`.

### Push discipline

Commit + push the eval report + samples + a v0.1 findings doc immediately after the run lands. Per `feedback_push_immediately_after_commit.md`.

### Budget

| Item | Cap |
|---|---|
| Pre-flight | ≤ $0.05 |
| Real run (~7 min A6000) | ≤ $0.15 |
| Eval (~1 min) | ≤ $0.05 |
| Buffer | ~$4.75 |
| **Hard cap** | **$5.00** |

### What is NOT in scope this entry

- Stage 4B (external HF questions via SDG) — Codex explicitly deferred until v0.1 outcome lands.
- Stage 4C 70/30 mix retrain — gated on 4A v0.1 result + 4B pilot.
- Architecture changes (Codex directive: keep arch + LR unchanged).

### Provenance trail

- v0 entry: 2026-05-14T15:00Z (above)
- v0 outcome: 2026-05-14T16:45Z (above)
- Codex v0.1 directive: `codex_audit.md` commit `3b03207` 2026-05-14T16:??Z
- Diversity evaluator patch: commit `b030bf2` 2026-05-14T17:00Z
- Findings doc: `docs/working/stage4a_v0_2026_05_14/FINDINGS.md`

### OUTCOME — 2026-05-14T17:20Z

Sequence ran to completion per the locked v0.1 entry (note: SSH disconnect at ~T+10min due to user-side power outage; `nohup` detach kept pod-side process alive, training finished cleanly via background). **NOT promoted.** Two mechanical gates failed: `normalized_recovery_rate` 0.000 < 0.10, `unique_output_ratio` 0.229 < 0.40. Five gates passed including the new diversity floor `mode_collapse_ratio` 0.111 ≤ 0.15.

Headline deltas vs v0: TF accuracy +4.7pp (0.773), validity rate +2.2pp (0.927), top-mode share dropped substantially (now 11.1% of records); unique-output count tripled to 60/262. Model now produces one favorite template per surface family rather than v0's single template across categories. Recovery still 0 — input-content mapping not learned.

Full findings: `docs/working/stage4a_v01_2026_05_14/FINDINGS.md`. Run dir on pod: `/workspace/tksCAS/stage4a_v01_20260514T170228Z`. Eval dir on pod: `/workspace/tksCAS/stage4a_eval_v01_20260514T171317Z`. Total v0.1 cost ~$0.09.

Diagnosis: β curriculum lifted the LM head signal as expected, but the Wave 2.5 input distribution is the new ceiling — too templated for content-conditional encoder learning. Codex's pre-stated next-lever trigger fires: Stage 4B external-question SDG is justified.

Per "backup IF it promotes" condition: local-archive scp NOT executed. Codex review pending (`inbox_claude.md` 2026-05-14T17:20Z) on Stage 4B kickoff scope.

## 2026-05-14T17:35Z — Stage 4B pilot (external Q → CAS SDG → SFE; 500-record corpus audit, NO training)

DECISION: Run a 500-record Stage 4B pilot per Codex directive 2026-05-14T17:30Z (post v0.1). External questions only (answers dropped); CAS answers generated by our SDG; SFE filter applied; acceptance rate + category spread + failure pattern reported. **No model training in this entry's scope** — pilot is corpus-quality audit only. v0.2 retrain is a separate later AUTHORIZED entry, gated on user sample-read sign-off of the pilot corpus.

AUTHORIZED: yes

RATIFIED-BY: Codex audit (relayed 2026-05-14T17:30Z) + user chat "go" 2026-05-14T17:45Z. Scope-of-go: install datasets, build 3 new scripts (ingest + SDG + review pack), CPU smoke 10 records, surface to Codex, then full 500-record pilot, sample-read 50, FINDINGS doc. No model training. $5 hard cap.

CONTEXT: Stage 4A v0.1 (entry above) reduced mode collapse but still 0% recovery. Diagnosis: Wave 2.5 prompts too templated for input-content mapping. Codex's pre-stated trigger fires. Per user-ratified data rule (memory `feedback_cas_native_data_strategy_2026_05_13.md` 2026-05-14 refinement): "Foreign questions can broaden CAS. Foreign answers cannot define CAS."

### Honest scoping flag — engineering work is required

The existing `cas-synthetic/scripts/generate_path_d_*.py` pipeline generates **English from CAS seeds** (the direction that built Wave 2.5). Stage 4B needs the **inverted** direction: **external English question → CAS expression**. A new generator script is needed. Estimated ~3-5 hours of engineering before the first API call:

1. `cas-synthetic/scripts/ingest_oasst2_questions.py` — load OASST2 via HF `datasets`, filter to user-side questions only, write 500 records to `cas-synthetic/data/stage4b/oasst2_questions_pilot.jsonl`. Drop all `assistant` / `prompter` reply fields. License manifest written alongside.
2. `cas-synthetic/scripts/generate_stage4b_pilot.py` — new SDG. For each external question, call Haiku to propose a candidate CAS expression, compile via `api/notation/compiler.py`, retry on compile error (up to 3 tries), apply SFE-style gates (next §), write accepted records to `wave3_step2_5`-shape JSONL.
3. New SFE gates appropriate for inverted direction (Codex to confirm):
   - **Compile gate:** `compile_expression(proposed_cas).valid` must be True (hard reject otherwise).
   - **Anti-jargon gate:** proposed CAS must use CAS surface tokens (no English leakage); reject if it contains common-English n-grams.
   - **Round-trip judge gate:** second Haiku call rates 1-5 whether the candidate CAS plausibly maps to the question; reject if < 3.
   - **Length sanity:** proposed CAS within 4-256 tokens (no trivial short / runaway long outputs).
4. Sample-read pack writer (50 records stratified by grammar category) — same shape as Wave 2.5's `wave3_step2_5_500_review_pack` files.

### Pre-flight requirements

| Item | Status |
|---|---|
| `datasets` package | NOT installed locally — needs `pip install datasets` |
| `anthropic` SDK | ✅ installed (v0.100.0) |
| OASST2 license | ✅ Apache 2.0 per dataset scout consolidated 2026-05-07 (primary recommendation) |
| Anthropic API key | check `ANTHROPIC_API_KEY` env var on laptop before launch |
| Wave 2.5 SFE infra | check `cas-synthetic/validation/level3_review_gate.py` can be reused or needs adapter |

### Scope

| Param | Value |
|---|---|
| Dataset source | OASST2 (Apache 2.0) — scout's primary, NOT OASST1 (user noted OASST1 earlier; scout's audit picks OASST2 as the cleaner variant) |
| Questions sampled | 500 (after filtering to user-side prompts) |
| Model | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) — same drafter Wave 2.5 used per memory `project_path_d_wave_2_5_promoted_2026_05_08.md` |
| Max retries per question | 3 (per Wave 2.5 SFE pattern) |
| Round-trip judge calls | 1 per surviving record (so up to 2 Haiku calls per question) |
| API spend cap | **$5** (Haiku at ~$0.0058/record × 500 with retries ≈ $3-4, $5 hard cap) |
| Wall-time | ~1-2 hours on laptop (CPU + network bound) |
| Pod GPU | NONE — pure laptop work |
| Final pilot output | `cas-synthetic/data/stage4b/pilot_500_<TS>.jsonl` + `pilot_500_<TS>.manifest.json` + `pilot_500_review_pack.md` |

### Pilot deliverables (the report Codex wants)

After the pilot runs, emit a findings doc at `docs/working/stage4b_pilot_2026_05_14/FINDINGS.md` with:

1. **Acceptance rate** — n_accepted / n_attempted, broken down by reject reason (compile fail, anti-jargon fail, judge fail, length fail).
2. **Category spread** — for each of the 10 grammar categories used in Wave 2.5 (state_literal, binary_composition, ..., inversion), what proportion of accepted records map to it. Diversity expected to differ from Wave 2.5's distribution.
3. **Failure patterns** — top 5 reject reasons by frequency, sample reject records, what Haiku tried but rejected.
4. **50 sample reads** (stratified by category) for user audit.
5. **License manifest** with OASST2 source URL + license string + retrieval timestamp.

### Gate criteria for v0.2 retrain ratification (NOT for the pilot — separate entry)

These are pre-stated so Codex + user know what to look for when reviewing the pilot:

| Gate | Floor | Rationale |
|---|---|---|
| Acceptance rate | ≥ 10% (≥ 50 accepted of 500) | If lower, pilot itself failed; revisit prompts or model |
| Category spread | ≥ 5 grammar categories represented | Avoid degenerate "all state_literal" pilot |
| Human sample-read | ≥ 40 of 50 samples judged "this CAS plausibly captures the question" | User's call |
| No foreign-answer text | 100% of records have empty external-answer fields | Hard rule per data strategy |

### Kill-switch (during pilot run)

Stop + report failure if ANY:
1. API spend > $5
2. Acceptance rate after first 50 attempts < 5% (signals broken prompts or wrong model)
3. Wall-time > 3 hours
4. Anthropic API error rate > 20% over a 50-record window

### What is NOT in scope

- v0.2 retrain — separate AUTHORIZED entry, post pilot user-audit pass.
- Stage 4C 70/30 mix — depends on v0.2 result.
- SQuAD v2 (user-vetoed earlier).
- Natural Questions (CC-BY-SA, scout flagged for IP attorney consult).
- Pre-existing path_d generator changes — Stage 4B builds new generators, doesn't modify the Wave 2.5 path.

### Provenance trail

- Stage 4A v0 outcome: 2026-05-14T16:45Z entry above
- Stage 4A v0.1 outcome: 2026-05-14T17:20Z entry above
- Codex Stage 4B directive: relayed 2026-05-14T17:30Z (audit commit hash pending)
- Data rule refinement: `feedback_cas_native_data_strategy_2026_05_13.md` (2026-05-14 update)
- Dataset scout findings: `docs/working/dataset_scout_consolidated_2026_05_07.md` (OASST2 = primary)
- Wave 2.5 SFE precedent: `project_path_d_wave_2_5_promoted_2026_05_08.md` (Haiku drafter pattern, $0.0058/record cost reference)

### OUTCOME — 2026-05-14T19:30Z

Stage 4B pilot ran to completion per Codex audit `0e97599`. **374/500 accepted (74.6%), 364 clean-train (after 9 copyright-quarantine), $1.44 spent of $5 cap, 20.4 min wall-time.**

Judge score distribution on accepted: 53% scored 5, 44% scored 4, 3% scored 3 (floor). Rejected by judge: 86 score-2 records + 2 score-1.

Reject reasons: 88 haiku_judge, 31 cas_compile (after 2 repair attempts), 5 haiku_self_reject, 3 length_sanity.

Category spread: state_literal=190 (51%), recipe=121 (32%), binary_composition=53 (14%), let_binding=9 (2%). 6 Wave 2.5 categories did NOT emerge — these are CAS-internal patterns (cross_register_omega, fractal_sequence, diagram_export, rpm_chain, inversion, meta_logic_relation) that don't have direct natural-language analogs in user questions. Wave 2.5 already covers these.

Copyright flags: 12 total (9 in accepted set → quarantine, 3 in rejected). The 9 quarantined are NOT in the 364 clean-train count.

Repair pipeline: 56 records (11.2%) needed at least one compile-repair retry; 25 salvaged, 31 lost after max-2 attempts.

Full report: `docs/working/stage4b_pilot_2026_05_14/FINDINGS.md`. 50 sample reads + 5 judge-rejected + 3 compile-rejected + all 9 quarantine + 5 repair examples: `docs/working/stage4b_pilot_2026_05_14/sample_reads_50.txt`.

No v0.2 retrain in this scope. Pending user sample-read of the 50 to gate the next AUTHORIZED entry for v0.2 retrain.

## 2026-05-14T19:45Z — Stage 4A v0.2 pod retrain (Wave 2.5 + Stage 4B clean-train mix)

DECISION: Retrain Stage 4A on a merged corpus combining Wave 2.5 (5,244 records from `track1_merged_2026_05_14.jsonl`) + Stage 4B clean-train (364 records from `stage4b_pilot_20260514T185757Z_accepted.jsonl` minus 9 quarantined copyright-flagged). All trainer hyperparameters frozen at v0.1 values. **Tests the corpus-diversity hypothesis: does broader English-side variety recover the input-content mapping that v0.1's templated Wave 2.5 prompts could not learn?**

AUTHORIZED: yes

RATIFIED-BY: Codex audit `728be8c` (Stage 4B pilot PASS, 50 sample reads cleared 40/50 bar) + user chat "go" 2026-05-14T19:55Z. Scope-of-go: build merged corpus (Wave 2.5 + 364 Stage 4B clean-train at natural ratio), pre-flight smoke, full training with v0.1 hparams frozen, full-val eval `--limit 0`, sample read 12, immediate local backup on promote.

CONTEXT: Stage 4B pilot 374/500 accepted, 364 clean-train (entry above 19:30Z). Sample-read gate passed per Codex 728be8c. Stage 4A v0 mode-collapsed; v0.1 reduced collapse but still 0% recovery; diagnosis attributed to Wave 2.5's templated-renderer English prompts not teaching content-conditional mapping. Stage 4B adds real-user prompt diversity for the 4 natural cognitive-operation categories.

### Design decisions worth flagging up-front

**1. Mix ratio: natural, NOT 70/30.** The original Stage 4 spec recommended 70% local / 30% external. Current natural ratio is ~93/7 (5,244 Wave 2.5 vs 364 Stage 4B). To hit 70/30 would require either:
   - Downsampling Wave 2.5 to ~850 records (throws away most own-data — bad)
   - Upsampling Stage 4B via 6× replication (1 record seen 6× per epoch — risk of memorizing the specific 364 — bad per memory `feedback_cas_native_underfit_over_overfit_short_epochs.md`)

Decision: **mix at natural ratio (Wave 2.5 5,244 + Stage 4B 364 = 5,608 unique records, ~6.5% Stage 4B share)**. Same 6-epoch curriculum so the broader English distribution is seen multiple times without record-level duplication. If v0.2 fails the recovery gate AGAIN, the next lever is generating more Stage 4B records (cheap at $1.44 per 500), not changing mix ratio. This is the underfit-over-overfit pattern from memory.

**2. Category-spread exception (Codex 728be8c).** Stage 4B emerged 4 categories instead of the AUTHORIZED entry's 5-floor. Acceptable because Wave 2.5 already covers the missing 6 categories (cross_register_omega, fractal_sequence, diagram_export, rpm_chain, inversion, meta_logic_relation) — these are CAS-internal patterns not naturally requested in user English. v0.2 corpus has ALL 10 categories represented (Wave 2.5 supplies the missing 6 with renderer-shaped prompts; Stage 4B supplies real-user prompt diversity on the 4 natural categories).

**3. Hparams frozen from v0.1.** All training-side knobs unchanged so v0.2 vs v0.1 is a clean A/B on corpus only.

### Scope (deltas from v0.1 in **bold**)

| Param | v0.1 | v0.2 |
|---|---|---|
| Pod | A6000 48GB | same |
| **Corpus** | Wave 2.5 only (5,244 records) | **Wave 2.5 + Stage 4B clean = 5,608 unique records** |
| Tokenizer + BPE | as v0.1 | same |
| Epochs | 6 | same |
| Batch size | 32 | same |
| Approx steps | 936 | **~1,000** (5,608 × 6 / 32 = 1,051) |
| LR | 2e-4 | same |
| `--beta-curriculum-steps` | 200 | same |
| Arch flags | d-model 512, 6/8 enc, 6/8 head | same |
| `--use-cas-prefix` | OFF | same |
| `--seed` | 42 | same (deterministic val split → same 262 records ≈ for direct gate comparability) |
| Wall-time estimate | ~7 min observed | **~7-8 min** |
| Budget cap | ≤ $5 | ≤ $5 |

### Pre-flight requirements

1. Build merged corpus: new script `cas-synthetic/scripts/build_stage4_v02_merged_corpus.py` inverts Stage 4B accepted records (363 clean-train, excluding the 9 copyright-quarantine), concats with Wave 2.5 inverted records, emits one JSONL with manifest + sha256.
2. Verify merged corpus on laptop (record count, schema, dedupe).
3. scp merged corpus to pod alongside `train_native_nl_gen.py` (already at parity per v0.1 sync) + evaluator (already at parity).

### Codex pre-launch locks (carry forward from v0.1)

**Lock 1 — Full validation set (`--limit 0`).** Eval runs on all val records, no cap. With merged corpus and same seed, val ≈ 280-285 records.

**Lock 2 — Strict load.** Evaluator default strict; `--allow-load-mismatch` forbidden for promotion eval.

### Pod-side pre-flight smoke

Same Codex real-data micro shape on the merged corpus, swapped to CUDA:

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_native_nl_gen.py \
  --data-path cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_v02_preflight_TS \
  --device cuda:0 --limit 8 --epochs 1 --batch-size 4 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8 \
  --train-log-every-steps 1 --beta-curriculum-steps 10 --seed 1729
```

Pass criteria identical: corpus hash matches the merged-corpus sha256, loss_lm finite, mode=real, 2 global steps, training_complete event emitted.

### Real training launch

After pre-flight passes:

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/training/train_native_nl_gen.py \
  --data-path cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_v02_TS \
  --device cuda:0 --epochs 6 --batch-size 32 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8 \
  --lr 2e-4 --beta-curriculum-steps 200 \
  --train-log-every-steps 20 --seed 42
```

### Eval gate (full val, strict load, with diversity)

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_stage4a.py \
  --checkpoint /workspace/tksCAS/stage4a_v02_TS \
  --corpus cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl \
  --tokenizer-path cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json \
  --english-bpe-path cas-synthetic/data/native_nl/english_bpe_50k_20260507.json \
  --output-dir /workspace/tksCAS/stage4a_eval_v02_TS \
  --device cuda:0 --limit 0 --max-new-tokens 96 --sample-reads 12 \
  --d-model 512 --encoder-n-layers 6 --encoder-n-heads 8 \
  --head-n-layers 6 --head-n-heads 8
```

### Promotion gates (same as v0.1)

| Gate | Floor | v0.1 actual |
|---|---|---|
| TF per-token accuracy | ≥ 0.20 | 0.773 ✅ |
| Free-decode CAS validity rate | ≥ 0.50 | 0.927 ✅ |
| Normalized recovery rate | ≥ 0.10 | 0.000 ❌ |
| Per-bucket validity ≥ 0.25 in ≥ 7/10 | 7/10 | 9/10 ✅ |
| Unique output ratio | ≥ 0.40 | 0.229 ❌ |
| Mode-collapse ratio | ≤ 0.15 | 0.111 ✅ |
| Load mismatch | 0/0 | 0/0 ✅ |
| Human sample read | "model trying to write CAS" | mode collapse ❌ |

**Hypothesis we're testing:** the 2 failed gates (recovery + unique_output_ratio) lift materially with Stage 4B prompt diversity. If they don't, the diagnosis is wrong and we need a different lever (architecture, more Stage 4B records, different mix ratio).

### Kill-switch (unchanged from v0.1)

NaN, plateau > 50 steps, mode collapse during mid-train sampling, wall-time > 90 min, GPU spend > $5.

### Backup discipline

On successful eval pass (all 8 gates): scp run dir to `D:\tksCAS-archive\stage4a_v02_TS\`, three sha256 confirmations. Per `feedback_back_up_successful_runs_imperative.md`.

### Budget

| Item | Cap |
|---|---|
| Pre-flight | ≤ $0.05 |
| Real run (~7-8 min A6000) | ≤ $0.20 |
| Eval (~1-2 min) | ≤ $0.05 |
| Buffer | ~$4.70 |
| **Hard cap** | **$5.00** |

Cumulative Stage 4A spend (v0 + v0.1 + v0.2): ~$0.23 projected, plus $1.44 already spent on Stage 4B pilot. Total Stage 4 to date: ~$1.67. Hard cap on this entry alone: $5.

### What is NOT in scope

- Stage 4C 70/30 mix retrain (the original spec's mix recommendation) — depends on v0.2 result + whether more Stage 4B records help.
- Stage 4B expansion to 1K+ records — only justified if v0.2 partially works but plateaus.
- New AUTHORIZED entry for any architecture changes.

### Provenance trail

- v0 outcome: 2026-05-14T16:45Z entry above
- v0.1 outcome: 2026-05-14T17:20Z entry above
- Stage 4B AUTHORIZED + outcome: 2026-05-14T17:35Z (entry above) + 19:30Z (outcome above)
- Codex 4B PASS audit: commit `728be8c`
- Refined data rule memory: `feedback_cas_native_data_strategy_2026_05_13.md` (2026-05-14 refinement)
- Wave 2.5 inverted corpus: `cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl` (sha256 `8ced4726...`)
- Stage 4B accepted records: `cas-synthetic/data/stage4b/stage4b_pilot_20260514T185757Z_accepted.jsonl`

### OUTCOME — 2026-05-14T20:15Z

Sequence ran to completion per the locked v0.2 entry. **NOT promoted.** 5 of 8 mechanical gates pass; 3 fail (normalized recovery 0.007 < 0.10, unique_output_ratio 0.139 < 0.40 REGRESSED, mode_collapse_ratio 0.189 > 0.15 REGRESSED).

But the headline finding is **direction-positive**: **recovery moved from 0 → 0.7%** for the first time, concentrated in `state_literal` (3.2% exact) — the category that received 52% of Stage 4B records (190 of 364). All 9 other categories got 0 records from Stage 4B and remain at 0% recovery.

Hypothesis confirmed: external prompt diversity moves recovery off zero. Volume insufficient at 6.5% mix share; would need ~20-25% (the original spec) which requires generating more Stage 4B records.

Concerning side-effect: diversity REGRESSED from v0.1. Unique outputs dropped from 60/262 (23%) to 39/280 (14%); top mode now dominates 19% of outputs (was 11%). Likely cause: the 4-category concentration of Stage 4B reinforced the existing per-category favorite templates instead of broadening them.

Full findings + samples: `docs/working/stage4a_v02_2026_05_14/FINDINGS.md`. Per-bucket: state_literal 3.2% recovery (first non-zero anywhere), others 0%. rpm_chain still 0% validity (exposure-bias signature persists).

Run dir on pod: `/workspace/tksCAS/stage4a_v02_20260514T200413Z` (checkpoint `30019a89-f75a-42f1-816b-f29f2df7fe4b`). Eval dir on pod: `/workspace/tksCAS/stage4a_eval_v02_20260514T201152Z`.

Cumulative Stage 4 spend (Stage 4B pilot + v0+v0.1+v0.2): **~$1.68**. Hard cap untouched.

Per "backup IF it promotes": local-archive scp NOT executed.

Codex review pending (`inbox_claude.md` 2026-05-14T20:15Z) on next-lever sequence. My recommendation: Stage 4B v2 expansion (~$5-7 API to generate 1500-2500 more records targeting under-represented categories), then v0.3 at 20-25% mix.

## 2026-05-31T07:20Z — Condition-3 GPU comparative-capture (MTC.1)

DECISION: Launch Step 1 GPU activation extraction — GPT-NeoX-20B forward over the 1440 Condition-3 capture-view prompts → npz — then the $0 Step 2 matched-taxonomy comparator (CAS element vs Control B NC40 vs Control C NC28 vs lexical-kmeans vs scrambled null). Per chat "YES GO" (2026-05-31T07:20Z) + readiness report (pod 8xH200, neox cached 39G = $0 download, loader pre-flight PASS 1440/1440/40-classes).
AUTHORIZED: yes
RATIFIED-BY: user (chat "YES GO")
CONTEXT: docs/working/mtc_matched_taxonomy_20260530/CONDITION3_GPU_CAPTURE_AUTHORIZATION_BRIEF_20260531.md

Run on pod root@213.181.104.235:15509, single H200 (CUDA_VISIBLE_DEVICES=0), HF_HOME=/workspace/hf-cache.
Abort conditions live-watched: <1440 scenarios, NaN/all-zero layers, num_layers!=44 / hidden!=6144, truncation blow-up, wall >90min.
Back up npz + metadata + comparator result + commit hash to D:\tksCAS-archive\ immediately on success (standing rule).

---

### OUTCOME — 2026-05-31T07:40Z  (Condition-3 MTC.1 capture)

Capture clean (1440/1440, shape (1440,44,6144) fp16, no NaN/Inf, 0 all-zero layers,
tokens 61-72, fingerprint 44 layers / hidden 6144). No abort condition tripped.

**VERDICT: FAIL of the comparative-specificity gate at 20B on Condition-3 — honest negative.**

| label set | hidden | text | lift |
|---|---|---|---|
| CAS element (full) | 6.53% | 6.25% | +0.28pp |
| CAS element (NC28 view, 504/504) | 6.55% | 5.95% | +0.60pp |
| Matched control NC40 (full) | 84.72% | 94.44% | -9.72pp |
| Matched control NC40 (view) | 82.14% | 92.06% | -9.92pp |
| Matched control NC28 (view) | 84.72% | 94.64% | -9.92pp |
| Lexical kmeans40 | 22.64% | - | - |
| Scrambled null | 3.47% | - | ~chance 2.5% (pipeline calibrated) |

Specificity readout: CAS - matched control = **-78.19pp**; CAS - lexical = -16.11pp.

CAS hidden readout (6.53%) misses the prereg >=20pp PASS bar by a wide margin and is
only +0.28pp above its own near-chance text baseline. Coherent same-size non-CAS
taxonomies (NC40, NC28) are recovered at 82-85%. The scrambled null at 3.47% (~chance)
confirms the probe pipeline is calibrated, so the near-zero CAS signal is a real
finding, not an execution artifact.

Honest interpretation: probed linearly at the last token, GPT-NeoX-20B does NOT encode
the CAS 40-element partition for Condition-3 in a linearly-separable way. This follows
from Condition-3 succeeding at killing surface leakage (surface gate 6.25%): the CAS
meaning is human-recoverable (MP 100%) but invisible to both bag-of-words (6.25%) and a
linear probe of 20B last-token activations (6.53%), while lexically-present ordinary
content is strongly recoverable by both. The comparative MTC gate returns a negative for
CAS specificity at this scale/probe/fixture. Threshold NOT retuned after seeing result.

Artifacts (commit + backup): result `condition3_mtc_comparator_result_20260531.json`;
npz + metadata + logs + PROVENANCE.txt at
`D:\tksCAS-archive\condition3_mtc_capture_20260531\` (3 sha256 confirmations,
npz pod==archive `17a1c880...`). Cost: ~$0 marginal (model pre-cached; ran on an
already-running pod; ~1 min model load + ~1 min forward + ~8 min comparator).

What this does NOT claim: it is one model (20B), one fixture (Condition-3), one probe
(last-token MLP linear). It does not test non-linear readout, mean-pooled or
mid-sequence states, or other scales. It does not bear on Condition-2 (hidden-vs-text
only). It does bear on the comparative-specificity PASS the project was chasing: not
demonstrated at 20B on Condition-3.

---

## 2026-06-10 — Typed-Probe v4 GPU run: AUTHORIZED: yes

**AUTHORIZED: yes** — for the Typed-Probe v4 matched-sampling run on the user-provided
RTX A6000 pod (38.147.83.24:14970).

Basis (both gate keys + preconditions satisfied):
- **User chat GO (explicit, repeated, 2026-06-10):** "go" (write v4 tooling), "use it",
  "use gpu if needed" — recorded by Claude on the user's behalf; this is the user's
  authorization, not agent self-authorization.
- **Codex audit complete and accepted:** `codex_audit.md` commit `4ad9aa3` (all six v4
  patches folded into the design and the frozen prereg).
- **Prereg frozen:** `typed_probe_gate_prereg_v4_matched_sampling.md` commit `c02323f`,
  sha256 `c2e222c3…`.
- **No-GPU tooling built + verified:** `analyze_confirmatory_v4.py` (`b37306a2`, selftest
  PASSED — group-CV removes the row-CV false-PASS leak), `run_screen_v4.py` (`f4764398`),
  `run_confirmatory_capture_v4.py` (`3a33acf3`) — all compile-clean.

Scope of this authorization: Stage-S behavioral screen, then (if the band yields ≥40
matched prompts) Stage-C matched-sampling capture, on Qwen2.5-1.5B with the frozen probe.
Steward discipline still applies: run the cheap Stage-S screen first and report before the
larger Stage-C capture; honor the §11 kill conditions; the agent does NOT stop the pod
(user stops it). Still pending before capture: build the in-band candidate prompt bank
(no-GPU) and set up the bare pod (env pins + upload kit/probe/scripts, verify shas).

---

## 2026-10-25T02:57Z — Typed-Probe v5 Stage S authorization

DECISION: Record the owner’s GO for Stage S only under the frozen v5 preregistration; no AWS run starts until the required judge panel is reachable within the frozen cost rules.
AUTHORIZED: yes
RATIFIED-BY: user + codex
CONTEXT: `docs/working/agent_exchange/codex_audit.md` (2026-10-25T02:57Z review); `docs/working/typed_probe_gate_prereg_v5_safe_handling_20261025.md` (SHA-256 `c3049fbf65565cf062fdddafd91200b96a2c7fbbd3eed7daaeb513900b5e7132`).

Owner GO: GO.

Scope: Stage S behavior-only screen only, within the frozen `us-west-2`, `g5.2xlarge`, 90-minute-per-stage, storage, cleanup, and US$5.00 total AWS limits. The named judge panel and other preregistered checks remain required. Stage C must wait until Wakil labels the 30 calibration examples and at least 24/30 exactly match the frozen panel. This entry is authorization, not a run receipt; Stage S has not started.

---