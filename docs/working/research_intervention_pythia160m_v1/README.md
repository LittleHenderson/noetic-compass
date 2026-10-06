# Pythia-160M research intervention V1

This directory is a prospective, family-specific research lock. It does not
authorize a model load or intervention run.

The lock fixes one bounded Pythia-160M hidden-state experiment to:

- `EleutherAI/pythia-160m` revision
  `50f5173d932e8e61f858120bcb800b97af589f46`;
- the tokenizer blobs in `PYTHIA160M_MODEL_MANIFEST_V1.json`;
- a disjoint calibration/held-out split drawn from the sealed Stage 9 scenario
  archive;
- a sparse layer-3 `^0|C` direction derived from the sealed cover artifact;
- signed doses, no-op, same-norm random, wrong-layer, wrong-token, wrong-sign,
  wrong-axis, and patch-back controls;
- numerical collateral-harm floors and fail-closed compute limits.

The inherited generic intervention worker is synthetic-fixture-only. A real
Pythia executor and independent auditor do not yet exist and must be
implemented, locally validated, committed, and hash-bound before a one-use
owner receipt can be created. Framework import, snapshot load, scoring, and
output creation remain prohibited at this checkpoint.

GPT-2 is explicitly outside this lock. It remains a later, separately locked
second-architecture comparison.

Claim boundary: research-only; no live steering or worker/product integration;
no production, safety-steering, prompt-injection-prevention, Gate 2, ACCEPT, or
LICENSED claim.
