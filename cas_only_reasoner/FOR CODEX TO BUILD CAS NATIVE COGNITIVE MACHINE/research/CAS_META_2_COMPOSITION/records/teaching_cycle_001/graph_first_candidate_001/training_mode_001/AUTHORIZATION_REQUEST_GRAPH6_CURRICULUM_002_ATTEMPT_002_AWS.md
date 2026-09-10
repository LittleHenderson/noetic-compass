# GRAPH6_CURRICULUM_002 — attempt 002 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for attempt 001, which failed
after 564.5 s at the FIRST checkpoint reload, before any training.

## What went wrong (both defects mine, both fixed)

1. **The checkpoint payload was not weights-only-safe.** PyTorch 2.6 changed
   `torch.load`'s default to `weights_only=True`; my payload embedded
   `torch.__version__`, whose runtime type is
   `torch.torch_version.TorchVersion`, so the job refused the checkpoint file it
   had just written (`_pickle.UnpicklingError: Weights only load failed`).
   Fixed: the payload stores the version as a plain **string**, and
   `load_checkpoint` passes `weights_only=True` **explicitly** — the safe default
   is never disabled to make a checkpoint load. Two regression tests pin it
   (including one that an unsafe payload must be refused).
2. **A failed worker was misreported as a launch failure.** `collect()` demanded
   an artifact manifest that a worker failing before upload never writes; that
   turned a clean, fully recorded worker failure into
   `AWS_CURRICULUM_LAUNCH_FAILED`. Fixed: when the worker reports
   `REMOTE_WORKER_FAILED`, `collect()` records the result and returns
   `artifacts_available: false`, `reason: REMOTE_WORKER_FAILED`.

The launcher's fail-closed path worked correctly throughout: one reservation
created once, the worker's error preserved verbatim, evidence persisted, cleanup
complete (instance `i-0b56a1eed5c813cc9` terminated, bucket and results deleted),
zero retries, hygiene re-checked independently (0 active job-tagged instances, 0
buckets, 0 leftover security groups). Record:
`ATTEMPT_GRAPH6_CURRICULUM_002_001_FAILURE.md`.

## What is unchanged (the pre-registered design)

Frozen candidate, encoder and tokenizer fitting set, CAS framing, `operation:^6`
scope; **control** = the existing 30 lessons, **varied** = the 30 new relationship
lessons; three **paired** seeds `20260913/14/15` with matched initial weights and
separate optimizers; a balanced round-robin schedule identical in both
conditions; checkpoints at **64** and **256** updates; **6 learners / 1,536
updates**; the untouched final panel (30 pairwise non-isomorphic arrangements,
90 cases, reach 10/10/10, teaching envelope and vocabulary only); real checkpoint
files with in-job reload verification and verified artifact collection before
bucket cleanup; and the pre-registered rules — `VARIED_CURRICULUM_BETTER` iff ≥ 2
of 3 seeds show varied−control ≥ +0.10 with family-clustered 95 % CI low > 0
**and** ≥ 2 reach 0.50 absolute; repetition effects reported but not gating.

Also unchanged from your review: the `none` shortcut fix (`none` offered in 7
shared-part lessons — correct in 4, an incorrect distractor in 3) and the panel
wording ("unseen arrangements within the documented teaching envelope"; equal
difficulty is **not** claimed).

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `210109c7cc848b4cf8e68c15ba31a186fe5638f8` |
| archive_sha256 | `c24f2f9ce2d01a44ac79e46bfdc59788256200b6a2079c3223f8a6758a0f20f9` |
| archive_bytes | 408480 |
| manifest_sha256 | `c5b35dc4f544cbf43fe4a9190f12db71d249722dbaba6020c5ef49fae9c830dd` |
| member_count | 37 |
| package | `training_mode_001/graph6_curriculum_package_002/` |
| launch request | `training_mode_001/graph6_curriculum_launch_002/launch_request.json` (sha256 `63cacaddbb30c8f92ea981c983764de31757d1ad2b3dc8ec00a79ecc9ebe6b3a`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6curr-20260910073000-210109c7` |
| launcher | `aws/graph_training_curriculum_launch.py` at commit `210109c7` |
| preregistration | `GRAPH6_CURRICULUM_002.md`; evidence `CURRICULUM_002_CHECK.json` (sha256 `187457c6…`) |

## Budget (one authorization)

| Item | Value |
| --- | --- |
| Instance | 1 × `g7.2xlarge` (RTX PRO 4500), no T4 fallback |
| Wall ceiling | 900 s per learner, 3,600 s worker, 7,200 s instance (2 h) |
| Reservation | one new **`$7.00`** (2 h × `$2.52` + `$1.48` ancillary, rounded up) |
| Ledger after | revision 48 → 49: `$256.00` reserved / `$144.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup; artifacts collected first |

## What I need from you

**GO / NO-GO** for this replacement job (one new owner-signed record + one new
`$7.00` reservation). On GO I mint the owner record binding these exact
identities, register, and execute — nothing before.
