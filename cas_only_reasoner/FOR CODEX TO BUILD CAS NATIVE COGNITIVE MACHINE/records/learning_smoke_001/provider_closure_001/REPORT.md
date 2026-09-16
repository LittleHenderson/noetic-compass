# Independent AWS closure readback

The ordered-ingestion smoke job is closed. The broader account still contains named resources from an older CAS teaching job.

Observed **2026-09-16 18:50:53–18:50:55 UTC**, account **807562639912**, region **us-west-2**, profile `default`. The script permits only an explicit set of read APIs and blocks model imports. No provider mutation, reservation, checkpoint decoding, or object-body download occurred.

The caller-pinned lifecycle result is `receipt_cas-meta2-ingestionsmoke-20260916183635-6ef614bf/result.json`, SHA-256 `a99859a9bd93af0e502798399737e15a35bb8b2c9de17fad039b8fb860eb92cb`; its bytes were unchanged.

- Instance `i-0df9728e05ae06711`: fresh AWS response says **terminated**, tagged to this job. State transition: `User initiated (2026-09-16 18:41:25 GMT)`.
- This job's security group: absent. Worker role, worker instance profile and timer role: `NoSuchEntity`. Job schedule: `ResourceNotFoundException`.
- No active or stopped instances carrying `cas_meta_job`, and no CAS-tagged volumes or network interfaces. No interface attached to this instance. No `cas-meta2-` schedules.
- Retained bucket `cas-meta2-ingestionsmoke-20260916183635-6ef614bf-807562639912`: present in `us-west-2`; all four public-access blocks enabled; default `AES256` encryption; `BucketOwnerEnforced` ownership. No bucket policy, lifecycle rule, or Object Lock configuration was returned; versioning returned no status. This is not a WORM or independent-backup claim.
- `results/` contains **24 objects, 706,239 bytes**. HEAD checks on the result marker, manifest and all three checkpoints match the local verified file lengths. Bodies were not downloaded again; this check establishes retained presence and configuration, not a second content-hash verification.

The wider account scan returned security group `sg-0e709db963556da39`, worker and timer roles, and a worker instance profile named for `cas-meta2-teaching-20260908134143-ebd84f71`. They belong to a different named job and were left untouched. It also returned one untagged, stopped `g6e.xlarge` instance, `i-0c3028734c8885542`; no attribution to this CAS run is made. Thus the raw broad receipt correctly remains `PARTIAL_OR_OPEN`. `summary.json` separately records the fully confirmed closure of this job and the retained evidence bucket.

The first local invocation used Python isolated mode and could not import the established user-site `boto3` installation. It made no provider call. `initial_failure.json` preserves that failure. The same script then ran with the normal Python interpreter and bytecode disabled, matching the earlier read-only audit configuration.

`provider.json` preserves observation times, projected responses and AWS request IDs. `receipt.json` preserves every individual check, including the broader resource findings. `summary.json` records the scope distinction and source hashes. Budget publication and final billing are outside this readback.
