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
