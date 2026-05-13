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

## 2026-05-12T17Z — Candidate E Stage 2c primary gate

DECISION: At `--stage e2c`, ONLY `tf_per_token_accuracy ≥ 0.70` is load-bearing. swap pair_pass_rate and TF identifier_recovery_rate are reported as informational diagnostics; they cannot fail the e2c run.

AUTHORIZED: yes

RATIFIED-BY: user + codex (audit verdict 2026-05-12 + user confirm "Launch")

CONTEXT: docs/working/candidate_e/stage2_launch_lock_2026_05_12.md §E2c evaluator section. Code: `evaluate_candidate_e_stage2.py` lines 869-878 (`if args.stage == "e2c": overall_pass = tf_per_token_gate_pass`). Tests pinned: `test_e2c_gate_only_per_token_load_bearing`, `test_e2b_gate_still_requires_both`.

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
