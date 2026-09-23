# Corrections to the historical account of Helm (2026-09-23)

**The owner's instruction.** "Correct the historical account: Helm 2.0 had two runs with losses but only one
failed run, and the original rule has no automatic zero-loss veto."

**How corrections are applied.**
- They are **additive**. Every old sentence stays where it is.
- Each correction is applied as a dated note next to the old text. It points here.
- `BRAIN_LINEAGE.md` says "Never edit an old one", so its rows are annotated, never rewritten.

**Who writes the notes.** Under the coordination record (`_handoffs/HELM_NEXT_PHASE_20260923/`), Codex is
proposed as the single writer of `BRAIN_LINEAGE.md` and `AUDIT_PACK.md`. This file is the content those notes
point to.

**Line numbers.** They refer to the files at commit `4eb98682`. The root `CHANGELOG.md` is the worktree-root
file.

**The authority for the arithmetic.** It is the frozen grader's own output:
- `records/typed_pointer_001/admission_001/gate_reading.json` for Helm 2.0-experimental;
- `records/typed_pointer_001/admission_helm1_certified/gate_reading.json` for Helm 1.0.

Claude re-read both on 2026-09-23. The recorded values are in C1.

| Id | Where | What it says | What the frozen record says | Source |
|---|---|---|---|---|
| C1 | `BRAIN_LINEAGE.md:231` | `per seed: 20260917 False, 20260918 True, 20260919 False` | 20260917 **passed**: 11 gained, 1 lost, p 13/4096. 20260918 passed: 12/0, p 1/4096. 20260919 failed: 7/1, p 9/256. **One failed run, not two** | `admission_001/gate_reading.json` `seeds.*.G_LEARN_population`; A7 section 1; D10 |
| C2 | `BRAIN_LINEAGE.md:234-235` | "Two seeds each broke one ... and the gate requires zero broken on every seed" | Two runs **did** lose one question each. The rule has **no zero-loss veto**. A run passes when b > c, the exact one-sided p <= 1/100, and gains cover at least 2 kinds and 2 worlds. With one loss, a run needs 10 gains | `evaluate_gates.py:112-114`, `:301-321`; A7 section 1 |
| C3 | `AUDIT_PACK.md:60` | "pass mark: **7** improved, **0** broken" | 7 is the smallest passing gain count **only when nothing is lost** (2^-7 <= 1/100 < 2^-6). It is not a pass mark with a zero-loss condition. This row is where the shorthand first appeared (commit `50d6a7e2`) | D18 |
| C4 | Root `CHANGELOG.md:1196` | "The bar was **7** improved with **0** broken" | As C3 | D18 (certification commit `c95dc6ac`) |
| C5 | `BRAIN_LINEAGE.md:392`; `AUDIT_REPORT_20260920_INDEPENDENT.md:231` | "the gate's OWN bar (improved >= 7, broken 0)"; "improved at least 7, broken 0, one-sided p at most 1/128" | As C3. The audit's floor comparison is still valid as a paired test (b = 2, c = 1 gives p = 1/2), but its statement of the rule is not the grader's | D18; `evaluate_gates.py:301-321` |
| C6 | `HELM_ARCHITECTURE_FINDING_AND_PLAN.md:172-181`; `AUDIT_REPORT_20260920_INDEPENDENT.md:229`; the docstring in Helm source `pointer_learner.py:125-138` (source file **not edited**: it is pinned historical source) | Every head is scored independently, so "nothing enforces a joint answer"; a bijection "cannot be represented at any width"; it needs a matching layer (Sinkhorn) | The **decoder** already enumerates complete bijections and never picks duplicate targets. Helm 1.0's limit was that every source slot received the **same** target-score row, so every complete bijection had the same total score. Row/column normalisation alone cannot change the complete-assignment decision. Helm 2.0's pair scorer removed the restriction. That change is not isolated as the cause of the improvement | A7 section 3; A2/A5 finite-matrix checks |
| C7 | `BRAIN_LINEAGE.md:195`, `:198`; `HELM_ARCHITECTURE_FINDING_AND_PLAN.md:106`, `:127`; root `CHANGELOG.md:970`, `:1004-1005` | "the one-hop adjacency rule **is the architecture's ceiling**"; "VIA needs two" | The local message-input defect was real: `block` was assigned and never read. But "the whole model is one-hop" is **too strong**: other answer paths read global pools, marked node states and direct adjacency. No measurement shows the defect set the limit. Status: **INFERRED, not measured** | A7 section 3; D9 |
| C8 | `AUDIT_REPORT_20260920_INDEPENDENT.md:227`; `BRAIN_LINEAGE.md:395` | "`analogy` is the one kind ... no zero-learning rule touches" | The pre-run rule LB18 (same shape, different domain), written into the protocol before either run, answers the 5 frozen analogy questions. A5's degree comparator answers 70/70 analogy records | D7; A7 section 3 |
| C9 | `BRAIN_LINEAGE.md:670`, the evidence column of the Helm 1.0 row | `receipt_2026091{7,8,9}/` + `admission_001/gate_reading.json`; "one hop was the ceiling" | Those folders now hold **Helm 2.0** receipts. The certified Helm 1.0 evidence was renamed, with zero content changes, to `receipt_helm1_certified_2026091{7,8,9}/` and `admission_helm1_certified/` (commit `df20eb46`). The ceiling clause is as C7 | the rename record in `BRAIN_LINEAGE.md` (Helm 2.0-experimental section) |
| C10 | `records/typed_pointer_001/trusted_rescore.py` 0.2 and its committed reading `trusted_rescore_reading_helm2_experimental.json` | The per-run rule ">= 7 gained AND 0 lost"; the reading prints 20260917 `passed: false` beside `agree: true` | The rule is as C2. The agreement check compared only counts and the label, never each run's pass result. **The 0.2 files are preserved as history.** Codex owns the repair. Claude's reference implementation is `trusted_rescore_reference_claude_v0_3.py` on `research/helm-integration-20260923` | D19; A7 section 5 |

**What is NOT corrected, because it was right:**
- Both labels: Helm 1.0 `LEARNS_NEW_WORLDS`; Helm 2.0-experimental `NO_TRANSFER_TO_NEW_WORLDS`.
- All six gained/lost counts.
- The p values the frozen grader printed.
- The frozen grader and every receipt.
- The historical 18-question population.

**Record limit.** These corrections restate what the frozen files already say. They change no label, no
certificate and no receipt.
