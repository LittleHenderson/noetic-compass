# Lineage scheme — the owner's clarifications, recorded beside the proposal

**Date:** 2026-09-21. **Source:** `FABLE_Q0_Followup_Draft_20260921.md`, the owner-side response to
the first return, §2 (Q0 status), §3 (lineage), §4 (what the results mean), §6 (push evidence).
**Status of this file:** a RECORD of the clarifications as delivered. The draft's own header says it is
a recommendation for the owner to adopt; it is not a signed ratification. The versioning extension in
`BRAIN_LINEAGE.md` therefore stays marked *proposed* until the owner's own word arrives. Nothing below
changes a verdict row.

Kept as a separate file, pointed to from `BRAIN_LINEAGE.md`, so that the lineage file itself is not
edited on two branches at once (the Helm 2.0 engineer's branch and this lab branch).

---

## 1. Q0 status — corrected

The first return reported Q0 "closed". The draft is right that this overstated it. The directive's Q0
exit needs three things the first return explicitly listed as still open:

- a trusted scorer identity, rubric and target-set identity anchored **outside** the run directory;
- adversarial tamper tests (altered scores; altered scores plus a rewritten run manifest; evaluator
  substitution; wrong split; duplicate ids; missing/extra predictions; malformed/non-finite values);
- **independent rescoring of the raw predictions**, not trust in run-supplied totals.

**Status now:** `Q0_DISCOVERY_COMPLETE / Q0_EVALUATOR_BOUNDARY_OPEN`. The engineering PASS in the
first return is a *reported* status, not independent release acceptance. `verify_evidence_hashes.py`'s
PASS establishes byte agreement with what the run recorded; it is not a trusted evaluator. Package task
`T01` (owner F5) is the open item; because no independent custodian exists in this environment, any
evaluator built by this session carries `EVALUATION_NOT_INDEPENDENT` until a genuinely separate
session holds the final split.

## 2. The lifecycle, with the conditions the draft attaches

The proposal in `BRAIN_LINEAGE.md` — **X.0-experimental → X.0-rc → X.0** — is kept, with these
clarifications, each of which tightens it:

| stage | clarification |
|---|---|
| **experimental** | An architectural change receives its experimental identity **when it exists**, even if its engineering check later fails. The check is recorded separately. A changed model is never left unidentified because a PASS is absent. A branch name does not establish a Helm 3.0 implementation; the standalone lab has its own identity. |
| **rc** | Requires the **unchanged** `LEARNS_NEW_WORLDS` result on the three preregistered seeds, **and** closure of the applicable evaluator-integrity and custody gates, **and** comparative criteria passed for the declared scope. The required families, outcome definitions, seed-selection policy, regression limits and permitted N/A statuses are **frozen before** the confirmatory run. Filling in four status fields is not acceptance. Averaging gains across families, or picking the best seed, must not conceal a mandatory-family failure. |
| **release** | rc, plus independent audit/reproduction, plus release notes with the **complete outcome profile**. Disclosing a regression does not waive a predeclared blocking criterion. |
| **evidence** | Historical gate worlds and already-examined development panels keep their true exposure history. Any stronger prospective evaluation is separately versioned and sealed; it is never substituted retroactively to promote the current 2.0 result. |
| **arms** | Both certified 1.0 and experimental 2.0 remain comparison arms. Weight reuse requires an explicit tensor **and inference-semantics** migration record. All seeds and failed jobs are preserved, not only a selected candidate. |

Under this, today's placements are unchanged: Helm 1.0 = release; Helm 2.0-experimental = experimental,
unpromoted; Helm 3.0 = reserved, nothing exists.

## 3. What the Helm 2.0-experimental result means — the draft's arithmetic, checked

The draft derived, from the first return's counts, the held-back delta *outside* correspondence. Checked
here against the per-kind table already in `BRAIN_LINEAGE.md` (never-shown 127 = correspondence 20 +
the other 107):

| seed | held-back delta (127) | correspondence delta (20) | the other 107 |
|---|---:|---:|---:|
| 20260917 | +19 | +20 | **−1** |
| 20260918 | +17 | +20 | **−3** |
| 20260919 | +18 | +20 | **−2** |

So the supported description is exactly the draft's: **a substantial correspondence gain, mixed
cross-family performance, no certified-gate upgrade.** Not "no useful progress"; not "general transfer".

Attribution stays open: the gain is **not** attributed solely to the matching head until a matched
ablation separates recurrence, matching, reach-head, decoder and optimizer contributions. The `_rms_unit`
numerical repair is kept common to every viable arm; a NaN configuration is recorded as unsafe, never as
a low score. The stronger isomorphism baseline for correspondence remains registered-as-open; soft-score
quality is to be reported apart from task-valid joint decoding. The `9b84b35c` smoke stays attributed to
Helm 1.0.

## 4. Push status — reconciled with evidence

The first-return message said the push was in progress; the attachment said it completed. Both were
true at their moments. The evidence: after the background job finished, `git ls-remote --heads origin
research/helm-2.0-iterating-rounds` returned
`c58d4f42a733f496ebb07275d3897ba8f4e67932 refs/heads/research/helm-2.0-iterating-rounds`, equal to the
local HEAD at that time. **PUSHED**, no force, no deletion, no merge. The lab branch
`research/helm-3.0-cas-lab` is likewise on `origin` (verified after each of its pushes).

## 5. Multi-session rule, adopted

One source-owning agent per worktree and branch. Before edits: repository root, branch, parent commit,
owner session, active runs, output roots are recorded (the first return does this). Staged paths are
explicit and the staged diff is inspected; `git add -A` is retired on shared trees. A run's frozen
source snapshot is never edited while it is active. Experiment outputs are to be identified by lineage,
source SHA, protocol, seed and run id, not by date-only receipt names — a Helm-baseline-owner task.
