# Handoff brief for an external advisor (paste-ready)

You are being asked to advise on one narrow workstream inside a larger research
project. You are an advisor only: the project owner approves every change, and
the frozen experiment rules cannot be overridden by suggestions. Please read
the scope and constraints before answering.

## The project in one paragraph

CASformer is a Transformer whose attention is rebuilt around typed
Cause->Effect junctions (CJTs) governed by a CAS-Ohm conductance law, wrapped
in a verifier-gated runtime with budgets, repair, and replayable evidence.
Measured results so far: learned procedure selection improved 8/72 -> 66/72
(one proven skill); learned program composition is an honest 0/72 on held-out
nested tasks (depth 3: 0/48, depth 4: 0/24) - these numbers are frozen and must
never be rewritten. The current sub-task does NOT touch composition. It is a
small input-dependent classification pilot called "condition skill v9".

## Current sub-task scope

Two labelled integer conditions (value vs limit, at_least or at_most, per
semantic slot) map to four classes L0..L3. A new CUDA-seeded candidate with the
original four-dimensional CJT network configuration is trained offline (100
epochs, batch 64, AdamW lr 0.003, 2,400 steps per family) and compared with a
parameter-matched generic softmax-attention control. Frozen dataset: 1,536
train, 384 validation, 384 fresh-instance test, 384 withheld-direction-pair
test. Constant-class baseline is exactly 25%; per-bit chance is 50%. A frozen
deterministic adjudicator (PASS/FAIL/EVIDENCE_INCOMPLETE) assigns the claim
status from written gates: joint accuracy > 0.25, both bits > 0.50,
trained > untrained, six evaluation controls at joint accuracy 1.0, exactly
2,400 steps, unchanged source pins, and an independent provider attestation.

## Hard constraints (non-negotiable)

- All neural work runs on AWS GPU only (one g7.2xlarge, RTX PRO 4500, no T4,
  torch 2.11.0+cu128, CUDA 12.8). No local CPU inference. No automatic retries.
- Exactly one paid run, reservation $4.00 against the $400 campaign ledger.
- Private test targets must stay unread until blind predictions are sealed.
  Checkpoint selection uses validation only.
- Byte-verifiable evidence for everything: exact git-object source packaging,
  SHA-256 manifests, guarded pure-test receipts.
- No redesign of CASformer, no new architecture, no claim promotion. The
  0/48, 0/24, 0/72 composition results are preserved exactly.
- The owner is the only approver. Advisors suggest; governance rules decide.

## Progress so far (all pure, no neural work, no reservation yet)

1. Dataset, protocol, trainer, and frozen adjudicator are committed, tested
   (222 guarded pure tests), and published byte-identically.
2. Owner approvals are recorded as executable files: adapter build + single
   $4 run pre-authorized; budget scope = $400 campaign ledger; pre-run metric
   amendment (per-bit baseline corrected from 0.25 to 0.50).
3. Adapter module 1: frozen resource plan + inert launch-request contract
   (20 tests passing).
4. Adapter module 2: source package builder that reads exact git objects at a
   pinned commit, carries the candidate + dataset + baseline closure, enforces
   member/size/hash bounds, and verifies zip readback (9 tests passing).
5. Adapter module 3: remote worker (bounded safe extraction, manifest rehash,
   one trainer run with explicit flags and an independent process-group kill,
   allowlisted result collection with a 32 MiB bound, failure recorded without
   retry) - 11 tests passing.
6. Adapter module 4: launch lifecycle (inert plan by default; hash-bound
   request plus separate standing authority; one-shot $4.00 reservation under
   the campaign ledger after read-only preflight; provider identity outside
   the trainer; cleanup on every exit) - 23 tests passing.
   Guarded re-capture over the whole adapter: 222 passed (checks_011).
   Remaining before any paid run: the separate AWS provider adapter (real
   boto3 calls, still absent by design), the independent audit, the source
   freeze, and the hash-bound request/authority pair.

## Questions for you (please answer concretely)

1. Package member selection: the package carries the v9 candidate, frozen
   dataset, protocol/approval records, requirements, and the frozen baseline
   closure named by the committed BASELINE_MANIFEST.json. What attack or
   failure mode am I missing in packaging exact git objects into a bounded zip?
2. Remote worker design (next): bounded extraction to a fresh directory,
   hash-verified against the manifest, pinned dependency install, one trainer
   run with an independent 600-second process-group kill, 32 MiB trainer
   output bound, result collection on success and failure, no restart. What
   hardening should be added for extraction TOCTOU, output bounding, or
   result collection?
3. Launch lifecycle ordering: preflight (read-only provider checks) ->
   reservation once -> launch -> collect -> cleanup -> adjudicate with
   attestation. Any ordering or failure-handling gaps in that plan?
4. Adjudication gate set: joint > 0.25, per-bit > 0.50, trained > untrained,
   controls joint accuracy 1.0, oracle 1.0, constant baseline exactly 0.25,
   2,400 steps, source pins, provider attestation. Would you add, remove, or
   reword any gate before the run?
5. If you were the independent auditor of this adapter, what three things
   would you check first?

Keep answers scoped to this pilot. Suggestions that change thresholds or the
dataset require the owner's approval and must be recorded before any run.
