# Learning revision: preserve inputs and teach nested calls

The first full composition experiment remains a negative result: CAS and the
matched generic model each solved 0/72 held-out tasks. Its complete evidence is
committed as `74b2322b1bd39cd09da071b61372f3183c2c9ada`. This revision does not
rewrite that experiment or treat its already-inspected test set as unseen.

`EXPERIMENT_V2.json` records the new protocol before paid execution. Its exact
bytes and entrypoint are bound into the source archive. There is no new AWS
spending allowance: the same $400 total cap and shared ledger apply.

## What changes

- `features_v2.py` preserves exact problem/tag text, including names, case and
  whitespace. It fits word units on training inputs only. A fixed UTF-8 byte
  fallback represents unknown text. It does not parse the requested program.
  Exact text recovery is not a claim about numeric float32 precision or what a
  trained model understands.
- `curriculum_v2.py` supplies 768 training tasks, including real calls inside
  child procedures, and 48 validation tasks. Every procedure name used in the
  bounded output vocabulary receives positive training examples. All targets
  use the unchanged A/B/C junctions, IR and admission rules.
- `train_v2.py` trains matched CAS/generic generators on the same batches.
  Checkpoint selection first measures freely generated validation programs and
  bindings. Teacher-forced token loss is only a later tie-breaker. Invalid
  generated programs are not repaired by the rule parser or a grammar mask.

## What the new evaluation measures

There are 24 matched triplets, or 72 test cases:

1. A new depth-3 graph with a training wording combination.
2. That same graph and observations with a reserved wording combination.
3. A matched depth-4 graph with the original wording and observations.

The depth pair preserves the ordered native RUN operations, their input
dependencies and final selected result. Every procedure performs real native
work; extra depth is not an empty wrapper. The cases within a triplet are
deliberately related, so 72 is not a count of independent graph samples.

Graphs and observation instances do not overlap across training, validation and
test splits. The frozen original curriculum's 376 graph hashes are excluded.
Construction uses formal structure first, surface wording second, then a
separate existing parser to check meaning. These are controlled procedural
descriptions, not unrestricted language or algorithm discovery from an outcome.

All five arms remain: CAS untrained/trained, generic untrained/trained and the
authored rule parser. Every prediction is sealed before evaluation opens private
test targets. The unchanged executor and native verifier check actual intermediate
and final outputs. Valid traces alone do not count as correct answers.

The public dataset manifest does not expose validation/test target-token or
binding frequency maps. Coverage is checked during construction, but the learner
receives only training frequency counts and zero-missing-token assertions.
One early pure audit fixture mechanically generated the registered dataset in
memory; no target contents were displayed, inspected by an agent or saved by
that fixture. The fixture now uses a separate test seed (`982341`). No learning
or experiment choice was based on outcomes from the registered test tasks.

## Execution and evidence gates

Local checks are limited to text, JSON, hashes, source and control logic. Model
construction, tensors, gradients and native neural execution run only on AWS.
The v2 campaign checks the real longest 16-example training batch with the
registered model dimensions before learning. It records finite gradients,
operating-region activity and observed GPU memory use. That check does not prove
the entire job fits memory; deadlines and failure receipts remain necessary.

Use `tools/build_launch_bundle.py --experiment-profile learning_v2` after an
intentional source commit. The launcher reads only the allowlisted entrypoint
from that verified manifest. It keeps the two-hour resource cutoff, bounded
collection, cleanup and the shared budget ledger. Default profile behavior
continues to select the original campaign.

Inspect new packets with `tools/inspect_cloud_packet_v2.py`, then
`tools/audit_stored_packet_v2.py`. The original v1 tools and receipts remain
available for the first run. Audit tools never deserialize checkpoints on this
laptop. Checkpoint loading and neural inference require AWS CUDA.

## Current boundary

Final prelaunch pure validation passed 615 test functions and 89 subtests, with
two GPU test modules skipped. All 316 protected baseline files and all checked
source files stayed unchanged. Exact command, raw output and hashes are in
`records/local_learning_v2_002/receipt.json` and its neighboring files. The earlier
604-test pass is retained separately in `records/local_learning_v2_001`.

The GPU preflight, training and held-out native evaluation have not run at this
source freeze. No learning gain is claimed yet.
The full CASformer vision remains open, including broad language, complete
Noetic meanings, learned durable memory, missing-skill acquisition, cross-device
continuity and physical hardware.
