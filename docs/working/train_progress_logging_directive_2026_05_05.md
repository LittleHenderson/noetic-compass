• Yes. Next run should have a lightweight training progress
  log, separate from eval.

  Do not use --eval-every-steps 5 or 10 for this. That would
  run the full eval every 5-10 batches and slow training badly.

  What should be added is something like:

  --train-log-every-steps 10

  And inside the batch loop it should print:

  {
    "event": "train_progress",
    "epoch": 0,
    "batch": 10,
    "batches_per_epoch": 8678,
    "global_step": 10,
    "train_loss_avg": 2.91,
    "elapsed_sec": 42.3,
    "batches_per_sec": 0.24,
    "eta_epoch_min": 598.0
  }

  Even better: always print batch 1, 5, 10, then every 50 or
  100 after that. That proves epoch 0 actually started without
  flooding the log.

  Copy/paste for Claude:

  For the next restart, add lightweight train progress logging.

  Do not use eval_every_steps for this.

  Add a CLI flag:
  --train-log-every-steps 10

  In the inner training batch loop, print a flushed JSON event
  named `train_progress` every N batches, plus always at batch
  1, 5, and 10 of epoch 0.

  Include:
  - epoch
  - batch number within epoch
  - total batches per epoch
  - global_step
  - running average train loss
  - elapsed seconds since epoch start
  - batches/sec
  - estimated minutes remaining in epoch

  This should not run eval and should not save checkpoints. It
  is only observability.
