# Typed-Probe v5 Stage S bootstrap recovery 2 amendment

**Status: AUTHORIZED: yes.** This dated amendment records one additional Stage S startup-recovery attempt under the owner's existing instruction to prove the watchdog and launch Stage S within the US$5 AWS cap. It does not change the v5 science protocol or authorize Stage C.

## Owner instruction

> “Prove the watchdog works, then launch Stage S within the US$5 AWS cap.”

The owner also approved a US$10.00 total Claude API cap for the v5 work. This retry stays under that existing cap and the existing US$5.00 all-in AWS cap.

## What failed and what changes

The first corrected Stage S instance used the documented `/opt/pytorch/bin/python` path and downloaded the frozen inputs, but its startup check still failed with exit code `20`. The log combines PyTorch import, Transformers import, and CUDA availability into one check, so it does not say which part failed. The model runner did not start and no Stage S science output was produced.

The next bootstrap will report PyTorch and Transformers imports separately, then wait up to 300 seconds for CUDA and a visible GPU. It will stop and record the exact import or GPU check if the environment is still not ready. The runner, models, prompt bank, rubric, sample count, and analysis remain unchanged. No local model run is allowed.

## Scope and limits

- One additional Stage S startup-recovery attempt only, using run ID `typed-probe-v5-stage-s-retry2-20261025-0430z`, in `us-west-2b` on an On-Demand `g5.2xlarge`.
- The independent watchdog must pass its no-target scheduled check and live tagged-target termination proof for this run ID before Stage S launch.
- **AWS all-in cap: US$5.00.** Refresh exact AWS prices before preparation and launch. Stop if the complete maximum-scenario estimate exceeds the cap.
- The combined EC2 ceiling remains **10,800 seconds** across all v5 instances. Every prior GPU startup and watchdog sentinel counts against it. Do not run instances concurrently. Stage S remains limited to **5,400 seconds**.
- The watchdog-sentinel ceiling stays **300 seconds total** across v5 proof attempts. Earlier sentinel attempts used **79 seconds**, leaving at most **221 seconds** for this run's proof.
- Claude API use stays under the existing **US$10.00 total cap**; Stage S keeps its frozen **US$4.249728** upper bound. Bootstrap failure cannot submit model generations or judge batches.
- Any next startup failure remains 🟥 FAILED / WITHDRAWN as an operational result and Stage S remains ⬜ NULL / INCONCLUSIVE / NOT RUN. No further launch is included in this amendment.
- Stage C remains unauthorized. Wakil must label all 30 blind examples; at least **24/30** must exactly match the frozen panel, and Stage C needs a new owner authorization.

Authorized under the owner's direct instruction in this Codex conversation. Decision record: `docs/working/agent_exchange/decisions.md`.
