# Codex Onboarding — read this before doing anything (2026-05-14)

**Audience:** a fresh Codex instance picking up Noetic Compass / CAS-Native work.

**Why this exists:** Wakil + the prior Codex thread + Claude have shipped substantial work over the last two weeks (Atlas v0, SGGS Phase 1, Mode 7 mechanistic alignment, Stage 3 chat REPL, Step 5B NL bridge). A fresh agent that doesn't know what already exists will burn money, time, and fragile invariants. Read every section before you propose anything.

---

## 1. Project identity (one paragraph)

Noetic Compass is an AI psychology + ethics assessment platform built on the Cognitive Architecture System (CAS) v7.7 framework. The shipping artifact has three layers: (1) **CAS-Native AI** — Python+PyTorch models that produce structured CAS expressions and natural language conditioned on CAS state; (2) **API surface** — FastAPI backend that serves model traces, idea-atlas operations, mode7 mechanistic streams, etc.; (3) **Dashboard** — React 19 + Vite + Tailwind 4 + Three.js viewer at noeticcompass.com that renders trace JSON as visible thought trees in both 2D SVG (`TRACE`) and 3D Three.js (`TRACE 3D`) modes. Authoritative reference is `CLAUDE.md` at the repo root.

---

## 2. Current state of the world (2026-05-14)

### What's live and demoable

- **Frontend on Vercel** at `https://noeticcompass.com` — fresh prod deploy of commit `34550f3`. Trace 2D + Trace 3D tabs render Atlas v0 traces; complex Θ-recipe demo card walks through the full CAS surface.
- **Stage 3 CAS-Native checkpoint** at `D:\tksCAS-archive\stage_e3_20260513T043823Z\ckpt_final.pt` — 0.78 dev / 0.64 held-out free-decode identifier recovery, 0 cross-emission. Loader: `cas_native.inference.stage3_local_loader.load_stage3_local()`. This is the canonical "good CAS-Native checkpoint" for the structural-prediction lineage.

### What's broken right now

- **Railway trial expired.** Backend at `noeticcompass.com/api/*` has been running the **April 27** image; nothing has actually deployed there in 2+ weeks despite git pushes. The user's debit card is prepaid → Railway rejects it for subscriptions. Two paths under discussion:
  - **Downgrade Railway to serverless free tier** (sleeps on idle; may or may not require card on file)
  - **Migrate to Render Starter ($7/mo)** — debit card accepted; standard bank debit works. Repo Dockerfile (`noetic-compass-scaffold/noetic-compass/Dockerfile.api`) is drop-in ready.
  - Status: **user is mid-decision**. Do NOT trigger any deploy or backend migration yourself without checking `inbox_claude.md` for a decision update.

### What's in flight (don't conflict)

- **Lane A — conversational dialogue training run** (Codex's own active plan as of 2026-05-13):
  - From-scratch random-init training on `cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_*.jsonl`
  - Target output: `cas-native/training/runs/native_nl_full_50k_20260514/`
  - Trainer code: commit `4787c2d`
  - `--use-cas-prefix` enabled
  - **Do NOT resume from B3** (`b3_full_50k_prodshape_20260507/`) — its manifest pins `use_cas_prefix=false` which is incompatible with the new architecture.
  - **Do NOT resume from Stage 3** (`stage_e3_20260513T043823Z/`) — different architecture (simplex MVP, not dialogue decoder).

### Latest commits on master (HEAD-down)

```
4787c2d  cas-native: normalize manifest shard paths
2ec2b5a  cas-native: train NL from sharded manifest
e367255  mode7: report CAS Native runtime readiness
e4ee84d  mode7: include CAS Native trace runtime modules
4e69e28  mode7: wire CAS Native live trace runtime
68d622c  feat: add Mode 7 live graph stream
34550f3  fix: align Mode 7 with mechanistic attribution     ← deployed to Vercel
```

---

## 3. The two CAS-Native lineages (do NOT conflate)

There are TWO parallel CAS-Native training tracks. They are NOT the same model. Confusing them will cause you to propose incompatible checkpoint resumes.

### Lineage 1 — Structured-prediction (CAS↔English)

- **Architecture:** Simplex MVP encoder/decoder with scheduled-sampling (E3 ablation path), `cas_prefix_mask`, copy-distribution heads.
- **Canonical checkpoint:** `D:\tksCAS-archive\stage_e3_20260513T043823Z\ckpt_final.pt` (sha `5ac364e78419ec8591d25120ce9314f87d2c816467fcf9875802d3d831903a88`).
- **Powers:** the `cas chat-stage3` REPL, Atlas v0 trace generation, the `traceability_v0` JSON schema, the chat REPL's plain-English + technical-detail rendering, NL→CAS heuristic bridge.
- **Gate scores:** 0.78 dev / 0.64 held-out free-decode identifier recovery, 0 cross-emission.
- **Status:** Shipped. Demoable. This is what the Atlas v0 tabs render.

### Lineage 2 — Conversational dialogue (Lane A)

- **Architecture:** B3-style native NL gen + cas_prefix conditioning.
- **Prior attempt:** B3 (`b3_full_50k_prodshape_20260507/`). Falsified on broader eval 2026-05-12 per memory `project_b3_broader_eval_falsified_2026_05_12.md`.
- **Active iteration:** Lane A — Codex's own active plan; random-init, fresh training run.
- **Status:** Not yet trained. No usable artifact today.

### "Most advanced CAS-Native"?

- Most advanced *structural-prediction* checkpoint today: **Stage 3 (Lineage 1)**.
- Most advanced *conversational-dialogue* checkpoint today: **nothing** — B3 falsified, Lane A not yet trained.

---

## 4. Hard rules — non-negotiable

These are extracted from user memory and lock-in entries. Violating any of them has cost real time in this project. Do not propose work that breaks them.

### Anti-recidivism (do not repeat falsified levers)

- **No more EOS bias / first-n masking / aux heads / extra epoch.** v1e exhausted these; phase C kill-switch tripped (24-pack 18/24 → 12/24 with truncations + stage-var stalling). Memory: `project_v1e_killswitch_tripped_simplex_pivot_2026_05_11.md`.
- **B3 strategy was falsified.** Don't resurrect Stage 7-bis or propose more B3-shaped runs. Lane A is the next iteration and is already planned correctly.
- **Don't propose CAS-CLM as prompt encoder.** Modality mismatch confirmed. Memory: `project_cas_transformer_modality_mismatch_pivot.md`.

### Foreign-model architecture rule

- **No foreign pretrained models in production stack.** No TinyLlama / Llama / Qwen / Mistral / Phi / Gemma / GPT-2 / BERT. Generation head built from scratch. Memory: `feedback_no_foreign_architecture_cas_only.md`.
- **No foreign-model distillation as CAS supervision.** Style priors only, with sample-read audits. Memory: `feedback_cas_native_data_strategy_2026_05_13.md`.

### Traceability rules

- **Traceability is the whole purpose.** Every output walks back to its origin: input → CAS → activations → attribution → admissibility → output. Memory: `feedback_traceability_is_the_whole_purpose.md`.
- **Object traceability required.** Every domain object carries `id + created_at + version + parent_ids + source + trace_id`. Memory: `feedback_object_traceability_required.md`.
- **Mode 7 = Network Attribution / Mechanistic Trace.** It is NOT "the live tree." The Living Thought Atlas is the SGGS witness viewport that renders Mode 7 traces. Don't conflate these (Codex audit 34550f3 explicitly aligned this). Schema version `mode_7_trace.v1`.

### Evaluation rules

- **Sample-level outcomes are the only true eval signal.** Aggregate stats can lie. Memory: `feedback_samples_are_the_only_true_eval_for_cas_native.md` + `feedback_real_metric_is_samples.md`.
- **5-layer eval required:** Loss → sample quality → CAS silence (no jargon leak) → CAS grounding (round-trip via K=9) → traceability. Memory: `feedback_cas_native_5_layer_eval.md`.
- **Compile rate is a separate eval layer.** Round-trip K=9 measures state preservation, not expression validity. Memory: `feedback_audit_only_after_automated_checks.md`.
- **Always restore baseline hparams for full retrains.** Smoke defaults regress 49.5%→34.0% canonical. ALWAYS pass `--lr 0.001 --batch-size 128 --weight-decay 0.0001` for full `train_structured_prediction.py` runs. Memory: `feedback_always_restore_baseline_hparams_for_full_retrains.md`.
- **Eval-file-slip is a recurring bug.** Always grep for `_v77_relabeled` before launching any train/eval run. Memory: `feedback_eval_file_slip_recurrent.md`.
- **`train_structured_prediction.py` defaults `--limit` to 128.** Always pass `--limit 100000` for full runs. Memory: `feedback_limit_default_128_trap.md`.
- **Underfit > overfit.** Default training to 2-3 epochs not 5+. Sample-read after every epoch. Memory: `feedback_cas_native_underfit_over_overfit_short_epochs.md`.
- **Audit corpus shape BEFORE proposing reuse.** Line counts ≠ data quality. Memory: `feedback_audit_corpus_before_proposing_reuse.md`.

### Engineering hygiene

- **Push immediately after every commit.** Not at end of session. Memory: `feedback_push_immediately_after_commit.md`.
- **Back up successful runs immediately.** Three independent sha256 confirmations to `D:\tksCAS-archive\<run_dir>\`. Memory: `feedback_back_up_successful_runs_imperative.md`.
- **GPU for real training, not CPU.** Forward passes through pretrained backbones with > 1K steps → cloud GPU. Memory: `feedback_gpu_vs_cpu_for_real_training_runs.md`.
- **Train_progress logging required.** Every training script with an inner batch loop emits `train_progress` JSON at batches 1/3/5/N. Memory: `feedback_train_progress_logging_required.md`.
- **PYTHONFAULTHANDLER=1 alone is not enough for SIGQUIT safety.** Must call `faulthandler.register(signal.SIGQUIT, ...)` explicitly. Memory: `feedback_pythonfaulthandler_does_not_make_sigquit_safe.md`.
- **Canary cost dominates short runs.** Default `--sample-canary-at <final_step>` only for `n_steps ≤ 1000`. Memory: `feedback_canary_cost_dominates_short_runs.md`.
- **Parallelize SDG with training.** CPU-bound SDG + GPU-bound training have no resource conflict. Memory: `feedback_parallelize_sdg_with_training.md`.

### Communication rules

- **Plain language, no jargon.** Define inline. No "load-bearing" / "modality mismatch" / "structured-prediction" without translation. Memory: `feedback_plain_language_no_jargon.md`.
- **Separate evidence levels in every status.** Distinguish wired / works / sample-looked-good / gate-passed / prototype / validated. Memory: `feedback_separate_evidence_levels_in_status.md`.
- **Gemini citations need verification before acting.** Memory: `feedback_gemini_citations_need_verification.md`.
- **Default Gemini model is `gemini-3.1-pro-preview`.** Memory: `feedback_gemini_default_model.md`.
- **Anti-drift gates ≠ content-preservation gates.** Both required for Path D promotion. Memory: `feedback_anti_drift_gates_not_content_preservation.md`.

---

## 5. Agent-exchange protocol (how to communicate)

Files in `docs/working/agent_exchange/`:

- **`inbox_claude.md`** — Claude → Codex notifications. Codex reads to know what Claude shipped. Claude appends after every meaningful unit of work.
- **`codex_audit.md`** — Codex → Claude audit results. Codex appends after every audit. Claude reads to know what Codex flagged.
- **`decisions.md`** — `AUTHORIZED: yes` entries gating expensive work (pod runs, multi-hour training, IP-affecting changes). Both write; neither launches without an `AUTHORIZED: yes` ratified by user chat "go".
- **`heartbeat.md`** — liveness signals.
- **`poll_log_*.md`** — read-state tracking.

### Dual-gate AUTHORIZED protocol

Pod launches and other expensive operations require BOTH:
1. `AUTHORIZED: yes` in `decisions.md` with explicit scope.
2. User chat "go" — direct typed approval.

Both required. Memory: `feedback_agent_exchange_file_protocol.md`.

### What to write where

- **Shipped code** → commit message + `inbox_claude.md` entry pointing at the commit hash.
- **Audit of someone else's commit** → `codex_audit.md` entry naming the commit hash + verdict (PASS / PASS WITH PATCHES / FAIL).
- **Proposing a multi-hour or money-spending operation** → `decisions.md` entry with `AUTHORIZED: pending` + explicit scope, wait for user chat "go".

---

## 6. Atlas v0 + SGGS — what's shipped

### Atlas v0 (commit `f5c053d` + patches)

- TRACE tab in `IdeaAtlasPage.tsx` (`ViewMode='trace'`)
- 2D SVG renderer: `dashboard/src/components/idea-atlas/ThoughtTreeView.tsx`
- TS schema validator: `dashboard/src/lib/trace.ts` (per-node id + node_key + kind + role + label + normalized_label; per-edge keys + dangling-edge rejection; schema_version match)
- TraceLoader: file-picker, drag-drop, URL `?trace=` param, bundled DEMO_TRACE + DEMO_TRACE_COMPLEX (14-node Θ recipe)
- CLI: `cas atlas-save` saves traces to `~/.cas_atlas/traces/`
- Tests: 34/34 dashboard vitest, including end-to-end smoke against committed fixture

### SGGS Phase 1 (commits `e5c6547` + `4253c2b` + patches)

- TRACE 3D tab (`ViewMode='sggs'`)
- Three.js scene: `dashboard/src/components/idea-atlas/SggsScene.tsx` (901 lines)
- React.lazy boundary so the ~600 KB three+sprite bundle code-splits
- Glow halos (always-on), pulse on selected card, ambient float (3.2 s sine, per-card phase offset), damped bounce on click, fullscreen toggle, color-key overlay
- MediaPipe Hands gesture spike (NOT yet wired into the live TRACE 3D tab): `sggs_hands.ts`, `sggs_gestures.ts`, `HandsPanel.tsx`. Privacy copy: "Video stays on this machine. No camera frames are uploaded. MediaPipe model files may load from a CDN on first use unless self-hosted."
- SSE streaming: `cas-native/inference/sggs_stream.py` + `dashboard/src/lib/sggs_stream.ts` (Last-Event-ID resume, strict per-kind validator, 17 pytest + 36 vitest tests)
- ErrorBoundary: `SggsErrorBoundary.tsx` (rose-themed fallback for WebGL init failure / unsupported / chunk load failure / runtime errors)
- Tests: 58/58 SGGS vitest
- SGGS Phase 2 (live witnessing + rewind) NOT YET BUILT. Plan doc: `docs/working/sggs_v0_implementation_plan_2026_05_13.md`.

### Mode 7 alignment (commit `34550f3`)

- `/mode7/live` SSE route emits head_commits carrying mechanistic axis_attrs:
  - `mode7_semantics.mode === 7`, `.name === "Network Attribution / Mechanistic Trace"`
  - `activation_hooks` (with `hook_status`)
  - `activation_layers` (non-empty)
  - `per_head_attribution` (noetic/domain/drive/register heads, each with `top_tokens`)
  - `load_bearing_tokens`
  - `logits_summary` (per-head logit counts)
  - `copy_distribution_summary` (with coverage)
  - `domain_descent_attention` (applicable / selected_domain / observed_domains)
  - `structural_commit_linkage`
- Tests: 3 pytest in `tests/test_mode7.py` pinning the full contract
- TS selectors: `selectMode7ActivationLayers`, `selectMode7AttentionHeads`, `selectMode7LoadBearingTokens`, `selectMode7LogitsCopySummary`, `selectMode7MechanisticTrace`, `selectMode7StructuralCommitLinkage`, `selectMode7AxisPayload`, `hasMode7MechanisticAxisAttrs`
- UI: `Mode7LiveShell.tsx` renders Mode 3 Symbolic Trail side-by-side with Mode 7 Mechanistic Trail
- Compiler page also exposes Mode 7 view

---

## 7. What's queued in user-locked plans

### v1 Step ordering (Path C + Path D, locked 2026-05-07)

8-step execution order with 7-dim user-facing eval gate + 9-check structural preservation. Doc split (Path C arch / Path D curriculum). Slogan: "Fluency last. Object preservation first."

### Path D Wave 3 (currently in progress)

NL annotation pipeline — Claude API budget needed. Last promoted state: Wave 2.5 SFE-gated 5,268 cas_to_english records (commit `96ec022`).

### Stage 4 NL Front Door Training Spec

Doc only at `docs/working/stage4_minimal_nl_training_spec_2026_05_13.md`. 4 curriculum tasks, 3-tier data hierarchy, $1–500 v0 cost band. **NOT a training launch.** Separate AUTHORIZED entry required before any pod work.

### SGGS roadmap

- **Phase 1** (baseline 3D viz): shipped Atlas v0 + SGGS scaffolding.
- **Phase 2** (live witnessing + rewind): NOT BUILT. Streaming protocol skeleton exists; needs (a) ViewMode='mode7live' tab to consume the stream and grow cards in real-time, (b) timeline scrubber UI, (c) actual inference server hookup beyond the demo CLI.
- **Phase 3** (counterfactuals, persistent storage, mobile/tablet, VR/AR): explicitly deferred.

### Living Thought Atlas (the FLAGSHIP)

Memory `project_living_thought_atlas_flagship_2026_05_13.md`. Infinite space, omnidirectional spin, replay/slow-motion, Inversion Replay (flip CAS axis → ghost branch), zoom token→atlas. The "I get it" layer for non-ML stakeholders. The Atlas IS the SGGS witness viewport where commits appear live — Mode 7 is what populates the cards with mechanistic detail.

---

## 8. What NOT to propose

Concrete things that have already been tried, decided against, or that conflict with active commitments:

1. Resuming Lane A from any prior checkpoint. Random init is correct.
2. Mode 7 = "the live tree." Wrong. Mode 7 = mechanistic. Living Thought Atlas = the live viewport.
3. SGGS-as-prompt-encoder.
4. Foreign-model distillation as CAS supervision.
5. More v1e levers (EOS bias / first-n / aux heads / extra epoch).
6. Stage 7-bis or any B3-shape resurrection.
7. CAS-CLM as the NL encoder.
8. Force-directed graph in TRACE 3D v0. Hierarchical extrusion is the v0 choice; force-directed is Phase 1 W2-3 work (not now).
9. Mocking the database in integration tests. Memory feedback: prior incident on prod migration.
10. Skipping `git push` after commit.
11. Treating Stage 4 spec as a launch authorization. It's a spec doc only.

---

## 9. Tech stack quick reference

- **Backend**: Python 3.12, FastAPI, uvicorn, pytest. Lives in `noetic-compass-scaffold/noetic-compass/api/`. Dockerfile at `noetic-compass-scaffold/noetic-compass/Dockerfile.api`.
- **CAS-Native model code**: PyTorch 2.x, Python. Lives in `noetic-compass-scaffold/noetic-compass/cas-native/`.
- **CAS engine (Rust)**: `noetic-compass-scaffold/noetic-compass/cas-engine/` — built via maturin in Dockerfile.api.
- **Frontend**: React 19 + TypeScript 6 + Vite 8 + Tailwind 4 + Three.js 0.171 + MediaPipe Hands. Lives in `noetic-compass-scaffold/noetic-compass/dashboard/`.
- **Deployment**:
  - Frontend → Vercel (live at noeticcompass.com)
  - Backend → Railway (CURRENTLY BROKEN, see §2)

---

## 10. What to do first when you start work

1. Read this doc end-to-end.
2. `git pull` and `git log --oneline master | head -20` to see what's landed since this doc was written.
3. Read `docs/working/agent_exchange/inbox_claude.md` (last 200 lines) to see what Claude has shipped.
4. Read `docs/working/agent_exchange/decisions.md` (last 200 lines) to see AUTHORIZED entries.
5. Read `docs/working/agent_exchange/codex_audit.md` (last 200 lines) to see prior Codex audits — including your prior instance's audits. Pay particular attention to any "PASS WITH PATCH BLOCKERS" entries that may not be resolved.
6. Check whether the backend deploy issue (§2) has been resolved. If not, do not propose changes that depend on the production backend being current.
7. Check whether Lane A has actually launched. If yes, do not propose changes to its trainer config; if no, audit the launch command flag-by-flag against this doc + against `feedback_always_restore_baseline_hparams_for_full_retrains.md`.

---

## 11. Quick-reference paths

| Thing | Path |
|---|---|
| Project root | `C:\Users\wakil\OneDrive\Desktop\tksCAS\` |
| CAS framework reference (READ FIRST for any CAS work) | `CLAUDE.md`, `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` |
| Stage 3 checkpoint | `D:\tksCAS-archive\stage_e3_20260513T043823Z\ckpt_final.pt` |
| Stage 3 loader | `noetic-compass-scaffold/noetic-compass/cas-native/inference/stage3_local_loader.py` |
| Atlas v0 design | `docs/working/atlas_v0_thought_tree_viewer_design_2026_05_13.md` |
| SGGS plan | `docs/working/sggs_v0_implementation_plan_2026_05_13.md` |
| Mode 7 design | `docs/working/mode_7_traceability_design_2026_05_13.md` |
| Traceability v0 schema (Python) | `noetic-compass-scaffold/noetic-compass/cas-native/inference/traceability_v0.py` |
| Traceability v0 schema (TS) | `noetic-compass-scaffold/noetic-compass/dashboard/src/lib/trace.ts` |
| SGGS stream protocol spec | `docs/working/sggs_stream_protocol_2026_05_13.md` |
| Stage 4 NL spec (DOC ONLY) | `docs/working/stage4_minimal_nl_training_spec_2026_05_13.md` |
| Compiler grammar | `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` |
| User memory index | `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\MEMORY.md` |

---

## 12. One-line summary

**Lane A from scratch is correct. Stage 3 simplex is the canonical structural-prediction checkpoint and is incompatible as a Lane A warm-start. Mode 7 = mechanistic, not the live tree. Living Thought Atlas = the SGGS witness viewport. Don't conflate the two. Read `MEMORY.md` before proposing anything expensive.**
