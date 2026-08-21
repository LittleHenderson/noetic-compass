# AWS GPU standby

This stack creates a launch template, an SSM-only instance role, and a security
group with no inbound access. It does not create or reserve a GPU instance.

The pinned fallback is `g6e.xlarge` (one NVIDIA L40S, 48 GiB) in `us-west-2`.
Its first boot writes `STANDBY_ONLY_NO_MODEL` and shuts the instance down. A
real run requires a separate, reviewed start and experiment binding; this is
not a substitute for the frozen RunPod A40 preregistration.

No capacity reservation is used because an unused reservation is billed at the
full instance rate. The current AWS On-Demand G/VT vCPU quota must be at least
4 before an instance can be launched or started.
