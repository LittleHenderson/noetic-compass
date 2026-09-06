# Saved-checkpoint prediction stage

`cas_meta2.ablation_predict_v4.run` connects the four preserved checkpoints to
the two grammar modes. It is implemented but has not run on AWS CUDA.

The entry point requires the explicit decoder-ablation job environment, Linux,
CUDA and a 1–900 second bound. The GPU cannot be a T4. Its input reader verifies
the exact preserved ZIP and only decompresses approved public-side members;
it does not open private targets or previous predictions.

The stage uses the unchanged `TrainingConfig` defaults and frozen checkpoint
loader. That loader rejects mismatched tokenizer, configuration, vocabulary,
family, source, epoch, selection record or state dictionary. The output retains
both original checkpoint metadata and its explicit path relocation. No optimizer
is constructed or stepped. Saved files are never overwritten.

For each checkpoint, the stage compares the frozen decoder with the shared
decoder in original-grammar mode on all 72 public tasks, using the same batch
size. It also runs the corrected grammar. Exact original-mode parity and exact
unchanged state tensors are required; parameter gradients must remain absent.
The simple-rule comparator receives the same public problems.

Each mode produces 72 rows / 360 arm predictions and a seal compatible with the
unchanged `campaign_v3.evaluate_sealed` interface. Both modes must finish and the
prediction child must exit successfully before either native evaluation starts.
The prediction receipt explicitly reports native evaluation as incomplete.

## Remaining integration

The bounded parent process, CLI dispatch, actual GPU tests, runtime identity
receipt, allocation cleanup, source-bound launch package, paid-job timeout and
final artifact audit are not supplied by this function. Its time checks cannot
interrupt a stalled CUDA call; an independent process/instance deadline remains
mandatory. It is not an OS sandbox against arbitrary file reads. The parent must
own the evaluation stage and must never accept a partially written seal following
a child failure. Reuse the exactly reconstructed full dataset without bypassing
the frozen evaluator's validation.

The separate `ablation_campaign_v4` module now implements parent/CLI dispatch,
runtime identity capture, authored GPU-test invocation, and native evaluation
ordering. It has not run on AWS. See `ABLATION_CAMPAIGN_V4.md` for the remaining
paid-launch and evidence-verification requirements.

This comparison is retrospective decoding diagnosis. Even an improved result
would not demonstrate new training, fresh held-out generalization, or accepted
learned procedural memory.
