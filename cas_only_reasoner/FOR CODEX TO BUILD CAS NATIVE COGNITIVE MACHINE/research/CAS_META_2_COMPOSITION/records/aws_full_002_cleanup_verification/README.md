# Independent cleanup verification — full AWS job 002

Final result: `CAS_META_2_FULL_002_CLEANUP_INDEPENDENTLY_VERIFIED`.

Use `closure_verification_receipt_v2.json` and `provider_calls_v2.jsonl` as
the completed independent check. All 21 checks passed on 2026-09-05 at
20:55:29 UTC. No cloud resources, original launch evidence, or budget
records were changed by either verification attempt.

The first checker assumed EC2 would still return a terminated-instance
record. The successful exact-ID lookup instead returned `Reservations: []`,
and the checker raised `IndexError` before checking the remaining resources.
Its original helper, provider log, and failure receipt are preserved here.
The second checker handles an absent instance record and also verifies that
no job-tagged instance remains in a nonterminated state. The immutable
original launch receipt supplies the historical termination confirmation.

The completed check confirms removal of the job's volume, security group,
instance profile, worker role, timer role, and termination schedule. Its
three result objects remain in the dedicated S3 bucket, encrypted and
blocked from public access, with seven-day expiration. The local artifact
was rehashed; remote metadata and the small completion receipt bind it to
the retained result. Private evaluation contents were not opened.

The shared budget remains $18 reserved and $382 unreserved under the $400
total cap. No reservation was refunded. The original compute/EBS/IPv4
estimate is $1.853199078259259259259259259; it excludes S3 requests and
retention, transfer, and taxes, and is not an AWS invoice.

Executed command (working directory: CAS_META_2_COMPOSITION):

```powershell
& 'C:/Python314/python.exe' -B 'records/aws_full_002_cleanup_verification/verify_readonly_closure_v2.py'
```

The helper refuses to overwrite existing output. Preserve these records
and use a new output name for any future independent check.
