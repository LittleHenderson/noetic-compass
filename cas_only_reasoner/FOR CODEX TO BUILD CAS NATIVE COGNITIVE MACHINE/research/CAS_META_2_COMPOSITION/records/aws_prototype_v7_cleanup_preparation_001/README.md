# V7 cleanup and cost observation — prepared, not executed

This records-only helper is for exactly
`cas-meta2-20260906094002-39762c47`, source
`42f9164754312f12850d9b8789c062fa7fb8069f`. Its names were checked against the
actual local launch receipt. This preparation performed no AWS call.

The seven cleanup checks cover instance `i-0cba54498bb3a3745`, job-tagged EBS
volumes, security group `sg-0afb9d8c6c74b706e`, the `-worker` instance profile,
the `-worker` role, the `-timer` role, and the scheduler named after the job.
Account `807562639912` and region `us-west-2` are fixed. Resource names cannot
be supplied as general-purpose command-line targets.

## Future use

Default mode is local preparation only:

```text
python -B records/aws_prototype_v7_cleanup_preparation_001/check.py
```

After the launch receipt has a final status, root can hash that exact receipt
and explicitly run the following with its actual hash:

```text
python -B records/aws_prototype_v7_cleanup_preparation_001/check.py --observe-aws --launch-receipt-sha256 FINAL_RECEIPT_SHA256 --output records/aws_prototype_v7_001/cleanup_cost_check_001.json
```

The placeholder above is not accepted. The helper checks the external final
receipt hash, exact job/source/resources/plan/reservation/recorded price before
creating a provider client. It rejects a still-`STARTING` receipt. The output
must be a new JSON file inside the exact job's records directory. It checks the
launch receipt and ledger hashes again afterward; neither is edited.

The explicit observation makes at most nine direct read-only operations: one
STS identity call, seven cleanup calls, and one bounded read of the retained
S3 `results/complete.json` object. SDK retries are disabled. It performs no
launch, termination, deletion, retry, budget reservation or refund. The S3
bucket remains under its existing separate retention policy.

## Time and cost boundaries

Every successful cleanup observation records the request ID and exact HTTP
Date supplied by AWS. Instance identity includes its provider `LaunchTime`,
which must match the launch receipt. The S3 completion object must match the
final launch receipt's result before its `LastModified` time is used. That
timestamp means the completion object was written; it is not the exact GPU
computation end time.

The compute estimate uses the recorded $2.52/hour rate. Launch-to-completion
and launch-to-termination-observation are reported separately. The latter uses
the provider response date plus one second because HTTP Date has one-second
precision. This is an upper observation endpoint, not an exact termination
timestamp. A running or unverified instance gets no completed-runtime bound.

The unchanged reservation is $7. The registered maximum planning estimate is
$6.46: $2.52/hour over 7,800 seconds plus a $1 ancillary allowance. The helper
also compares the observed compute estimate plus that same allowance with $7.
This comparison does not establish total cost: EBS, public IPv4, S3, transfer,
taxes and other fees are not measured. The allowance is not a provider receipt.
No invoice or automatic refund is claimed.

## Executed local tests

```text
python -B -m pytest records/aws_prototype_v7_cleanup_preparation_001/test_check.py -q -p no:cacheprovider -p cas_meta2.pytest_no_aliases_v4
CAS_PYTEST_ALIAS_SUPPRESSIONS=0
24 passed
```

Tests use synthetic responses only. They check all seven exact selectors,
nine read-only calls, provider timestamps, missing/foreign/live resources,
pagination, permission errors, completion-object mismatch, cost arithmetic,
and refusal to make clients without an explicit final-receipt pin.
