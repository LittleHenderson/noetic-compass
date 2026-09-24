# Owner direction, 2026-09-24 (verbatim), and how it is applied

## The owner's words, exactly

Typed:

> YOU HAVE THE GO AHEAD ON BOTH OF THE FOLLOWING:    ⬜ Not started, on purpose: training the repaired Helm, the next Q4 run, and the late-reach experiment. Each needs its own go-ahead and stays separate.

Pasted with it:

> Here is my chosen direction.
>
> 1. TEST SET
> Build the improved test as a new version beside the historical test.
> Use five- and six-part problems within the accepted checker’s scope,
> with six-part problems as the main next difficulty level.
>
> Do not add seven-part cases until the checker and actual learner path
> support them through a separately tested change.
>
> Bigger is not enough. Include different wiring with the same simple
> counts, genuine no-match/no-path cases, and structures withheld from
> teaching and candidate-bank exposure. Fix the success rules before tuning.
>
> 2. RESCORER
> Use an explicit historical-compatibility mode for the recognized old
> grading-description mistake only.
>
> Require verified original evidence and apply the preserved historical
> rule. Show the warning and both rule descriptions. Never rewrite the
> original record.
>
> Reject unknown, altered, incomplete, or incompatible evidence for trusted
> acceptance. New runs do not receive the historical exception.
>
> 3. SECRET TEST COPIES
> Keep the protected copies for now. Inventory them without exposing the
> answers to the builder. Identify the authoritative archive and verify
> its backup and access restrictions.
>
> Prepare a specific cleanup proposal for unnecessary duplicates.
> Do not delete any copies under this instruction.
>
> 4. REPAIRED HELM TRAINING
> Select a controlled repaired-versus-unchanged training comparison as
> the next model experiment, after the OFF preservation check, enabled-path
> checks, larger-question integration, and evaluation preparation pass.
>
> Prepare the exact AWS job plan with source, data, starting weights,
> runs, update/time/dollar limits, stopping conditions, and cleanup.
> Bring that named plan to me for launch approval.
>
> Do not combine this with Q4, extra architecture changes, or automatic
> retries. Continue preparation and ordinary checks already covered by
> current permissions.

## How it is applied

The newest, most specific words govern where they refine an earlier decision.

| # | Direction | Applied as | Replaces |
|---|---|---|---|
| 1 | Test set | **HSET-2**: a new version beside HSET-1A (which is kept unchanged). It has 5- and 6-node problems, with 6 nodes as the main level, all within checker v2's accepted scope (`7f85af1e`). It has **no 7-node cells.** It adds degree-matched different wirings, real no-match and no-path answers, and shapes withheld from teaching and from candidate-bank exposure. The success rules are frozen in evaluation design v0.3 before any model is read or tuned | The 6/7-node HSET-1B design (`b5a4d525`, `5773b7ad`). It was never built or launched. Its committed salt was never used; whether it is reused is decided and recorded in the v0.3 design before any build |
| 2 | Rescorer | **Compatibility mode.** Only the recognised mistake is accepted: the 0.2 anchors' recorded "zero-loss veto" description. The anchor must be verified original evidence (hashes match). Scoring then applies the preserved historical rule, and prints a warning and both rule descriptions. The original records are never rewritten. Any unknown, altered, incomplete or incompatible evidence is refused for trusted acceptance. New runs never get the exception. Builder task, then a fresh review | The "fail-closed, refuse all wrong-rule anchors" reading of 2026-09-23 |
| 3 | Protected copies | The coordinator makes an inventory by name, size and sha256 only, with no answer content, and never hands it to a builder. It names the authoritative archive and checks its backup and access limits. It writes a specific cleanup proposal. **Nothing is deleted** | — |
| 4 | Repaired-Helm training | **The next model experiment is a controlled repaired-versus-unchanged training comparison.** A named AWS job plan is brought to the owner for launch approval. Before that, these must pass: OFF preservation (**passed**: `OFF_PRESERVED_ON_T4`, `41071a3f`), the enabled-path checks, the larger-question integration, and the evaluation preparation. It is not combined with Q4, with extra architecture changes, or with automatic retries | The 2026-09-23 plan to launch 3 switch-ON seeds straight after the test run. The $60 approval still bounds the test run, which is an enabled-path check. **No seed job is launched without the owner's approval of the named plan** |
| — | The next Q4 run | Q4-SDG-1 error-panel diagnostic launched 2026-09-24: `i-0bb026161de743f23`, $1.00 ceiling. Any Q4 training (A versus B) still needs a stated dollar ceiling before launch | — |
| — | Late-reach experiment | Go-ahead noted. **Correction (same day): its scope IS on disk.** It is `HELM-REACH-LATE-1`, `records/helm_eval_design_20260923/EVALUATION_DESIGN_v0_2.md` section 3.1: one named reach query; the final checkpoint `course_p10`; a 0.003 control branch from the saved pass-1 checkpoint that must reproduce `VIA /n1` in all 4 presentations, with `VIA_N1`/`VIA_N3` within 1e-3 of 26.474693298339844 and 22.808488845825195; stop if the control does not reproduce. The first version of this row said no scope existed; that was wrong. The owner named item 4 as the next model experiment, so late-reach needs its own job manifest, limits and one runner before any launch. It stays separate and is not run now | — |
