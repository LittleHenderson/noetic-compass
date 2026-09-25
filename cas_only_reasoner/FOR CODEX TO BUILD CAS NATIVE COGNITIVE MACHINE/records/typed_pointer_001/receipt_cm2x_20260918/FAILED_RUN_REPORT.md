# HELM 2x attempt failed at 2,108 of 2,940 updates

This is a failed, incomplete run, not a certified 2x result. The runtime raised `TYPED_MATCHED:PRACTICE_DEADLINE_EXCEEDED` at 12,301.5 worker seconds. The pointer worker inherited the practice helper's 12,300-second guard despite its own declared 23,100-second limit. The planned outer timeout and budget were not exhausted.

The failure delivery published these fixed pass-10 aggregates: course **502/564**, held-back **115/127**, trained **322/358**, excluded **65/79**, and development **8/59**. These are measured, not certified. Pass 20 was not produced, so this attempt cannot answer the 1x-versus-2x question. Constant LR 0.003 and seed 20260918 remain recorded.

The pass-10 checkpoint at cursor 1470 survives locally and in the retained private S3 archive. Its recorded model, optimizer, encoder, RNG identities and all 11 counters equal the historical R18 sidecar. The entire checkpoint file differs because its run identity differs. No checkpoint was deserialized here. See `../midpoint_capture_cm2x_20260918/r18_midpoint_comparison.json`.

The receiver downloaded 538 objects (187,270,971 bytes). Independent opaque byte hashing matched all 538 inventory entries. Exactly 74 of the frozen 128 required artifacts exist; 54 were not produced. The requirement remains 128. Private item-level scoring, prediction and training-log bodies were not opened and are not included in this public commit.

The original operator exited 1. AWS independently confirmed instance i-0adf52b7fa801e08b terminated, zero matching security groups, and absent worker/timer roles and instance profile. Compute cleanup is complete. The S3 evidence bucket remains retained under the existing deletion guard; storage remains active. The $19.20 reservation and $20 cap remain historical records. Actual billing is unavailable; the recorded launch-to-termination observation bounds compute alone at approximately $9.034.

No automatic retry occurred. A prospective fix must pass the intended pointer/practice deadline boundaries and helper route checks before any newly authorized attempt. The completed 33 prelaunch checks did not cover this inherited runtime guard. This closeout executes no model or tests.

Exact source, file hashes, missing-artifact count, aggregate readouts and live cleanup observation are in `failure_closeout.json`. Original receiver/lifecycle receipts remain unchanged; their measurement-complete field does not establish a completed 20-pass experiment.
