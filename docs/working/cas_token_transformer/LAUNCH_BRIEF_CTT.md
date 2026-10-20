# Launch brief — CTT-1 (for the coordinator / launch controller). NOT LAUNCHED.

## What runs, in one paragraph
One AWS GPU host (`g5.xlarge`, us-west-2; fallback `g4dn.xlarge`) builds the training data from frozen code and
frozen seeds, trains the CAS-token translator from scratch (main model 9,585,566 parameters, 3 seeds; twin 2,482,718
parameters; a shuffled-pairs control; an untrained control), scores every arm on the custodian-sealed machine-side exam
E-MACHINE-S and (reported only) on the sealed 98, and runs the six spent wave exams through wave 5's loop with the
translator OFF, OFF-with-its-folder-deleted, and ON (each seed). The frozen reader runs later on the laptop.

## Preconditions (all must hold; the runner refuses otherwise)
1. `APPROVAL_RECORD_CTT.json` (owner's verbatim pre-approval + zip `83bfa752...`, cap 8.00 USD).
2. The custodian has drawn and sealed the MACHINE-SIDE exam E-MACHINE-S per `custody/CUSTODIAN_PROCEDURE_CTT.md`
   section M (laptop, 0 USD, no human writer; seed from the approval record). The builder never handles it.
   (Amendment A-CTT-1: the human exam E-HUMAN-W is an optional later pass, `kit/run_ctt_human.py`.)
3. Sources staged exactly as `HELM_CTT_20261019/kit/STAGE_CTT.json` says:
   `ctt` = `HELM_CTT_20261019_SOURCE_CTT.zip` (`83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec`);
   `deps` = `HELM_CTT_DEPS_20261019.zip` (`fc89054a6893a149301ee8504dbd325e7b46a75b0152d80622e4096cf06acd3f`);
   `r1w5` (`b6598687...`), `r1w3b` (`a4f82556...`), `r1w3` (`152bca2a...`), `w1` (`31f97d67...`);
   `spent` = a carrier of ENGLISH64/FACES64 `_X3` (`a5a4286a...`, `8c1ff66a...`), `_X4` (`d47c293d...`, `758f5cba...`),
   `_X5` (`1eb17c91...`, `2c7cac21...`) and R1_W3B_HOST.json (`5f479f61...`), R1_W4_HOST.json (`aa223fa1...`),
   R1_W5_HOST.json (`c243a4cd...`);
   `emachine` = the custodian's carrier (E_MACHINE_S_CTT.json + E_MACHINE_SEAL_RECORD.json); `sealed98` = the custodian's carrier of `real_heldout_unparseables_98.jsonl`
   (`e269a448...`).
4. Image: an AWS Deep Learning AMI with PyTorch 2.x + CUDA; `HELM_CTT_AWS=1`; `--expected-zip-sha256` = the value in
   the approval record; `--deadline-epoch` = launch + 5 h.

## Limits (RUN_LIMITS_CTT.json)
Cap 8.00 USD across both attempts; instance life 6 h (self-terminate); job wall 5 h; preflight 15 min; data build
30 min; one attempt + one plumbing retry (only if no model was scored). No rerun with changed settings.
Expected: about 2–3 h on g5, about 2–3.5 USD.

## First run of the neural code
`model.py`, `train.py`, `serve.py` have never run (no torch on the laptop: 475 MiB > 300 MiB limit). Stage 1
(preflight) is the GPU smoke: 1% data build, 50 training steps, exact parameter count asserted against the formula,
one translator-process audit. If it fails, nothing was scored: that is plumbing; read `PREFLIGHT_CTT.json` and the
stage logs before any retry.

## After the run
1. Download the output folder; verify sha256 of every file against `RUN_RECORD_CTT.json` / the draft merge input.
2. Custodian: `custody.seal_exam confirm` → `E_MACHINE_SEAL_CONFIRM.json`.
3. Fill `MERGE_INPUT_CTT.json` from `MERGE_INPUT_CTT.draft.json` (+ `exam_seal`, `approval_record` paths and sha256),
   then on the laptop: `python -X utf8 -B -m ctt_score.merge_ctt --pass primary --merge-input MERGE_INPUT_CTT.json --out CTT_READING.json`.
4. Record per job: source hashes, purpose, instance id/type/region, start/stop UTC, limits, actual cost, cleanup proof
   by a second describe call, backup to `D:\tksCAS-archive\` with three sha256 confirmations; spec-sheet row in the
   same commit as the result (negatives kept).
