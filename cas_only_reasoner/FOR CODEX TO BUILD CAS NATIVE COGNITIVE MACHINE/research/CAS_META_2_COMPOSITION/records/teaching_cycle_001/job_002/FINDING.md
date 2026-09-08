# Second teaching attempt: EC2 rejected the new IAM profile

Transport source: `d158201c6cc8dfc7da6bc933bd56bf25ded8ae37`.
Job: `cas-meta2-teaching-20260908052433-f44ebc7a`.

The corrected price handoff passed the real preflight. The canonical ledger
recorded one new $8 reservation: revision 18, $110 reserved, $290 unreserved
inside the inclusive $400 cap. This is not an AWS invoice and is not refunded.
Ledger SHA256: `d373d6a541abd66a92436be782ecb9f1d709ca8ca704e3e0a2f71d46b7988b2d`.

The provider recorded this sequence on 2026-09-08 UTC:

- 05:24:53.027: instance-profile creation returned.
- 05:24:53.232: role attachment returned.
- 05:24:54.043: IAM readback matched the expected profile and attached role.
- 05:24:55.295: the single `RunInstances` call was requested.
- 05:24:55.540: EC2 rejected the same profile ARN with `InvalidParameterValue`.

The exact error is preserved in `launch/teaching_provider_0030.json`:
`Invalid IAM Instance Profile ARN`. The ARN is the one IAM just created and
returned. The launch was requested 2.063 seconds after attachment. The inherited
IAM helper returns immediately on a matching readback; its 60-second timeout is
not a 60-second propagation wait. The receipt explicitly did not prove EC2
propagation.

A cross-service visibility delay is the leading explanation, not a demonstrated
AWS internal cause. AWS documents that newly created roles can take time to
become visible at other endpoints:
https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot.html#troubleshoot_general_eventual-consistency

Both recovery observations found no instance IDs. The final cleanup receipt
`launch/004_cleanup_result.json` reports the job bucket, uploaded inputs, roles,
profile and security group removed and confirmed absent, with no volumes or
schedule left. No instance termination is claimed. The local source copy and
all launch receipts remain available; no training data or result was lost.

The correction will add a bounded 120-second settling interval after a matching
IAM readback, followed by another exact identity check. It remains a mitigation,
not proof that EC2 can use the profile. No model, budget limit, overall deadline,
resource type or single-launch rule changes. This job and its reservation are
closed as an unsuccessful attempt; a later attempt needs a new source identity
and fresh request. No neural update or learning outcome occurred here.
