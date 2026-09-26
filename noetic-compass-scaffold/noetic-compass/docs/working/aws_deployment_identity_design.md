# AWS deployment identity: design proposal

Status: **proposal, awaiting owner decision.** No code in this document has been applied.

## The problem

`scripts/tests/test_acceptance_authority_contract_alignment.py` pins the production identity
as a single tuple and asserts that about ten modules agree on it. The tuple is Render's:

| Field | Current value | Render-specific? |
|-------|---------------|------------------|
| `PRODUCTION_API_ORIGIN` | `https://cas-harness-customer-api.onrender.com` | yes — hostname |
| `PRODUCTION_SERVICE_ID` | `srv-d9bijbjtqb8s73cn4n20` | yes — Render service id |
| `PRODUCTION_SERVICE_NAME` | `cas-harness-customer-api` | no — lane name |
| `PRODUCTION_DISK_ID` | `dsk-d9bijbjtqb8s73cn4o60` | yes — Render disk id |
| `PRODUCTION_DISK_NAME` | `cas-harness-customer-support` | no — mount name |
| `PRODUCTION_DISK_MOUNT_PATH` | `/var/customer-support` | no |
| `PRODUCTION_LEAD_STORE_PATH` | `/var/customer-support/leads.jsonl` | no |
| `RENDER_SERVICE_URL` | `https://api.render.com/v1/services/srv-…` | yes — Render API |
| `PRODUCTION_HEALTH_URL` | `<origin>/health` | derived |

Modules carrying these values: `api/acceptance_authority_contract.py`,
`api/services/customer_production_acceptance_authority.py`,
`scripts/verify_customer_production_acceptance.py`, `scripts/verify_production_runtime_readiness.py`,
`scripts/collect_customer_readiness_facts.py`, `scripts/collect_root_ci_protected_deploy_facts.py`,
`scripts/collect_airtable_crm_acceptance_source.py`, `scripts/collect_hosted_customer_journey_evidence.py`,
`scripts/collect_runtime_worm_evidence.py`, `scripts/collect_hosted_runtime_worm_evidence.py`,
`scripts/collect_operational_acceptance_draft.py`, `scripts/build_alert_delivery_gate_payload.py`,
plus the scaffold-side `build_support_crm_acceptance_evidence.py` and
`publish_customer_production_acceptance_authority.py`.

Three of them do more than read a constant. They ask the platform who they are:

```python
if os.environ.get("RENDER_SERVICE_ID") != PRODUCTION_SERVICE_ID:
    refuse()   # evidence must never be collected from an unintended service
```

That guard is load-bearing. Today, on AWS, `RENDER_SERVICE_ID` is absent, so the guard cannot
pass in its current form — which is why this is a design question and not a rename.

## What changes mechanically

Five of the nine fields are provider-neutral and need no decision:

| Field | New value |
|-------|-----------|
| `PRODUCTION_API_ORIGIN` | `https://api.noeticcompass.com` |
| `PRODUCTION_SERVICE_NAME` | `cas-harness-customer-api` (unchanged) |
| `PRODUCTION_DISK_NAME` | `customer-support` |
| `PRODUCTION_DISK_MOUNT_PATH` | `/var/customer-support` (unchanged) |
| `PRODUCTION_LEAD_STORE_PATH` | `/var/customer-support/leads.jsonl` (unchanged) |

## What needs your decision

### 1. The service-identity guard

Render injected `RENDER_SERVICE_ID`; AWS does not inject an equivalent. Proposed: inject
`NC_DEPLOYMENT_SERVICE_ID` through SSM into both lanes, set to the EC2 instance id
(`i-0bd0a082507a51ae3` for customer-production, `i-02137d196e671b5c1` for the canary), and
change the guard to compare against it. Same shape, same fail-closed behaviour, no platform
magic.

Alternative: use the ECR image digest as the identity. Stronger — it pins the exact artifact
rather than the box running it — but it changes on every deploy, so the constant would have to
be read from the environment rather than pinned in the repository, and the alignment test
would lose its fixed-value assertion.

**Recommendation: instance id for the guard, image digest additionally recorded in evidence.**

### 2. The disk identity

`PRODUCTION_DISK_ID` is Render's disk. Proposed: the EBS volume id attached at
`/var/customer-support`:

| Lane | Root volume | Data volume |
|------|-------------|-------------|
| customer-production | `vol-09b429279cab8cf13` (`/dev/xvda`) | **`vol-056e0897eb5b72c4c`** (`/dev/xvdb`, mounted at `/var/customer-support`) |
| accounts-canary | `vol-0edcf704c0b197f83` (`/dev/xvda`) | none — the canary keeps packet bytes on the root volume |

So `PRODUCTION_DISK_ID` becomes `vol-056e0897eb5b72c4c` and `PRODUCTION_DISK_NAME` becomes
`customer-support`, recorded in `.aws/deployment-control.json` alongside the instance id.

### 3. The root-CI deploy evidence — the real question

`collect_root_ci_protected_deploy_facts.py` currently gathers its facts from Render's API:

```
https://api.render.com/v1/services/{id}/deploys?status=live&limit=2
https://api.render.com/v1/services/{id}/deploys?limit=1
```

and validates a Render deploy id against `^dep-[A-Za-z0-9]+$`. This feeds the
`root_ci_protected_deploy` acceptance gate, whose meaning is: *the protected-master commit
that CI signed off is the one actually running in production.*

AWS has no single equivalent. The closest honest construction is:

| Evidence | AWS source |
|----------|-----------|
| Which commit produced the running artifact | the protected `master` SHA baked into the image as a build argument at build time, exposed by the service |
| Which exact artifact is running | the ECR image digest of the deployed tag |
| Which build produced it | the CodeBuild build id and its source SHA |
| What is serving it now | the App Runner service revision, or the EC2 instance plus CloudFront distribution |

Those four are verifiable and dereferenceable, and together they mean the same thing the Render
deploy id meant. But they are a **different evidence shape**, so this changes what the gate
accepts, not just where it reads from.

Options:

- **A. Build the AWS equivalent** (recommended). Add a build argument carrying the protected
  `master` SHA, bake the image digest and build id into the service environment, and write a new
  collector that produces the same four facts from AWS. The gate keeps its meaning and its
  fail-closed posture; the evidence fields change shape, so the acceptance contract documents
  that.
- **B. Keep the Render deploy evidence** until Render is fully retired, and accept that this one
  gate cannot pass on AWS in the meantime. Cheapest, but the gate stays red and the migration is
  incomplete in a documented way.
- **C. Drop the gate** for the AWS lanes. I do not recommend this: it removes the check that the
  signed-off commit is the one running, which is one of the few controls that actually
  distinguishes this product's deployment story.

**Recommendation: A.** It is more work than B and far less than the value of the control.

### 4. Narrowing the Render control

`render-blueprint-control-offline` is a required status check and `.render/blueprint-control.json`
lists three blueprints. Once the customer and canary identities move, those two must leave the
Render manifest and the Render verifier's expectations, leaving only the accounts-off lane.

This does **not** shut down any Render service. It only stops the repository claiming that
Render is where production runs. The services themselves still get retired last, exactly as
planned, and the live Render check keeps verifying the one lane still declared there.

## What the change looks like when done

One pull request containing: the tuple rewrite across the modules listed above, the identity
guard change, the new root-CI collector for AWS, the Render manifest narrowed to one blueprint,
the Render verifier and its tests narrowed to match, the alignment test rewritten to the AWS
tuple, and `scripts/plan_render_hostname_sweep.py --apply` to move the remaining hostname
references. Then the acceptance contract records the new evidence shape.

## What I will not do without your say-so

Rewrite the acceptance/evidence machinery so that a gate accepts a different kind of proof.
That is a change to what counts as evidence, and it is yours to authorise, not mine to assume.
