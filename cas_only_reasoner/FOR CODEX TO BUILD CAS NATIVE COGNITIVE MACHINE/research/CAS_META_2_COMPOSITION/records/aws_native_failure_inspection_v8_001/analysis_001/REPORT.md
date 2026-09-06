# Saved native-failure record analysis

Saved-image JSON and hash/link examination only. No SQLite connection, tensor decoding, neural replay, new native execution, training or qualification. This cannot recover state that was never captured in the standalone image.

The first stored nonreturnable operation is tick 6, CJT R.
Its recorded label is L0; the authored expected label is L1. The verifier recorded REPAIR: SEMANTIC_OFF_AXIS.

The failed full execution retained 6 committed native ticks; 5 had accepted, singly published effects.
These are not additional completed full tasks, a neural replay, or proof of training readiness.

| Tick | CJT | Input tick | Expected | Recorded | Verifier | Published |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | A | None | L1 | L1 | ACCEPT | 1 |
| 2 | B | 1 | L3 | L3 | ACCEPT | 1 |
| 3 | C | 2 | L2 | L2 | ACCEPT | 1 |
| 4 | R | 3 | L1 | L1 | ACCEPT | 1 |
| 5 | C | 4 | L2 | L2 | ACCEPT | 1 |
| 6 | R | 5 | L1 | L0 | REPAIR | 0 |

Checks: indexed packet bytes, exported payload hashes, opaque blob hashes, trace digests, eleven-phase order, contiguous ticks, state chain, final head, receipt ownership, candidate/effect/evidence links and the sealed R_CR operation/input prefix.
The original 21 ticks in the four completed executions are separate evidence and are not re-audited here.
