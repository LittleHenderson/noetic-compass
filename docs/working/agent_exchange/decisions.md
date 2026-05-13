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
