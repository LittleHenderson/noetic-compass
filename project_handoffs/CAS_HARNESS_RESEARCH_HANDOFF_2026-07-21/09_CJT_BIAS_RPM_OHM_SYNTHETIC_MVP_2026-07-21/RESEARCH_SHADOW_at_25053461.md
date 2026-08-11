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
| `CJT_BIAS_RPM_OHM_SYNTHETIC_V0` | `SYNTHETIC_HARNESS_MVP_PASS` at most | A CPU-only deterministic-plumbing MVP can test planted signed/Fisher gains, response to a commanded synthetic Bias dose, local response, four fixed operating-window classifications, and two-field synthetic RPM trace/state checks. It does not measure a hidden-state Bias coordinate, discover operating boundaries, validate a production RPM ledger, or execute a language model. The broader `SYNTHETIC_HARNESS_PASS` target is unavailable. |

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

## Run the synthetic recovery harness

The synthetic lane uses a 13-dose design, separate response,
derivative/logit, direct-equivalence, and RPM-DAG blocks, plus grouped held-out
curve competition. Fifteen logical prompt groups are split 9/3/3 and each group
is crossed with two shared split-specific seeds; seed identities do not overlap
between calibration, selection, and evaluation. Commanded synthetic Bias
micro-doses have an observed Cause-hold gate, but there is no independent
`measured_bias` coordinate; `g_B` is response per commanded dose only. RPM
contrasts use three evaluation-group cluster-bootstrap plumbing ranges and
require every evaluation cell to agree with a two-field
`prerequisite_identity:decision` trace and planted state pattern. The current
generator has intercept-only stochastic variation, so slope and paired-contrast
ranges can collapse to zero width; calibrated confidence coverage, type-I error,
and power are not established. Bonferroni correction is applied separately to
the seven-parameter and eight-RPM families at nominal familywise alpha 0.05; it
does not establish joint 15-endpoint familywise control. The active-window
R-squared is a pooled fit computed and scored on the same EVALUATION rows, not
cross-fitted prediction. Current containment and probe-strength metrics
are planted MVP controls, not recovered principal-angle or probe-reliability
measurements. The lane contains one
identifiable recovery scenario and four controls that must fail closed for the
registered reason.

It requires a committed standalone Git bundle because the receipt binds every
worker Python source file, `.gitattributes`, the synthetic protocol, and the
isolated synthetic research lock; shared production requirements are not
changed. Launch requires CPython isolated mode (`-I`), which ignores
`PYTHONPATH` and user-site additions. After source-bundle verification, the
runner verifies CPython 3.14 launcher/runtime-DLL bytes, checks that the lock
rows equal the registered versions, and prehashes the metadata file trees for
NumPy, Pydantic, pydantic-core, annotated-types, typing-extensions, and
typing-inspection before importing any of them. It then imports the
schema/engine and re-verifies that all six dependency records are unchanged.
The receipt includes all six module/tree hashes and file counts so its aggregate
dependency-manifest hash is independently recomputable.

This remains `SELF_HASHED_UNATTESTED`, not a secure supply-chain sandbox.
Python provenance binds the launcher and runtime DLL, but not the complete
pure-Python standard library or every standard-library extension module:

```powershell
python -I scripts\run_cjt_ohm_synthetic_recovery.py `
  --code-revision <40-hex-git-commit> `
  --code-bundle C:\path\to\implementation.bundle `
  --expected-code-bundle-sha256 <64-hex-bundle-sha256> `
  --output C:\path\to\cjt_ohm_synthetic_receipt.json `
  --seed 20260721 `
  --bootstrap-replicates 1000 `
  --enable-shadow
```

The runner refuses overwrite, flushes and publishes the new output with a
same-directory no-replace hard link, reopens it, validates the strict schema,
and verifies its content hash. The file itself is fsynced, but Windows parent-
directory fsync is not implemented, so publication is not claimed crash-
durable. Omitting
`--enable-shadow` writes nothing. No GPU, network, model weights, or hidden
states are used.

The protocol is currently an unanchored draft. Therefore even a
`SYNTHETIC_HARNESS_MVP_PASS` remains `SHADOW`,
`verdict_influence=NONE`, and `NOT_LICENSED`. The report explicitly says
`SELF_HASHED_UNATTESTED` and retains only the synthetic dataset digest, not a
raw observation attachment. Execution memory is Python `tracemalloc` peak
memory, not process RSS or native NumPy peak memory. The MVP exercises planted
PIECEWISE and SATURATING truth families across eight current competitors;
standalone truth fixtures and complete diagnostics for the other six competitors
remain open. A Bias-by-drive interaction family is registered as future work but
is not run because the MVP curve-competition rows use centered Bias. The
candidate grids and window selectors are draft code registration bound to the
reported source revision and bundle hash, not independent prospective
preregistration. This slice proves only deterministic recovery plumbing on
planted structure; it does not prove statistical operating characteristics or
that a real model contains that structure.

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

1. Independently review the synthetic implementation and results, then freeze
   and externally anchor its exact protocol, runner, scenarios, dependency
   closure, and power analysis without changing the observed outcome.
2. Externally anchor the frozen technical protocol and corpus manifest, then run
   the eight-block exact-token Jacobian/JVP/VJP/finite-difference canary on an
   isolated research GPU with at least 24 GB VRAM.
3. Freeze the J-Space decomposition and all random, lexical, PCA,
   pseudo-definition, duplicate-screen, and uncertainty controls before any
   live-gradient correspondence analysis.
4. Build a genuinely new, independently authored and independently labelled
   neutral holdout under a separate prospective protocol. Existing Stage-7
   remains retrospective and source-derived.
5. Register an exact external CJT drive, internal test point, bias, unit
   direction, and output functional; run zero plus positive and
   negative doses with signed mediator, registered output, off-target, sham,
   random, orthogonal, wrong-drive, and shuffled controls.
6. Compare null, affine, reciprocal, saturating, Hill, and piecewise curves on
   untouched held-out data and run the P1-P4 falsification gates.
7. Repeat across seeds and Pythia scales, then run unchanged gates on at least
   one non-GPT-NeoX architecture before advancing any external claim.

The owner-defined CJT boundary is recorded in
`docs/working/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721.md`:
voltage/desire/stimulus/trigger/`^8` Above-Cause is external to the CJT.
An internal intervention dose is not automatically voltage.

The additive Bias/RPM design is recorded in
`docs/working/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md`.
It keeps bias as the CJT base/control condition and corrected v7.4 RPM as a
separate one-directional Desire-to-Wisdom-to-Power prerequisite sequencer
around the CJT. Its deterministic CPU synthetic-plumbing subset is implemented
by `CJT_BIAS_RPM_OHM_SYNTHETIC_V0`. The real-model scientific design remains
unfrozen and non-executable until its model adapter, manifests, power analysis,
hashes, and external anchor are fixed.

Passing one method does not pass either of the others. None of these methods is
licensed for verdict influence at this stage.
