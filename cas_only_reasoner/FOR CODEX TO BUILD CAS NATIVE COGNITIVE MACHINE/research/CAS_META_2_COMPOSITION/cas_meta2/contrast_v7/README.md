# Exact-original curriculum candidate integration

This version preserves the frozen v6 neural policies, decoder, loss, optimizer,
validation-only checkpoint selection, and native executor boundary. It changes
the input loader to accept the separately checked, exact 256-record training
append. The accepted model and executor are not changed.

The caller must supply the public loader's SHA-256 from a source-bound experiment
registration. The training process and parent training checker use the same
public-only loader, including the final reload before predictions are sealed.
Neither calls the private-target parent validator.

The 640 new base records plus the exact original 256 give 896 training tasks:
depth 1 = 128, depth 2 = 384, depth 3 = 384. Validation has 96 tasks, and the
test has 72 tasks in 24 related triplets. At batch size 16 and 200 epochs,
the request is 11,200 optimizer steps per family. These are planned counts,
not a completed run. The AWS data process must record and verify the actual
assembled counts before full training starts.

The portable dataset builder, public-only loader, versioned evaluator, campaign,
source bundle, and bounded AWS launcher are implemented. Paid execution requires
the exact registered specification, a pinned successful recovery review, a
committed source package, and the current job's real GPU smoke check. Local pure
tests do not stand in for that GPU check or for a completed learning result.

The registered plan reserves $7. Its limits are 450 seconds for the GPU check,
180 for data assembly, 3,300 for training, 2,700 for native evaluation, 6,900 for
the campaign, 7,200 for compute, and 7,800 for the instance. These are limits,
not promises that every phase will finish. The earlier v6 native replay took
2,221.574 seconds; the new 2,700-second limit leaves estimated headroom for fresh
cases without changing the scoring or neural core.

See `EXPERIMENT_PROTOCOL_PROTOTYPE_V7.md` at the package root for split meaning,
matched comparison conditions, and the required report. Earlier experiments
remain separate evidence. No new held-out result is claimed by this README.

Never run neural work or load checkpoints on the laptop. All such execution
requires the registered AWS CUDA job. No automatic launch, retry, promotion,
or acceptance is provided by these modules.
