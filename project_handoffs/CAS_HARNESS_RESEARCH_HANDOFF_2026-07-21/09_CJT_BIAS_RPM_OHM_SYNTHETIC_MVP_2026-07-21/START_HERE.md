# Synthetic CJT / Bias / RPM / CAS-Ohm MVP — 2026-07-21

## Read this result correctly

The deterministic synthetic research harness ran successfully from an exact
committed Git bundle. Its result is `SYNTHETIC_HARNESS_MVP_PASS`.

Plain English: the measuring machinery can recover deliberately planted
signals and stop for four deliberately broken cases. This is like proving that
a diagnostic scanner reads a calibrated test bench correctly. It is not proof
that the scanner diagnoses every real engine.

Every receipt authority field remains
`SELF_HASHED_UNATTESTED / SHADOW / NONE / NOT_LICENSED`,
`claim_eligible=false`, and `model_execution=NONE_SYNTHETIC_ONLY`.

## Exact identity

- Branch: `codex/jspace-ohm-synthetic-20260721`
- Commit: `25053461c94de23850da7f9c853c420aab1bae62`
- Tree: `b377232896eb5bd4c087268dcc0988d88dfba290`
- Parent contract commit: `5d9a9d4206990e673d86a0c62518fd1a44ab6b1e`
- Bundle SHA-256:
  `28CB29B80E27DD1E13E86E9C889B13A6963CE48DE40C65703A75BB23E0CCF8BF`
- Receipt file SHA-256:
  `76E907BD8A51B466A8BFB0BA84EE5D9A2E5DDA7C51CC4B171D86C07B3FC9E764`
- Envelope content SHA-256:
  `816c7f387a1cf42f971a64a885b537984694057bab4891747df152919ec01ef1`
- Report content SHA-256:
  `61007b04ae3d7eb96cf4d94e3c3a264794eec55d4cb041b0a5cd3ce93a5f46f6`
- Protocol SHA-256:
  `F8382F355B4058C14A439260C42E4066ABBEAF033AE2F499AF759500F49D61DB`
- Research lock SHA-256:
  `4DD1DCACCB2D531F4A8FCF0A50CE77CC60D9F48F276DC32190247BFF7C406D46`

## What passed

- One identifiable planted scenario: `SYNTHETIC_RECOVERY_PASS`.
- Four exact `EXPECTED_FAIL_CLOSED` controls: near-zero Bias sensitivity,
  nonlinear response, RPM confounding, and incomplete RPM trace.
- `62` focused tests, `418` complete worker tests, and `96` production
  audit/evidence/fleet quarantine tests.
- Unmocked CPython 3.14 `-I` execution with the exact lock and 1,000
  bootstrap replicates.
- Strict independent reopen of both content hashes.

## What did not happen

No GPU or language model ran. No hidden states or activations were read. No
prompt injection was detected. No real output was controlled. No
cross-architecture or 300B capacity was tested. No Evidence Packet, WORM
anchor, customer verdict, `ACCEPT`, or `LICENSED` capability was created.

These remain intended objectives. Current honesty labels describe current
evidence; they do not define the project's final ceiling.

## Folder contents

- `CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle` — complete Git history.
- `CJT_BIAS_RPM_OHM_SYNTHETIC_RECEIPT_25053461.json` — no-overwrite receipt.
- `CJT_BIAS_RPM_OHM_SYNTHETIC_V0.json` and `.lock.txt` — protocol and lock.
- `CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md` — broader
  prospective real-model contract.
- `RESEARCH_SHADOW_at_25053461.md` — implementation/limitation guide.
- `IMPLEMENTATION_AND_TEST_REPORT.md` — engineering evidence.
- `INDEPENDENT_REVIEW.md` — reviewer result and remaining limits.
- `REPRODUCTION_COMMANDS.md` — novice PowerShell instructions.
- `ARTIFACT_HASHES.txt` — critical hashes.

## Next executable gates

1. Externally timestamp/anchor the protocol, bundle, and receipt with readback.
2. Retain raw synthetic observations as a separately hashed artifact.
3. Add clusters and stochastic heterogeneity; test coverage, type-I error, and
   power.
4. Bind a qualified real-model adapter/revision and run the registered
   hidden-state/intervention controls on an isolated GPU with at least 24 GB.
5. Repeat unchanged gates across architectures and scale before universality;
   design and execute genuine 300B capacity separately.
