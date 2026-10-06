# HELM neural learning — plan v1 for stages 1–2 (DRAFT, NOT FROZEN)

**Serves:** `docs/directives/2026_10_06_helm_neural_learning.md` stages 1 and 2; `docs/HELM_VISION_AND_ROADMAP.md` ability 2 and 3 (neural form), roadmap step 8. Decision package: `docs/working/helm_neural_learning_decision_package_2026_10_06.md`.
**Status:** draft for the owner's freeze. It changes nothing in the official R8B plan, criteria or results. It becomes "v1 frozen" only when the owner records the freeze with the R8B verdict known and before any outcome of a run under it is inspected. Nothing here authorizes a run, spending, push or merge.
**Version rule:** any change after freeze is v2 and is recorded before the affected test.

## 0. What this plan is for

The directive's first question is: what did HELM learn, did it keep it after restarting, and can it use it when the example changes? Stages 1–2 answer the first two parts for one taught target. This plan fixes, before any run, what is compared, what counts as exact, what the control is, and what is recorded — so the answer cannot be shaped by the answer.

## 1. Preconditions (gates; all owned outside this session)

| gate | owner | state at drafting |
|---|---|---|
| G1 R8B verdict and custody: shipped-source freeze, owner record, controller receipt, closeout, acceptance seal, endpoint manifest, endpoint locators retrieved and compared with package B | operator; owner of record | missing at the source cut → UNKNOWN |
| G2 AWS access path for the authorized operator (`ProfileNotFound`, `InvalidAccessKeyId` resolved) | operator; owner | blocked at the source cut |
| G3 ledger reconciliation and one job approval within the $250 ceiling | owner | provisional $97.59, billing pending; no job approved |
| G4 exact-source binding for the launch (the 0/32 old-hash issue resolved) | operator | open |

No part of §3 runs until G1–G4 are recorded in the launch record. If G1 yields a verdict other than EPISODE_CLEAN_QUALIFICATION_REQUIRED, §3 does not apply and §4 (R9-mini) is the only route, under its own freeze.

## 2. Objects, identities, and what "exact" means

**Root state.** The pinned native root model and state digests (roadmap §7.2) and the inherited checkpoint `5a8a3069…` (4,025,999 bytes). Every arm starts from a private copy of the original state; the accepted learned checkpoint is NOT established by these inputs.

**Continuation bundle** (roadmap §7.3; the unit that "restart" is defined over). A resumable episode is the set of all of these, each with a SHA-256 in the bundle manifest:

1. model state (the state_dict checkpoint; weights only);
2. bound configuration, topology, decoder and semantic lineage identities;
3. original constraint rows and controls; original parameter reference;
4. accepted/refused-step cursor; cumulative, rounding and nominal path totals;
5. teaching admission and schema identities (the three admitted matrices);
6. optimizer state, schedule state and RNG state **when used**, or an explicit declaration that each is absent and why;
7. the frozen plan version, source revision and hashes, seed, operator record and applicable approval.

A bundle missing any member without a declaration is INCOMPLETE and the comparison does not run.

**Exact.** Two bundles are exact-equal when every member's bytes are identical (SHA-256 equal). Two inferences are exact-equal when the logits for all 128 TRAIN cases are bit-identical under the declared deterministic settings (fixed seeds, single thread, deterministic kernels, same precision, same device class). If the runtime cannot be made deterministic, a numeric tolerance is declared here before the run, the match is reported as "within tolerance τ", and the word exact is not used. **Tolerance declaration for v1:** none; exactness is required. (Changing this is a v2 amendment, recorded before the test.)

**Retrieval disabled.** During every scored prediction in stages 1–2 no memorized-answer lookup, answer-bearing retrieval, LLM teacher or symbolic helper is active. The symbolic organism in `scripts/cas_rpu` is not connected and is never part of this result.

## 3. Procedure (PLAN_AFTER_R8B step (a), unchanged; the directive's stage 1–2 requirements added as recording and controls, not as new criteria)

**Part 1 — full replay.** Replay arm M from ORIGINAL in a fresh process on the pinned machine type and compare all 129 states with the retained R8B record: state digest, observation, all 128 TRAIN rows and every update's path fields, then the final endpoint bytes against the retained receipt/endpoint. Any difference is INVALID: parts 2 and 3 do not run. (Reproducibility; not learning.)

**Part 2 — stop, save, fresh-process continuation.** At owner-fixed cuts (32 / 64 / 102 are the plan's examples, not decisions), stop, save the continuation bundle, end the process, start a genuinely fresh process, load the bundle, continue to 128, and compare every later digest, row and the final endpoint bytes with the uninterrupted reference. An independent forward-only loader re-predicts the 128 TRAIN cases from the final bundle. Any divergence fails part 2 and blocks part 3.

**Stage 1 recording (directive).** For the arm-M episode, record per TRAIN case: before/after prediction, correctness, loss; per anchor: correctness and margin before/after; the set of parameters that changed (which of the three admitted matrices, and the norm of each change); any case that got worse ("damage elsewhere"). The report lists both.

**Stage 2 control (directive) — discarded-update arm.** From the same pre-teaching bundle, restore in a fresh process with every mutable learning member reset to its pre-teaching value (model state, optimizer/schedule/RNG if present, cursor, path totals, caches) and re-predict the 128 cases. The retained-update and discarded-update predictions must differ only where the taught update changed them; the discarded arm must lack the correction. This arm adds no training and therefore no cost beyond one inference pass.

**Part 3 — qualification** stays as PLAN_AFTER_R8B §5 defines it (exposed 32-case panel; four unchanged conditions; a refusal is final; a clean check stays private). It can detect regression; it cannot certify novelty. Not a stage-3 result.

## 4. Fallback: R9-mini (only if G1 yields no eligible verdict; separately frozen as its own plan)

Same root state, same matched128 driver, guards and admission, one owner-selected wrong TRAIN target, three arms (M, discarded-update control, sham), 128-step allowance, fresh-process reload with exact-equal bundle and exact-equal 128-case inference. It answers stages 1–2 on a new episode and does not touch the R8B record. Needs: its own versioned plan, a job approval, the same gates.

## 5. Pass criteria (frozen here for stages 1–2; the R8B criteria themselves are untouched)

- Part 1: INVALID on any difference. Part 2: fail on any divergence; the continuation bundle must be COMPLETE.
- Stage 1: the taught target correct at the retained endpoint; all 18 protected anchors correct with positive margin and per-anchor cross-entropy within the R8B bound; damage elsewhere reported, never hidden.
- Stage 2: fresh-process bundle exact-equal; 128-case inference exact-equal; discarded-update arm lacks the correction.
- Denominators: 128 TRAIN cases; 18 anchors; the number of cuts fixed by the owner.
- Any failure is reported as the branch PLAN_AFTER_R8B names (INVALID, FAILURE, CREDIT_TO_BASELINE, EPISODE_CLEAN_NOT_TARGET_SPECIFIC) with no rescue run. A zero is a zero.

## 6. Record (every launch)

Bound to: exact source revision and hashes; this plan's frozen version; checkpoint identity; seed; operator record; approval reference; machine type; actual runtime and cost. Saved: per-item before/after, aggregate accuracy and loss, restart evidence (bundle manifests before and after, loader output), failures, discrepancies with explanation. The bundle manifests are checked with `scripts/helm_neural/bundle_check.py` (stdlib; byte-level), which is preparation tooling, not evidence of learning.

## 7. Roles and models

Claude (this session; configured `claude-fable-5-1`, serving model may differ, reasoning setting not exposed): this plan, the record template, the bundle checker, the report. Operator: launch through the receipt-pinned controller path. Owner: gates, freeze, approvals. Independent evaluator: not needed for stages 1–2; required before stage 3.

## 8. What stages 1–2 will not show

Transfer to unseen examples; a second skill without loss; advantage over ordinary teaching; growth; cooperation; anything about the symbolic organism. Those are stages 3–5 with their own frozen plans and a custodian-held panel.

## Amendment log

| date | change | reason | by |
|---|---|---|---|
| 2026-10-06 | v1 draft written; not frozen | directive: "record the amendment before the affected test" | Claude |
