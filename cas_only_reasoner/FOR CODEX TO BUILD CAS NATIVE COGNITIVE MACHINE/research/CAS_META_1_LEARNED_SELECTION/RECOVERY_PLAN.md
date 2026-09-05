# CAS-META-1 sealed evaluation recovery

Approved task ceiling: $100 total. The owner rejected further T4 use and said
"go". This recovery uses one bounded AWS g7.2xlarge job. No neural work runs on
the laptop. H100 remains unavailable under the account's current P-instance quota.

## Why a second job is needed

Source `a4dc9f2fc6f6d4f3d5e0b31100ac131327e02109` ran on a T4 in job
`cas-meta1-20260905103339-cd06685e`. All four GPU integration tests passed.
CAS training took 57.839461555 seconds and generic training took 13.099626616
seconds. Each performed 840 optimizer steps over 60 epochs. Six checkpoints and
all 360 test predictions were saved. The 2,700-second stage limit stopped native
evaluation after 72 references and 62 first-arm cases. The full comparison was
not completed. This is a timeout, not a successful learning result.

The original launch receipt records an initial cleanup failure. The separate
cleanup closure records confirmed termination and removal of job-owned compute,
volume, roles, profile, schedule, and security group. The original receipt is
not rewritten. The evidence bucket retains its seven-day expiry.

## Rules fixed before the recovery launch

- Preserve all original checkpoint bytes, selected epochs, public/private data,
  and all five arms' sealed predictions. No training or selector inference in
  recovery. Test labels do not influence a new model selection.
- Re-execute all 72 cases for all five arms, including previously completed T4
  cases. No failed case or arm leaves a denominator.
- Generate all 72 direct native references on the new GPU. Exact output-byte
  and durable-effect comparison remains unchanged. Cross-GPU reference output
  differences are reported; frozen executor weights must remain byte-identical.
- Eight spawned processes, one CPU thread per process, independent stores, and
  one GPU. Profile fixed case zero before the remaining parallel cases. This
  changes scheduling only, not the accepted executor or verifier.
- Runtime or durable-evidence failures stop the recovery. They cannot become
  model errors. Incorrect supported choices still count as incorrect answers.
- 1,650-second recovery limit, 1,800-second compute stage, 2,400-second instance
  deadline. One $2 reservation is added to the same $100 task ledger. No automatic
  retries, no T4 fallback. Actual AWS billing is reported separately from reservations.

## Original evidence identity

- Packet: `76fbb522a97e3018e946857ce71599fbdea8bb6daffd29bd15fb7cf2d091f7a0`
- Predictions: `00e7a2b7d72c86d4dc9d7bdb3dd74f2c7338bb650b7e7e8136dfa6dd9ee09bc8`
- Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`

The packet, historical launch receipt, and cleanup records are included in this
source commit. The recovery result will be bound to its own source commit and
the original packet. The byte-only packet inspector never loads a checkpoint.

## Claim boundary

This is one seed and three authored procedures on a small synthetic curriculum.
Completion can show learned selection and binding of supported CJT programs.
It cannot establish CAS-specific advantage, general reasoning, language-model
capability, complete Noetic fractals, or production readiness.
