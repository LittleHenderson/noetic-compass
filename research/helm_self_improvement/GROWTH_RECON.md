# C3-R source inspection — implementation and execution pending

Inspected HELM scientific source `c45f775f225dd06cc20cdf313f0a0398486e0d61`:
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py`
under the historical CNCM root. File SHA256:
`0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8`.
Read through Git from the audit repository; no model imported or executed.

The `world_head` at lines 856–858 is Linear(WORLD_CANDIDATE_WIDTH, WIDTH),
GELU, LayerNorm(WIDTH), Linear(WIDTH, 1). Blind widening changes LayerNorm's
normalization and is not admitted as function preserving. The shared recurrent
core and suspended native callers are excluded from this first proposal.

A prospective compatible operator is a separate residual specialist on the
same world candidate input: `old_world_score(x) + B * GELU(A*x)` with the
same scalar output. Initialize A nonzero with a separately recorded RNG and
B zero. This preserves the initial arithmetic contribution for finite inputs;
it does not promise identical floating-point output on every device. B can
receive gradient first; A generally receives gradient only after B updates.
Do not initialize both matrices to zero or count A's initial zero gradient as
a successful trainability probe. Nonfinite inputs remain a refusal condition.

Migration proposal: retain every original named tensor and its AdamW state;
register A/B before optimizer construction (current lines 1777–1845 bind the
entire named container). New entries start with explicitly zero moments and
step zero. Preserve old parameter ordering and map state by exact names/shapes,
not positional guesses. Parameter-group, scope and run-identity schemas must
be versioned together. A newly initialized optimizer is a different policy,
not exact continuation. No change to the running seed19 source is authorized.

The existing checkpoint contains model, optimizer, encoder, three RNG streams,
cursor, model revision, elapsed budget, counters and mode (lines 2104–2141).
All must reload or roll back together. Activate only at a committed boundary
with no pending batch; rebuild caches and shape-dependent state. Growth
parameters require optimizer visibility, forward participation, gradients,
updates after at least two suitable steps, and a contribution ablation.
All those execution checks are NOT_RUN. No capacity or benefit claim follows
from this source inspection. Use a prospective matched extra-training control
on unchanged capacity with the same primary compute budget before claiming
useful growth. This document adds no GPU job, implementation or new budget.
