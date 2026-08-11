# Attempt 3 preparation: corrected dependency layout

> **Historical record -- never execute.** Attempt 3 obtained and verified its
> exact RFC3161 timestamp, then was superseded before wrapper/model/CUDA
> execution because the child interpreter lacked `-B`. Attempt 4 later used a
> different approved query exactly once and failed closed before CUDA at the
> OpenSSL 3 stdin certificate preflight. Both identities are consumed. Do not
> execute this preparation sequence or reuse any Attempt 3/4 nonce, run ID, PRE,
> protocol, query, approval, timestamp, anchor, launch configuration, or output
> root. The current successor is the independently reconstructed Attempt 5
> implementation freeze at
> `04_PROTOCOL_AND_ANCHOR/ATTEMPT_05_IMPLEMENTATION_FREEZE_F72B89CD/`, status
> `IMPLEMENTATION_FREEZE_PASS / NO_PRE_OR_RUN_IDENTITY / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`.
> A fresh Attempt 5 GPU prestage and identity must be created; every command
> below remains historical context only.

Historical checkpoint status: `PERSISTENT_PRESTAGE_VERIFIED / RESEARCH_POD_STOPPED / ATTEMPT_3_IDENTITY_NOT_FROZEN / NO_EXTERNAL_QUERY / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Purpose

Attempt 2 proved that the anchored fail-closed evidence path works, but it
did not reach CUDA or the model. Attempt 3 will rerun the official Jacobian
technical canary with the runtime virtual environment and the frozen
dependency source bundle physically separated. Attempt 2 must remain
unchanged.

The repair is operational. Do not weaken the dependency verifier, remove only
one symbolic link, edit the frozen 15-file bundle, or reuse the Attempt 2
identity.

## Completed persistent pre-stage on 2026-07-22

The research pod was restarted only long enough to prepare and verify reusable
bytes on its persistent `/workspace` volume. No official Attempt 3 workspace,
nonce, run ID, protocol, anchor payload, RFC3161 query, CUDA execution, or
model execution was created. The pod was stopped again after verification;
the RunPod UI showed compute `Not running` and total idle storage rounded to
`$0.01/hour`. The production pod was untouched.

The exact frozen verifier accepted the corrected dependency root:

- root: `/workspace/cas-jlcv1-dependency-bundle-a8969eb7`
- regular files: `15`
- file-manifest SHA-256:
  `10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`
- lock SHA-256:
  `deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`
- linked or extra entries: none

The frozen runner's import boundary was also rechecked against the persistent
runtime layout. Before loading the ML stack it rejects any preloaded `torch`,
`transformers`, or `jlens` module; it then places the verified dependency root
first on `sys.path` and fails closed unless `jlens.__file__` resolves inside
that verified root. The ordinary virtual-environment import observed during
operator diagnostics therefore cannot silently substitute the bootstrap copy
of `jlens` during the official runner path. This is a source-control check,
not model execution or a scientific result.

Other persistent pre-stage identities were also verified:

- runtime Python:
  `/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python`
  (`Python 3.11.10`, PyTorch `2.12.0+cu130`, Transformers `5.9.0`,
  NumPy `2.4.6`);
- reconstructed repository: `/workspace/cas-jlcv1-repo-a8969eb7`, exact
  commit/tree listed below, clean after checkout;
- exact implementation bundle:
  `/workspace/cas-jlcv1-implementation-a8969eb7.bundle`;
- exact implementation manifest:
  `/workspace/cas-jlcv1-implementation-manifest-a8969eb7.json`;
- regular-file Pythia snapshot: `/workspace/cas-model-a8969eb7`; all five
  file hashes match the frozen model manifest, including model-weight
  SHA-256
  `29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270`;
- frozen input publications:
  `/workspace/cas-jacobian-v1-bootstrap/01_FROZEN_INPUTS`; the model, source,
  provider, attestation, token, and publication-marker hashes match the
  registered values.

An initial unexecuted upload used an older bundle. It was detected by its
SHA-256 before checkout, relabeled
`/workspace/cas-jlcv1-implementation-rejected-a40efb18.bundle`, and never
used for an official workspace, protocol, anchor, or execution. Its SHA-256
is `a40efb18b647272bfd199be036ae04bae86ea3ec60f6fef5984fa2702e1685f6`.

The explicitly unanchored operator record is
`05_ATTEMPT_03_PRESTAGE_OPERATOR_RECORD.json`, SHA-256
`15ae9676a0abdea93b006dd4712a860cf01a018f41f341d3777796f5847b9604`.
It is reproduction context, not a provider attestation or scientific receipt.

## Frozen implementation identities

- source commit: `a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0`
- source tree: `cce2d477bb0f423ee6a2669ee680eaac7b999322`
- implementation-manifest SHA-256: `5561105d014d0bd3a943fc9d498ebc6f657b2e1024018ff95af06f244a9974fa`
- complete bundle SHA-256: `0db2c2f6deb3bf797af2b9a42b84714236f66cce48e6c74b769ccbb63c101fff`
- dependency file-manifest SHA-256: `10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`
- dependency lock SHA-256: `deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`

If any source byte changes, freeze a new commit, tree, bundle, implementation
manifest, tests, protocol bindings, and review record before proceeding.

## Required remote layout

Use separate paths with separate jobs:

- `/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv` - persistent
  runtime environment only;
- `/workspace/cas-jlcv1-dependency-bundle-a8969eb7` - exactly the 15 frozen
  Jacobian-lens dependency source files, all regular files, no `.venv`,
  symbolic links, reparse points, caches, logs, or extra files;
- `/workspace/cas-jlcv1-repo-a8969eb7` - exact clean implementation checkout;
- `/workspace/cas-model-a8969eb7` - exact five regular model files;
- a fresh Attempt 3 workspace - frozen input and operator records;
- a fresh, empty create-once output directory - producer publications only.

The clean source bundle to transfer already exists locally at:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\c\noetic-compass-scaffold\noetic-compass\live-trace-worker\research_environments\jacobian_lens_v1`

## Historical execution checklist (superseded; do not execute)

1. Recheck the signed-in RunPod state and start only the stopped research pod.
   Do not use or modify the production pod. Require an observed GPU capacity
   of at least exactly `24_000_000_000` decimal bytes (`24 GB`).
2. Re-verify every persistent pre-stage path and hash above after restart.
3. Run the frozen dependency-bundle verifier again against the exact remote
   source-only root. Require the exact 15-file manifest and lock hashes above,
   no linked entry, and no extra entry.
4. Confirm the frozen ML import boundary is still clean: no `torch`,
   `transformers`, or `jlens` module may be preloaded, and the runner must
   resolve `jlens` from the verified dependency root.
5. Reconstruct and verify the exact source commit/tree, implementation
   manifest, complete bundle, model revision, execution-token publication,
   input publications, and intended launch target paths.
6. Capture a fresh raw RunPod provider observation, then create a fresh
   Attempt 3 workspace and a pre-existing empty output directory. Generate a
   fresh 32-byte nonce and derive a fresh run ID before creating any canonical
   run-bound controller, network, PRE, or protocol record.
7. Build the fresh canonical controller receipt from that raw observation and
   nonce record. Freshly generate the runner Git/OpenSSL and receiver
   Git/Python/NumPy/OpenSSL binding records for this run.
8. Build a fresh run-bound two-phase network-guard plan from those actual
   bindings, including a fresh absolute-path, byte-count, and SHA-256 binding
   for the current `libseccomp.so.2`. Do not reuse Attempt 2's plan or hashes.
9. Capture fresh PRE evidence only after the final runtime, dependency, model,
   tool, host, and guard layout is fixed. PRE must bind this run ID and the
   fresh network-plan SHA-256.
10. Freeze the fresh V1 protocol and the separate 22-path launch-target
   mapping. The mapping's base-protocol target must be the raw V0 protocol.
   Do not build the launch configuration yet; it requires the verified
   timestamp response and anchor receipt created below.
11. Freeze the fresh anchor payload and RFC3161 query.
12. Record the query's exact byte length and SHA-256, then present those exact
   bytes to the owner for a new explicit disclosure approval. Do not send the
   query before that approval, and send the approved query at most once.
   Keep the research pod running and every bound local/remote byte unchanged
   while approval is pending. If the pod restarts or any binding changes,
   preserve the unsent query as superseded and restart with a fresh nonce,
   PRE, protocol, payload, and query.
13. Retain the response bytes and transport record, then verify the returned
    RFC3161 nonce, imprint, policy, signature, responder chain, and pinned
    trust root. Build the verified anchor receipt only after those checks pass.
14. Build and hash the launch configuration from the verified anchor receipt,
    timestamp query/response, fresh protocol, and frozen path mapping.
15. Run the unchanged official wrapper. Preserve every log and receipt whether
    it passes or fails.
16. Capture POST evidence, recover the whole attempt directory, independently
    rehash it off-pod, and run the standalone receiver.
17. Stop the research pod after complete recovery and independent
    verification. Record the final provider state and cost state.

## Technical-pass boundary

A successful wrapper exit alone is not a technical pass. The receiver must
independently establish the expected phase-two TSYNC/post-guard CUDA evidence,
the exact `24_000_000_000`-byte (`24 GB`) capacity gate,
all `213` registered artifacts, all `1,248` registered autograd calls, exact
PRE/POST bindings, and the protocol's remaining pass conditions. Any missing
or contradictory field fails closed. Even a verified technical pass remains
`SHADOW / verdict_influence=NONE` and does not by itself license semantic
probing, prompt-injection detection, steering, universality, 300B operation,
production use, or `ACCEPT`.

## Replay-governance hardening

The current implementation prevents reuse of a nonempty output directory but
does not globally prove that a nonce, anchor, or run ID was never reused in a
different empty directory. Attempt 3 governance therefore requires a fresh
identity by procedure. Add an append-only consumed-run-ID/attempt ledger
before treating global replay prevention as closed.

The standalone receiver does not currently ingest the launch configuration or
the path-mapping file. Retain and hash both files, and require the producer to
enforce their expanded content, but do not describe either file as
independently receiver-bound or RFC3161-anchored until that receiver boundary
is implemented.

## What follows a verified Jacobian technical pass

Only after independent technical closure should the separate
`CJT_JSPACE_OHM_JOINED_CANARY_V0` experiment begin. That downstream study
must preregister signed intervention doses, CJT Bias operating points, intact/
disrupted/sham RPM conditions, prompt groups including injection families,
output-steering outcomes, held-out evaluation, uncertainty, and matched, sham,
random, orthogonal, and wrong-sign controls. It requires its own fresh anchor
and cannot inherit a scientific conclusion from the Jacobian canary.
