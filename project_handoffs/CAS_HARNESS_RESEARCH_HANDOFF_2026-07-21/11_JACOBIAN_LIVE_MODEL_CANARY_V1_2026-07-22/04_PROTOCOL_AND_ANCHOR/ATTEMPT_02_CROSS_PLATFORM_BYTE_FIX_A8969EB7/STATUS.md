# Attempt 2 final status

Status:

`RFC3161_ANCHOR_VERIFIED / OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_PRE_CUDA_PREFLIGHT / NO_MODEL_OR_CUDA_EXECUTION / FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION / SHADOW / NONE / NOT_LICENSED`

The explicitly approved exact 105-byte RFC3161 query, SHA-256
`2cdd55bcc9af08ffe478b5a0e5f6a0e68172ccbf70588d4a6d8c1cbcada542f4`,
was sent once to DigiCert. DigiCert returned HTTP 200 with a 6,035-byte
response, SHA-256
`d81216b3d34a5c114aca53086fd96789563b71ac3c30178305a8ac326b9f0eca`.
Independent verification bound the query nonce, payload imprint, policy,
signature chain, responder certificate, and pinned root at
`Jul 22 18:57:15 2026 GMT`. The canonical anchor-receipt SHA-256 is
`2b9daefdf02b03c6e071cc850f452c706844cddf99bac03dd47f6e9ab17bd63c`.

The anchored official shadow attempt entered phase-one seccomp preflight and
published a create-once failure receipt. It failed closed at
`PRE_CUDA_PREFLIGHT`; failed gates were `PRE_CUDA_BINDINGS_UNVERIFIED` and
`PRE_CUDA_PREFLIGHT_FAILURE`. The exact retained failure hash resolves to:

`PRE_CUDA_PREFLIGHT:CanaryContractError:dependency bundle contains a linked directory`

Root cause: the launch mapping pointed `dependency_bundle_root` at
`/root/cas-jlcv1-env`, which combined the exact 15-file frozen dependency
source bundle with the live Linux `.venv`. A Linux virtual environment contains
linked directories, while the verifier correctly requires the frozen source
bundle to contain only its 15 exact files and no links or extras. The repair is
an operational path separation: keep `/root/cas-jlcv1-env` as the runtime and
use a separate clean source-only bundle root for Attempt 3.

CUDA was not initialized, model weights and execution-token tensors were not
authorized or materialized, no model block ran, no artifact was produced, and
observed autograd calls were `0/1,248`. Producer status is `FAILED_CLOSED`;
verdict is `NONE`; claim status is `NOT_LICENSED`.

The standalone receiver independently verified the retained publication chain,
exact bound bytes, RFC3161 anchor, PRE/POST evidence, and operator-retained
provider/environment bindings. PRE/POST status is
`IMMUTABLE_ENVIRONMENT_MATCH`. Receiver status is
`FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION`; scientific
conclusion is `NO_SCIENTIFIC_CONCLUSION`. Receiver-receipt SHA-256 is
`c0cef95574997d707e1fd30ad3286338182f7aa1f76bde81afab8a82659a28d1`.

The A40 research pod was stopped after the complete evidence chain was copied
and independently verified. The production pod was not used or changed.

This result creates no `ACCEPT`, technical pass, semantic-probing,
prompt-injection, output-control, J-Space, CJT, RPM, CAS-Ohm, universality, or
300B license. Preserve Attempt 2 unchanged as negative evidence. Attempt 3
requires a separate clean dependency source root, fresh empty workspace and
output, fresh PRE capture, nonce, run ID, protocol, launch mapping, RFC3161
query/response, and anchor. Do not reuse this run ID or anchor for changed
launch bytes.
