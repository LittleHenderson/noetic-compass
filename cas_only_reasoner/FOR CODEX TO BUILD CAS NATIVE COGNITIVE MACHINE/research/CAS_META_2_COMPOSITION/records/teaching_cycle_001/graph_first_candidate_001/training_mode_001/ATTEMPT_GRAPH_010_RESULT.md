# Graph-first ^6 training — AWS attempt 010: FIRST COMPLETED TRAINING RESULT

Status: **AWS_GRAPH_TRAINING_FINISHED.** The full pipeline ran end to end:
launch, bootstrap, encoding, the candidate ^6 module, 64 registered updates
per framing condition (128 total), the sealed validation/test evaluation with
predictions recorded before answers, upload, collection, and a complete
cleanup with zero leftovers. Ledger 32 → 33 (`$182.00` reserved, `$218.00`
unreserved).

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909073316-0390037d` |
| request sha256 | `059ef45d76c8a47387e37f59434d02119744b2af1fc9b77a74cb02dac9cabbe0` |
| authority sha256 | `a454c8202eaac324f9d20a43f6a79c3175c92cea13eb7a366095c3c55ba59ec5` |
| owner record sha256 | `5db79165f65e2547d69d7f4b87e9f711a4b0ac17f1d9a7c3661efe2a1dc2ceac` |
| collected result sha256 | `b1b361633842c14d4ce3712fb7bb683919f30cc137ab77ac70763acd03997ae1` |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909073316-0390037d/`

## Deliverables (both arms; conditions differ only in prompt framing)

| Deliverable | cas | generic |
|---|---|---|
| completed updates | 64 | 64 |
| checkpoint identity | `690f6b61…` | `24b7c186…` |
| containment | `contained: true`; permitted changes `left.weight`, `merge.weight`, `right.weight` (exactly `operation:^6`); forbidden changes: none | same |
| lesson exposure (records per op) | LIST_PARTS 10, FIND_SHARED_PART 10, REACHED_VIA 10 | same |
| lesson exposure (updates per op) | 22 / 22 / 20 | 22 / 22 / 20 |
| before losses (per op) | `1.0986123085021973` (= ln 3) all three ops | LIST_PARTS `1.0986122965812684`, others ln 3 |
| after losses (per op) | ln 3 all three ops (unchanged) | ln 3 all three ops (unchanged) |
| sealed evaluation (validation) | LIST_PARTS 1/2, FIND_SHARED_PART 0/2, REACHED_VIA 1/3 | same |
| sealed evaluation (test) | LIST_PARTS 1/2, FIND_SHARED_PART 0/1, REACHED_VIA 1/2 | same |

## Honest reading of the result

1. **The training machinery works end to end.** Constructed → forward → three
   scores → finite loss → backward → permitted updates, verified by the
   digest-level containment report: only the module's own three weight
   matrices changed; nothing outside `operation:^6` moved.
2. **The bounded pilot shows NO measurable learning.** Losses are flat at the
   uniform three-way value ln 3 before and after 64 updates per condition,
   and sealed accuracy sits at chance (≈ 4/12 across both splits). Within the
   registered allowance, the ^6 module did not improve at identifying an
   idea's parts, a shared part, or a connecting path.
3. This does NOT establish that repeated graph teaching cannot work — the
   owner's framing stands: 64 optimizer steps are not 64 complete teaching
   cycles. It does establish the machinery and gives a real baseline to
   compare any further authorized pilot against.
4. Claims remain honest: `specialist_claimed: false`,
   `answer_edges_present: false`, `sealed_splits_read: false`; frozen
   negatives `0/72` untouched.
