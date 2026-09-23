# AWS job: Helm analogy-wiring before-readings, preservation reference, probe self-test

**Authority.** The owner said in chat on 2026-09-23: "use aws", and then "use aws as there is only 354 mb of 16
gbs locally". This is standing run authorization under `docs/OWNER_RUN_AUTHORIZATION_20260922.md`.
**Runner:** Claude, the independent checker. This is a checker job, not a Codex build job.

| Limit | Value |
|---|---|
| Machine | ONE `g4dn.2xlarge`: NVIDIA T4, 8 vCPU, 32 GiB, us-west-2, on-demand |
| Price | $0.752/hour (AWS pricing API, 2026-09-23) |
| Image | AWS Deep Learning base, NVIDIA driver, Ubuntu 24.04 (the SSM parameter in `launch.py`) |
| In-machine timer | 150 minutes, then the operating system powers off at 153. The machine is destroyed on shutdown |
| Client deadline | 160 minutes after launch. `watch.py` terminates the machine and retries until AWS confirms it is gone |
| Worst-case cost | 160/60 x 0.752 = **$2.01**, plus about $0.01 for the public address and the disk. **Ceiling $3.00** |
| Credentials on the machine | **none**. Presigned links only: one download (the bundle) and two uploads (progress and results) |
| Left behind | nothing: no key pair, role, Elastic IP or snapshot. The S3 objects sit in the existing bucket under `helm-integration/` |
| Work | forward passes only. No training. Nothing is written back to any repository |
| Automatic retries | none. The launcher refuses to run twice (`launch_record.json`) |

**The jobs, in order.**
1. **Preflight.** It checks CUDA, the two wheels, the course load, one forward pass per question kind, and the 6
   checkpoints. It records every file opened. If it fails, the job ends immediately.
2. **Group A, side by side.**
   - The probe v0.2 before-readings for seeds 20260917, 20260918 and 20260919 (fresh, `initial.pt` and
     `final.pt` for each).
   - The probe self-test (`POSITIVE_COMPARISON`, `NEGATIVE_UNIFORM`, `NEGATIVE_COUPLED`).
3. **Group B, side by side.** The preservation fingerprints for all 9 models on the T4. This becomes the T4
   switch-OFF reference.

**The rules.** They are frozen in `../analogy_wiring_probe/PREREG_ANALOGY_WIRING_PROBE_v0_2.md` (amendments A1 and
A2) and `../analogy_wiring_probe/PREREG_PROBE_SELF_TEST.md`.
