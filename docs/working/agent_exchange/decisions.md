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
