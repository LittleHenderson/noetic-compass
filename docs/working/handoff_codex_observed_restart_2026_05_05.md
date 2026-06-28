# Codex handoff - observed v1 restart - 2026-05-05

## Status

Codex took over the RunPod intervention after the prior v1 retrain stayed frozen after `model_init`.

Pod:
- SSH: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`
- Repo on pod: `/workspace/tksCAS`
- Trainer path: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py`

## Stuck run stopped

Old run dir:
- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart`

Final snapshot before termination, at `2026-05-05 15:18:36 UTC`:
- PID: `11823`
- Elapsed: `09:22:35`
- CPU/MEM: `99.8% / 6.0%`
- Last log mtime: `2026-05-05 07:21:15 UTC`
- Last event: `model_init`
- `epoch_end` count: `0`
- GPU: `NVIDIA RTX A6000, 530 MiB, 14%, 76.36 W`
- Run dir contained only `launch.log`

Action:
- Sent normal `SIGTERM`: `kill -TERM 11823`
- Waited 10 seconds.
- Process exited cleanly.
- GPU dropped to `1 MiB, 0%, ~26 W`.
- No `SIGQUIT` was used.
- No force kill was needed.

## Trainer patch

Remote original backed up before replacement:
- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py.codex_bak_20260505_1520`

Local temp patch files were created under `.codex_runpod_patch/` during the edit.
They were only a staging area for the remote patch. The durable before-state is
the remote backup listed above.

Patch scope:
- Added `import time`.
- Added structured-token trainer argument: `train_log_every_steps: int | None = None`.
- Added CLI flag: `--train-log-every-steps`.
- Added flushed JSON `train_progress` events in the structured-token inner batch loop.
- Always logs epoch 0 batch `1`, `5`, and `10`.
- Then logs every `N` batches when `--train-log-every-steps N` is set.
- Added `train_log_every_steps` to manifest config.
- Added `flush=True` to structured-token `epoch_end`; the eval print in that path is also flushed.
- No model math, optimizer, data, eval cadence, labels, or hyperparameters were changed.

`train_progress` event fields:
- `event`
- `mode`
- `epoch`
- `batch_in_epoch`
- `batches_per_epoch`
- `global_step`
- `train_loss_avg`
- `elapsed_sec`
- `batches_per_sec`
- `eta_epoch_min`

Verification:
- Local syntax check passed with `python -m py_compile .codex_runpod_patch\train_structured_prediction.py`.
- Remote syntax check passed with `python3 -m py_compile cas-native/training/train_structured_prediction.py`.
- Remote grep confirmed the flag and event are present.

## Smoke runs

Smoke 1:
- Run dir: `cas-native/training/runs/v1_progress_smoke_2026_05_05_1521`
- Limit: `128`
- Eval limit: `10`
- Epochs: `1`
- Device: `cuda`
- Result: passed, but only had 2 batches, so it could only prove batch 1 logging.

Smoke 2:
- Run dir: `cas-native/training/runs/v1_progress_smoke640_2026_05_05_1528`
- Limit: `640`
- Eval limit: `10`
- Epochs: `1`
- Device: `cuda`
- Result: passed.

Smoke 2 key log events:
- Batch 1 printed.
- Batch 5 printed.
- Batch 10 printed.
- `epoch_end` printed.
- Eval printed.

Observed smoke speed after `model_init`:
- `10` batches completed in `6.216` seconds.
- This proves the patched inner loop is observable and can move on CUDA.

## Full observed restart

New run dir:
- `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart`

Python PID:
- `14170`

Launch command, from `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass`:

```bash
PYTHONUNBUFFERED=1 python3 cas-native/training/train_structured_prediction.py \
  --input ../../cas-synthetic/data/level2_scaffold/level3_combined_v1_v77_relabeled.jsonl \
  --eval-input ../../cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --out-dir cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart \
  --input-mode structured_token \
  --epochs 20 \
  --paraphrase-augment-train 3 \
  --limit 200000 \
  --diagram-loop-pairs 0 \
  --device cuda \
  --train-log-every-steps 10
```

Latest check, at `2026-05-05 15:25:23 UTC`:
- PID `14170` alive.
- Elapsed: `01:20`.
- CPU/MEM: `100% / 0.6%`.
- Log is actively writing startup tokenization progress.
- Latest visible progress: `4000 / 555400` tokenized.
- `model_init=0`
- `train_progress=0`
- `epoch_end=0`
- GPU: `NVIDIA RTX A6000, 1 MiB, 0%, 24.62 W`

This GPU state is expected during tokenization. The diagnostic moment is after `model_init`.

Important note:
- The SSH launch command timed out locally after starting the background job.
- A follow-up SSH check confirmed the full Python process is running as PID `14170`.
- `pgrep` also showed a parent bash command from the timed-out SSH session. Do not confuse that shell with the trainer. Monitor PID `14170`.

## Next monitor command

```bash
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  "date -u; \
   ps -p 14170 -o pid,etime,pcpu,pmem,cmd; \
   tail -n 30 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart/launch.log; \
   printf 'model_init='; grep -c model_init /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart/launch.log; \
   printf 'train_progress='; grep -c train_progress /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart/launch.log; \
   printf 'epoch_end='; grep -c epoch_end /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_observed_restart/launch.log; \
   nvidia-smi --query-gpu=name,memory.used,utilization.gpu,power.draw --format=csv,noheader"
```

## Decision rules from here

If `model_init` has not appeared:
- Keep monitoring tokenization progress.
- GPU idle is normal.

If `model_init` appears:
- Expect `train_progress` batch 1, 5, and 10 soon after.
- If batch 1 appears, the old "silent epoch 0" problem is solved.
- Estimate first epoch duration from the first few `train_progress` rows.

If `model_init` appears and no `train_progress` appears within a few minutes:
- The hang is in the first batch path after model init.
- Do not wait hours.
- Stop and inspect:
  - `tokens_to_structured_token_batch`
  - `batch_targets_from_records`
  - first `model(batch, graph_batch=graph_batch)` call
  - `structured_prediction_loss`

If epoch 0 finishes:
- Eval should print immediately after `epoch_end`.
- Full artifacts still only write at normal completion:
  - `manifest.json`
  - `structured_token_vocab.json`
  - `best_structured_token_model.pt`
  - `samples.jsonl`
