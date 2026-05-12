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

## 2026-05-12T15Z — Pod launch authorization protocol

DECISION: 5-step pre-launch checklist required before every pod launch — (1) sync files, (2) MD5-verify pod vs local, (3) resolve checkpoint path, (4) verify launch flags include `--max-cas-prefix-len 192` and correct `--ablation`, (5) confirm GPU idle. Both `AUTHORIZED: yes` here AND a "launch" / "go" chat message required. Either alone is not enough.

AUTHORIZED: yes

RATIFIED-BY: user (locked across E2a, E2b, E2c launches)

CONTEXT: docs/working/candidate_e/stage2_launch_lock_2026_05_12.md pre-launch checklist. Applied at E2a (commit 8ad6a3b), E2b (commit f53baca), E2c (commit cfcbc39).

---
