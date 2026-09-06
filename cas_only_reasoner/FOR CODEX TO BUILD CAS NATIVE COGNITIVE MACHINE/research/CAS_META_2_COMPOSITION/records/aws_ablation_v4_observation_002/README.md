# Corrected comparison: startup observation

Job: `cas-meta2-20260906032109-361b34a0`.
Instance: `i-09ed76379ad9536b1`.
Source: `9f562c761c7cb84c767673b2fab735cdd031b499`.
Source archive: `../aws_ablation_v4_source_002/source.zip`.

At 2026-09-06 03:21:55 UTC the read-only provider check confirmed the exact
job-tagged instance running and its shutdown schedule enabled for
2026-09-06 05:21:28 UTC. No bootstrap log or result existed yet.
The launcher separately verified the schedule's termination target.
This is startup evidence, not evidence that GPU tests or model evaluation passed.

Observe the existing job with `read_status.py`. Do not restart it because a
poll yields no output. The live launcher receipt is
`../aws_ablation_v4_002/launch_receipt.json`; preserve it after termination.

Budget ledger revision 7 reserves $53 cumulatively and leaves $347 unreserved
under the $400 cap. This run's reservation is $7, not an AWS invoice.
No automatic retries are enabled.
