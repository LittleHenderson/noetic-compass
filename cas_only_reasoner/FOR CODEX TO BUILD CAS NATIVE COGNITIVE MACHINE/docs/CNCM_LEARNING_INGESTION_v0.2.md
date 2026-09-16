# Learner-visible complete containment inventory

Input version 0.2 makes the source's completeness assumption part of the public
learner input. It does not add six lessons when a person opens six cube faces.
The shared formal/contextual/analogy structure remains teaching source material;
viewer navigation itself is not a model call or a weight update.

The version 0.1 adapter already repaired the old `Facts ... contains ...` export
by rendering explicit `node` and `rel` lines. Its actual CUDA teaching/reload run
is preserved at source `6ef614bfb448abb586a6f8c0c92058e57de9238b`, published in
checkpoint `9504f93c59bbdcc1babbea4ac555e286fe40aec9`. That input still omitted the
complete-inventory assumption. The new version corrects this distinct gap.

## Public contract

Every prepared question now contains this exact line after its node/relation
inventory and before its question and options instruction:

> Containment inventory is complete within this supplied snapshot; an unlisted direct contains relation is absent from this snapshot.

The line is identical for every view, operation and answer. It is emitted only
when the source explicitly declares `contains_inventory_complete` as boolean
`true`. Incomplete, missing or ambiguous declarations do not become scored
complete-inventory lessons. This version does not implement open-world answers.

For `LIST_PARTS(Cloth)`, an empty answer is justified only within that declared
complete snapshot. It makes no claim that real cloth has no components. Likewise,
absence of a direct relation does not rule out an indirect path through other
listed relations; `REACHED_VIA` keeps its existing path semantics.

The public validator requires one exact declaration in its canonical position.
Missing, changed, duplicate or moved statements are refused even if an input ID
is recomputed. Validation consults no teacher answers. Source-based supervision
remains a separate operation. Public text, training text, tokenizer round-trip,
ordered frames and input identity all include the statement. The encoder treats
it as a framing line; it does not solve the graph or enforce an answer numerically.

## Version and evidence boundary

Prepared, lesson and rendering schemas advance from 0.1 to 0.2. Existing 0.1
packets are not silently upgraded. Prepare again from the source, fit the
tokenizer on the new training inputs and bind fresh model-origin and projection
identities before a new training run. Old checkpoint/input identities must not
be reused as proof of compatibility. The ordered encoder algorithm is unchanged.

Historical viewer packages and learning-smoke evidence remain unchanged. The
current adapter source intentionally differs from the preserved baseline.
Version 0.2 first passed pure checks, including explicit learner test doubles.
A later fresh AWS run at source bedc06d52211491b7de4ef955227822801faa4a1 completed
64 updates and 178 forward calls, with exact initial/final same-worker reloads.
Its taught questions improved 0/3 to 3/3; the other exposed questions changed
1/3 to 2/3, consisting of two gains and one lost answer. Delivery and current-job
closure are independently checked in records/learning_smoke_v02_001/STATUS.md.
The earlier run's 64 updates and exact reload results remain bound to its exact
version 0.1 input and source. Neither run proves better learning against a matched
control, delayed retention, unseen transfer or a CAS-specific benefit. The fresh
tokenizer/model bindings also prevent a causal comparison between these two runs.

Evidence and a learner-visible Cloth example are under
`records/learning_completeness_001/`. The next scientific gate remains a matched
multi-seed comparison with equal information and compute, explicit speed,
retention and transfer measures, and protected final scoring.
Every comparison arm must receive the same completeness information. Count its
tokens and framing work in the same input/compute limits; do not grant only the
CAS arm the assumption needed to answer an absence question.
