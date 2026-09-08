# Binding-fit training check — launch attempt 001 refused at preflight (negative record, $0 spent)

Status: REFUSED_AT_PREFLIGHT. This attempt never created a budget reservation,
never launched an instance, and spent nothing. It is recorded here permanently;
it is not a retry target and its job id must never be re-executed.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-binding-20260908120635-035f9ac7` |
| request sha256 | `7910b607fc875f608a6cf6a38cace17abd3399e7ca5cde2b65dcf0627ba73cac` |
| authority sha256 | `bf7b421ef0e2a770582c8363552898a78ae55ac1373725fe43d516e7461a6fd0` |
| source_sha (freeze commit) | `31e787923390cfdfc83d2326b48e606da0fa71a1` |
| archive_sha256 | `ddf39e5ea481c74b7f14ff866969dabb814ef83fa288e657af93d5b3520e55e9` |
| manifest_sha256 | `bfb6379457ce699e43e8bca1c51357e743169ae42cfd26d328717893b2e6a94f` |
| reservation created | no |
| reservation_usd spent | `0.00` |
| instance launched | no |

Evidence: `receipt_cas-meta2-teaching-binding-20260908120635-035f9ac7/intent.json`
(the full byte-bound request/authority/ledger snapshot) and
`receipt_cas-meta2-teaching-binding-20260908120635-035f9ac7/failure.json`.

## What failed

`failure.json` (verbatim):

```json
{"exception":"An error occurred (AccessDeniedException) when calling the GetProducts operation: ","exception_type":"AccessDeniedException","stage":"preflight"}
```

The preflight got through STS identity, the AMI, the instance type, and the
instance-type-offerings checks, then failed on the AWS Price List API call
(`pricing.get_products`), which the launcher was issuing from `us-west-2`.

## Root cause

The AWS Price List API only serves its bulk endpoint from `us-east-1` (and
`ap-south-1`). A pricing client built with the session region `us-west-2` gets
`AccessDeniedException` on `GetProducts`. The launcher built every client —
including `pricing` — with the frozen session region.

## Fix (committed with this record)

`aws/binding_fit_launch.py` `build()` now builds the five resource clients
(`sts`, `ec2`, `iam`, `s3`, `scheduler`) with the frozen session region
`us-west-2` and the `pricing` client explicitly with `region_name="us-east-1"`.
A regression test was added:
`tests/test_binding_fit_launch.py::test_build_prices_client_from_us_east_1`
(launcher test count is now 35).

The frozen resource plan, the source archive, and the manifest are unchanged:
the launcher module is not a package member, so `source_sha`, `archive_sha256`,
and `manifest_sha256` for the re-attempt are identical to this attempt's.

## Policy basis for a corrected re-attempt

- Zero automatic retries: no part of this attempt is re-run.
- This attempt reserved nothing and spent `$0.00`; its refusal was a preflight
  refusal, not a consumed run.
- The corrected re-attempt therefore uses a NEW job id
  (`cas-meta2-teaching-binding-20260908191109-dcf939ab`), new request/authority
  files (in `launch_inputs_002/`), and a new receipt directory. This is a
  refused-launch recovery, not a retry; the attempt-001 files above are
  preserved untouched as the negative record.
