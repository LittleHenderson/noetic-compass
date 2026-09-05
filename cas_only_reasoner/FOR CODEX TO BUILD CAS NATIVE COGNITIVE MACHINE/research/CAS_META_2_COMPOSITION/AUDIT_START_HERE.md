# CAS-META-2 audit entry point

This package is a separate research candidate. Its target is learned generation and execution of bounded nested CJT programs with named intermediate values. A runnable package, a passed smoke test, and a useful learning result are three different milestones.

## Current source and preserved baseline

The candidate is on branch `codex/cas-meta-2-composition` in the existing `meta1` worktree. Earlier accepted source and weights remain unchanged.

- Accepted META-0 baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- META-1 evidence commit: `6a4524d5f21f77194b35d0830d2b16da8530b17d`.
- Candidate source commit, archive hash, AWS job identity, raw outputs and cleanup receipt will be recorded per launch. Never substitute branch HEAD for a recorded launch SHA.

## Safe local checks

Run from this package with Python that has pytest and boto3 installed:

```text
C:/Python314/python.exe -B tools/validate_local.py --output records/new_local_audit
```

The tool refuses a reused output directory. It blocks imports of neural libraries during the tests. It checks all 316 protected baseline files before and after testing, parses source without running it, and saves exact commands, stdout, stderr, XML counts and source hashes.

Mock backend tests establish control behavior only. The GPU test module is skipped locally. Do not run training, model construction, checkpoint loading, native neural tests or tensor evaluation on this laptop.

## Important implementation paths

- `cas_meta2/ir.py`: strict program admission, size/depth/expansion limits and explicit reference names.
- `cas_meta2/curriculum.py`: structural task generation, separate public parser, name-independent graph splits and allowed native edges.
- `cas_meta2/codec.py`: public inputs and symbolic program tokens.
- `cas_meta2/policy.py`: separate CAS and generic neural generators with the same decoder and binding head.
- `cas_meta2/executor.py`: named-value call stack, planned charges, unique run identities and event replay.
- `cas_meta2/native.py`: unchanged native CJT calls and private direct-reference execution.
- `cas_meta2/stored.py`: read-only replay of saved composition events against the selected program, actual database receipts, input/output bytes, final state and compute charges. This is documentary checking, not a new neural execution or restart test.
- `cas_meta2/train.py`: paired training, validation-only checkpoint selection, checkpoint saving and public prediction sealing.
- `cas_meta2/campaign.py`: smoke, training, all five arms, private evaluation and bounded failure handling.
- `aws/launch.py`: source-pinned cloud execution and owned-resource cleanup.
- `aws/budget.py`: one continued owner-approved allowance, not a fresh allowance per stage.
- `tools/build_launch_bundle.py`: only committed source bytes enter the cloud source ZIP.
- `tools/inspect_cloud_packet.py`: checks the downloaded archive, every member hash, source binding, GPU test counts, saved checkpoint hashes and recorded result totals; safely extracts to a new directory. It never loads a checkpoint.
- `tools/audit_stored_packet.py`: after successful packet inspection, validates published trace schemas and rechecks saved program steps, memory references, compute charges and actual input/output bytes against sealed choices. It never runs a model.
- `VISION_REQUIREMENTS.md`: the complete destination, including requirements this candidate does not yet implement.

## Cloud reproduction

A paid reproduction must go through the capped launcher. The total owner allowance is $400 across this campaign and previous reservations. H100 is currently quota-blocked; the approved launch plan uses one Blackwell `g7.2xlarge`, not T4. Each attempted job conservatively reserves $7, with a two-hour outer cutoff. The machine must confirm the cloud cutoff before neural execution.

Before launch, the included source must be committed and its archive validated. Use the launcher's `--smoke-only` mode for the initial runtime check. Full mode must retain all initial/best/last candidate checkpoints, five-arm predictions sealed before test-gold access, each native reference and result, exact test counts, resolved environment and cleanup evidence. A timeout or omitted evidence is a partial result, not success.

The local launch receipt binds the exact source SHA, source ZIP hash, AWS job, budget reservation, downloaded artifact hash and cleanup state. A later cleanup correction must be a separate receipt; do not rewrite the initial failure history.

## Evidence inspection order

First inspect the original ZIP with `tools/inspect_cloud_packet.py`, passing its exact packet SHA256, source SHA, job identity and independently saved source-bundle receipt. Use a new `records/` inspection directory and a new `records/*_extracted` extraction directory. The inspector reports failed/partial runs separately from complete smoke/full runs. Its process exit code alone is not a claim that a run succeeded; read `status` and `completed_run_evidence_verified`.

Only a complete, successfully inspected smoke/full packet can enter `tools/audit_stored_packet.py`. Pass `--inspection-receipt`, optionally `--extracted`, and a new `--output` directory under `records/`. This second check derives verdicts from saved database contents and the selected source program; it does not merely recount saved true/false fields. Both tools are safe data-only checks for this laptop. Their receipts explicitly exclude neural reproduction and restart claims.

The first failed Blackwell attempt is documented in `records/AWS_SMOKE_001_FINDING.md` and preserved by evidence commit `b0261e8d7daaf7812cacf22ebc722acb1f56514f`. Its source is still `2a3ec1132770b121881a49effee2aa5d4e0494fb`, not the evidence commit. All 69 packet members were checked; the run remains failed. The separate cleanup receipt closes only resource cleanup, not the policy test failure.

## What a positive result would establish

The intended measured result is improved execution of unseen bounded structural tasks after training. Correctness requires the declared dependency structure, observation binding, named intermediate references and all actual native output bytes. Trace integrity or a final symbol alone does not establish task correctness.

The initial public curriculum explicitly describes operations and dependencies in controlled wording. Its task is translation and composition from those instructions, not algorithm discovery from an outcome alone. New structural combinations and held-out wording test bounded generalization; they do not establish unrestricted language understanding or self-directed procedure invention.

A positive result still would not establish general language, full Noetic semantics, learned missing-skill repair, general recursion, durable skill installation, CAS-specific superiority, complete CNCM, physical analog hardware or production readiness. Those remain in the full vision.
