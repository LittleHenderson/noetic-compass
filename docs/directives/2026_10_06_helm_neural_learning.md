# HELM directive — neural learning: a small useful skill that improves through teaching, survives a full restart, and works on new examples

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` §1 abilities 2 (learns), 3 (retains), 5 (CASalesces, later); roadmap step 8 and the neural-growth outcome type of §2. The destination is stated only there; this directive does not restate it.
**Status:** proposed wording from the owner, received 2026-10-06 (`HELM_Suggested_Neural_Learning_Directive.docx`), stored verbatim in substance below; the active writer's gate answer, amendments and decision package follow in the amendment log and in `docs/working/helm_neural_learning_decision_package_2026_10_06.md`.
**Authority:** this directive grants no run, spending, push or merge authority beyond what the owner has separately approved. The earlier $1 approval was for a specific job after ledger reconciliation and is not general approval. Permission to amend the approach does not create new authority.

## Gate answer (vision §3), written before any work

Ability 2, with 3 as the restart condition. Before: the native model at the pinned root checkpoint answers a specific TRAIN target wrongly (R8 at 64 steps: 18/128 correct, target wrong). After: after the frozen teaching procedure, the target is correct at the retained endpoint, the 18 protected anchors remain correct, and the correction is present after a genuinely fresh process restores the saved checkpoint, with weights byte-identical and inference on the 128 TRAIN cases identical; a discarded-update control, restored from the same pre-teaching state with all mutable learning state reset, lacks the correction. Criterion: frozen in the existing R8B plan and its step (a) (unchanged); denominator 128 TRAIN cases and 18 anchors; later stages (unseen transfer, second skill, ordinary-teaching baseline) each get their own frozen criteria and a fresh custodian-held panel before they are scored. What it will not show: transfer beyond the taught example (stage 3), general learning, growth, or cooperation; symbolic lessons in `scripts/cas_rpu` are kept distinct and are not this result.

## The owner's directive (proposed wording, 2026-10-06)

### Make neural learning the next priority

I want HELM's next milestone to be a small, useful skill that improves through teaching, survives a full restart, and works on new examples. Start with the existing HELM learner and R8B work. My immediate goal is something I can use and show to peers: teach a specific skill, restart HELM, then watch it handle a new example.

Keep the larger vision of neural learning, retention, useful growth and cooperation in view. For this phase, concentrate on a credible demonstration of that learning loop. Work on infrastructure only where it removes a concrete obstacle to the demonstration.

### You may amend the approach before testing

Use your engineering judgment. If a different sequence, method or measurement would give a clearer answer with less cost or effort, record your amendment before the affected test. State what you would change, why, what evidence it will produce, and the effect on cost, timing and interpretation. You may make engineering amendments within existing authority. Bring decisions that need my approval to me before acting.

Keep the existing official R8B plan, criteria and results intact. Any changed claim, threshold, method or test panel belongs in a new, clearly versioned plan recorded before its outcomes are inspected. Do not make a failed result pass by changing its criteria afterward. Permission to amend this proposal does not create new run, spending, push or merge authority.

### Check the current position first

Inventory the latest source, checkpoints, run records, approvals and results before building or repeating anything. If the work has advanced, use the newer verified evidence and identify what it supersedes. Continue the existing HELM_VISION_AND_ROADMAP.md and the memory directive work associated with PR 248; avoid creating another competing roadmap.

Preserve these distinctions when checking the record:

- Official R8 at 64 steps missed its correction target. Accuracy improved from 18/128 to 21/128, all original 18 correct answers remained correct, and reported loss fell from 36.18 to 9.92. Those are partial results, not an official pass.
- The exploratory continuation first corrected the target at step 102 and reached 22/128 while keeping the original 18. It was outside the official window. At step 64, loss worsened on 59/110 unprotected items; that does not mean 59 correct answers were lost. A control also improved on the target, so causal claims need comparison.
- The 128-step R8B plan cleared an independent review on October 5 at 3:04 p.m. PDT, with 54 logic checks. That is preparation. No verified R8B run is established in this draft's starting record.

### Prove the learning loop in stages

Choose the smallest task that can expose a genuine change in learned behavior. A task with an unseen rule or hidden parameter may be enough if it is cheap to teach and cannot be passed by looking up memorized answers. Keep the stages connected so each answers a specific question.

1. **Show a neural correction.** Show the original model's behavior, the teaching it receives, and the changed behavior afterward. Identify the learned weights or other neural parameters that changed. Keep a saved fact, retrieved note or symbolic correction separate from a neural-learning claim. Record both useful changes and damage elsewhere.
2. **Keep the skill after a fresh start.** End the process and start a genuinely fresh one from the saved checkpoint. Verify the weights and, where relevant to resuming learning, optimizer state, counters and random-number state. Check exact inference behavior under the declared reproducible conditions. If numerical nondeterminism requires tolerances, define them beforehand and do not call a tolerance-based match exact.
3. **Use it on unseen examples.** Evaluate examples held by an independent evaluator and unavailable during training or model selection. Show whether the learned skill transfers beyond the correction example. During scored answers, no LLM teacher, memorized-answer lookup, answer-bearing retrieval or symbolic helper may supply the solution. Ordinary task tools must be disclosed and matched across comparison arms.
4. **Learn something else without losing the first skill.** Teach a separate skill, restart again where relevant, then measure both the new learning and retention of the earlier skill. Examine protected and unprotected behavior. Retaining 18 protected answers supports that narrow claim; it does not establish general retention.
5. **Compare with ordinary teaching.** Compare HELM's proposed learning method with a straightforward teaching or fine-tuning baseline under fair conditions. Establish whether the added mechanism improves useful learning, retention, cost or another predeclared goal. If the ordinary baseline performs equally well, report that plainly and make no claim of CAS superiority.

### Set the standard before seeing the answer

Keep the existing official R8B pass criteria unchanged. For later experiments, propose the sample sizes, thresholds, failure conditions, permitted degradation and stopping rule before opening the final evaluation. Explain why the tradeoff would be useful to me. Earlier suggested panel sizes or thresholds are proposals unless separately approved or adopted under existing authority.

A partial win is worth reporting when its limits are clear. A negative result is also useful if it rules out an explanation or points to a smaller, better test. Passing code checks or completing an error-free run establishes preparation, not demonstrated learning.

### Make the evidence trustworthy

**Keep training and final evaluation separate.** Use separate training, selection and final-test data. Freeze the chosen model and plan before the final test, and score that held-out test once for the declared decision. Do not use qualification answers to choose examples, checkpoints, hyperparameters or methods. Once final answers have informed a change, use a new independently held panel for the new claim. Any necessary rerun must be identified and justified.

**Match the comparisons.** Use the same starting checkpoint, paired seeds, relevant parameters, precision, tasks, permitted tools and resource budget across arms except for the declared experimental difference. Report unavoidable differences. Preserve the frozen R8B matched arms, reproduction and sham requirements; add later controls only when they resolve an important uncertainty at bounded cost.

Include a discarded-update control when testing whether a persisted neural update caused the improvement. Restore all mutable learning state, not just weights, so the comparison cannot be explained by leftover optimizer state, counters, random state or caches. The retained-update and discarded-update cases should differ only in the update being tested.

**Keep an inspectable record.** Bind each launch to its exact source revision and hashes, frozen plan version, checkpoint, seed, operator record and applicable approval. Save per-item before-and-after results, aggregate accuracy and loss, restart evidence, failures, actual runtime and cost. Explain any discrepancy instead of silently replacing a record.

The earlier source-to-operator record gap, including the 0/32 old-hash binding issue, must be resolved before relying on the affected launch as exact-source evidence. The earlier $1 approval was for a specific job after ledger reconciliation; it is not general approval for new experiments.

### Use the existing operating limits

Keep computation within the existing AWS-only constraint. Do not substitute local CPU or GPU testing. Use the authorized operator and approved access path. The starting record shows ProfileNotFound for the operator's normal AWS profile and InvalidAccessKeyId on Claude's side; verify whether those blockers still apply.

If access remains blocked, name the exact missing step and its owner. Do not request keys in chat, bypass access controls or create credentials under this directive. Continue useful review and planning that does not depend on the blocked run.

Before spending, reconcile actual charges and the current ledger with the applicable written project ceiling and job-specific limits. The last $97.59 figure was provisional, with actual billing still pending. Do not treat it as verified remaining headroom. Seek the required approval for a new or changed job, higher cost or expanded scope.

### Keep growth experiments purposeful

Adding neurons or other capacity is a later option if a specific capacity limit explains an observed failure. State the hypothesis, expected benefit, comparison and cost first. Do not let growth machinery or repeated auxiliary checks become an open-ended prerequisite for testing learning. RPA remains optional unless new evidence justifies its overhead.

### Keep one clear work tree

Use this as the proposed sequence and update it from the actual inventory. Labels below describe the plan, not a claim that any new work has started.

| label | item |
|---|---|
| HELM goal | Useful learning that persists and transfers |
| Current | Inventory the existing learner and R8B evidence |
| Waiting | Exact-source binding, access, ledger and launch gates |
| Next | Complete or assess the existing frozen R8B comparison |
| Then | Neural correction and fresh-process retention |
| Then | Unseen transfer and retention after other learning |
| Then | Fair comparison with ordinary teaching |
| Alternative | Smaller task or simpler teaching method |
| Later | Capacity growth if a specific failure supports it |
| Support | Existing memory work, used only where helpful |
| Parked | Optional RPA work and new project branches |

Existing CAS/RPU symbolic fresh-process retention work used 20 development seeds and five sessions on one host. PR 248 advanced to 159c1fad on October 6 at 9:02 a.m. PDT with explicit, retractable TOLD rules for new relations and tokens. That source change is not verified execution, induced learning or a weight change. Keep symbolic retention distinct from the neural result requested here.

### Assign roles and record the actual models

Suggested division: Claude owns the inventory, proposed amendments and implementation; the existing authorized operator owns approved launches; an independent evaluator owns held-out answers, scoring and review. Keep evaluator custody separate from model selection. A named external model or reviewer is only a proposed participant until its assignment and access are confirmed.

For each active role, record the project, task, actual provider and model identifier, reasoning or intelligence setting when exposed, and status. If the runtime does not expose a setting, write "not exposed." Do not infer a model or effort level from a display name or historical metadata.

### Give me a realistic start and finish window

For planning only, allow roughly half to one working day for inventory and an amended plan, then roughly one to three working days for one bounded experiment and review after access, evidence and spending gates are clear. Replace these estimates with timings grounded in the actual work. Give calendar start and finish windows in Pacific local time, using the correct PDT or PST label for each date.

The earlier two-to-four-week discussion is a rough horizon for a usable learning loop, not a deadline or a promise. If a result fails, explain the smallest useful next test and its time and cost before widening the work.

### Return a short decision package first

Send me the latest verified position, your amendments and reasons, the smallest next claim and test, who owns each step, estimated start and finish times, and any approval needed. Then report demonstrated learning, retention, transfer and harms with the evidence that supports each claim. Keep preparation and unresolved questions clearly labeled.

The question I want answered is simple: what did HELM learn, did it keep it after restarting, and can it use it when the example changes?

## Amendment log

| date | change | reason | by |
|---|---|---|---|
| 2026-10-06 | Directive received and stored; gate answer written; decision package delivered as `docs/working/helm_neural_learning_decision_package_2026_10_06.md`; roadmap §6 row added; the Codex-prepared consolidated source handoff applied to the roadmap as §7 with the active writer's verification notes. | owner's instruction "check the current position first" and "return a short decision package first" | Claude (active writer) |
| 2026-10-06 | **Amendment A1 (engineering, within authority):** the inventory step uses the Codex-prepared consolidated source handoff (roadmap §7, read-only, byte-hashed) as its baseline instead of a second inventory, because the native learner, checkpoints, receipts and results live on the owner's machine and in the operator's records, which this cloud session cannot read. What this session verified itself is limited to the repository. | avoids duplicate work; states the reach of this session honestly | Claude |
| 2026-10-06 | **Amendment A2 (engineering, within authority):** stages 1 and 2 are taken together as the smallest next claim, and they are executed as PLAN_AFTER_R8B step (a) parts 1–2 on the existing R8B arm M endpoint, not as a new task — conditional on the actual R8B verdict being EPISODE_CLEAN_QUALIFICATION_REQUIRED. If the R8B verdict or custody is UNKNOWN, the smallest next step is resolving custody (operator), not a run. A separately versioned minimal experiment ("R9-mini", one target, discarded-update control, fresh-process reload) is the fallback and needs a new job approval. | the directive's own order ("complete or assess the existing frozen R8B comparison" before "neural correction and fresh-process retention"); no rescue run | Claude |
| 2026-10-06 | **Amendment A3:** the symbolic lesson work (PR #248 contract §13) is classed as *Support* in the work tree and is never reported under neural learning; its reports carry "neural change: none" as a measured zero. RPA stays parked. | the directive's separation of symbolic correction from neural claims | Claude |
