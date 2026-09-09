# Graph-first ^6 — ln(3) neural diagnostic: REGISTERED authorization request

Status: **AUTHORIZED_BY_OWNER / REGISTERED.** The owner's instruction
**"register it"** (recorded `2026-09-09T08:41:39Z`) authorized the prepared
measurement-only neural diagnostic described in `LN3_DIAGNOSTIC.md`. This is
NOT a larger training run: the frozen 64-steps/600 s-per-condition pilot
allowance is untouched, no optimizer step is taken anywhere in this job, and
the completed attempt-010 evaluation result stays intact.

## What this job measures (no updates, no answers consulted)

`cas_meta2/graph_teaching/diagnostic.py` (measurement spec, in the package):

1. Per-record three scores and spread (after frozen projection → pooling →
   ^6 module → fixed readout), including the correct slot's score.
2. Option geometry: pairwise cosines among the three option vectors and
   problem-to-option cosines.
3. Same-example, alternative-target gradient test: for one example, loss
   values and per-matrix gradient norms (`left.weight`, `merge.weight`,
   `right.weight`) for each of the three targets, WITHOUT any update.

Both prompt-framing arms (cas, generic) are measured. The worker records the
module checkpoint identity before and after each arm and fails closed
(`WEIGHTS_CHANGED_BY_DIAGNOSTIC`) if any weight changed.

Bound decision rules (from `LN3_DIAGNOSTIC.md`):

- Equal scores (spread ≈ 0) while option vectors are distinct → the fixed
  readout/projection is where the distinction is lost.
- Option vectors near-parallel (cosine ≈ 1) → projection/pooling erases
  distinctions before the readout.
- Losses differ per target but gradient norms ≈ 0 → the corrective signal
  does not reach the module.
- Gradient norms differ usefully per target → the machinery can express a
  preference and the flat ln(3) pilot points to the small allowance or
  optimization dynamics — a measured answer, not an inference.

## Registered package identities

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909084139-f6f49be5` |
| source_sha | `68c9fc7a4c0983ffba9bcafa47f8c59a1c0d1fc2` |
| archive_sha256 | `c19d1df47e9f15174bf465203bd1d4db85bdc5be90a86ed3382db6f22ea9824d` |
| manifest_sha256 | `fb15dcb02b4f51ce54ce9664b3bf515acbbc266d5d972dfe7b01f4d95b5febb5` |
| package | `training_mode_001/ln3_diagnostic_package_001/` |
| launcher | `aws/graph_training_ln3_diagnostic_launch.py` at commit `68c9fc7a…` |
| request sha256 | `c4af2c824ed2427038ca0984965d1826d0923350380bb5cce98bd91aeb3adf3f` |
| authority sha256 | `70e4a4517b9c368ac2fccf34991d0f9e211c69f8ed7050fcca1b07edfa2452c6` |
| owner record sha256 | `836438161b25f0eaf49432ccdcb78781c2bd65d0da0bd750358d915ed5139f38` |

Launch inputs: `training_mode_001/ln3_diagnostic_launch_001/` (request is
inert with `launch_authorized: false`; the authority names the owner record
and the frozen measurement-only budget). Owner record:
`training_mode_001/OWNER_AUTHORIZATION_AWS_LN3_001.json`.

## Budget (exact)

One new `$4.00` reservation through the canonical budget helper, exactly
once, no refund, no automatic retry. Ledger today (before): revision 33,
`$182.00` reserved / `$218.00` unreserved. After this job's reservation:
revision 34, `$186.00` reserved / `$214.00` unreserved.

## Preserved constraints

- Accepted models unchanged; attempt-010 evaluation kept intact; sealed
  splits are NOT consulted by this job.
- Frozen negatives `0/72` untouched; no learning or capability claim follows
  from this measurement alone.
- Original errors preserved on any failure; evidence persisted on every exit;
  verified cleanup.
