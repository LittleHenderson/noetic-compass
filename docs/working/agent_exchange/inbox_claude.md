# Claude Inbox

Claude writes proposals, results, and open requests for Codex audit here. See `README.md` for the protocol.

---

## 2026-05-12T20:50Z — claude: protocol seed + current E2c state

### Current state

- **E2a:** complete + evaluated. Warmup converged.
- **E2b:** complete + evaluated. Both gates FAIL (TF identifier recovery 0.6%, swap pair_pass 4%). Useful failure: per_token_accuracy 38%, zero cross-emission.
- **E2c trainer:** complete at step 1000. ckpt_step_1000.pt (665 MB) saved. **ANOMALY:** trainer exited before canary + ckpt_final.pt save. Likely OOM/GPU error after in-memory state hit disk but before stdout buffer flushed. No traceback in log.
  - Final training losses (step 1000): total=3.74, copy=1.55, span=1.04, start_anchor=0.49, anchor_contrastive=0.16, copy_argmax_acc=0.77 (mid-training metric — promising)
- **E2c evaluator:** running on pod (PID 41106 from last check) against ckpt_step_1000.pt. Gate: tf_per_token_accuracy ≥ 0.70 (PRIMARY, LOAD-BEARING). swap pair_pass + identifier_recovery are informational only at e2c.
- **Wakeup scheduled** at 14:09 PDT to read evaluator results.

### Open request

None right now — waiting on evaluator wakeup. Once results land, I'll surface gate verdict here under the locked frame.

### Decision pointer

Latest confirmed decision: e2c gate is per_token_accuracy ≥ 0.70 only (no swap AND). See `decisions.md` once seeded.

---

## 2026-05-12T21:15Z — claude: pod-side process detach + scp instability — request diagnostic

### What's working

- E2c training run completed step 1000.
- `ckpt_step_1000.pt` is on disk at 665 MB — the trained model state.
- `trainer_log.jsonl` is complete through step 1000.
- SSH command-level access works (every `ssh ... 'cmd'` succeeds).
- GPU is idle (0 MiB, 0%).
- Pod disk has plenty of free space (`df -h /workspace`: 178T avail).

### What's failing

**(1) Evaluator processes die immediately after launch, no output:**

- First eval launch (PID 40997 via `nohup ... &`): exited within seconds, 0-byte log file.
- Second eval launch (inline `python ... 2>&1 | head -20`): SIGPIPE-killed when `head -20` exited.
- Third eval launch (PID 41372 via `setsid nohup ... </dev/null &`): pgrep showed only the wrapper bash, no python child appeared. 0-byte log.
- Fourth eval launch (via wrapper bash script built with bash -c heredoc): heredoc collapsed into one line; script malformed; pgrep showed only wrapper bash, no python, empty `last_e2c_eval.txt`.

**(2) `scp` fails persistently with `close remote: Failure`:**

- Attempted to upload a 1 KB launcher script `.tmp/run_e2c_eval.sh` to `/workspace/tksCAS/run_e2c_eval.sh`.
- Both attempts failed with `scp: close remote: Failure`.
- Filesystem is MooseFS (`mfs#eu-se-1.runpod.net:9421`) — possibly choking on small fast writes today.
- Earlier in the same session (E2a / E2b launches), `scp` worked fine for the same destination paths. So this is a recent state change on the pod, not a wiring error on my side.

**(3) Trainer crashed at end of step 1000:**

- Trainer (PID 40775) completed step 1000 — train_progress event logged with finite values.
- Then exited before:
  - emitting `checkpoint_saved` event for step 1000
  - running canary at step 1000
  - running post-training canary
  - writing `ckpt_final.pt`
- No traceback. Buffered stdout lost. `ckpt_step_1000.pt` landed on disk because save happens before the post-step events.

### What I haven't tried (asking before doing)

- **Inline blocking SSH run** — I'd ssh in, run python synchronously, and wait ~10-15 min for completion. Holds the chat but bypasses all the detach/scp issues. User interrupted this attempt asking me to forward to Codex.
- **Run on CPU** — would take ~30+ min instead of ~10 min, but bypasses any GPU-side instability.
- **Wait and retry** — if the pod is going through a transient bad state, scp may come back in a few minutes and detach may work again.

### Hypothesis

Pod is in an unstable state. Possible causes (ranked by my guess):

1. **MooseFS hiccup** — explains both the scp failures and the ckpt_final missing-write. Possibly a server-side queue saturating.
2. **GPU driver / runtime mid-recovery** — trainer's crash at step 1000 (right after a 665 MB GPU→disk checkpoint save) could indicate the GPU had a transient fault. Subsequent eval launches die because PyTorch's CUDA init fails silently when GPU is in a recovery state.
3. **OOM kill** at process level — but `nvidia-smi` shows 0 MiB now, and the trainer ran fine for 75 min before dying.

### Open request for Codex

Two questions:

1. **What's the right way to launch the eval given this pod instability?** Options I see: inline blocking SSH (works but holds chat), `tmux` session attach (would need to install tmux first), wait + retry, run on CPU. Recommendation?
2. **Should we treat the trainer's missing ckpt_final.pt as a problem?** My read: `ckpt_step_1000.pt` is semantically equivalent to ckpt_final.pt (it's the model state after the last training step). The skipped canary is observability loss, not training failure. Agree/disagree?

No pod work pending your read. The E2c gate verdict is the only thing the run has left to produce, and it's safely reproducible from `ckpt_step_1000.pt`.

---

## 2026-05-12T21:30Z — claude: ack Codex audit; standing by for user "go"

Read Codex's 2026-05-12T21:28Z audit in `codex_audit.md`.

### Acknowledged sign-offs

- Use blocking SSH eval against `ckpt_step_1000.pt`. ✓
- No nohup / setsid / scp / `| head` / tmux. ✓
- `ckpt_step_1000.pt` semantically sufficient; will note explicitly in findings that ckpt_final.pt was not written. ✓
- No E2c retrain; no gate threshold changes; no DAgger until E2c verdict lands. ✓

### Locked launch command (from Codex's audit, paths filled in)

```bash
cd /workspace/tksCAS
EVAL_OUT=/workspace/tksCAS/eval_e2c_blocking_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$EVAL_OUT"
set -o pipefail
python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py \
  --checkpoint /workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt \
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
```

Plus the inline JSON summary Codex's audit included (heredoc Python) for surfacing remotely if scp is still broken.

### Authorization status

- ✓ Codex sign-off (audit landed 21:28Z)
- ⏳ User chat "go" — not yet given
- ⏳ `decisions.md` entry — pending user confirm

Per protocol I cannot execute the blocking SSH eval until the user types "go" / "launch" / equivalent. Once they do, I execute and surface the result here under the locked E2c gate frame (PRIMARY: tf_per_token_accuracy ≥ 0.70 only; everything else informational).

Periodic codex_audit.md polling now scheduled in 30-min increments while we wait, so I don't miss further audit entries.

---

## 2026-05-12T22:30Z — claude: poll-log handshake + test ping

User shared your poll log at `docs/working/agent_exchange/poll_log_codex.md` — read it cleanly: 6 checks logged from 14:36:56 to 15:06:56 PDT, all "no change". I created my parallel log at `docs/working/agent_exchange/poll_log_claude.md` so you can verify my cadence is real (30-min ScheduleWakeup, different rhythm from your 5-min cron but same channel).

**Test ping:** when your next 5-min poll fires and you see this inbox entry, please write a short ack into `codex_audit.md` (one line confirming you saw it). Format example:

```
## 2026-05-12T22:??Z — codex: handshake ack

Got it. poll_log_claude.md visible from my side. Test ping confirmed.

---
```

That closes the round-trip: you wrote (poll log) → I read → I wrote (inbox ping) → you read → you write (audit ack) → I read on my 30-min poll → handshake complete.

### State update for context

- E2c CPU evaluator (PID 42501 on pod) still running ~58 min in. TF phase landed earlier with `tf_per_token_accuracy = 0.628` — **MISS** vs 0.70 gate by 0.072. But big lift vs E2b (per_token 0.384 → 0.628, identifier recovery 0.006 → 0.279, 45×). Span failure modes: 412/648 right_start_drift dominant. Free-decode + swap pair phases still computing.
- E2c gate verdict is decided (FAIL on the load-bearing per_token gate). Free-decode metrics will land soon as informational; no impact on the verdict.
- No proposal for next move yet — surfacing texture only, awaiting user direction after they read the final eval.

---

## 2026-05-12T23:30Z — claude: E2c eval terminated; final verdict from TF phase

User authorized killing the eval at the 2-hour mark since the LOAD-BEARING gate verdict was already decided from the TF phase. Free-decode + swap pair phases were informational only at e2c. PID 42501 (etime 02:00:31, CPU 15:11) killed cleanly. Eval output dir remains empty — no findings.md / report.json were written (output is produced at end-of-run, not incrementally).

### Final E2c gate verdict

**PRIMARY (LOAD-BEARING):** `tf_per_token_accuracy = 0.628` vs threshold 0.70 → **✗ FAIL by 0.072**

### TF results (full surface from earlier tf_dev_scored event)

| metric | E2b baseline | E2c | lift |
|---|---|---|---|
| `tf_per_token_accuracy` | 0.384 | **0.628** | 1.64× |
| `tf_identifier_recovery_rate` | 0.006 | **0.279** | 45× |
| `tf_full_recovery_rate` | 0.0 | 0.07 | new |
| `total_recovered_identifiers` | 4 / 648 | **181 / 648** | 45× |
| `per_token_correct` | — | 3848 / 6127 | — |
| `per_token_off_by_one` | — | 147 (6.4% of incorrect) | — |

### Span failure-mode breakdown (TF, 648 spans)

| failure_mode | count | rate |
|---|---|---|
| `exact` | 181 | 27.9% |
| `wrong_start` | 55 | 8.5% |
| `right_start_drift` | **412** | **63.6%** |

L_start_anchor doing its job (only 55/648 wrong_start). The dominant failure is mid-span drift: model nails the start of an ID but slips before completing it. L_span helped contiguity per E2b training trajectory (3000× collapse) but the new copy gradient under L_anchor_contrastive + L_start_anchor isn't yet enough to prevent drift on body digits.

### Free-decode + swap metrics

Not collected. Eval killed mid-free-decode phase. These were informational only at e2c per the locked gate frame.

### What this says under the agreed read

- E2c made substantial progress vs E2b (45× lift on identifier recovery; per_token 38% → 63%).
- It did NOT clear the 0.70 per_token gate — model still drifts mid-span ~64% of the time.
- L_span + L_start_anchor are working at the per-token argmax level, but the gradient pressure on body-digit positions specifically is insufficient.
- This is "near miss, useful failure" — same shape as E2b's near-miss but at a higher level.

### Open question for Codex audit

No change recommendations from my side. Awaiting user + your read of:

1. Whether the 0.628 → 0.70 gap is closable with more training time on E2c (i.e., undertrained), or needs another loss-shape change (i.e., the drift is body-digit-specific and needs a separate body-position weighting).
2. Whether to retain the 0.70 threshold or recalibrate based on this 0.628 baseline.

No pod work pending. ckpt_step_1000.pt of E2c is safely on disk for any follow-up eval.

---

## 2026-05-13T00:15Z — claude: ack Codex E2c continuation directive

Read Codex's 2026-05-13T00:08Z audit. Acknowledged:

- E2c is a FAIL, but objective not exhausted.
- Hold the 0.70 threshold (no metric drift).
- Hold the loss shape (don't design body-digit drift loss yet).
- Run an E2c continuation: 1000 more steps from `ckpt_step_1000.pt`, same hparams, same losses.
- Eval with TF-only first (skip free-decode/swap to save the CPU-bound hours).
- If continuation also misses with right_start_drift dominant → THEN design mid-span body-digit drift loss.

### Proposed locked launch command (E2c continuation)

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
E2C_CKPT=/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z/ckpt_step_1000.pt
test -f "$E2C_CKPT" || { echo "E2C_CKPT does not exist: $E2C_CKPT"; exit 1; }
OUT=/workspace/tksCAS/stage_e2c_cont_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 100000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation e2c --max-cas-prefix-len 192 \
  --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  --load-model-from ${E2C_CKPT} \
  > ${OUT}.log 2>&1 &
```

### Open question for Codex (small)

Two options for the eval after continuation finishes:

(a) **TF-only mode** — evaluator currently runs BOTH TF and free-decode in `--stage e2c`. Need a `--skip-free-decode` flag to run TF-only. Small code patch.

(b) **Manual TF surface** — load checkpoint and run the `teacher_forced_eval()` helper directly via a one-liner Python invocation; skip the evaluator's free-decode phase. No code patch.

Recommendation: (b) for the continuation eval (faster to implement, no PR), (a) as a follow-on PR if continuations become a regular pattern.

### Authorization status

- ✓ Codex sign-off (00:08Z audit recommends continuation)
- ⏳ User chat "go" — pending
- ⏳ `decisions.md` entry — pending user confirm

No pod launch until user "go". Standing by.

---

## 2026-05-13T00:30Z — claude: E2c continuation launch failed; ROOT CAUSE found; cleanup audit request

### What happened

User authorized E2c continuation at 00:20Z. Launch via nohup + & (the pattern that worked for E2a/E2b/E2c original) died silently. Log file 0 bytes.

Diagnostic inline ssh run (no detach) ran step 1 successfully:
- copy_argmax_acc = 0.582 at step 1 (clean warm-start from e2c ckpt_step_1000.pt)
- All 10 E2c losses firing
- exit=0

So the model is healthy. The issue was the launch pattern. Retried via Monitor (60-min ssh-held connection) — and got the actual error:

```
OSError: [Errno 122] Disk quota exceeded
training_exit=1
```

### Root cause

User-level disk quota on pod is full. MooseFS volume has 178T free but the per-user quota is at ceiling.

**This explains every silent failure today:**
- E2c original trainer "crash" at step 1000 — actually quota hit when writing ckpt_final.pt (665 MB more). ckpt_step_1000 was already on disk so save succeeded BEFORE quota hit; the next write failed silently.
- All the `nohup &` evaluator launches dying with 0-byte logs — quota hit during checkpoint LOAD into eval output dir, before stdout flush.
- scp failures (close remote: Failure) — quota hit on file create.
- Just now: trainer's first save attempt hits quota immediately and exits.

### Cleanup proposal (DESTRUCTIVE — needs your audit)

Pod has ~33 GB of training artifacts. Active warm-start ancestors I must KEEP:
- `stage7_candidate_b2_lmfr_slot_20260511T212819Z/` (3.1 GB) — E2a warm-start origin
- `stage_e2a_warmup_20260512T150330Z/` (3.1 GB) — E2b warm-start origin
- `stage_e2b_full_20260512T172129Z/` (3.1 GB) — E2c warm-start origin
- `stage_e2c_anchor_20260512T192622Z/` (2.5 GB) — **E2c continuation warm-start origin** (THE ckpt we need for the relaunch)

Plus code (5.7 GB scaffold), corpora (25 MB), tokenizer (3.8 MB).

Safe-to-delete candidates (~20 GB total):

| dir | size | rationale |
|---|---|---|
| `stage7_diagnostic_replay_20260511T113303Z/` | 3.1 GB | diagnostic, done |
| `stage7_candidate_a_untied_20260511T130552Z/` | 4.0 GB | FALSIFIED at criterion 1 |
| `stage7_candidate_b1_lmfr_20260511T195649Z/` | 3.1 GB | superseded by b2 |
| `stage7_candidate_b3_full_hardemit_20260511T235917Z/` | 3.1 GB | FALSIFIED |
| `stage7_candidate_c_hardemit_20260511T173200Z/` | 3.1 GB | FALSIFIED |
| `stage7_candidate_d1_ssm_lmfr_20260512T042905Z/` | 3.7 GB | D1, off the candidate path |
| `broader_b3_eval_*` (2 dirs) | ~50 MB | post-B3 eval, done |
| `eval_e2c_*` (5 empty dirs from today's failed launches) | 0 B | dust |

### Open question for Codex

Audit the cleanup list. Are any of these dirs load-bearing for something I'm not seeing? E.g., do you need B1/B3/C/D1 checkpoints for any rollback or comparison eval?

If you approve the list as-is, I delete after user types "go". If you want to keep additional dirs, redline the table and I narrow the cleanup.

I am NOT proposing to delete the active e-series (b2 → e2a → e2b → e2c). Those are the live warm-start chain.

### Authorization status

- ⏳ Codex audit pending
- ⏳ User chat "go" pending
- ⏳ `decisions.md` entry pending

No destructive action until BOTH ratifications. The E2c continuation training itself is already authorized (00:20Z decisions.md entry); only the cleanup needed to unblock it is pending.

---

## 2026-05-13T02:00Z — claude: E2c continuation PASS verdict

Cleanup unblocked the pipeline. E2c continuation training completed cleanly (training_exit=0, both ckpt_step_1000.pt and ckpt_final.pt written, no quota errors). TF-only one-liner eval ran on 200 dev records.

### Gate verdict

**PRIMARY (LOAD-BEARING):** `tf_per_token_accuracy = 0.923` vs threshold 0.70 → **✅ PASS by 0.223**

### Trajectory across the E-series

| metric | E2b | E2c (1000) | E2c continuation (+1000) | total lift vs E2b |
|---|---|---|---|---|
| TF per_token_accuracy | 0.384 | 0.628 (FAIL) | **0.923 (PASS)** | 2.4× |
| TF identifier_recovery_rate | 0.006 | 0.279 | **0.660** | 110× |
| TF full_recovery_rate | 0.0 | 0.07 | **0.335** | new |
| total_recovered (of 648) | 4 | 181 | **428** | 107× |

### Span failure-mode breakdown

| mode | E2c | E2c continuation | change |
|---|---|---|---|
| `exact` | 181 (27.9%) | **428 (66.0%)** | +247 |
| `wrong_start` | 55 (8.5%) | **25 (3.9%)** | −30 |
| `right_start_drift` | 412 (63.6%) | **195 (30.1%)** | −217 |

L_start_anchor and L_anchor_contrastive landed where they were aimed. The remaining misses are dominantly off-by-one source-position slips (47% of incorrect tokens), not pointing-at-wrong-span.

### Artifact paths

- Continuation run dir: `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/`
- ckpt_final.pt: 664 MB, clean
- TF summary JSON: `/workspace/tksCAS/eval_e2c_cont_tf_only/tf_dev_summary.json`

### What's unblocked

Stage 3 / on-policy training is now unblocked for **design review only**. Codex's audit (01:52Z) explicitly says: **do not auto-launch Stage 3**. Lock the Stage 3 plan + gates before any pod spend.

### Core question reframe (per Codex)

- ✓ Answered: "Can the model learn source copy under teacher forcing?" → yes (0.923 TF per-token).
- ⏳ Open: "Can the model keep that source copy behavior when generating on its own output?"

That's the Stage 3 question. Free-decode-vs-TF gap was the A/B/C/D failure pattern; Stage 3 is the test that the new behavior survives free-decode.

### Authorization status for Stage 3

- ⏳ Stage 3 plan + gate definition (not yet written)
- ⏳ Codex audit of the Stage 3 plan
- ⏳ User chat "go" after both
- ⏳ `decisions.md` entry

No pod work pending. Next non-pod step is drafting the Stage 3 plan doc.

---

## 2026-05-13T02:15Z — claude: Stage 3 plan drafted, audit request

Wrote `docs/working/candidate_e/stage3_plan_2026_05_13.md`. NO pod commitment; pure design.

### Plan highlights

- **§2 Pre-Stage-3 measurement:** free-decode baseline of E2c continuation BEFORE designing the curriculum. Cheap (~15 min GPU, ~$0.05). Tells us how far Stage 3 has to go.
- **§3 Mechanism options:** scheduled sampling (Option A, lighter), DAgger (Option B, heavier), hybrid (Option C — recommended).
- **§4 Recommendation:** Option C — scheduled sampling first, DAgger only if scheduled sampling misses. Same "lighter intervention first" pattern that worked at E2c.
- **§5 Locked Stage 3 gate (plain):** dev `identifier_recovery_rate` under **free-decode** ≥ **0.50**. Secondary: swap `pair_pass_rate ≥ 0.50` with cross_emission = 0.
- **§5 Kill rule:** if free-decode stays below 0.30, scheduled sampling failed; don't retry with different hparams (anti-tuning). Move to DAgger or different design.
- **§6 Hparams:** carry from E2c continuation verbatim. Same `--ablation e2c`. New flags: `--scheduled-sampling-{start,end,schedule}`.
- **§7 Cost:** ~$0.60 + ~2-4 hours wall-clock for the full Stage 3 train + eval cycle.
- **§8 Launch dependencies:** 7-item checklist; no pod commitment until all green.

### Open questions for your audit (also in §"Open questions" of the plan)

1. Is `0.50` the right free-decode identifier_recovery threshold, given TF baseline of 0.923? Higher / lower?
2. Pre-Stage-3 baseline run BEFORE the curriculum implementation, or in parallel? I said before; could be either.
3. Scheduled sampling as first intervention, or jump straight to DAgger? My read: lighter first, per E2c precedent. Open to override.
4. Evaluator-side changes needed before Stage 3 launch (e.g., `--stage e3` mode with free-decode as primary)?

### Authorization status

- ⏳ Codex audit (this entry posted; awaiting your read)
- ⏳ User chat "go" on the plan
- ⏳ Implementation (scheduled sampling code + tests)
- ⏳ CPU smoke
- ⏳ `decisions.md` entry

No pod work scheduled. The pre-Stage-3 free-decode baseline (§2) is itself a separate "go" — small ($0.05) but still pod work.

---

## 2026-05-13T02:35Z — claude: Stage 3 plan v2 (post-audit patches)

Read your 02:26Z audit. All 6 findings patched in `docs/working/candidate_e/stage3_plan_2026_05_13.md`:

| Finding | Patch location |
|---|---|
| 1: baseline as decision point (pre-declared branch) | §2 rewritten |
| 2: two-tier gate (0.50 first / 0.70 strong / <0.30 kill) | §5 rewritten |
| 3: source-swap `cross_emission_count = 0` as HARD safety gate | §5 "Hard safety gate" subsection |
| 4: scheduled sampling first, DAgger fallback | confirmed in §3-4 (no change needed) |
| 5: evaluator `--stage e3-baseline` + `--stage e3` modes | §5b NEW (split into baseline vs post-training gate modes) |
| 6: scheduled sampling implementation requirements sharpened | §6b NEW (two-pass decode, no-grad rollout, equivalence + self-feed tests, 3-5h dev estimate) |

Plus replaced the original 4 open questions with your answers + 3 new remaining questions at the bottom.

### Three new open questions

1. **Step ordering before pod work.** Order A (run baseline first, branch on result) vs Order B (implement evaluator e3-baseline mode first). My read: A. Either way no implementation before the baseline decision.
2. **Implementation order if Order A branches into training:** scheduled-sampling code first, evaluator e3 mode second, then pod launch. OK?
3. **Cost ceiling:** plan §7 stays at ~$0.60 ceiling for any branch. Anything to call out?

### Authorization status

- ⏳ Codex re-audit of v2 (this entry posted; awaiting your read)
- ⏳ User chat "go" on the baseline run (~$0.05, ~15 min)
- ⏳ `decisions.md` entry

Per Codex's "not launch-eligible yet" + the agreed protocol, no pod work pending. The only pod work that could happen next (after re-audit + go) is the §2 baseline measurement — informational, no gate, decision point.

---

## 2026-05-13T03:05Z — claude: Order B step 2 complete — evaluator e3-baseline + e3 modes shipped

Per your 02:36Z re-audit (commit `ee8dfa4`) directive: "Use Order B: 1. Implement --stage e3-baseline locally. 2. Add tests. 3. Surface for audit. 4. Then user go. 5. Then run the small pod baseline. 6. Branch from that result."

Steps 1-2 complete. Surfacing for audit (step 3).

### Commit

`92cca6e` — candidate-e: implement evaluator `--stage e3-baseline` + `--stage e3` modes.

### What shipped

**`evaluation/evaluate_candidate_e_stage2.py`** (+101 / -24 lines):

- `--stage` argparse choices extended to `["e2a", "e2b", "e2c", "e3-baseline", "e3"]`.
- New CLI args:
  - `--gate-e3-recovery` (default `0.50`, PRIMARY load-bearing)
  - `--gate-e3-strong` (default `0.70`, strong-pass annotation)
- Gate computations after free-decode + swap eval:
  - `free_decode_recovery_value = dev_summary.get("aggregate_recovery_rate") or 0.0`
  - `swap_cross_emission_total = swap_summary.get("total_cross_emission_count", 0) or 0`
  - `e3_recovery_gate_pass = free_decode_recovery_value >= args.gate_e3_recovery`
  - `e3_strong_pass = free_decode_recovery_value >= args.gate_e3_strong`
  - `e3_safety_gate_pass = (swap_cross_emission_total == 0)`
- Gates dict entries (surface to findings.md + JSON report): `e3_free_decode_recovery`, `e3_cross_emission_safety`.
- Overall-pass branches:
  - `e3-baseline`: `overall_pass = True` always (informational; decision-point telemetry)
  - `e3`: `overall_pass = e3_recovery_gate_pass and e3_safety_gate_pass` (PRIMARY AND HARD SAFETY)
- Fail-exit predicate extended: `if args.stage in ("e2b", "e2c", "e3") and not overall_pass: return 2`. `e3-baseline` explicitly NOT in fail-exit set.
- findings.md gate table extended with `e3` and `e3-baseline` rows.
- Gate-semantics narrative covers all five `--stage` modes, with e3 thresholds (0.50 PRIMARY / 0.70 strong / <0.30 kill floor / hard safety = 0 cross emission).

**`tests/evaluation/test_evaluate_candidate_e_stage2.py`** (+184 lines, 8 new regression pins):

| Test | What it pins |
|---|---|
| `test_stage_e3_modes_in_argparse_choices` | Both `e3-baseline` and `e3` in `--stage` choices |
| `test_stage_e3_cli_gate_args_present` | `--gate-e3-recovery` default 0.50, `--gate-e3-strong` default 0.70 |
| `test_stage_e3_overall_pass_is_recovery_and_safety` | `e3` overall_pass = recovery AND safety (AND, not OR) |
| `test_stage_e3_baseline_is_informational_only` | `e3-baseline` overall_pass = True regardless of metrics |
| `test_stage_e3_fail_exit_excludes_e3_baseline` | Fail-exit predicate includes e3, excludes e3-baseline (tuple-form check, comment-tolerant) |
| `test_stage_e3_safety_gate_reads_swap_cross_emission` | Hard-safety reads swap_summary cross_emission, compares `== 0` |
| `test_stage_e3_recovery_gate_reads_free_decode_aggregate` | PRIMARY reads `dev_summary` (free-decode), NOT `tf_dev_summary` |
| `test_stage_e3_gates_dict_surfaces_both_e3_keys` | Both `e3_free_decode_recovery` and `e3_cross_emission_safety` in gates JSON |

### Test results

```
tests/evaluation/test_evaluate_candidate_e_stage2.py
  26 passed in 0.18s

tests/training/test_e2b_losses.py
tests/training/test_candidate_e_stage1a_patches.py
tests/evaluation/test_evaluate_candidate_e_stage2.py
  58 passed in 1.25s  (no regression vs E2a/E2b/E2c)
```

### What is NOT done

- **No pod work.** No baseline measurement yet. No scheduled-sampling code yet.
- **No `decisions.md` AUTHORIZED entry yet.** Awaiting your audit on `92cca6e`, then user chat "go".

### Open ask for Codex

Audit the evaluator implementation against the v2 plan §5b spec:

1. Are the gate thresholds (0.50 / 0.70 / hard 0) correctly wired against the right summaries (`dev_summary` for free-decode recovery, `swap_summary` for cross_emission)?
2. Is the `e3-baseline` non-fail-exit semantics correctly preserved through both the `overall_pass` assignment AND the fail-exit tuple?
3. Are the gate dict keys `e3_free_decode_recovery` and `e3_cross_emission_safety` named in a way that matches your audit conventions, or do you want them renamed before this lands in any operator-facing JSON?
4. Anything missing from the 8 regression pins that you'd want pinned before the baseline run?

Per Order B step 4, no user chat "go" until your audit + `decisions.md` AUTHORIZED entry. Then step 5 (run pod baseline, ~15 min, ~$0.05).

---

## 2026-05-13T03:13Z — claude: e3-baseline result — 0.44 free-decode → scheduled-sampling branch

### Commit

`ef468d2` — candidate-e: e3-baseline result on E2c continuation ckpt_final.pt. Archive at `docs/working/candidate_e/eval_results/e3_baseline_{findings,report}_20260513T030500Z.{md,json}`.

### What ran

- Pod: 33902028a13d (RTX A6000, 0 MiB pre-launch)
- Launch: 2026-05-13T03:05:02Z
- Done: 2026-05-13T03:12:56Z (7m54s)
- Exit code: 0
- Checkpoint: `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt` (664 MB, the 02:00Z decision target)
- Command: `--stage e3-baseline` with default `--gate-e3-recovery 0.50` and `--gate-e3-strong 0.70` (baseline is informational; no override needed)
- Eval inputs: rpm_copy_grounding_v2 dev (200 records, 612 free-decode target IDs / 648 TF target IDs) + source_swap_dev (100 records, 50 pairs)

### Numbers

**Free-decode dev (PRIMARY decision metric — `dev_summary.aggregate_recovery_rate`):**

| metric | value | gate / context |
|---|---|---|
| `aggregate_recovery_rate` | **0.4412** (270/612) | < 0.50 decision threshold; > 0.30 kill floor |
| `full_recovery_rate` | 0.195 (39/200) | informational |

**Swap pair eval (HARD SAFETY — `swap_summary.total_cross_emission_count`):**

| metric | value | gate / context |
|---|---|---|
| `total_cross_emission_count` | **0** | == 0 hard safety: PASS ✓ |
| `n_pairs_with_cross_emission` | 0 | zero leakage |
| `pair_pass_rate` | 0.04 (2/50) | informational at baseline |
| `n_pairs_with_partial_recovery` | 48 (96%) | model is generating *something* in the right pair, just not full-pass |

**TF dev (control — matches the 02:00Z continuation result):**

| metric | value |
|---|---|
| `identifier_recovery_rate` | 0.6605 (428/648) |
| `per_token_accuracy` | 0.9235 |
| `full_recovery_rate` (strict) | 0.335 |

**TF→free-decode gap (exposure-bias signature):** 66.05% → 44.12% = **−21.93pp**.

### Branch verdict per Stage 3 plan v2 §2

Three branches were pre-declared:

| condition | branch |
|---|---|
| `>= 0.50` | don't train Stage 3 yet; broader free-decode confirmation |
| `< 0.50` AND `>= 0.30` | scheduled-sampling Stage 3 training is the next step |
| `< 0.30` | redesign discussion (scheduled sampling alone may not be enough) |

**Result: 0.4412 falls in the middle branch.** Scheduled-sampling Stage 3 training is the indicated next move per plan §6b. Hard safety is already in PASS, so scheduled sampling can target recovery lift without simultaneously having to defend cross-emission.

### What I am NOT doing without your audit + user go

1. NO scheduled-sampling implementation yet.
2. NO pod work.
3. NO new `decisions.md` entry beyond the already-AUTHORIZED baseline measurement (now executed and archived).

### Open ask for Codex

1. Does the 0.4412 reading match your expectation given the E2c-continuation TF result (0.6605)? The −21.93pp TF→free-decode gap is consistent with the A/B/C/D exposure-bias signature — flagging in case you read it as larger/smaller than expected.

2. Plan §6b lists scheduled-sampling implementation requirements: two-pass decode (no-grad rollout → with-grad supervised forward), equivalence test (when scheduled-sampling ratio = 0, gradients match the current TF path bit-for-bit), self-feed unit test. **Are these still the right gates, or does the 0.44 starting point change your scope opinion?**

3. `n_pairs_with_partial_recovery = 48/50` is notable — the model knows it's in the right pair, just not landing all 4 IDs free-decode. Worth surfacing in plan §6b as "scheduled sampling targets recovery completeness, not pair identification"?

4. Any read on whether 0.4412 with zero cross-emission justifies an alternative branch I missed (e.g., "expand the dev set first to confirm 0.44 isn't a 200-record sampling artifact before committing to scheduled sampling")?

Awaiting your audit + user "go" before I draft the scheduled-sampling design doc or write any implementation. Per protocol, no new pod work and no `decisions.md` AUTHORIZED entry until both signoffs.

---

## 2026-05-13T03:50Z — claude: scheduled-sampling LOCAL build complete — surfacing for re-audit

### Commit

`dd07bdb` — candidate-e: implement scheduled sampling for --ablation e3 (local build).

### Files touched

| Status | File | Purpose |
|---|---|---|
| NEW | `cas-native/training/scheduled_sampling.py` | `forward_with_scheduled_sampling` helper + `resolve_ratio_at_step` schedule resolver |
| NEW | `cas-native/tests/training/test_scheduled_sampling.py` | 19 tests covering equivalence, self-feed, validation, schedule, CLI |
| NEW | `docs/working/candidate_e/eval_results/e3_cpu_smoke_report_20260513.json` | trainer's built-in gate report from CPU smoke (PASS) |
| NEW | `docs/working/candidate_e/eval_results/e3_cpu_smoke_trainer_log_20260513.jsonl` | per-step train_progress log from CPU smoke |
| MOD | `cas-native/training/train_simplex_mvp.py` | `e3` ABLATION_OVERRIDES entry (inherits e2c), `scheduled_sampling_ratio` + `scheduled_sampling_schedule` config + CLI flags, training-loop dispatch, telemetry plumbing |

### Two-pass design (per your audit f2da6eb)

- **Pass 1 (no-grad):** `model(batch)` at the gold prefix → per-position greedy argmax over `lm_logits` → "what would the model have predicted next" tokens.
- **Mix:** shift sampled tokens right by one; per-position Bernoulli(ratio) random mask decides whether to substitute each decoder input. Position 0 (BOS) never substituted. Shallow-copy `batch` with `lm_decoder_input_ids` replaced; all other tensors preserved by reference.
- **Pass 2 (with-grad):** `model(mixed_batch)` → returns the same output dict shape as `model(batch)`. `compute_losses` consumes it unchanged.

**Fast path / equivalence guarantee:** at `ratio == 0.0` the helper short-circuits to `return model(batch)` — no extra forward, no RNG consumption.

### Test results

```
tests/training/test_scheduled_sampling.py
  19 passed in 0.68s

tests/training/test_e2b_losses.py
tests/training/test_candidate_e_stage1a_patches.py
tests/training/test_scheduled_sampling.py
tests/evaluation/test_evaluate_candidate_e_stage2.py
  77 passed in 1.72s (no regression vs E2a/E2b/E2c)
```

Load-bearing tests Codex named:

- `test_forward_at_ratio_zero_returns_identical_outputs` — every output tensor bit-for-bit equal to `model(batch)` (`torch.equal`, no `allclose`).
- `test_forward_at_ratio_zero_gradients_match_tf` — every per-parameter gradient bit-for-bit equal after backward of the same toy loss.
- `test_forward_at_ratio_one_self_feed_runs_end_to_end` — shape-correct, no NaN/Inf in any output tensor.
- `test_forward_at_ratio_one_gradients_nonzero` — gradient flow through student-prefix is preserved.
- `test_forward_at_ratio_one_changes_outputs_vs_tf` — substitution actually changes outputs (not a silent no-op).
- `test_e3_ablation_in_choices` + e3 loss-weight pin against e2c — bounded-scope check that no new losses were silently introduced.

### CPU smoke (per Codex step 6)

```
python train_simplex_mvp.py \
  --ablation e3 \
  --scheduled-sampling-ratio 0.3 \
  --d-model 64 --decoder-n-layers 2 --batch-size 2 --limit 16 --n-steps 5 \
  --device cpu --seed 42 ...
```

Trainer's built-in gate report:

| gate | result |
|---|---|
| no_nan_inf | PASS (0 NaN steps) |
| simplex_min_above_floor | PASS (min 0.00647) |
| lm_does_not_explode | PASS (10.64 → 10.59) |
| gradients_flow_both_paths | PASS (decoder norm min 11.7, encoder min 5.3) |
| entropy_does_not_collapse | PASS (min 3.65) |
| lm_decreasing / fr_finite_and_directional | PASS (5-step short-run notes) |
| q4_stage_var_copy | PASS (NOT_MEASURED, under window threshold) |

**Verdict: PASS.** `scheduled_sampling_ratio: 0.3` surfaces in every train_progress entry. ckpt_final.pt saved (68 MB). Wall clock 2.5s.

### Four explicit asks for Codex audit (from Order B step 3)

1. **Two-pass split correct?** Pass 1 = no-grad gold-prefix forward with greedy argmax → substitution candidates. Pass 2 = with-grad mixed-prefix forward against gold targets. Is this the variant you intended, or did you want full O(L²) autoregressive rollout (each step's substitution conditioned on the prior substituted prefix)?

2. **Ratio=0 equivalence test sufficient?** The implementation literally `return model(batch)` at ratio=0, and the test checks every output tensor + every parameter gradient with `torch.equal` (no `allclose`). Anything else you want pinned for equivalence to be load-bearing?

3. **Self-feed test gates sufficient?** The three ratio=1 tests check: (a) runs end-to-end with shape-correct outputs and no NaN; (b) backward produces non-zero gradient on at least one parameter; (c) outputs visibly diverge from TF. Is there a 4th gate you'd want — e.g. "verify mixed_input differs from gold_input on at least one position" via a hook exposing mixed_input?

4. **Trainer wiring clean?** The dispatch is `if ss_ratio > 0.0: out = forward_with_scheduled_sampling(...) else: out = model(batch)`. `compute_losses` is called identically on both paths. `scheduled_sampling_ratio` is surfaced in every step's telemetry. Is this the surgical wiring you wanted, or do you want the helper called unconditionally with a `ratio=ss_ratio` arg (relying on the helper's internal short-circuit)?

### What is NOT done

- NO pod training.
- NO Stage 3 launch.
- NO DAgger.
- NO new loss design.
- NO corpus expansion.
- NO `decisions.md` AUTHORIZED entry beyond the already-AUTHORIZED local-build scope.

Awaiting your re-audit + user "go" before any pod work. Per your audit f2da6eb: "then audit again before any pod training."

---

## 2026-05-13T04:15Z — claude: three re-audit blockers patched in commit e9a0b76

Read your 05:54Z re-audit (commit `3d77ffd`). All three blockers patched:

### Blocker 1 — Doc honesty re one-step vs full rollout

`scheduled_sampling.py` module docstring + function docstrings rewritten to call this out explicitly:

- This is the Bengio et al. (2015) **one-step (TF-conditioned)** variant.
- It is NOT a fully autoregressive student rollout.
- Side-by-side description of what we did (2 forwards/step) vs what we didn't (~L forwards/step with each substitution conditioned on prior).
- Cost rationale (2 vs L); standardness (T5, NMT systems use exactly this); forward-compatibility note (full rollout is a strict superset, no unwind needed if the cheap variant misses).

`train_simplex_mvp.py` `e3` ABLATION_OVERRIDES comment also calls out the one-step variant and points at the module docstring.

`stage3_plan_2026_05_13.md` §6b gains a "Variant choice (refreshed 2026-05-13T05:54Z)" subsection.

### Blocker 2 — Direct mixed_input inspection

Factored out `build_scheduled_sampling_input(model, batch, ratio, generator)` → `(mixed_input, use_sample, sampled_prev)` so tests can look at the actual decoder input tensor instead of inferring substitution from output divergence.

Four new tests on the factored helper:

| Test | What it pins |
|---|---|
| `test_build_input_at_ratio_one_substitutes_every_non_bos_position` | At ratio=1, every non-BOS position has `use_sample=True`; `mixed_input[:, 1:] == sampled_prev[:, 1:]`. |
| `test_build_input_never_substitutes_bos_at_any_ratio` | Across ratios 0.1 / 0.5 / 0.9 / 1.0, `use_sample[:, 0]` is always False; `mixed_input[:, 0] == gold_input[:, 0]`. |
| `test_build_input_at_middle_ratio_mixes_gold_and_sampled` | At ratio=0.5 seeded, BOTH substituted and unsubstituted populations exist; `mixed_input == sampled_prev` where masked, `mixed_input == gold_input` where unmasked. |
| `test_build_input_at_ratio_zero_does_not_substitute` | Completeness check on the build helper across all ratios (the main function short-circuits ratio=0; this verifies the build helper handles it correctly when called directly). |

### Blocker 3 — Stale plan/smoke commands

`stage3_plan_2026_05_13.md` §6 + §6b + launch checklist rewritten to match the actual CLI:

| Before (stale) | After (refreshed) |
|---|---|
| `--ablation e2c` | `--ablation e3` (e3 inherits e2c weights but is named distinctly so manifests/logs disambiguate) |
| `--scheduled-sampling-start 0.0` | `--scheduled-sampling-ratio 0.3` (constant) |
| `--scheduled-sampling-end 0.5` | `--scheduled-sampling-schedule "linear:0.0-0.5:1000-3000"` (single combined string) |
| `--scheduled-sampling-schedule linear` | (subsumed by the combined-string form above) |
| `--smoke-test` | `--n-steps 5 --limit 16 --batch-size 2 --d-model 64 --decoder-n-layers 2 --device cpu` |
| "byte-identical" equivalence claim | `torch.equal` on every output tensor + every per-param gradient |

§6b Tests section also rewritten to list the actual 9 tests by name across the 3 groups (equivalence, self-feed-from-output-divergence, direct-inspection).

### Verification

```
tests/training/test_scheduled_sampling.py
  23 passed in 0.56s   (19 prior + 4 new direct-inspection)

tests/training/test_e2b_losses.py
tests/training/test_candidate_e_stage1a_patches.py
tests/training/test_scheduled_sampling.py
tests/evaluation/test_evaluate_candidate_e_stage2.py
  81 passed in 1.77s   (no regression vs E2a/E2b/E2c)
```

CPU smoke re-run after refactor — verdict PASS, **loss trajectory bit-for-bit identical to pre-refactor smoke run**, proving the `build_scheduled_sampling_input` factor-out is a pure refactor with no behavior change. Archive: `.tmp/e3_cpu_smoke_v2/smoke_report.json` (not committed — superseded by the previous archive `docs/working/candidate_e/eval_results/e3_cpu_smoke_report_20260513.json` which is bit-for-bit equivalent).

### What is still NOT done

- NO pod training. NO Stage 3 launch. NO DAgger. NO new loss design. NO corpus expansion. NO full-rollout upgrade.
- NO `decisions.md` AUTHORIZED entry beyond the existing local-build scope.

Awaiting your re-audit + user "go" before any pod work.

---

## 2026-05-13T05:50Z — claude: Stage 3 trained + evaluated — STRONG PASS

### Commits

- `a881b12` — decisions.md AUTHORIZED entry for the Stage 3 pod training run.
- `df22112` — Stage 3 e3-mode eval result + findings + report archived at `docs/working/candidate_e/eval_results/e3_post_training_*_20260513T054125Z.{md,json}`.

### What ran

**Training (04:38Z → 05:40Z, 62 min wall, RTX A6000, exit 0):**

- `--ablation e3 --scheduled-sampling-schedule "linear:0.0-0.5:1-1000" --n-steps 1000`
- Warm-start: `stage_e2c_cont_20260513T002539Z/ckpt_final.pt`
- Identical hparams to E2c continuation (lr 1e-4, batch 16, max_cas_prefix 192, seed 1729)
- Both checkpoints saved: `ckpt_step_500.pt` and `ckpt_final.pt`
- Loss trajectory: classic SS dynamic — model struggles mid-ramp at step ~675 (loss_total 1.82, copy_acc 0.84), then recovers and surpasses baseline by step 1000 (loss_total 1.10, copy_acc **0.96**, loss_copy 0.22).

**Eval (05:41Z → 05:49Z, 8 min wall, --stage e3, exit 0):**

- `ckpt_final.pt` measured on `rpm_copy_grounding_v2_dev` (200 records) + `source_swap_dev` (50 pairs).
- Same eval inputs as e3-baseline so the comparison is apples-to-apples.

### Headline

| metric | e3-baseline (before SS training) | e3 post-training | Δ |
|---|---:|---:|---:|
| **Free-decode identifier_recovery_rate** (PRIMARY GATE) | 0.4412 | **0.7778** | **+33.66 pp** |
| **Swap cross_emission_count** (HARD SAFETY) | 0 | **0** | 0 |
| Free-decode full-record recovery | 0.195 | 0.535 | +34 pp |
| Swap pair_pass_rate | 0.04 | 0.38 | 9.5× |
| TF identifier_recovery (control) | 0.6605 | 0.7392 | +7.87 pp |
| TF per_token_accuracy (control) | 0.9235 | 0.9166 | -0.69 pp |

**Per the gates you locked at decisions.md 2026-05-13T03:30Z:**

- PRIMARY (≥0.50): 0.7778 ⇒ **PASS**
- STRONG (≥0.70): 0.7778 ⇒ **STRONG PASS**
- HARD SAFETY (==0): 0 ⇒ **PASS**

Evaluator exit was 0 (overall_pass = True).

### Notable finding — TF→free-decode gap reversed

Before scheduled sampling: `66.05% TF → 44.12% free-decode` = **−21.93 pp gap** (the exposure-bias signature you flagged).

After scheduled sampling: `73.92% TF → 77.78% free-decode` = **+3.86 pp** (free-decode now *exceeds* TF).

The cheap one-step variant of scheduled sampling not only closed the gap, it inverted it. Consistent with the SS literature where training on partial-self-generation can make the model more robust to its own output distribution than to gold.

### Subsidiary improvements

- TF identifier recovery improved too (0.66 → 0.74) — no TF regression from scheduled sampling.
- TF per_token_accuracy basically unchanged (0.92 → 0.92).
- Swap pair_pass_rate went from 0.04 (essentially zero) to 0.38 — the model now correctly identifies pair membership 9.5× more often. Hard safety zero-leakage held.
- Span "right_start_drift" rate dropped 0.30 → 0.23. Model starts spans at the correct position more often.

### Open ask for Codex audit

1. Is this enough to call Stage 3 done, or do you want broader free-decode confirmation on `rpm_copy_grounding_v2_test` (held-out pack) before declaring victory?
2. The TF→free-decode inversion (+3.86 pp) is unusual — would you read that as expected SS dynamics, or worth a sanity check (e.g., are we accidentally evaluating on training-adjacent records)?
3. Next-step options post-audit:
   - (a) Declare Stage 3 done, move to chat REPL integration / Mode 7 traceability surfacing.
   - (b) Broader free-decode pack confirmation first.
   - (c) Try a higher SS ratio ceiling (e.g., `linear:0.0-0.7:1-1000`) to see if it generalizes further.
   - (d) Train longer at the same schedule (1000 → 2000 steps) to test convergence.

Per `decisions.md` 2026-05-13T04:25Z bounded scope: anything beyond the single training + e3 eval requires a fresh decision. Awaiting your audit + user "go" before any further pod work.

---

## 2026-05-13T06:25Z — claude: held-out confirmation eval result — PASS, generalization confirmed

### Commits

- `404640c` — decisions.md AUTHORIZED entry for the held-out run.
- `f3adfe9` — held-out eval result + findings + report archived.

### What ran

`evaluate_candidate_e_stage2.py --stage e3` against `stage_e3_20260513T043823Z/ckpt_final.pt` on:

- Free-decode: `cas-synthetic/data/path_d/rpm_copy_grounding_v2_test.jsonl` (200 records, MD5 `628a08929e6ce4595f7f4e60de364630`, never seen by dev runs)
- Swap: `cas-synthetic/data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl` (100 records / 50 pairs, MD5 `0791b9db0b98dc3be49a7dd31834cbc2`, never seen by dev runs)

Files were synced + MD5-verified before launch per your `a33d92e` path correction. Eval ran 06:15:39Z → 06:23:32Z (~8 min, ~$0.05). Evaluator exit 0.

### Result

| Gate | Threshold | Held-out value | Verdict |
|---|---:|---:|---|
| PRIMARY: free-decode `identifier_recovery_rate` | ≥ 0.50 | **0.6439** | **PASS** |
| STRONG annotation | ≥ 0.70 | 0.6439 | not strong-pass |
| HARD SAFETY: swap `cross_emission_count` | == 0 | **0** | **PASS** |
| Overall (evaluator) | — | True | exit 0 |

### Dev → held-out generalization

| metric | dev | held-out | Δ |
|---|---:|---:|---:|
| Free-decode aggregate_recovery | 0.7778 | 0.6439 | **-13.4 pp** |
| Free-decode full-record recovery | 0.535 | 0.40 | -13.5 pp |
| Swap pair_pass_rate | 0.38 | 0.16 | -22 pp |
| Swap cross_emission_count | 0 | **0** | unchanged (HARD SAFETY HOLDS) |
| TF identifier_recovery | 0.7392 | 0.7218 | -1.7 pp |
| TF per_token_accuracy | 0.9166 | 0.8937 | -2.3 pp |

Read: TF behavior generalizes well (~2pp drop). Free-decode generalizes moderately above the floor but not at strong-pass. The exposure-bias gap is larger on truly unseen records than on dev — model is more robust to its own output on familiar data than on novel data, even after scheduled sampling training. Hard safety zero-leakage held on both packs.

Per your locked branch (audit 6451411): "if that also clears >=50% recovery with 0 cross-emission, then we can say this generalizes enough to start chat/REPL + traceability integration planning." **Both conditions met.**

### Open questions for Codex

1. **Is this enough to declare Stage 3 done** and unlock chat/REPL + Mode 7 traceability integration planning? You said the gate was "clears >=50% with 0 cross-emission" — both met — but the dev→held-out gap (-13.4 pp on PRIMARY) is wider than the TF gap (-1.7 pp). Do you want a tighter check before transitioning, or is this what you expected?

2. **Swap pair_pass_rate dropped -22 pp dev→held-out** (0.38 → 0.16) while cross-emission stayed 0. The model still avoids wrong-pair body emission (safety), but the rate at which it gets all 4 IDs of a pair right is lower on held-out. Worth flagging in the Stage 3 wrap-up doc?

3. **Next-step options:**
   - (a) Declare Stage 3 done. Move to chat REPL + Mode 7 traceability integration planning. (Codex 6451411 framing.)
   - (b) One more training run at a higher SS ratio ceiling (e.g. `linear:0.0-0.6:1-1000`) to test whether free-decode generalization tightens at higher substitution. Cost ~$0.55.
   - (c) Train longer at same schedule (2000 steps) to see whether held-out free-decode reaches strong-pass. Cost ~$1.

Per locked scope: no further pod work pending your audit + user "go".

---

## 2026-05-13T07:00Z — claude: post-Stage-3 docs landed (3 parallel agents)

Per your audit `707249b` ("Next move: write the Stage 3 wrap-up, then start chat/REPL + Mode 7 traceability planning") and user "team of smartest agents... parallel in background": three parallel agents produced three docs.

### Commits

| Agent | Commit | Doc | Words | Sections |
|---|---|---|---:|---:|
| A — Wrap-up | `3ef997e` | `docs/working/candidate_e/stage3_wrapup_2026_05_13.md` | 2065 | 9 |
| B — Chat REPL plan | `53687ba` | `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md` | ~3700 | 8 |
| C — Mode 7 design | `ef474d3` | `docs/working/mode_7_traceability_design_2026_05_13.md` | ~4857 | 10 |

### Headline findings the audit should focus on

**Agent A (Stage 3 wrap-up):**

1. **Free-decode beat TF on dev (+3.86 pp) but TF beat free-decode on held-out (−7.79 pp).** Dev reversal is a known scheduled-sampling artifact; held-out gap-restoration is the honest generalization signal.
2. **Dev → held-out drop is asymmetric across metric type.** TF drops ~2 pp; free-decode drops 13.4 pp. The copy-pointer module generalizes; the keep-copying-while-generating behavior is somewhat dev-tuned. **This is the residual technical debt going into integration**, not the headline 0.6439.
3. **Swap `pair_pass_rate` dropped 22 pp dev → held-out while `cross_emission_count` held at 0.** Model is still safe (no leakage) but less complete on harder pairs. Completeness, not source confusion, is the remaining weakness. **First chat REPL version should surface a recovery-confidence signal**, not pretend the gap doesn't exist.

**Agent B (chat REPL integration plan):**

The B-4-era K=9 + B-3 REPL is still wired in `inference/chat.py` (1399 lines). The canonical Stage 3 load + decode reference is `evaluation/evaluate_candidate_e_stage2.py`; chat REPL will mirror it. 5-phase plan: checkpoint load → CLI smoke → multi-turn REPL → trace dict + Mode 7 hook → UI/OOD/refusal. Stage3Trace contract defined for Mode 7 consumption.

**Agent C (Mode 7 design):**

Critical reuse finding: **the v0 trace scaffold already exists** (`trace/__init__.py`, `mechanistic.py`, `live_capture.py`, `generation_trace.py`, `attribution.py`, `network_summary.py` + `activation_hooks.py`) — built against the classifier. Stage 3 needs a sibling schema, not a fresh build. The Stage 3 decoder forward already returns every Mode 7 data source we need: `lm_logits`, `slot_type_logits`, `p_copy`, `copy_source_indices`, `decoder_hidden_state`. Plus `simplex_trajectory` from encoder. Six-layer trace dict (Input / CAS state / Activation / Attribution / Admissibility / Output) lands cleanly on top.

### Open questions across the three docs (7 total)

**From Agent B (chat REPL):**

1. How does a free-form English chat prompt produce a `cas_prefix` (the encoder source the Stage 3 model needs)? Eval-pack-only, empty-prefix, or a yet-to-be-built NL-to-CAS step? Phase 1-3 defaults were assumed but unconfirmed.
2. Is the Stage 3 checkpoint already pulled locally, or only at `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt` on pod? Phase 1 smoke needs a local copy. (~664 MB.)

**From Agent C (Mode 7):**

3. Path A vs Path B for Drive/Register marginals: Path A = build dedicated aux heads; Path B = derive from per-position slot-type decisions. Agent C recommended Path B for v1 (cheaper, reuses existing slot_type_head). Audit OK or push Path A?
4. Should the one-line trace marker surface the swap-pair `cross_emission` verdict inline? Agent C recommended yes (it's the Stage 3 hard safety gate). Audit OK?

**From Agent A (wrap-up, talking points worth confirming):**

5. Is the "dev → held-out asymmetry" framing (copy-pointer generalizes; keep-copying-while-generating is dev-tuned) accurate per your read of the eval data? Or is it overinterpreting two paired numbers?
6. Should the wrap-up doc explicitly call out the "no further training" decision as a hard lock, or leave the door open contingent on integration findings (e.g., if Mode 7 surfaces a specific generalization failure mode, then targeted training)?
7. The wrap-up's "Limitations and open questions" section enumerates the residual technical debt. Does it match your audit-time view of where the model is weakest, or are there other failure modes you want surfaced before integration starts?

### What is NOT done

- NO code changes. NO pod work. NO new `decisions.md` entries beyond the planning-phase authorization at 2026-05-13T06:30Z (commit `7d5cec9`).
- NO start on chat REPL implementation (Phase 1 of plan B). Waiting for your audit of plans B + C + answer to the 7 open questions, then user "go" on which phase to execute first.

---

## 2026-05-13T07:15Z — claude: Stage 3 ckpt_final.pt archived locally — first-priority backup done

Per your first-priority directive ("Yes. First priority. Before building REPL, Mode 7, or anything else, preserve the good checkpoint locally. Without that checkpoint, all the integration work has nothing reliable to load.") and user chat "Go!!" 2026-05-13T07:05Z: backup landed.

### Commit

`7c72a48` — Stage 3 ckpt_final.pt archived locally + registry doc.

### What ran

scp pod → local archive on 5 files:

| File | Size | sha256 (pod ↔ local match) |
|---|---:|---|
| `ckpt_final.pt` | 664,482,404 B | `5ac364e78419ec8591d25120ce9314f87d2c816467fcf9875802d3d831903a88` |
| `ckpt_final.pt.manifest.json` | 2,652 B | `28c13127e919097ee3337eab13bcb929c6b104ee5afecd6f7af64e80d05a9dd6` |
| `trainer_manifest.json` | 2,045 B | `346223ff286b2c245ec29ba61f62b88c16acdb57a0863cd67ca8110bb7fcc849` |
| `trainer_log.jsonl` | 63,542 B | `5be168ad9c24c8dfe27f1fa394dd0800633e0a03ba9221f73c86073d5798e196` |
| `smoke_report.json` | 61,185 B | `83893bc5810f9eb386afa2dc6c44daa37fb88286074381fbd88df0b3533680e2` |

**Bit-for-bit verified.** Independent `sha256sum` on pod and local; all 5 hashes match.

### Local archive

- Path: `D:\tksCAS-archive\stage_e3_20260513T043823Z\`
- Convention: matches existing `D:\tksCAS-archive\v0_rc1\` + `v1e_phase_c\` archive structure.
- NOT committed to git (664 MB binary).

### Registry doc (committed)

`docs/working/candidate_e/checkpoint_archive_registry.md` records: archive path, all sha256 hashes, pod source path, training config verbatim from manifest, loss weights, warm-start lineage chain (b2 → e2a → e2b → e2c → E2c-cont → Stage 3), required runtime artifacts (tokenizer.json + english_bpe.json with their hashes), what the model can / cannot do, dev → held-out asymmetry notes.

This doc is the canonical pointer for anyone trying to find the trained checkpoint locally; verification is a single `sha256sum` command.

### Pod side

The pod copy at `/workspace/tksCAS/stage_e3_20260513T043823Z/` is UNTOUCHED. We have two copies now: one on pod, one locally. If the pod is wiped, the local archive can be re-uploaded; bit-identical guarantee holds.

### What is NOT done

- NO change to Stage 3 training. NO new training runs. NO inference. NO chat REPL code.
- Still pending your audit of the three planning docs (commits `3ef997e`, `53687ba`, `ef474d3`) and the 7 open questions surfaced at 2026-05-13T07:00Z inbox entry. After your audit, user "go" on which integration phase to execute first.

---
