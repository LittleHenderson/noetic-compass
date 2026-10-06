# Neural learning — decision package (2026-10-06)

**For:** Little Henderson. **From:** the active PR #248 writer (this Claude session). **Answers:** `docs/directives/2026_10_06_helm_neural_learning.md` ("return a short decision package first"). **Points at:** `docs/HELM_VISION_AND_ROADMAP.md` (§4 ability 2 and 5, §7 consolidated handoff).

Everything below is labelled verified (checked in this repository by this session), reported (stated by the source analysis in roadmap §7 or by the directive; not reachable from here), or preparation.

## 1. Latest position

**Verified in this repository.**
- Symbolic retention at survival level (a): first-look run on 20 unseen seeds, 1200 process launches, zero disagreements with recompute, zero stale record hits; fault schedule exact (`docs/working/helm_multi_session_evaluation_2026_10_06.md`).
- Symbolic lessons (contract §13): a told, retractable rule applied to unfamiliar instances across fresh processes, untaught twins GAP; development tests and a 10-seed fault run complete; the first-look run on 20 unseen seeds was in progress when this package was written and is reported in `docs/working/helm_lessons_evaluation_2026_10_06.md` on completion. **Neural change: none.**
- Nothing neural exists in this repository beyond `cas-native/` training infrastructure, which is not the HELM learner.

**Reported, not reachable from this session (roadmap §7).**
- Root checkpoint identity (4,025,999 bytes, SHA-256 `5a8a3069…`), three inherited operation matrices, pinned native root model and state digests.
- R7: obstacle measured, no protected learning. R8 (64 steps): official FAILURE, target wrong, 18 anchors kept, 21/128. R8 report-only continuation: target correct at step 102, 22/128, outside the window, with a control that also improved. R8B (128 steps, arms S / X5 / M / Bg / Cg / B4): **outcome custody missing** — no closeout, acceptance seal, endpoint manifest or receipt was found at the source cut; the controller directories named in the plan were absent. Missing means UNKNOWN.
- Access: operator profile `ProfileNotFound`; Claude-side `InvalidAccessKeyId`; both recorded before any AWS request. Ledger: $97.59 provisional against the $250 ceiling, billing pending; the $1 approvals were job-specific.

**What this session cannot do.** The learner, checkpoints, receipts and results live on your machine and in the operator's records. From this cloud container I can read only what is attached or in the repository. I cannot run the native code, verify a checkpoint byte, or confirm the R8B outcome.

## 2. Amendments (engineering, within existing authority; recorded before any test)

- **A1 — Inventory by reuse.** Adopt the Codex-prepared handoff (roadmap §7) as the inventory baseline rather than repeat it. Effect: saves the half-to-one day the directive budgets; the residual inventory is one question to the operator (A2). Cost: none. Interpretation: the handoff's external claims stay "reported".
- **A2 — Stages 1 and 2 together, on the existing R8B arm M, as PLAN_AFTER_R8B step (a).** A neural correction that survives a fresh process is the smallest claim that is also the directive's stage 2; the existing plan already freezes it (part 1 full replay of M from ORIGINAL comparing all 129 states; part 2 stop/save/continue at owner-fixed cuts; forward-only loader re-predicts 128 TRAIN cases). Condition: the actual R8B verdict must be EPISODE_CLEAN_QUALIFICATION_REQUIRED. Any other verdict, or UNKNOWN custody, means step (a) does not run. Effect: no new task, no new criteria, no rescue run. Cost: one AWS job in the historical envelope (m6i.xlarge, one attempt, $1 cap), which is not covered by any existing approval.
- **A3 — Fallback, only if custody cannot be resolved: "R9-mini", separately versioned.** Same root checkpoint, same matched128 driver and guards, one wrong TRAIN target, three arms (M, discarded-update control restored from the same pre-teaching state with optimizer/counter/RNG reset, sham), fresh-process reload with byte-equal weights and identical 128-case inference, frozen before launch. It answers stages 1–2 on a new episode without touching the R8B record. Cost: one job, same envelope, needs a new job approval and a versioned plan.
- **A4 — Symbolic work is Support.** The lesson family is finished as a symbolic result and is not extended for this milestone; RPA stays parked.

## 3. Smallest next claim and test

**Claim:** "After the frozen teaching procedure, the taught TRAIN target is correct at the retained arm-M endpoint, the 18 protected anchors remain correct, and the correction is present after a genuinely fresh process restores the saved checkpoint with byte-identical weights and identical inference on all 128 TRAIN cases; the discarded-update control lacks it."

**Test:** PLAN_AFTER_R8B step (a) parts 1–2 (A2) or R9-mini (A3). Denominator: 128 TRAIN cases, 18 anchors. Pass criteria: the existing plan's, unchanged. Exactness: byte equality of weights and identical logits under the declared deterministic settings; if the runtime cannot be made deterministic, the tolerance is declared before the run and the match is reported as tolerance-based, never as exact.

**What it will not show:** transfer to unseen examples (stage 3), learning a second skill without loss (stage 4), advantage over ordinary teaching (stage 5), growth, cooperation.

## 4. Owners

| step | owner | status |
|---|---|---|
| Retrieve the latest R8B shipped-source freeze, owner record, controller receipt, closeout, seal, endpoint manifest and locators; name the verdict | authorized operator (and you, as owner of record) | **waiting** |
| Restore the operator's AWS access path; confirm whether `ProfileNotFound` / `InvalidAccessKeyId` still apply | operator / you | **waiting**; no key in chat |
| Reconcile actual charges with the ledger and ceiling; approve one job | you | **waiting** |
| Decide A2 vs A3 once the verdict is known; freeze the plan version | you (decision), Claude (drafting) | ready to draft on your word |
| Write the step (a) comparison script and the continuation-bundle checklist against the B package | Claude, **only with the B package attached or a session on your machine** | blocked on access to B |
| Launch, receipts, raw artifacts | operator, through the receipt-pinned controller path | after gates |
| Held-out panel for stage 3, custody, scoring | independent evaluator (to be named) | not started |
| Report learning, retention, transfer, harms | Claude | after the run |

Models in use for this package: this session reports `claude-fable-5-1` as configured; the serving model may differ and the reasoning setting is not exposed. The Codex analysis reports GPT-6-based Codex, variant and effort not exposed.

## 5. Start and finish windows (Pacific, PDT in October)

- **Inventory and amended plan:** done in substance with this package on Mon 2026-10-06 PDT (A1); the remaining inventory item is the R8B custody answer, which is the operator's.
- **Bounded experiment and review (stages 1–2):** earliest start the first working day after all three gates clear (custody verdict, access, job approval). If they clear on Tue 2026-10-07 PDT: run Wed 2026-10-08 PDT, review and report by Fri 2026-10-10 PDT. If the verdict forces A3, add one day for the versioned plan: run Thu 2026-10-09, report by Mon 2026-10-13 PDT.
- **Stages 3–5:** not scheduled; each needs its own frozen plan and a custodian first. The two-to-four-week horizon for a usable loop is plausible only if stage 2 passes and a custodian is named this week.

## 6. Approvals needed from you

1. The R8B custody answer, or your instruction to the operator to produce it.
2. One AWS job approval for step (a) or R9-mini, within the ceiling, after ledger reconciliation.
3. Confirmation of A2 (run step (a) on the existing arm M) or A3 (R9-mini), once the verdict is known.
4. A named independent evaluator for stage 3 and beyond (not needed for stages 1–2).
5. Access for me to the B package (attach it, or run a session on the machine that holds it) if you want me to write the comparison script rather than only the plan.

Nothing in this package starts a run, spends, or publishes.
