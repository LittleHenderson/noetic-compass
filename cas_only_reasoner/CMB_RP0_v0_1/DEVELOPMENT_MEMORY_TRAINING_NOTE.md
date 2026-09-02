# CMB-RP0 — `development_memory_feeds_training = true`

**Owner ruling 2026-09-02, Fix D.** Recorded so the structural-forgery trigger's dormancy is
honest rather than convenient.

```
development_memory_feeds_training     true
production_memory_feeds_training      false
```

## Why this note exists separately

The structural-forgery trigger reads only **production** flags, and its declared state is
`production_memory_feeds_training = false`, which yields `DORMANT`.

Read without this note, that looks like a contradiction. **CMB-RP0 is literally an experiment in
which retrieved memories enter training** — that is the whole point of the bench, and the reason
it exists at all: a wrong memory *shown* to a user can be dismissed, but a forgery in a
*training batch* is written into the weights and cannot be taken back.

So the honest statement of the trigger's dormancy is:

> **The experimental replay bench used memory in training. No deployed system currently does.**

Both halves are true, and neither may be dropped.

## What was actually done, exactly

- **9 registered worlds (700–708)**, one AWS T4, `$0.2039`.
- Each arm selected 32 past memories and **mixed them into the training batches** of the next
  task — `torch.cat([new_task_batch, replayed])` — so replayed content reached the optimizer.
- Under the `POISONED` condition, **132 forgeries per world were eligible for that selection**,
  and every arm ingested some: `CMB_AUTHORIZED` `5.67`, `CMB_RETRIEVED` `5.33`, `DEGREE_FILTER`
  `4.41`, `CLASS_BALANCED_POOL` `16.00`.
- The learner was a ~4,800-parameter MLP over synthetic worlds. **No production system, no real
  user data, no deployed model.**

## Why this note does NOT change the CMB-RP0 result

**The frozen protocol is not retrofitted.** Per the owner's ruling section 5, CMB-RP0 completed
under its own registered law, and applying the later trigger to it would change an experiment
after launch. This note **records** a fact about the bench; it alters no measurement, no status
word, and no artifact.

`CMB_RP0_RECEIPT.json` is **not edited** — its content hash
`f2fbfd0c97df96f7c8ad159a39841f9f15fc62c0558b4a78bc4508bab934022e` is the run's determinism
proof, and the same principle that preserved `RGM02_RECEIPT.json` byte-identically applies here.

The result stands unchanged: `TWO_TIER_GATE_EARNS_NOTHING` / `CMB_REPLAY_BEATS_NO_REPLAY_ONLY` /
`NOT_PROMOTABLE`.

## Where this binds instead

**`CMB-RP1` may not launch** unless `check_structural_trigger.py` returns a clear state, or the
structural defence it demands is implemented and independently audited. That is where the
trigger has authority — over successor work and real deployment, not over a finished run.
