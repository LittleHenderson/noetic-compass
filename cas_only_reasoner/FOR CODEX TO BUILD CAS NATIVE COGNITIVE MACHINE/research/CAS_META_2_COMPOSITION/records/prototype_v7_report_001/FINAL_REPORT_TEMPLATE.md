# V7 learning result — PENDING template

This is an unfilled report, not a completed learning result. It was prepared from the public observation at **2026-09-06 09:53:16 UTC** and the frozen specification. No current private test data, model, checkpoint, or result packet was read to prepare it. Replace PENDING only with checked evidence; never copy an older experiment's score into v7.

## Bottom line

**PENDING:** Did trained CAS solve more new tasks than its untrained copy, and how did it compare with the matched generic model and rule selector?

Job: `cas-meta2-20260906094002-39762c47`.
Frozen source: `42f9164754312f12850d9b8789c062fa7fb8069f`.
Completed packet SHA256, independent review receipt/path/SHA256, and final status: **PENDING**.

## Actual assembly observed; outcome checks pending

The saved public stage log reports the following assembled counts, including the exact original **256** practice records. This is observed assembly metadata, not an independent recount of the current dataset or a training result.

| Partition | Records | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
|---|---:|---:|---:|---:|---:|
| Training | 896 | 128 | 384 | 384 | 0 |
| Validation | 96 | 32 | 32 | 32 | 0 |
| Test | 72 | 0 | 0 | 48 | 24 |

Training consists of a new 640-record base plus the exact original 256 records. Those original records are permitted only in training. Their 128 contrast pairs must stay together. Validation/test bytes must remain unchanged by the append. Final byte-bound confirmation: **PENDING**.

The test design has **24 related triplets**, not 72 independent structures: same-depth, changed-wording, and deeper-call variants. Report fresh task instances, unseen program combinations, and unseen wording as separate checks. The final report must state what the checked graph/wording exclusions establish; a new instance alone does not establish a new program combination. These condition views overlap the depth groups and must not be added together.

The registered rules use the same permitted inputs and unchanged executor/verifier for all five arms. Checkpoint selection uses validation only; private test targets must stay outside training. Final evidence of that separation: **PENDING**.

### Declared matched conditions

CAS and generic receive the same 896 training examples in the same shuffled order, with 200 epochs, 11,200 optimizer steps each, batch 16, and AdamW (learning rate 0.001; weight decay 0.01). The shared decoder, observation-binding pointer, and lexical-copy head start from exactly copied common parameters. The generic encoder's real feed-forward width is adjusted to closely match parameter count; no disconnected filler parameters are added. Actual CAS/generic parameter counts, width and remaining difference: **PENDING from the checked training receipt**.

Both neural families use the same public inputs, output grammar and unchanged execution/checking rules, with no gold program or answer supplied during test selection. The rule control is a hand-written public-problem parser, not a learned model. Equal permitted information does not mean identical prior machinery. Equal optimizer steps and similar parameter counts do **not** establish equal elapsed time or FLOPs; report actual per-family compute separately.

These are source-declared conditions, not a claim that training has finished. Source: [v7 trainer](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/contrast_v7/train.py:143>) and [matched policy construction](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/policy_v3.py:162>), inspected as text only.

Sources: [public assembly observation](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_prototype_v7_observation_001/status_20260906T095315185201.json>) and [frozen specification](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/EXPERIMENT_PROTOTYPE_V7.json>).
The stage log reports assembly receipt SHA256 `0547a6cf730272c409cf4e4e691679df5591aa368c34e71d6835cc327d104f91`; that receipt itself was not opened for this template.

## Complete-task correctness

Each score below must be **correct / attempted**, not trace-valid / attempted. PENDING means both the numerator and actual attempted denominator remain unreported. The expected counts are a coverage requirement, not a substitute for the measured denominator. Rejections and post-start failures remain attempts and incorrect answers.

| Group | Expected per arm | CAS before | CAS after | Generic before | Generic after | Rule |
|---|---:|---|---|---|---|---|
| All | 72 | PENDING | PENDING | PENDING | PENDING | PENDING |
| Depth 3 | 48 | PENDING | PENDING | PENDING | PENDING | PENDING |
| Depth 4 | 24 | PENDING | PENDING | PENDING | PENDING | PENDING |
| Same-depth condition | 24 | PENDING | PENDING | PENDING | PENDING | PENDING |
| Changed wording | 24 | PENDING | PENDING | PENDING | PENDING | PENDING |
| Deeper calls | 24 | PENDING | PENDING | PENDING | PENDING | PENDING |

Coverage must include all **72 references and 360 arm outcomes**. Partial output must remain partial; do not omit failed cases or publish a success-only denominator. Coverage, five-arm completeness, and before/after change: **PENDING**.

| Arm | Actual attempts | Pre-execution rejections | Complete executions | Post-start failures | Correct tasks |
|---|---|---|---|---|---|
| CAS untrained | PENDING | PENDING | PENDING | PENDING | PENDING |
| CAS trained | PENDING | PENDING | PENDING | PENDING | PENDING |
| Generic untrained | PENDING | PENDING | PENDING | PENDING | PENDING |
| Generic trained | PENDING | PENDING | PENDING | PENDING | PENDING |
| Rule | PENDING | PENDING | PENDING | PENDING | PENDING |

## Binding, child selection, and first recorded mistakes

Report every arm, by depth and condition, in the linked machine-readable review. Use correct/expected site counts and correct/incorrect/unknown/attempted task counts; do not collapse unknowns into false.

| Metric | CAS before → after | Generic before → after | Rule |
|---|---|---|---|
| Verifier input-binding correctness: correct / incorrect / unknown / attempted | PENDING | PENDING | PENDING |
| Verifier procedure and dependency correctness, separately | PENDING | PENDING | PENDING |
| Literal observation binding: correct / expected | PENDING | PENDING | PENDING |
| Literal named input sites: correct / expected | PENDING | PENDING | PENDING |
| Literal named child sites: correct / expected | PENDING | PENDING | PENDING |

Literal name matching is not semantic input-binding correctness or complete-task correctness. Equivalent renaming can fail literal matching. Child-site order is not execution order.

Per unsuccessful case, retain: case index/task ID, arm, execution status, saved action identity, comparison/reference identity, first recorded differing field or event, and exact evidence path. If no comparison is available, say **UNKNOWN**. Full per-case file and category totals: **PENDING**.

Separate complete-trajectory differences from first disagreements in committed RUN rows after a runtime failure. A matching partial prefix does not prove an early return. Missing failed-tick records do not identify its cause. The first recorded difference is **not proof of the earliest causal neural decision**; overlapping categories must be labeled.

## Checkpoints and compute

Registered plan: 200 epochs, batch 16, 11,200 optimizer steps per family; validation-only selection. These are planned values, not reported completion. Record actual epochs/steps and the validation-selection receipt.

| Family | Checkpoint | Actual epoch / steps | Full file address | SHA256 |
|---|---|---|---|---|
| CAS | Initial | PENDING | PENDING | PENDING |
| CAS | Validation-selected | PENDING | PENDING | PENDING |
| CAS | Final | PENDING | PENDING | PENDING |
| Generic | Initial | PENDING | PENDING | PENDING |
| Generic | Validation-selected | PENDING | PENDING | PENDING |
| Generic | Final | PENDING | PENDING | PENDING |

Actual training/native/whole-job wall time, GPU/environment identity, exact command receipts, and process exits: **PENDING**.
Committed native-run counts, reserved policy units, and compute-completeness flags by arm: **PENDING**.
Failed-tick compute stays **UNKNOWN** where absent; committed-prefix totals are lower bounds, not FLOPs.

Canonical reservation entry and reserved amount: **PENDING**.
Launcher cost estimate with included/excluded charges: **PENDING**.
Final billed cost/invoice: **PENDING / UNAVAILABLE until supplied**.
Cleanup/termination evidence and receipt time: **PENDING**.
A reservation is not a bill or a target to spend. Do not carry older remaining-budget figures into this report.

The known-fixture smoke (352/24/9, one epoch, 22 steps per family, 9 references/45 arm outcomes) and the original four GPU contract tests are separate gates, not new held-out learning results. Final gate evidence: **PENDING**. Do not add them to the main 72 tasks. Preserve the distinction between checked checkpoint bytes, GPU-authored changed-weight claims, stored native replay, and independent neural arithmetic.

## History and claim boundary

Keep the earlier familiar fit **0/24 → 24/24**, original composition result **CAS 0/72, generic 12/72, rule 72/72**, and recovered-v6 result **CAS 0/72 → 0/72, generic 0/72 → 0/72, rule 72/72** separate. See [historical evidence index](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/HISTORICAL_EVIDENCE.md>).

Final learning conclusion: **PENDING**. A valid trace is not a correct answer. No automatic acceptance, merge, CAS-specific advantage, general reasoning, AGI, or production-readiness claim follows.
