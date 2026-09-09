# Binding-fit check: intended runtime environment vs the recorded successful teaching-job environment

Comparison between the frozen intended environment of this check
(`aws/binding_fit_launch.py` RESOURCE_PLAN) and the recorded successful
teaching-job environment (job 003, `cas-meta2-teaching-20260908052915-8b5df59c`),
whose worker exited 0 after 1587 optimizer updates. All cited evidence is
retained in the repository; nothing here proposes a driver fix and no
environment behavior is guessed.

## Intended environment (this check, frozen)

| Field | Value |
|---|---|
| account | `807562639912` |
| region | `us-west-2` |
| ami | `ami-0fbbd0facbc9e3cff` |
| instance_type | `g7.2xlarge`, count 1 |
| gpu | `RTX PRO 4500` (name contains), 1 visible |
| torch | `2.11.0+cu128`, index `https://download.pytorch.org/whl/cu128` |
| cuda version (plan) | `12.8` |
| wheels | `casformer_reference-0.1.0` (sha `0487363c…`), `cas_neural_cjt-0.2.0` |
| mode entrypoint | `cas_meta2.binding_fit_training.mode.launch`, which calls `gpu_adapter._cuda()` — fail-closed `CUDA_REQUIRED_NO_CPU_FALLBACK` / `EXACTLY_ONE_VISIBLE_GPU_REQUIRED` |

## Recorded successful teaching-job environment (job 003)

Evidence paths (all retained):

- `records/teaching_cycle_001/job_003/launch/001_preflight_result.json`:
  account `807562639912`, ami `ami-0fbbd0facbc9e3cff`, instance type
  `g7.2xlarge`, gpu name `RTX PRO 4500`, region `us-west-2`, rate `2.52`.
- `records/teaching_cycle_001/job_003/evaluation_001/extracted/train/worker_identity.json`:
  instance `i-0272a6d80f3b5ad75`, imageId `ami-0fbbd0facbc9e3cff`,
  instanceType `g7.2xlarge`, region `us-west-2`, python `3.12.3`, wheel
  `casformer_reference` sha `0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee`
  — the same wheel sha this check packages.
- `records/teaching_cycle_001/job_003/evaluation_001/extracted/bootstrap_evidence/environment.txt`:
  `torch==2.11.0+cu128`, `cuda-toolkit==12.8.1`, `nvidia-cublas-cu12==12.8.4.1`,
  `nvidia-cudnn-cu12==9.19.0.56`, and the rest of the cu12 library set — the
  same frozen stack this check installs.
- `records/teaching_cycle_001/job_003/evaluation_001/extracted/bootstrap_evidence/torch_install.json`:
  torch wheel URL `https://download-r2.pytorch.org/whl/cu128/torch-2.11.0+cu128-cp312-cp312-manylinux_2_28_x86_64.whl`
  (the `download-r2` delivery domain of the same cu128 index this check uses),
  sha `d252cf975fb18c94a85336323ad425f473df56dab35a44b00399bd70c7a3b997`.
- Worker exit receipt `records/teaching_cycle_001/job_003/evaluation_001/extracted/driver/train.exit.json`:
  exit code 0, phase train.

## Actual differences identified

1. **Bootstrap/environment evidence capture.** Job 003 retained
   `bootstrap_evidence/{bootstrap.log, environment.txt, torch_install.json,
   wheel_install.json, dependency_install.json}` and a `worker_identity.json`.
   This check's worker retains none of those — only `results/result.json`.
   This is the difference that made attempt 003's inner failure unreadable.
   (Fixed for errors by the worker change committed in `d031ba61`; the broader
   environment-capture difference remains and is reported, not silently
   changed.)
2. **Independent CUDA observation.** Job 003's own receipts state
   `provider_identity_proved: false` and carry the boundary
   "Simulated learners prove orchestration only. CUDA observations require
   independent retained evidence" (`campaign_summary.json`); no nvidia-smi,
   driver-version, or `torch.cuda.is_available()` observation is retained in
   its records. This check's attempt-003 run retained no environment capture
   at all. Therefore **no retained evidence in either direction shows whether
   torch 2.11.0+cu128 sees CUDA on this AMI/instance combination.** The
   binding-fit mode requires real CUDA; the successful teaching job's record
   does not independently prove CUDA ran there. The attempt-003 inner failure
   remains UNKNOWN — the CUDA idea stays a hypothesis, nothing more.
3. **Bootstrap layout.** Job 003 used `/opt/cas-teaching` paths and its own
   worker entrypoint; this check uses `/opt/cas-binding-fit` and the rendered
   `binding_fit_worker.py`. Transport difference only, not a runtime
   environment difference.
4. **Identical everywhere else:** account, region, AMI, instance type, GPU
   name, python 3.12, the torch 2.11.0+cu128 stack, and the
   `casformer_reference` wheel sha.

## What is NOT proposed

No driver fix, no AMI change, and no environment modification is proposed on
the basis of this comparison — there is no retained driver evidence to act on.
The actionable, evidence-based next step for a future authorized run is to
preserve the original inner error (now demonstrated by
`tests/test_binding_fit_worker_execution.py`) and, if the owner directs, to
capture the same bootstrap/environment evidence class job 003 retained.
