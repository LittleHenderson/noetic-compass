# Implementation and test report

## Outcome

CAS Harness now has a real research-shadow foundation for future J-Space,
Jacobian-lens, and CAS-Ohm work. The foundation safely reads the recovered
signed hidden states, checks their provenance and shape, and emits a
claim-excluded baseline receipt.

It does not yet perform the three scientific measurements.

## Added source

Relative to protected parent
81b5c18bd83e1f01ccd398dcad3865a674335b7f, final commit
de1a117d028e655840931e9702911c1967a3d6a4 adds:

- live-trace-worker/RESEARCH_SHADOW.md
- live-trace-worker/app/runtime/hidden_state_artifact.py
- live-trace-worker/app/runtime/research_shadow.py
- live-trace-worker/app/schemas/research_shadow.py
- live-trace-worker/scripts/run_research_shadow_baseline.py
- live-trace-worker/tests/test_research_shadow.py

Total feature diff: 6 files, 1,890 insertions.

## Safety and provenance behavior

The loader rejects unsafe ZIP members, duplicate members, object arrays,
non-finite values, incompatible tensor shapes, invalid layer metadata,
unpinned model revisions, invalid capture provenance, and artifact changes
during verification. NumPy loads with allow_pickle=False.

The runner is opt-in with --enable-shadow. Before importing any local
application module, it:

1. hashes the supplied standalone Git bundle;
2. reconstructs the declared commit in an empty bare repository;
3. rejects an incomplete/thin bundle;
4. discovers every committed Python file under the full worker app tree;
5. compares each executing working-tree blob, the runner, and
   requirements.txt with the declared commit.

The receipt excludes raw vectors and fixes:

- execution_mode = SHADOW
- verdict_influence = NONE
- claim_status = NOT_LICENSED
- claim_eligible = false

The receipt content hash is tamper-evident content binding. It is not a
digital signature or external timestamp.

## Real-artifact run

The final run used the recovered Pythia-160M NPZ:

- file bytes: 109,414,103
- SHA-256:
  454a4f017d56ed393e50d7e88d29486b3379e96ae930a1123698c6275298ead6
- evaluation tensor: [3080, 12, 768]
- definition tensor: [3, 28, 12, 768]
- hook: complete transformer block output
- signed values: retained
- token-ID hashes: present
- dose values: [0.0]

The file was rehashed and reopened. Its storage status remains
LOCAL_HANDOFF_ONLY and NOT_DURABLY_OBJECT_STORED.

## Verification

Run on 2026-07-21:

- Python compilation: PASS
- focused research-shadow suite: 13 passed
- complete live-trace-worker suite: 248 passed
- canonical receipt-content verification: True

The final reviewer found no remaining claim-integrity or source-provenance
blocker. The protected checkout was not modified or merged.

## What must happen next

1. J-Space: register hashed CAS and taxonomy-independent bases, then run
   grouped holdout correspondence with random, lexical, length, domain, and
   surface-text controls plus bootstrap uncertainty.
2. Jacobian-lens: rerun the exact pinned model with gradients and a registered
   output functional; compute projected JVP/VJP and finite-difference checks.
3. CAS-Ohm: fix the existing eraser coordinate mismatch, register exact test
   points and unit directions, then run zero plus positive/negative doses,
   signed mediator/output effects, off-target checks, controls, competing
   curve families, uncertainty, and prospective P1-P4 falsification gates.
4. Repeat on multiple seeds and Pythia scales, then on at least one
   non-GPT-NeoX model before advancing any universality claim.
5. Only after small-model contracts pass should the same contracts be moved
   toward genuine distributed 20B, 100B, and 300B-class execution.
