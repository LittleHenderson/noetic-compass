# First recorded transition differences and per-depth task results

Use receipt_v2.json with the current run.py. The initial script and receipt.json
are preserved in commit 152043fd. Review found that differing operation kinds
should not also compare kind-specific fields as separate wrong decisions. The
revised classifier stops at that operation-kind difference; task scores and
trajectory coverage did not change.

The script checked the complete comparison packet and passed stored-audit digest
before and after reading it. It ran 11 small self-checks and produced 720 rows:
72 tasks x five selectors x two decoder modes. No model or provider was used.
Every failed case either records rejection before execution or the first
observed difference from the successful, exact-target rule trajectory. Matching
prefixes compare recorded input/output references with run-specific Effect IDs
replaced by their producer addresses. Resource CHARGE events are excluded.

For both modes, native task correctness is:

| Selector | Depth 3 | Depth 4 |
| --- | ---: | ---: |
| CAS untrained | 0/48 | 0/24 |
| CAS trained | 0/48 | 0/24 |
| Generic untrained | 0/48 | 0/24 |
| Generic trained | 10/48 | 2/24 |
| Rule | 48/48 | 24/24 |

The corrected decoder has 36 CAS pre-execution rejections and 36 executed but
incorrect trajectories. The first differing events among those 36 include
input-binding differences in 14 cases and wrong child names in 12. Categories
can overlap at one event; they are not 36 mutually exclusive causes.

Example: case 0001 reaches SUSPEND at entry, seq 5, after two matching A runs.
The candidate supplies v0; the exact-target rule supplies v1. That is a recorded
first input-binding difference, not a claim about the earliest neural token
decision or what caused the training problem.

All results are retrospective on exposed cases. The successful rule trajectory
is a checked comparator, not the only semantically valid program. Correct tasks
are not relabeled failures for differing text. This analysis does not infer
runtime defects, hidden budget failures, or causal root causes from a mismatch.
It does not replace the stored semantic audit or establish fresh generalization.
