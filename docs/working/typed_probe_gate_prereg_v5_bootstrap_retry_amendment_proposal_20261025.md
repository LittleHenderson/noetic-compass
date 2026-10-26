# Typed-Probe v5 Stage S bootstrap retry amendment proposal

**Status: PROPOSAL — NOT AUTHORIZED.** No additional AWS launch may start under this proposal until Wakil adds a dated `AUTHORIZED: yes` decision and says `GO` for this amendment. The earlier GO covers the frozen plan; this proposal changes its launch count.

## Why a change is needed

The frozen Stage S AWS launch stopped before the experiment. Its bootstrap returned exit code `20` because it did not find Python with PyTorch, Transformers, and CUDA. The selected AWS AMI documents its Python path as `/opt/pytorch/bin/python`; the bootstrap checked `/opt/pytorch/bin/python3`, `/opt/conda/bin/python3`, and `/usr/bin/python3`, so it missed the documented path. The startup failure and its evidence remain recorded in `docs/working/agent_exchange/codex_audit.md` and `docs/working/typed_probe_gate_runlog.md`.

## Proposed recovery

- Keep the v5 science protocol, models, prompt bank, rubric, sampling, labels, and analysis unchanged.
- Allow one corrected Stage S retry and, only if Stage S finishes and the owner’s 30-label calibration gets at least 24/30 exact matches, one possible Stage C launch. This creates a maximum of three launches total: the failed bootstrap, the Stage S retry, and Stage C.
- Keep the approved AWS all-in cap at **US$5.00** and the combined paid EC2 limit at **10,800 seconds (180 minutes)** across every launch. The failed instance used **538 tracked seconds** from launch at `2026-10-25T03:49:15Z` to the completed termination call at `2026-10-25T03:58:13Z`. That leaves **10,262 seconds (171 minutes, 2 seconds)** for any later launch.
- If the Stage S retry uses its full **5,400 seconds (90 minutes)**, Stage C can use at most the remaining **4,862 seconds (81 minutes, 2 seconds)**. Any unused time from Stage S remains available to Stage C. No concurrent instances, larger instances, Spot instances, local inference, or higher AWS cap are proposed.
- Keep the approved **US$10.00 total Claude API cap**. The frozen Stage S upper bound stays US$4.249728. The failed bootstrap submitted no Claude request and used US$0.00 in Claude message charges.
- Use a new run ID and S3 prefix: `typed-probe-v5-stage-s-retry1-20261025-0400z`, preserving the failed launch's S3 logs and records.
- Check `/opt/pytorch/bin/python` first and log which candidate failed if the PyTorch, Transformers, or CUDA check does not pass. The bootstrap must stop before model execution if those checks fail. It must verify the frozen runner SHA-256 before execution.
- Keep the same Stage C gate: Wakil labels 30 blind examples, and at least 24/30 must exactly match the panel before Stage C may launch.

## Reviewable source changes prepared

The retry candidate bootstrap now checks `/opt/pytorch/bin/python` first and records which interpreter failed its environment check. The setup candidate uses the new run ID and S3 prefix. These are local proposal files only; they have not been uploaded, prepared in AWS, or run.

- Runner SHA-256: `b44bcbbd9ee9a41252e72bc9f1c9efef3fee6de07a701ad743c26399dd010268`
- Retry bootstrap SHA-256: `be6b0a2f513f05f096942670f04949aec64d5980045b0891119d060f35d6e067`
- Retry setup SHA-256: `6d7b84a1d81677dcd93a51806a0c707a0c99a7b5074954656738b4142dbc2879`
- Frozen amendment SHA-256: `7d259447e5e5bfc8e650694bba25cb99ee0d76760e76665c3d81eea9ffcc22fe`
- Frozen rubric SHA-256: `e176676df7cd4d1593288daf9a793e0c75a1a81cdc9d9c40980c4d1eb02307fd`

AWS documents the selected AMI's Python path in its [release notes for PyTorch 2.8 on Ubuntu 24.04](https://docs.aws.amazon.com/dlami/latest/devguide/aws-deep-learning-ami-gpupt28oss-ul2404-2026-07-27.html).
