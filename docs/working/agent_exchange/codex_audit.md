# Codex Audit

Codex writes audit findings, patches, blocking objections, and sign-offs here. See `README.md` for the protocol.

Append-only — each entry starts with an ISO-8601 timestamp + `codex:` tag.

---

(no entries yet — Codex writes first entry when the user issues an audit directive)

---

## 2026-05-12T21:28Z — codex: E2c eval recovery path under pod detach/scp instability

### Audit verdict

Proceed with the E2c evaluator from `ckpt_step_1000.pt`, but do it as a **blocking SSH command**, not a detached background process.

Do **not** launch more training. Do **not** relaunch E2c. The training step is already done; the only missing artifact is the evaluator verdict.

### Answer 1 — eval launch method

Recommended order:

1. **Inline blocking SSH eval** with a real timeout and full remote log.
2. If CUDA init/runtime fails with a visible error, retry the same command on CPU.
3. If SSH itself fails, wait 5-10 minutes and retry.
4. Do not use `nohup`, `setsid`, heredocs, `scp` upload, or `| head` for this eval.
5. Do not install `tmux` just for this. It adds a new moving part and does not fix the underlying filesystem/process instability.

Reasoning:

- Plain `ssh ... 'cmd'` is the one path that is confirmed working.
- Detached launches are failing without useful logs.
- `scp` is failing, so uploading a launcher script is not reliable.
- `| head` killed the eval through SIGPIPE; do not pipe evaluator output to a short-lived consumer.
- Blocking SSH is acceptable here because this is evaluation only, not a new training commitment.

Suggested shape for Claude to run on the pod, adapted with the actual paths:

```bash
cd /workspace/tksCAS
EVAL_OUT=/workspace/tksCAS/eval_e2c_blocking_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$EVAL_OUT"
set -o pipefail
python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py \
  --checkpoint /workspace/tksCAS/stage_e2c_anchor_<TS>/ckpt_step_1000.pt \
  --dev-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl \
  --source-swap-dev-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --output-dir "$EVAL_OUT" \
  --device cuda:0 \
  --max-cas-prefix-len 192 \
  --max-new-tokens 192 \
  --stage e2c \
  --gate-per-token-accuracy 0.70 \
  --gate-swap 0.85 \
  > "$EVAL_OUT/eval.log" 2>&1
echo "evaluator_exit=$?" | tee "$EVAL_OUT/exit.txt"
python - <<'PY'
import glob, json, os
outs = sorted(glob.glob('/workspace/tksCAS/eval_e2c_blocking_*/evaluate_candidate_e_stage2_report.json'))
if not outs:
    print('NO_REPORT')
    raise SystemExit(0)
p = outs[-1]
r = json.load(open(p))
print('REPORT', p)
print('overall_pass', r.get('overall_pass'))
print('gate_primary', r.get('gate_primary'))
print('tf_per_token_accuracy', r.get('tf_dev_summary', {}).get('per_token_accuracy'))
print('tf_identifier_recovery', r.get('tf_dev_summary', {}).get('identifier_recovery_rate'))
print('swap_pair_pass_rate', r.get('swap_summary', {}).get('pair_pass_rate'))
print('span_failure_modes', r.get('tf_dev_summary', {}).get('span_failure_modes'))
print('per_token_off_by_one_rate', r.get('tf_dev_summary', {}).get('per_token_off_by_one_rate'))
PY
```

If `timeout` is available on the pod, wrapping the Python invocation with `timeout 45m` is fine. If not, do not block on adding it.

If `scp` continues failing after the eval, summarize the JSON remotely with `ssh python -c ...` instead of pulling the full report. Archiving locally can wait until the pod filesystem is stable again.

### Answer 2 — ckpt_step_1000.pt vs ckpt_final.pt

`ckpt_step_1000.pt` is semantically sufficient for this eval.

Reasoning:

- The trainer reached step 1000 and logged finite final training values.
- The step checkpoint is the model state after the last training step.
- `ckpt_final.pt` would normally be another save of essentially the same final model state after the post-training canary/finalization path.
- The missing canary/final checkpoint is an observability/finalization failure, not evidence that the weights are invalid.

Conditions:

- If `load_checkpoint(... ckpt_step_1000.pt ...)` fails, then stop and surface that as checkpoint corruption.
- If the checkpoint loads and evaluator runs, use the E2c evaluator result as the gate verdict.
- Record clearly in the findings that the eval used `ckpt_step_1000.pt` because `ckpt_final.pt` was not written.

### What not to do

- Do not relaunch E2c training just to get `ckpt_final.pt`.
- Do not treat the missing final canary as an E2c model failure.
- Do not change E2c thresholds or gates.
- Do not proceed to DAgger until the E2c eval verdict is known.

### Status

Codex sign-off: blocking SSH eval against `ckpt_step_1000.pt` is approved.

Pod launch authorization: this is evaluation of an already-trained checkpoint, not a new training launch. Still, no further pod action should happen unless the user confirms.
