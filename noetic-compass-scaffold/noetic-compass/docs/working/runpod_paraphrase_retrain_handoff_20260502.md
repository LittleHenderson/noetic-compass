# RunPod Paraphrase Retrain Handoff - 2026-05-02

Purpose: live continuation log for the structured-token retrain with deterministic training paraphrases and the v7.7 Rule-4 / Omega overlap fix.

## Current Objective

Run a new GPU structured-token prediction baseline with:

- Training data relabeled by `cas-synthetic/scripts/relabel_v77_overlap.py`.
- `--paraphrase-augment-train 3`.
- Hyperparameters matched to the prior 20-epoch structured-token GPU baseline where possible.

Targets to beat:

- Canonical eval: 85.1% all-heads exact on current unique eval.
- Paraphrase eval: 37.2% all-heads exact / 44.4% prediction consistency.
- Hash baseline: 48.7% all-heads exact.

## Verified Local State

- Repo root: `C:\Users\wakil\OneDrive\Desktop\tksCAS`.
- HEAD verified: `a1b2f55 cas-synthetic: fix v77_rule_four / v77_omega structural overlap`.
- Recent commits verified:
  - `a1b2f55` v77 Rule-4 / Omega structural-overlap fix.
  - `74996a9` deterministic paraphrase augmentation in training.
  - `b2de74a` `eval_token_provenance` manifest block.
  - `a2ce9de` lexicon coverage diagnostic/report.
  - `b03a123` Wave 2-A Phase 1A lexicon expansion.
- Lexicon row count verified: `191`.
- Required train/eval data exists locally:
  - `cas-synthetic/data/level3_pilot_full.jsonl` - 57,994,413 bytes.
  - `cas-synthetic/data/level3_pilot_1k_tmp.jsonl` - 5,779,267 bytes.
  - `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl` - 2,267,939 bytes.
- Verification test run:
  - Command: `python -m pytest cas-synthetic/tests/test_v77_rule_four_generator.py cas-synthetic/tests/test_v77_rule_four_no_emergent_overlap.py -q`
  - Result: `13 passed`.
- `--paraphrase-augment-train` verified in `cas-native/training/train_structured_prediction.py`.

## Dirty Worktree Note

The repo has many unrelated modified/untracked files from prior work. Do not revert them. For this retrain, keep edits scoped to this handoff log and any explicit run artifacts.

## RunPod Connection

From prior handoff:

```powershell
ssh -i ~/.ssh/id_ed25519 -p 18933 root@135.84.176.142
```

Expected pod state:

- NVIDIA RTX A6000, 49,140 MiB.
- `/workspace/` initially empty.
- No repo/checkpoints present yet.

## Next Steps

1. Confirm SSH access and GPU state.
2. Transfer repo + needed data to `/workspace/tksCAS`.
3. Run `cas-synthetic/scripts/relabel_v77_overlap.py` on `cas-synthetic/data/level3_pilot_full.jsonl` on the pod before training.
4. Run structured-token training with `--paraphrase-augment-train 3` and baseline-compatible hyperparameters.
5. Evaluate canonical and paraphrase results with existing eval scripts.
6. Record exact commands, run paths, metrics, and blockers below.

## Live Log

- 2026-05-02: Local verification completed. No pod changes made yet.
- 2026-05-02 08:01 RunPod SSH verified. `nvidia-smi` showed NVIDIA RTX A6000, 49,140 MiB, 0% GPU util, no running processes.
- 2026-05-02 08:07 Transport completed with clean `git archive` snapshot plus explicit JSONL files. Remote repo path is `/workspace/tksCAS`.
- 2026-05-02 08:10 Remote environment verified: Python 3.11.11, Torch 2.5.1 installed. Remote data sizes: full train 56M, 1K train 5.6M, held-out eval 2.2M.
- 2026-05-02 08:14 Relabel completed on pod:
  - Command: `python3 /workspace/tksCAS/cas-synthetic/scripts/relabel_v77_overlap.py --in /workspace/tksCAS/cas-synthetic/data/level3_pilot_full.jsonl --out /workspace/tksCAS/cas-synthetic/data/level3_pilot_full_v77_relabeled.jsonl`
  - Counts: `n_total=29181`, `n_relabeled_to_v77_omega=1797`, `n_v77_rule_four_input=3681`, `n_v77_rule_four_remaining=1884`.
  - Idempotence dry-run on relabeled file: `n_relabeled_to_v77_omega=0`.
  - Original and relabeled line counts both `29181`.
- 2026-05-02 08:17 Training launched on pod as PID `5370`.
  - Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-paraphrase-v77fix-20epoch-gpu-20260502-0815`.
  - Log: `.../structured-token-paraphrase-v77fix-20epoch-gpu-20260502-0815/train.log`.
  - Command shape: direct file-path invocation of `train_structured_prediction.py`; module invocation failed because `cas_native` is created by the file-path shim.
  - Hparams: `--input-mode structured_token --epochs 20 --batch-size 128 --d-model 128 --bottleneck-dim 64 --lr 0.001 --weight-decay 0.0001 --device cuda --seed 42 --max-length 256 --vocab-min-count 1 --paraphrase-augment-train 3 --limit 100000`.
  - Startup log: `n_canonical=24855`, `n_train=99420`, `paraphrase_variants_per_record=3`, stage `tokenize_train`.
  - Non-fatal warning observed: Torch reports NumPy is not installed.
- 2026-05-02 08:26 Startup tokenization complete. `vocab_size=1931`; eval tokenization complete; model initialized. GPU memory allocated at ~666 MiB.
- 2026-05-02 08:45 Training process still running. `ps` shows PID `5370`, elapsed `27:22`, CPU ~100%, memory ~0.7%. Run dir still only has `train.log` because manifest/checkpoints are written at the end. Note: epoch/eval `print()` calls in the training loop do not use `flush=True`, so redirected stdout may not show epoch progress until the buffer flushes or the process exits.
- 2026-05-02 08:57 Training process still running. `ps` shows PID `5370`, elapsed `39:30`, CPU ~100%, memory ~0.7%. GPU memory still ~666 MiB, util ~11-14%. No `manifest.json` yet. Keep waiting unless a later owner intentionally chooses to abort/restart with different hparams.
- 2026-05-02 09:19 Training process still running. `ps` shows PID `5370`, elapsed `01:02:03`, CPU time `01:02:06`, CPU ~100%, memory ~0.7%. GPU memory ~666 MiB, util ~12%. No completion artifacts yet.
- 2026-05-02 09:35 Training process still running. `ps` shows PID `5370`, elapsed `01:17:43`, CPU time `01:17:47`, CPU ~100%, memory ~0.7%. GPU memory ~666 MiB, util ~12%. Still no `manifest.json`; continue waiting for the comparable 20-epoch run unless it becomes clearly impractical.
- 2026-05-02 09:50 Training process still running. `ps` shows PID `5370`, elapsed `01:33:12`, CPU time `01:33:15`, CPU ~100%, memory ~0.7%. GPU memory ~666 MiB, util ~12%. No artifacts beyond `train.log`.
- 2026-05-02 10:07 Training process still running. `ps` shows PID `5370`, elapsed `01:51:44`, CPU time `01:51:48`, CPU ~100%, memory ~0.7%. GPU memory ~666 MiB, util ~14%. No artifacts beyond `train.log`.
- 2026-05-02 10:13 Paraphrase-augmented 20-epoch run completed and failed:
  - Final canonical eval: `14/1000 = 0.014`.
  - Best epoch was epoch 5 at `14/1000`; all epochs were `0.004-0.014`.
  - Final predictions mostly collapsed to `expression_family=meta_logic`, `transition_kind=meta_logic_move`.
  - Training distribution after eval-overlap filter was not meta-logic-skewed (`v75_register=6498`, `v77_omega=5211`, `v74_baseline=4722`, `v77_rule_four=3255`, `v76_production=2676`, `meta_logic=2493` before augmentation).
  - Root cause found later: this run used the wrong input corpus, `cas-synthetic/data/level3_pilot_full.jsonl`, which is conversational/free-form. It is not the recoverable slot-reading corpus that produced the 85% structured-token win.
- 2026-05-02 10:32 No-augmentation control launched on the same wrong corpus as PID `6146`; by epoch 5 it was still only `1/1000`, confirming the corpus was the problem. PID `6146` was stopped after the diagnosis.
- 2026-05-02 10:40 Correct training corpus found locally: `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`.
  - Verified local line count: `19454`.
  - This file is explicitly named in the prior 85.3% run report as the training set.
  - First rows contain `families:` recoverable slot readings, unlike the conversational `level3_pilot_full.jsonl`.
- 2026-05-02 10:43 Correct corpus transferred to pod and verified: `19454` lines, `42M`.
- 2026-05-02 10:44 Correct corpus relabeled on pod:
  - Input: `/workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`.
  - Output: `/workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl`.
  - Counts: `n_total=19454`, `n_relabeled_to_v77_omega=1198`, `n_v77_rule_four_input=2454`, `n_v77_rule_four_remaining=1256`.
- 2026-05-02 10:52 Correct-corpus paraphrase run launched as PID `6442`.
  - Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`.
  - Input: `/workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl`.
  - Hparams: same as prior 20-epoch structured-token baseline plus `--paraphrase-augment-train 3`, with `python3 -u` for unbuffered logging.
  - Startup: `n_canonical=16570`, `n_train=66280`, `vocab_size=293`.
- 2026-05-02 11:14 Correct-corpus paraphrase run reached epoch 0 eval: `450/1000 = 0.45`; training is healthy. Earlier 1.4% failure is confirmed to be wrong-corpus, not model/code.
- 2026-05-02 11:46 Correct-corpus paraphrase run reached epoch 4 eval: `826/1000 = 0.826`; near prior canonical baseline while carrying relabel + augmentation.
- 2026-05-02 12:58 Correct-corpus paraphrase run reached epoch 13; best so far is epoch 10 at `868/1000 = 0.868`, beating prior current-eval checkpoint `851/1000 = 0.851`.
- 2026-05-02 13:51 Correct-corpus paraphrase run completed. Final manifest uses best epoch 10: `868/1000 = 0.868`, +1.7 pp over prior current-eval checkpoint and +38.1 pp over hash.
- 2026-05-02 14:55 Local artifact pull completed; GPU confirmed idle.
- 2026-05-02 14:56 Local eval diagnostics completed:
  - Canonical confusion report: `current_unique_eval_confusion.md`, all-heads exact `868/1000`.
  - Paraphrase report: `paraphrase_current_eval_report.md`.
  - Paraphrase all-heads exact: `0.413` (was `0.372`).
  - Prediction consistency vs canonical: `0.484` (was `0.444`).
  - Canonical-exact retention: `0.467` (was `0.424`).
- 2026-05-02 15:00 Added run report `STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md` and Session 48 changelog entry.

Monitoring commands:

```bash
ssh -i ~/.ssh/id_ed25519 -p 18933 root@135.84.176.142 ps -p 5370 -o pid,etime,pcpu,pmem,cmd
ssh -i ~/.ssh/id_ed25519 -p 18933 root@135.84.176.142 nvidia-smi
ssh -i ~/.ssh/id_ed25519 -p 18933 root@135.84.176.142 ls -lh /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-paraphrase-v77fix-20epoch-gpu-20260502-0815
ssh -i ~/.ssh/id_ed25519 -p 18933 root@135.84.176.142 tail -n 120 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-paraphrase-v77fix-20epoch-gpu-20260502-0815/train.log
```
