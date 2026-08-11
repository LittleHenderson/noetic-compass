# Implementation and Verification

Date: 2026-07-21

## Commit chain

- `14629b76`: verdict-excluded J-Space/CAS-Ohm shadow foundation.
- `de1a117d`: complete source-closure binding for the shadow runner.
- `d4dc5628`: Stage-27F eraser tensor-coordinate contract correction.
- `1e92b5bb`: unauthenticated research/fleet evidence quarantined from
  verdict authority.
- `405fb389`: exact-token Jacobian canary, deterministic token-block
  manifest, strict preregistration verifier, and external-drive ontology.
- `5d9a9d42`: prospective CJT Bias, corrected v7.4 RPM, and CAS-Ohm
  experiment contract.

Final full identity:

- commit: `5d9a9d4206990e673d86a0c62518fd1a44ab6b1e`
- tree: `92340278032bdbb5e98bf67381f62e81f1dc008e`
- bundle bytes: `35,654,734`
- bundle SHA-256:
  `E4E971A7990A4AEFD1EC550A4FFD870256301342EB7F18C6397D236D64FFFB5E`

Pinned Jacobian-lens dependency:

- commit: `581d398613e5602a5af361e1c34d3a92ea82ba8e`
- bundle bytes: `1,799,410`
- bundle SHA-256:
  `1DA9F6D9EF4E185615C1BD7A5B548C1FCAC513340C24B1DD8DE68115FC793E82`

## Implemented scope

The exact-token path consumes frozen 128-token IDs without calling the
tokenizer and uses `force_bos=False`. It validates the dataset/tokenizer
source snapshot, deterministic rank, domain-separated token and Merkle hashes,
atomic write/replace/reopen behavior, and the future-target SUM estimator.

The canary pins the Jacobian-lens source revision and checks JVP/VJP and finite
differences on the same prompt-local Jacobian. It is a technical calibration,
not a semantic result.

The CJT Bias/RPM/Ohm contract keeps `V_ext`, Cause, Bias,
`I_internal`, Effect, RPM, and internal `alpha` distinct. It requires
held-out predictive comparison among linear, affine, reciprocal, saturating,
Hill, piecewise, monotone, and interaction models; uncertainty intervals;
operating-region rules; prompt-injection outcome separation; causal controls;
and corrected one-way RPM prerequisite traces.

## Protocol identities

- `JACOBIAN_LENS_CANARY_V0`
  - canonical SHA-256:
    `1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5`
  - raw file SHA-256:
    `fb302300829889072c68e5fd0f0e9ac1710daa58aab4aae5abc76a8eee360cb1`
- `JSPACE_CORRESPONDENCE_V0_DRAFT`
  - canonical SHA-256:
    `228df1ff6cb231f2920bc92e22f9a99e30b36b5b08c7120fc5ab76369dc285b4`
  - raw file SHA-256:
    `31dcfda7f85abc02f9692b95c82d0e6c9f89ca2c44ab063acf83a7ac3ce5215d`

The Stage-7 material in the correspondence draft was already accessed and
scored. It is retrospective/source-alignment evidence and cannot become an
untouched prospective holdout.

## Verification results

- Strict protocol/exact-token trio: `95 passed in 0.62s`.
- Final focused Bias/RPM-adjacent set: `108 passed`.
- Complete live-trace-worker suite: `356 passed in 23.86s`.
- Whole repository: `2829 passed, 11 skipped, 3 xfailed in 49.49s`.
- Strict protocol verifier reproduced the registered canary canonical and raw
  hashes and confirmed `SHADOW / NONE / NOT_LICENSED`.
- Both Git bundles reported complete history and passed `git bundle verify`.

The first full-worker collection attempt on the host stopped with seven import
errors because `scikit-learn` was absent. This was an environment setup
issue, not a test assertion failure. It was resolved out-of-tree with pinned
`scikit-learn==1.8.0` under
`C:\tmp\cas-test-deps-py314`; no repository source changed.

## Reproduction

From the final branch checkout:

    Set-Location "C:\tmp\cas-jspace-ohm-shadow-20260721\noetic-compass-scaffold\noetic-compass"
    python live-trace-worker\scripts\verify_jspace_preregistration.py
    pytest -q live-trace-worker\tests\test_jspace_preregistration.py live-trace-worker\tests\test_jspace_exact_token_lens.py live-trace-worker\tests\test_jspace_token_manifest.py live-trace-worker\tests\test_research_shadow.py

If the test environment lacks scikit-learn, install the pinned dependency in an
isolated environment or out-of-tree target before running the complete suites.
Then run:

    pytest -q live-trace-worker\tests
    pytest -q

Verify the copied source histories:

    git bundle verify SOURCE\cas-jspace-ohm-shadow-5d9a9d42.bundle
    git bundle verify SOURCE\cas-jspace-ohm-shadow-405fb389.bundle
    git bundle verify PINNED_DEPENDENCY\jacobian-lens-581d398.bundle

Verify the whole dated handoff from its `06_REPRODUCTION_GUIDES` folder:

    powershell -ExecutionPolicy Bypass -File .\BUILD_AND_VERIFY_MANIFEST.ps1 -VerifyOnly

## Open execution gates

- freeze the exact source snapshot consumed by the token-block freezer;
- place the protocol digest in an independent timestamp/anchor;
- implement and hash the actual canary executor and receipt;
- execute the technical canary on an isolated GPU with at least 24 GB VRAM;
- freeze and execute the prospective CJT Bias/RPM/Ohm factorial design;
- admit an independently authored neutral semantic holdout;
- replicate unchanged gates on a non-GPT-NeoX architecture; and
- produce an actual sharded 300B execution and recoverable receipt.

