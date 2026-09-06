# Exact-prototype candidate integration — preparation only

This version preserves the frozen v6 neural policies, decoder, loss, optimizer,
validation-only checkpoint selection, and native executor boundary. It changes
the input loader to accept the separately checked, exact 256-record training
append. The accepted model and executor are not changed.

The caller must supply the public loader's SHA-256 from a source-bound experiment
registration. The training process and parent training checker use the same
public-only loader, including the final reload before predictions are sealed.
Neither calls the private-target parent validator.

The base640 plus exact256 design has896 training tasks: depth1=128,
depth2=384, depth3=384. At batch16 and200 epochs this would request11,200
optimizer steps per family. These are design counts, not a completed run.
Actual merged counts and all source/file identities must be checked before launch.

This directory is not yet a complete cloud experiment. The portable parent
dataset builder, versioned evaluator/campaign, frozen spec, updated exclusion
inventory, source bundle, full integration tests, and bounded launch remain
required. The current v6 AWS experiment is separate and unchanged.

Never run neural work or load checkpoints on the laptop. All such execution
requires the registered AWS CUDA job. No automatic launch, retry, promotion,
or acceptance is provided by these modules.
