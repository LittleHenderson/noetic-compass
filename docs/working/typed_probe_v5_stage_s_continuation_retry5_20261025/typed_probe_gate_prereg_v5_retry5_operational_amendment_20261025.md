# v5 Stage S retry 5 operational amendment

**Date:** 2026-10-25  
**Status:** AUTHORIZED FOR ONE CONDITIONAL ATTEMPT. The Stage S result has not been run.

## Owner authorization

Received in chat at 2026-10-25T17:11:27Z:

AUTHORIZED: yes; GO — approve one Stage S retry 5 in us-west-2a under docs/working/typed_probe_v5_stage_s_continuation_retry5_proposal_20261025.md, with the AWS cap of US$15.00 and the stated Claude caps.

## Scope

This amendment applies only to run typed-probe-v5-stage-continuation-retry5-20261025. It raises the AWS all-in cap from the prior US$5.00 limit to US$15.00 for this one Stage S attempt. The prior cap remains in the historical preregistration and earlier run records; this amendment does not change or erase those records.

The attempt is exactly one On-Demand g5.2xlarge launch in us-west-2a, with one RunInstances SDK attempt and no retry, zone fallback, or instance-type fallback. AWS placement and capacity must pass the live pre-launch checks. If any check fails, stop without launching. If AWS rejects the one request for capacity, record the failure and stop.

The frozen science scope is unchanged: use the pinned 1,920 replies and 1,280 existing Mistral labels; add only the missing 640 labels; generate no new Qwen replies; change no sampling, scoring, or safety rules. The Stage S limit remains 3,000 EC2 seconds, with a 2,500-second runner guard, 2,700-second scheduled stop, and 2,900-second hard stop. The combined EC2 ceiling remains 10,800 seconds, and the proposal's projected use is 10,672 seconds.

Claude remains capped at US$4.249728 for Stage S and US$10.00 total. Reserve each request before submission; do not retry an uncertain batch. The AWS estimate must be refreshed before setup and immediately before launch; stop if it exceeds US$15.00. The estimate is not an invoice.

This amendment does not authorize Stage C execution. Stage C remains gated on completed Stage S, Wakil's 30 blinded labels, and at least 24/30 exact matches to the panel.

## Cloud job record

- **Source:** pinned v5 Stage S source run and checkpoint identified in the retry 5 proposal.
- **Purpose:** finish the preregistered Stage S labels and outputs.
- **Instance:** one On-Demand g5.2xlarge, us-west-2a.
- **Limits:** one launch request; 3,000 Stage S EC2 seconds maximum; US$15.00 AWS cap; Claude caps above.
- **Cleanup:** terminate only retry 5 resources, remove its temporary disk and run-specific schedules, parameter, Lambda, profile, and roles; retain S3 receipts and logs.

