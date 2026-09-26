# Render → AWS: identity handoff

Written 2026-09-26. Companion to `render_to_aws_lane_migration_2026_09_26.md` (what moved and
why) and `aws_deployment_identity_design.md` (the approved design). This document is the
precise inventory for the remaining engineering, written so it can be finished without
re-deriving any of it.

## Where the migration stands

| Lane | State | Verified how |
|------|-------|--------------|
| accounts-off (serves `noeticcompass.com`) | live on App Runner, `bmxq2dmdam.us-west-2.awsapprunner.com` | login mints a token, `/scenarios` returns 400546 bytes |
| customer-production | live on EC2 `i-0bd0a082507a51ae3` + private RDS `nc-customer-pg` behind CloudFront `d2zcr7t1an5spf.cloudfront.net` | `/health` 200, `/health/ready` reports database ok and s3_worm verified, `/deployment` reports a configured identity |
| accounts-canary | live on EC2 `i-02137d196e671b5c1`, zero inbound rules, container bound to loopback | unreachable on 8000/22/443 from outside while healthy inside |
| Atlas viewer | live on S3 `nc-atlas-viewer-807562639912` behind CloudFront `dkpql0p4015ev.cloudfront.net` | `/`, `/audit-console` and deep links all 200; bundles contain `api.noeticcompass.com` and no `onrender.com` |

Secrets: every value that existed only in Render's dashboard was imported into SSM Parameter
Store through a temporary GitHub OIDC job, including all ten continuity keys. Airtable is
verified working (HTTP 200 against base `appXBoYskbfjNaFTs`, table `Leads`). The live worker's
credentials are in place but its RunPod pod answers HTTP 403, so both API lanes report
`ready: false` with `live_worker: unreachable`.

Cost: about `$79/month` calculated. Measured month-to-date is much lower because Cost Explorer
lags; the dominant line in the account is not this migration at all (see the migration record).

## Blocked, and on whom

| Blocker | Owner | Effect |
|---------|-------|--------|
| Two DNS records in the Vercel-managed zone | owner | hostname, TLS, live sweep, Atlas workflow tests |
| Starting the RunPod live worker | owner (GPU spend) | both API lanes stay `ready: false` |
| Reaching suspended Render to export anything it holds | owner (Render account) | step 7 cannot preserve data it cannot read |

The DNS records:

```
CNAME _30a27fe05b7706611a6520c0b2e2fe8f.api  ->  _a29e60938f344c281201dfe70f73a090.wzccmgtwzk.acm-validations.aws.
CNAME api                                   ->  d2zcr7t1an5spf.cloudfront.net
```

Once they exist: `python scripts/cutover_production_hostname.py` performs and verifies the
cutover. It refuses to act until the certificate is ISSUED.

## What remains: the identity swap

The repository still declares Render as production authority in code, and a test enforces that
every module agrees on one tuple. The origin cannot move to AWS while the Render identity stays.

### The tuple

Nine fields across fourteen modules:

| Field | Current (Render) | Becomes (AWS) |
|-------|------------------|---------------|
| `PRODUCTION_API_ORIGIN` | `https://cas-harness-customer-api.onrender.com` | `https://api.noeticcompass.com` |
| `PRODUCTION_SERVICE_ID` | `srv-d9bijbjtqb8s73cn4n20` | `i-0bd0a082507a51ae3` |
| `PRODUCTION_SERVICE_NAME` | `cas-harness-customer-api` | unchanged |
| `PRODUCTION_DISK_ID` | `dsk-d9bijbjtqb8s73cn4o60` | `vol-056e0897eb5b72c4c` |
| `PRODUCTION_DISK_NAME` | `cas-harness-customer-support` | `customer-support` |
| `PRODUCTION_DISK_MOUNT_PATH` | `/var/customer-support` | unchanged |
| `PRODUCTION_LEAD_STORE_PATH` | `/var/customer-support/leads.jsonl` | unchanged |
| `RENDER_SERVICE_URL` | Render API service URL | replaced by the AWS deploy identity |
| `PRODUCTION_HEALTH_URL` | derived | derived (unchanged shape) |

Modules carrying them: `api/acceptance_authority_contract.py`,
`api/services/customer_production_acceptance_authority.py`,
`api/services/acceptance_publication_authorizations.py`, `scripts/verify_customer_production_acceptance.py`,
`scripts/verify_production_runtime_readiness.py`, `scripts/collect_customer_readiness_facts.py`,
`scripts/collect_root_ci_protected_deploy_facts.py`, `scripts/collect_airtable_crm_acceptance_source.py`,
`scripts/collect_hosted_customer_journey_evidence.py`, `scripts/collect_runtime_worm_evidence.py`,
`scripts/collect_hosted_runtime_worm_evidence.py`, `scripts/collect_operational_acceptance_draft.py`,
`scripts/build_alert_delivery_gate_payload.py`,
`noetic-compass-scaffold/noetic-compass/scripts/build_support_crm_acceptance_evidence.py`,
`noetic-compass-scaffold/noetic-compass/scripts/publish_customer_production_acceptance_authority.py`.

Three of them assert platform identity at runtime:

```python
if os.environ.get("RENDER_SERVICE_ID") != PRODUCTION_SERVICE_ID:
    refuse()
```

Approved replacement: `NC_DEPLOYMENT_SERVICE_ID`, already injected into both lanes through SSM.

### The evidence shape — the real work

`scripts/verify_customer_production_acceptance.py` is **3466 lines** and validates receipts
against Render-shaped key sets. The CRM source receipt requires **64 keys, 10 of them named
`render_*`**:

```
render_service_name, render_repository, render_branch, render_auto_deploy_trigger,
render_service_response_sha256, render_deploy_status, render_deploy_commit_sha,
render_deploy_trigger, render_deploy_finished_at_utc, render_deploy_response_sha256
```

`COMMON_EVIDENCE_KEYS` (10 keys) carries `deploy_id`, and `CLAIM_MACHINE_SURFACE_KEYS` carries
three more Render-named fields. So the AWS equivalent must define what replaces each: the image
digest, the CodeBuild build id, the build start time, and the reported commit.

The reader that produces those facts is already built and verified:
`scripts/aws_deploy_identity.py` (19 tests; passes live against production). The service
reports them at `GET /deployment`, and the CodeBuild projects record them in each lane's SSM
path.

### The Render control

`.render/blueprint-control.json` lists three blueprints, `verify_render_blueprint_control.py`
asserts them, and `render-blueprint-control-offline` is a required status check. Once the
identity moves, the customer and canary entries must leave both, leaving only accounts-off.
This does not shut down any Render service; it stops the repository claiming Render is where
production runs.

It turns out the Render manifest does **not** have to be narrowed for the origin to move. The
entanglement is in
`scripts/tests/test_acceptance_authority_contract_alignment.py`, which asserted that the code
constant `PRODUCTION_SERVICE_ID` equalled the Render blueprint's service id. That assertion is
what ties the two together, and replacing it with a check against `.aws/deployment-control.json`
is enough to separate them — the Render manifest may keep describing the suspended Render
services it still governs. That smaller edit was made and passes.

### Measured scope of the swap, from an attempted run

The value substitution was applied once to find out what it actually costs, then reverted. The
numbers below are measured, not estimated:

| Measure | Result |
|---------|--------|
| Files changed by the value substitution alone | **39** |
| Test result afterwards (`scripts/tests`) | **143 failed, 588 passed** |
| Where the failures are | all in `test_verify_customer_production_acceptance.py` |

The failures are not spread out; they are one wall in one file. That file's fixtures encode the
Render identity directly — the Render service id `srv-d9bijbjtqb8s73cn4n20`, the onrender
origin, and the `render_*` receipt keys — so every fixture has to be rebuilt around the AWS
shape before the constants can move. There is no partial ordering that leaves the suite green:
the constants and the fixtures have to change together, in one change, with the acceptance
gates run afterwards.

Also learned: `.aws/deployment-control.json` must be excluded from the substitution. Its
`superseded` entries are the record of which Render services this migration replaced, and
rewriting them would destroy that record.

### The sweep

`scripts/plan_render_hostname_sweep.py` (committed, dry run by default) reports 38 files and 52
occurrences of the Render customer API host, with five files deliberately excluded and reasons
given. It must be applied in the same change as the tuple, because
`scripts/tests/test_acceptance_authority_contract_alignment.py` fails if the code origin moves
while the Render blueprint verifier still expects Render's own URL.

## Recommended sequencing

1. Extend `verify_customer_production_acceptance.py` with an AWS receipt shape, keeping the
   Render shape valid so the older evidence stays verifiable and no gate is silently loosened.
2. Rewrite the tuple across the listed modules; convert `collect_root_ci_protected_deploy_facts.py`
   to call `aws_deploy_identity` for the deployment half and keep its GitHub half.
3. Narrow `.render/blueprint-control.json`, its verifier and its tests to the one remaining lane.
4. Apply the sweep and rewrite the alignment test to the AWS tuple.
5. Run the acceptance gates; the contract documents the new evidence shape.

Steps 1 and 2 are the bulk. Nothing here should be attempted as a partial change: the alignment
test fails closed, which is what caught the premature sweep.

## How to verify the current state

```bash
python scripts/verify_aws_deployment_control.py --offline   # 4 lanes
python scripts/verify_aws_deployment_control.py --live      # compares against real resources
python -m unittest discover -s scripts/tests -p 'test_aws_deploy_identity.py'      # 19 tests
python -m unittest discover -s scripts/tests -p 'test_cutover_production_hostname.py'  # 6 tests
python scripts/aws_deploy_identity.py --deployment-url https://d2zcr7t1an5spf.cloudfront.net/deployment \
  --repository noetic-compass-api --tag v1 --expected-commit $(git rev-parse origin/master)
python scripts/plan_render_hostname_sweep.py                # dry run
python scripts/cutover_production_hostname.py               # refuses until DNS lands
```
