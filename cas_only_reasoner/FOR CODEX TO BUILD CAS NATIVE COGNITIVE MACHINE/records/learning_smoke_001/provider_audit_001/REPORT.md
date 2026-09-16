# Ordered-ingestion smoke: provider and spending audit

Status: **READ_ONLY_PREFLIGHT_PASSED — NEW_SMOKE_PACKAGE_AND_BINDINGS_REQUIRED**.

Observed 2026-09-16 17:54:27–17:54:40 UTC, AWS account `807562639912`, region
`us-west-2`, existing `default` profile. No credentials were printed. This audit
created no reservation, provider resource, billing change or model execution.

## Money and authority

The authoritative campaign ledger is the `meta1` copy, not the publication copy:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json
```

Its current head and all 75 history states passed `aws.budget.read_locked`:
revision 74, 76 reservations, $5,000 cap, $431 reserved, **$4,569 unreserved**.
Head SHA-256: `cd3928d0c0ae646de22612356618c709ea4ecd353bbf3b80d07e2aafbcc1546d`.
The vision-next publication copy is byte-equal. The audit checked stable head and
history bytes before/after without creating a lock. The real launch must recheck
through the canonical atomic reservation path.

The owner amendment raises the inclusive campaign cap from $400 to $5,000 and
preserves the no-refund rule and $7 per-job reservation. The original captured
goal and later in-session amendment remain separately hash-bound; the amendment
is not a new `get_goal` artifact. These are conservative reservation totals, not
invoiced charges. A new $7 reservation would leave $4,562 if nothing else changes.

Standing project authorization can be recorded for the concrete new smoke. It
must identify this job/package, state training=true and exact update/runtime
bounds, preserve the actual owner instruction and bind its own file hash. Do not
reuse the consumed old diagnostic owner record: it explicitly permits zero
updates, zero checkpoints and one different job. No new authorization record was
created by this audit, and no further user confirmation is inferred here.

## Current provider observations

- STS verified the expected account with the existing signed-in profile.
- No pending, running, stopping or shutting-down EC2 instances were returned
  across this account/region; no tagged CAS instances were returned when stopped
  instances were included. Both responses were unpaginated.
- The old ordered diagnostic's security group, worker role, instance profile and
  schedule are absent. Its instance query now returns no listed instance. Its
  earlier retained receipt reported termination; this new query does not invent
  a fresh termination event.
- `g7.2xlarge`: 8 vCPUs, one NVIDIA RTX PRO 4500 with 32 GiB GPU memory.
  The current on-demand Linux/shared price is $2.5200000000/hour.
- Applied quota `L-DB2E81BA`, Running On-Demand G and VT instances: 8 vCPUs.
  With no active instances, this fits one configured instance. It is not a
  capacity guarantee.
- AMI `ami-0fbbd0facbc9e3cff` is available, x86_64, Ubuntu 24.04 NVIDIA-driver base.
  Offerings and available default subnets exist in us-west-2a/b/c/d. The existing
  launcher's preference remains a, b, c; do not silently add retries or placement
  changes after a capacity failure.

`provider.json` retains query timestamps, request IDs and filtered responses.
No RunInstances, dry-run, quota increase, credential change or billing API was used.
Read access does not prove IAM creation, S3 writes, instance launch or capacity.

## Exact reusable path and prerequisites

Use `aws.graph_training_candidate_launch.CandidateProvider` and its `execute`
function with new request/authority validators and an explicit canonical ledger.
The existing lifecycle enforces owner bounds and one-use records, verifies the
source archive before reserving once, records the AWS-side reservation, creates
the bounded worker, collects declared evidence and runs compute cleanup in
`finally`. Reuse `aws.run_evidence` transport and a predeclared evidence contract;
preserve incomplete evidence independently of stopping compute.

Use `aws.ordered_encoder_launch` as a design example for a new wrapper, not as the
training launcher: its worker, authority and result contracts enforce zero
optimizer updates. The shared runtime ceiling is one instance, 7,200 seconds,
$7 reservation, zero automatic retries, encrypted 75-GiB EBS with delete-on-
termination, no inbound rules and HTTPS egress. The new smoke must also enforce
its smaller, explicit inner subprocess deadline and update count.

The committed-member resolver and manifest builder are in
`aws.graph_training_curriculum_launch`. Both frozen wheels exist and match:

| Wheel | SHA-256 |
|---|---|
| casformer_reference-0.1.0-py3-none-any.whl | `0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee` |
| cas_neural_cjt-0.2.0-py3-none-any.whl | `6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9` |

They are under `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist`.
The raw `cas_cjt/neural.py` source also exists, hash
`03521d2b17311680fd91cde7076e4bf5b38393f0d6db115d47be20f63413fc96`.
Worker setup installs torch 2.11.0 from the cu128 index, the two wheels without
dependency resolution, and pinned numpy/jsonschema/pytest requirements, on AWS
Python 3.11/3.12. This audit did not import them or install anything.

The new `cncm` adapter/cycle modules and their dependencies are outside the shared
resolver's automatic research-source directories. Explicitly include all required
committed `cncm` files, exposed fixture bytes and worker source, and add both the
package root and research root to worker `sys.path`. Rehearse the actual extracted
archive before paying. Bind exposed material only; exclude candidate final panels
and inherited legacy checkpoints. Require fresh matched initialization and exact
ordered-encoder identity, plus train/checkpoint/reload/public-prediction evidence.

Open gates: finish/freeze the new worker and reload code; build and rehearse its
committed archive; bind exact owner/request/authority/config/evidence files; then
re-run current preflight and make one canonical reservation. No merge, deployment,
CI success, numerical smoke completion or learned improvement is claimed.

All audit inputs, budget history and local prerequisites are pinned in
`budget.json`, `local.json`, `provider.json`, `finish.json` and `receipt.json`.
