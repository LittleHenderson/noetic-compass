# CAS-RLP v0.1 — Recursive Learning and Evolution Protocol

Fault diagnosis, candidate mutation, sandbox evaluation, promotion, and
rollback - built ABOVE the CAS-RRK kernel. RLP never modifies the kernel
executable; it evolves content (rules, parameters) across versioned
descendants and asks the unchanged kernel to judge each one.

## Run

    cd cas_only_reasoner/CAS_RLP_v0.1
    python -m pytest                # 23 tests
    python run_demo.py              # one full improvement cycle
    python run_demo_procedural.py   # strategy learning under budget

## What it demonstrates

- R0 Experience: failed episodes recorded automatically with provenance.
- R1 Skill (rules): the parent holds an overgeneralized rule
  taller(X,Y) :- height(X,Hx), height(Y,Hy). The held-out case
  (is bo taller than ada?) fails: the rule fires without comparing
  magnitudes. RLP diagnoses the overgeneral rule from the sealed trace,
  proposes two guarded repairs, promotes the gt-guard child (regression
  and held-out both pass), and rejects the lt-guard child (it breaks the
  protected regression case).
- R1 Skill (strategies): procedural learning. A fault class has a
  bounded pool of candidate repairs; an unstrategic order exhausts the
  repair budget, a learned order fits it. The strategy s_gt_first
  repairs the training case AND a held-out case of the same fault class
  (the overgeneralized bigger rule) in ONE sandbox evaluation each,
  and is PROMOTED under the acceptance law; s_lt_first fails within
  budget and is REJECTED. Unbudgeted default behavior is untouched
  (regression), the strategy memory is versioned with provenance
  prior_proof, decisions seal evidence, and rollback restores the
  parent strategy memory.
- R2 Architecture: parameter changes run in sandboxes. Starving the
  tick budget breaks the regression suite -> REJECTED. More ticks with
  no demonstrated held-out gain -> QUARANTINED.
- R3 Constitution: any mutation targeting the kernel, the sole-writer
  rule, the proof checker, benchmarks, or rollback is
  REJECTED_AS_PROTECTED before any sandbox runs.
- Evaluator tampering: a child that also weakens the tests that judge
  it is REJECTED_EVALUATOR_TAMPERING - a version may not rewrite both
  its reasoning method and its exam in the same transaction.
- Rollback: promotion preserves the parent; rollback restores it and
  re-runs the regression suite to prove the restoration.
- Acceptance law: every decision seals an evidence packet; the whole
  improvement cycle is deterministic (same cycle digest on every run).

## Layout

    spec/CAS_RLP_SPEC_v0.1.md   the four rings, the loop, the acceptance law
    rlp/                        versioning, diagnosis, mutations, sandbox,
                                acceptance, orchestrator
    fixtures/                   parent packages: r1 overgeneralized rule,
                                r2 parameter sandbox
    tests/                      13 tests across all rings

## Next

CCB-M1 (the mathematical learning and proof board) is the declared next
organ; RLP supplies the promotion machinery it will use to promote
procedures only after held-out mathematical evaluation.
