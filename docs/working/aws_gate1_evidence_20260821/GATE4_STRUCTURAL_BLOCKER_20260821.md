> # ⚠️ SUPERSEDED — THIS PAGE'S CONCLUSION IS WRONG
> **Corrected the same day by `GATE4_CORRECTION_REAL_BLOCKER_20260821.md`.** The findings about the canary hard-requiring an arm receipt are correct. The conclusion — that Gate 4 needs the AWS VPC guardian stack built — is **wrong**. That template is a *reference design*; the implementation the canary actually uses (`precreate_guardian_offline.py` + the GitHub stop supervisor) already exists and is hash-locked. **The real blocker is one missing GitHub secret, `RUNPOD_CANARY_V2_API_KEY`.** Retained undeleted because a wrong call that was caught is part of the record.

# GATE 4 — STRUCTURAL BLOCKER — the canary cannot launch, and the reason is by design

**Date 2026-08-21. Everything below was read from the frozen source, not inferred.**

Gate 4's stock and price step **passed** (Secure Cloud A40, `$0.44/hr`, `High`, `9 max`). The launch itself is blocked by a prerequisite that **cannot be satisfied today**, and this page is the proof, because "I chose not to launch" and "the system refuses to launch" are very different claims and only the second one is true.

---

## 1. The canary hard-requires an armed pre-create guardian. It cannot be switched off.

`run_open_weight_trajectory_canary_v2.py:805-810`:

```python
if launch.get("precreate_guardian_required") is not True:
    raise ValueError("pre-create guardian must remain required")
if launch.get("required_precreate_guardian_receipt_schema") != (
    "cas_runpod_precreate_guardian_arm.v1"
):
    raise ValueError("pre-create guardian receipt schema mismatch")
```

This is not a flag that can be set to `false`. Setting it to `false` **raises**. The requirement is welded into the loader.

## 2. The launch receipt is structurally impossible without that guardian.

`run_open_weight_trajectory_canary_v2.py:1318-1347` — the provider launch receipt keyset is exact-match (`if set(value) != required: raise`), and the required set **includes**:

- `precreate_guardian_receipt_sha256` — and `_required_upper_sha256` enforces it is a real 64-hex digest
- `precreate_maximum_hard_stop_deadline_utc`

So a launch cannot even be *recorded* without a genuine arm receipt from a live pre-create guardian. There is no path around this that does not involve forging a hash — which is the definition of weakening a gate.

## 3. The pre-create guardian is explicitly, deliberately not deployable.

`infra/runpod_precreate_guardian_aws/template.yaml`, lines 1-30:

```yaml
Description: >-
  INERT, non-deployed architecture reference for an independent RunPod
  pre-create guardian. It is not a deployment candidate. ...
  A separate reviewed successor is required for any live action.

Metadata:
  GuardianBoundary:
    Status: INERT_REFERENCE / NOT_A_DEPLOYMENT_CANDIDATE / NO_EXECUTION_AUTHORITY

Parameters:
  ActivationMode:
    AllowedValues:
      - INERT          # LIVE is deliberately absent
```

Deploying this template produces an **INERT** stack that arms nothing. `LIVE` is not merely unset — it is **absent from the allowed values**, and the template says changing that "requires a new review and source identity."

## 4. Even the INERT reference needs infrastructure that does not exist.

**All 17 template parameters are required; none has a default.** They include:

| parameter | what it demands |
|---|---|
| `GuardianVpcId` | a VPC with **no Internet Gateway or NAT route** |
| `GuardianPrivateSubnetIds` | **≥2 private subnets in distinct AZs**, no public route |
| `GuardianPrivateRouteTableIds` | their route tables, for a DynamoDB gateway endpoint |
| `DynamoDbManagedPrefixListId` | the regional managed prefix list, re-read before deploy |
| `ApiClientSecurityGroupId` | a same-VPC SG attached only to reviewed SigV4 clients |
| `ObserverProxySecurityGroupId` + `ObserverProxyHost` | a proxy admitting **only** `LIST /v1/pods` and `GET /v1/pods/{exact-id}` |
| `CreateProxySecurityGroupId` + `CreateProxyHost` | a proxy admitting **only** `POST /v1/pods` with exact ledger-bound bytes, with a one-reservation transport allowlist |
| `StopProxySecurityGroupId` + `StopProxyHost` | an equivalent stop-only proxy |

**None of this exists.** Building it means a private VPC plus **three HTTP-filtering egress proxies** that enforce method-and-path allowlists against RunPod's API. That is real infrastructure engineering, not a deploy command.

---

## What this means, stated honestly

**Gate 4 cannot complete today, and no amount of care on my side changes that.** The two available routes are:

1. **Build a reviewed, deployable successor** to the pre-create guardian, plus the private VPC and the three filtering proxies. Substantial, multi-session work — and the template's own text says a successor requires "a new review and source identity."
2. **Remove the requirement from the preregistration.** This is the fast route and it is the forbidden one: it deletes the only independent authority that can stop a paid pod when the launching process dies, and it requires forging `precreate_guardian_receipt_sha256`. That is precisely *"do not weaken a gate to make it pass."*

**Why the guardian matters concretely:** it is what stops a running `$0.44/hour` pod if this laptop loses power, the network drops, or the process is killed between create and stop. Without it, the "hard 30-minute limit" is enforced only by the same process that created the pod. If that process dies at minute 3, the pod bills until a human notices.

## What is genuinely ready

Everything else for Gate 4 is done and proven:

- Stock and price **checked and passed** — `$0.44/hr`, `High`, `9 max`, Secure Cloud.
- The model that **could not load** — found and fixed, re-pinned artifact loads and captures.
- The create-path **IAM gap that would have burned the paid attempt** — found and fixed.
- Gates 1, 2, 3 complete; the preprod control plane is **LIVE** with both binding gates verified.
- Independent stop layers that **do** exist: the GitHub Actions stop-supervisor and the local watchdog. They are real, but the canary does **not** accept either as a substitute for the pre-create guardian receipt.

## Recommendation

Treat "build the deployable pre-create guardian successor" as **its own scoped piece of work**, sized and reviewed on its own terms. It was never costed in the gate list, which is why the gate list reads as if Gate 4 were one step away. It is not.

**No pod created. No GPU exists. The A40/Pythia experiment remains `NOT RUN` — neither passed nor failed.**
