# HANDOFF TO CLAUDE — Bridge stance-matched non-CAS prefix control (spec sheet frontier #16)

Written 2026-08-23 ~21:45Z. Everything below is verified fact. Read it all before acting.

## 0. Status at handoff

**Attempt 4 FAILED (accelerate missing — see §6 item 6) and is terminating.** Attempt 5 is YOURS to launch with `bootstrap_userdata.sh` **v5** (adds `accelerate`). The bundle on S3 is already v5.

Live evidence:
- job log: `s3://cas-harness-runpod-92754088/bridge-control-20260822/logs/job.log`
- results land at: `s3://cas-harness-runpod-92754088/bridge-control-20260822/results/bridge_control_results_20260822.json`
- local live console (optional): `C:\Users\wakil\OneDrive\Desktop\CAS-Run-Dashboard\` — `serve.py` (127.0.0.1:8765) + `status_feed.py` (writes status.json every 15s from S3+EC2).

If the instance is already terminated when you start: fetch the results object FIRST and adjudicate (§5) — never relaunch before checking it.

## 1. What this experiment is

The missing control for Cap. 2's η→ε bridge: does a **non-CAS plain-English prefix carrying the same content** shift next-token likelihoods as much as the CAS readable prefix? Runs on the frozen 80-case 40E fixture (the May 2026 H100 run's exact cases), GPT-NeoX-20B fp16, conditions none / cas_probe / ctrl_probe / cas_gold / ctrl_gold / cas_raw × correct-vs-partner continuations.

Pre-registered verdict (PREREG §5 — FROZEN, never edit):
- C1: ctrl_probe delta-vs-none mean > 0 (else `CONTROL_ARM_INVALID_C1`)
- C2: mean(cas_probe delta) − mean(ctrl_probe delta), paired exact sign test p ≤ 0.05
  - ≥ +0.10 & p ≤ 0.05 → `CAS_FRAMING_ADDS_BEYOND_CONTENT`
  - ≤ −0.10 & p ≤ 0.05 → `CAS_FRAMING_WORSE_THAN_PLAIN_NAMING`
  - else → `NO_DETECTABLE_FRAMING_ADVANTAGE` (the "+1.412 = fluent prefix naming the answer" reading stands; Cap. 2 stays REAL + PARTIAL)

## 2. Frozen inputs (sha256, all locally verified)

- original result JSON (80 cases): 9363F54B89122B5F2EB20954FFBE56C4447D69F68D2E8A9E1CC2E7F42F27EE2B — `D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_bridge_proof_20260528\gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json`
- scenario fixture (8,320 items): b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537 — `D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_scenarios_20260527.json`
- activation npz (4.16 GB): 5f9a14714dcad87991a04a8317119b4eeb8097af7377446e59efb1c65f428610 — same closure dir
- probe eval report: e90268444fd914f558b2244c90c9d039936fc273bdefbad266ebaf844d004030 — same closure dir

## 3. Prepared experiment files (DO NOT MODIFY — hash-pinned by the prereg)

All in `docs/working/gate2_closure/bridge_control_20260822/` (successor worktree, branch codex/cas-interpretability-successor-v2):
- `PREREG_BRIDGE_STANCE_CONTROL_20260822.md` — sha256 b23aaeb7… (contains amendments A1–A4; append amendments, never edit old ones)
- `bridge_control_fixture_20260822.json` — sha256 042ff22bf5b6ce8e9336c02bb7687b8ba75b077bb39e0fb55429cc90ec9c34cb (80 cases, control prefixes embedded)
- `run_bridge_control_20b.py` — sha256 ec85c0788a67cd40cbbe4cfd3c141c070ea335dbfc0302e42bece294bd17607c (platform-agnostic; imports worker scripts from its own dir)
- `build_control_fixture.py` — a07859e9f2258acf4d43159053968a8f85553490076aa83f4350dd7edc9a0809 (reproducible from the frozen inputs; imports the bridge script's gloss templates)

## 4. AWS execution (verified facts, 2026-08-22/23)

- Credentials: `~/.aws` default profile = `cas-g5-operator` (807562639912), us-west-2. Verified allowed: ec2:RunInstances/TerminateInstances/ModifyInstanceAttribute/DescribeInstances, ssm:SendCommand/DescribeInstanceInformation, s3:PutObject/GetObject/ListAllMyBuckets, iam:PutRolePolicy/DeleteRolePolicy/GetRole, cloudformation:DescribeStacks. No aws CLI on PATH — build a venv: `python -m venv <v>; <v>/Scripts/pip install boto3`.
- Quota L-DB2E81BA (G/VT vCPUs) = 8.0 applied — sufficient.
- Standby stack resources (all in us-west-2): launch template `lt-0521aede1946e3bd7` (pins subnet in **us-west-2b** — capacity-flaky), AMI `ami-039f004668b2adc12` (**Ubuntu 22.04 DL AMI: docker preinstalled, NVIDIA drivers, NO python3-venv, and apt is unreachable because the SG allows egress on 443 only**), security group `cas-aws-gpu-standby-v1` (sg-0562c483e0364cdab, no ingress), instance role `cas-aws-gpu-standby-v1-us-west-2` (SSM core), VPC `vpc-0df2f8cc1b9f23838`.
- Launch: direct `run_instances` (not the LT — its pinned subnet hits capacity) with: AMI above, g6e.xlarge, instance profile name above, the SG, SubnetId from a sweep of us-west-2a/c/b/d (pick default-for-AZ first; retry every ~10 min on InsufficientInstanceCapacity — capacity is genuinely flaky), 100GB gp3 encrypted EBS, DisableApiTermination=True, tag Name=cas-bridge-control-20260822, UserData = `bootstrap_userdata.sh` (base64). Working implementation: `capacity_retry.py` (reads the bootstrap file, loops AZs until launch, attaches the policy, writes launch_state.json).
- Scoped inline policy (attach right after launch; name `bridge-control-20260822` on the standby role): s3:GetObject/PutObject on `cas-harness-runpod-92754088/bridge-control-20260822/*` + ec2:DescribeInstances/ModifyInstanceAttribute/TerminateInstances on the instance ARN.
- Bundle: `bundle.zip` = worker scripts/ + runner + fixture + prereg, already on S3 at the prefix. Rebuild via `build` steps in git history or just `Compress-Archive` of the same contents.
- Monitor: `monitor_bridge_control.py` (polls state + S3 log every 45s, force-terminates at 150 min).

## 5. Adjudication + records when results exist

1. Download results, verify the embedded `fixture_sha256`/runner/verdict against this doc.
2. Compute C1/C2 exactly as prereg §5 (the runner already prints them; trust only after re-checking the hashes).
3. Cleanup: `iam.delete_role_policy(RoleName='cas-aws-gpu-standby-v1-us-west-2', PolicyName='bridge-control-20260822')`; confirm no running instances.
4. Archive results to `D:\tksCAS-archive\bridge_control_20260822\` (results JSON + job.log + sha256SUMS).
5. Write `RESULT_BRIDGE_STANCE_CONTROL_20260822.md` in the experiment dir with exact numbers and the verdict word.
6. **Same-commit updates** (CLAUDE.md rule 1): spec sheet §10.16 (frontier #16 status) + §11 Change Log row; `CHANGELOG.md` entry; tracker prepend. Push BOTH branches — successor `codex/cas-interpretability-successor-v2` and tksCAS `codex/cascompass-legal-live-source` (mirror the spec sheet + changelog edits there too).

## 6. Failure ledger — do NOT repeat these

1. System pip on Ubuntu 22.04 = PEP 668 blocked.
2. DL AMI has no `python3-venv`; apt unreachable (443-only egress).
3. Each `docker run --rm` is ephemeral — deps installed in one container are absent in the next. The ENTIRE pipeline (deps → model download → run) must be ONE docker session (v4 does this).
4. Role credentials take up to ~2 min to propagate after policy attach — bootstrap waits up to 5 min.
5. Attempts 1–3 produced ZERO experiment data; total infra overhead ≈ $5.85 + attempt 4 in flight. Cap every run at $4 of experiment cost; self-terminate + 2h shutdown failsafe are in the bootstrap.
6. Attempt 4: NGC 24.10 image ships no `accelerate`; `device_map="auto"` raises. **Add `accelerate` to the container pip line** (v5 does).

## 7. Never change / never claim

- Prereg criteria, control template, fixture, or runner are FROZEN. Amendments append only.
- No `ACCEPT` anywhere. Cap. 2's status changes ONLY with a hash-verified artifact and a same-commit spec-sheet edit.
- The May reference value (+1.412050) is a replication anchor, not a bar this run must beat.
