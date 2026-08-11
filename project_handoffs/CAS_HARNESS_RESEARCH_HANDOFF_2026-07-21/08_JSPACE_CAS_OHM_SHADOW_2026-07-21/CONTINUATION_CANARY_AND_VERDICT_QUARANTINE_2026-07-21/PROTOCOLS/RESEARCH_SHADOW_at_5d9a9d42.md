# J-Space and CAS-Ohm research shadow foundation

This worker contains an opt-in, research-only foundation for future J-Space,
Jacobian-lens, and CAS-Ohm experiments. It is disabled by default and has no
customer-verdict effect.

## Current capability

| Method | Current executable status | Meaning |
| --- | --- | --- |
| `JSPACE_CORRESPONDENCE_V0` | `BASELINE_ONLY` | A hash-pinned, sign-preserving activation artifact can be validated. No basis/correspondence analysis runs yet. |
| `JACOBIAN_LENS_V0` | `NOT_COMPUTABLE_FROM_ACTIVATION_ONLY` | Detached activations contain no computational graph, output functional, JVP, or VJP. |
| `CAS_OHM_RESPONSE_PROFILE_V0` | `BASELINE_ONLY` | The existing artifact supplies dose `0.0` only. No response curve, conductance, effective resistance, beta, cutoff, or saturation is identified. |

All receipts fix these fields:

```text
execution_mode = SHADOW
verdict_influence = NONE
claim_status = NOT_LICENSED
claim_eligible = false
```

The schema rejects unknown fields. The receipt contains hashes, shapes,
provenance summaries, method statuses, limitations, and missing prerequisites;
it does not embed raw hidden-state vectors.

## Run the baseline reader

Use a committed Git bundle so the receipt can verify that the supplied code
revision is actually a head in the hash-pinned bundle.

```powershell
python scripts\run_research_shadow_baseline.py `
  --input-artifact C:\path\to\vectors.npz `
  --expected-sha256 <64-hex-artifact-sha256> `
  --code-revision <40-hex-git-commit> `
  --code-bundle C:\path\to\implementation.bundle `
  --expected-code-bundle-sha256 <64-hex-bundle-sha256> `
  --output C:\path\to\research_shadow_receipt.json `
  --enable-shadow
```

Omitting `--enable-shadow` exits without creating a receipt. The reader also
fails closed on a mismatched hash, malformed or oversized NPZ, duplicate/unsafe
archive members, object-dtype arrays, nonfinite values, coercible layer/token
metadata, inconsistent tensor shapes/dtypes, unpinned model revisions,
incomplete model-artifact inspection, or mismatched capture provenance.

`content_sha256` is a content hash, not a digital signature or independent
timestamp. The current artifact status is `LOCAL_HANDOFF_ONLY` and
`NOT_DURABLY_OBJECT_STORED` until an independently reread provider object version
is available.

## Deliberate non-integration

These shadow names are not added to the fleet planner's mandatory
`expected_outputs`. The API now rejects nested research-shadow schemas at
fleet and audit verdict ingress. Unknown schemas normalize to six
`unavailable` proof chips, and worker-supplied verifier/readiness fields
remain hash-committed but cannot authorize `ACCEPT` or `SUPPRESS`. A
shadow failure cannot make a normal audit fail, and a shadow success cannot
improve a verdict.

Do not attach shadow summaries to Evidence Packets. A future integration
requires a separately authenticated research-to-product promotion contract;
filenames, self-declared proof chips, and worker fields are never authority.

## Split technical protocol and scientific draft

The next step is split into two honest artifacts:

- `research_protocols/JACOBIAN_LENS_CANARY_V0.json` is a frozen technical
  preregistration. Its maximum positive status is
  `TECHNICAL_CANARY_PASS`. It tests exact-token Jacobian/JVP/VJP and
  finite-difference plumbing only. Canonical SHA-256:
  `1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5`.
- `research_protocols/JSPACE_CORRESPONDENCE_V0_DRAFT.json` is a
  retrospective scientific plan. Stage-7 test was already opened, scored, and
  stored in the recovered 2026-07-21 run, so Stage-7 cannot produce a
  prospective or license-candidate result. Canonical SHA-256:
  `228df1ff6cb231f2920bc92e22f9a99e30b36b5b08c7120fc5ab76369dc285b4`.

Run `scripts/verify_jspace_preregistration.py` before constructing the
frozen WikiText block manifest. The canary protocol still requires an
independent timestamp or anchor before GPU execution; an adjacent local hash
sidecar is not that anchor.

The 3,072-versus-768 eraser tensor-space corruption is mechanically fixed.
Exact historical calibration revision binding and a durable applied-
intervention receipt remain OPEN, so the eraser remains NOT LICENSED.

## Next executable gates

1. Externally anchor the frozen technical protocol and corpus manifest, then run
   the eight-block exact-token Jacobian/JVP/VJP/finite-difference canary on an
   isolated research GPU with at least 24 GB VRAM.
2. Freeze the J-Space decomposition and all random, lexical, PCA,
   pseudo-definition, duplicate-screen, and uncertainty controls before any
   live-gradient correspondence analysis.
3. Build a genuinely new, independently authored and independently labelled
   neutral holdout under a separate prospective protocol. Existing Stage-7
   remains retrospective and source-derived.
4. Register an exact external CJT drive, internal test point, bias, unit
   direction, and output functional; run zero plus positive and
   negative doses with signed mediator, registered output, off-target, sham,
   random, orthogonal, wrong-drive, and shuffled controls.
5. Compare null, affine, reciprocal, saturating, Hill, and piecewise curves on
   untouched held-out data and run the P1-P4 falsification gates.
6. Repeat across seeds and Pythia scales, then run unchanged gates on at least
   one non-GPT-NeoX architecture before advancing any external claim.

The owner-defined CJT boundary is recorded in
`docs/working/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721.md`:
voltage/desire/stimulus/trigger/`^8` Above-Cause is external to the CJT.
An internal intervention dose is not automatically voltage.

The additive Bias/RPM design is recorded in
`docs/working/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md`.
It keeps bias as the CJT base/control condition and corrected v7.4 RPM as a
separate one-directional Desire-to-Wisdom-to-Power prerequisite sequencer
around the CJT. It is a draft design, not part of either frozen protocol and
not executable until its runner, manifests, power analysis, hashes, and
external anchor are frozen.

Passing one method does not pass either of the others. None of these methods is
licensed for verdict influence at this stage.
