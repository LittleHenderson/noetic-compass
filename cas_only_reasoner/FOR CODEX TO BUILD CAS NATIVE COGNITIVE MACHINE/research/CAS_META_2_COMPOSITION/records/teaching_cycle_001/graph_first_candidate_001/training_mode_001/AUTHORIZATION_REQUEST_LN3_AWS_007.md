# Graph-first ^6 — relationship-encoder diagnostic — one-job authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Per the owner's directive, this returns
the prepared candidate and the bounded diagnostic request BEFORE any new
reservation or launch. Training remains pending.

## The prepared candidate (option 2)

`RELATIONSHIP_ENCODER_001.md` documents the actual encoding rule:
line-wise segmentation of the public problem on the `node`/`rel` markers
(a newline closes a line); each complete line is bound into ONE joint
vector by a fixed elementwise (Hadamard) product over its token rows;
bound lines are summed; non-structural framing/request tokens are
mean-pooled on top. Complete source-relationship-target pairings and
node-contents associations survive; independent role sums are NOT used;
the encoder does NOT compute the answer. The module interface (one d_model
vector in/out), the repaired token lookup, the option path, the learning
scope, and the teaching allowance are UNCHANGED; no trainable components
were added.

Verified purely with the real tokenizer at the vector level
(`test_structural_problem_encoder_preserves_pairings_not_order`):
same-token-multiset REWIRING → DIFFERENT problem vector; connection-list
REORDER of the same graph → IDENTICAL vector. 109 graph tests pass.

## What the diagnostic will measure (zero updates, both arms, same examples and weights)

- tag vectors, score differences (old vs corrected), alternative-target
  gradients, module outputs — as in attempt 006, now on the
  relationship-preserving problem encoder;
- graph-edit response for FOUR edits: retarget, node contents,
  same-token rewiring, and connection-list reorder — with token
  count/multiset fields per edit. **Requirement: the rewiring must move the
  module input/output beyond the reorder baseline** (reorder ≈ 0 at the
  vector level; tolerance: reorder output difference ≪ rewire difference);
- **target independence** (pure check on permitted records): changing the
  private corrective target leaves the public record and encoded input
  byte-identical.

No correct untrained answer is demanded; a changed argmax is not required
on every contrast — meaningful score and representation responses are the
criterion.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `f54827348fe3114da77006f71acfccf7a92b4b1d` |
| archive_sha256 | `b1dd44e961c9e8b25abb249ff355a20601531740e73c206609233242440c9c01` |
| manifest_sha256 | `da2ef8ba3df25135f5e57696bdd54bc47ee69583224a93a3e80aaf137ce3c0a9` |
| package | `training_mode_001/ln3_diagnostic_package_006/` |
| launcher | `aws/graph_training_ln3_diagnostic_launch.py` at commit `eac74033` (fixed) |

## The one-job request

- ONE measurement-only job (both framing arms), `optimizer_steps_permitted:
  0`, `max_wall_seconds: 1200.0`, sealed splits NOT consulted.
- ONE new `$4.00` reservation, exactly once, no refund, no automatic retry.
  Ledger today: revision 40, `$210.00` reserved / `$190.00` unreserved;
  after this job's reservation: revision 41, `$214.00` / `$186.00`.
- Worker fails closed if any weight changed; evidence persisted on every
  exit; verified cleanup.

If relationship preservation is demonstrated by this run, the next
experiment is the planned bounded teaching pilot — not another general
review. On GO I will mint the job id, write the owner record binding these
exact identities, register, and execute — nothing before.
