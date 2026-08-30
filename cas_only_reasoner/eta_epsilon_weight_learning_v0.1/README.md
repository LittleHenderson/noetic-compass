# eta_epsilon_weight_learning_v0.1

This folder is a FROZEN research plan. It is not a build. No model has
run. No GPU has run. No training code exists here yet.

## What this study asks (the one frozen question)

Can a CAS-aligned local readout, a right-inverse neural intervention,
and a profile-specific CAS-Ohm dose controller reduce the examples,
optimizer steps, or collateral forgetting needed to teach ONE narrow
skill to a small Transformer, compared with matched ordinary LoRA and
consolidation baselines?

Plain English: does reading a CAS coordinate out of a small model, then
computing a small weight change to move that coordinate, then using
CAS-Ohm to size the change, teach one skill with fewer examples or less
forgetting than plain fine-tuning?

## The skill under test

Active/passive semantic-role binding: given a sentence, name the verb,
the agent (who acted), and the patient (who was acted upon). "The dog
was chased by the cat" must give verb=chase, agent=cat, patient=dog.

Success = the exact role record improves. A CAS coordinate moving is
NOT success on its own.

## The claims (each must pass before the next gets credit)

1. READOUT — can the CAS probe read a CAS coordinate that generalizes?
2. REALIZATION — can a computed intervention move it AND fix behavior?
3. DOSE — can the proportional CAS-Ohm model predict movement on a
   disjoint split (it is zero-intercept linear, so it is tested against
   zero/mean and affine/quadratic, NOT against zero-intercept linear)?
4. LEARNING — split into four separate claims: 4A sample efficiency,
   4B optimizer efficiency, 4C retention, 4D wall-clock efficiency.
   No "or" join; each has its own status.

## The files here

- `CLAIM_BOUNDARY.md` — what this study does NOT attempt; claim words.
- `SOURCE_AUDIT.md` — the source files, their role, and read status.
- `TYPE_CONTRACT.md` — formal vs empirical maps; exact types.
- `PREREGISTRATION.md` — the full frozen plan (task, splits, controls,
  metrics, thresholds, falsifiers, gates).
- `EXPERIMENT_MANIFEST.yaml` — machine-readable version of the plan.
- `CLAIM_LEDGER.json` — every claim, status `PROPOSED`.
- `COST_ESTIMATE.md` — compute and money budget.
- `AMENDMENT_LOG.md` — change history; the v0.1 -> v0.2 rule.

## Phase status

- Phase 0A (this commit): plan corrected after owner review; eight owner
  decisions frozen; model `Qwen/Qwen2.5-0.5B-Instruct` hashed. Lock
  candidate status `AWAITING_OWNER_APPROVAL`.
- Phases 1-8: NOT started. Do not begin without owner sign-off of the
  lock candidate.

## The one rule above all

A beautiful internal CAS movement does not count unless the Transformer
learns the actual skill faster or keeps it better than the baselines.
