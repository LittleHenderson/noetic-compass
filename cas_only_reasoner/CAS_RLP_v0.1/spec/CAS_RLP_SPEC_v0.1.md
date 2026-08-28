# CAS Recursive Learning and Evolution Protocol v0.1

## Fault Diagnosis, Candidate Mutation, Sandbox Evaluation, Promotion, and Rollback

**Status:** FROZEN for Phase 1. Built ABOVE the kernel: CAS-RLP never
modifies the kernel executable. It composes new versions of content
(rules, parameters) and evaluates them by running the unchanged kernel.

---

## 1. The boundary

    IMMUTABLE OR SLOWLY CHANGING       MUTABLE                HIGHLY LEARNABLE
    CAS-RRK                            Reasoning boards       Memory / language boards
    state authority                    inference procedures   facts, vocabulary
    scheduling                         comparison strategies  grammar, examples
    branch isolation                   planning patterns      conventions
    transaction rules
    trace and rollback

RLP may rewrite the mutable and learnable layers. It must not rewrite the
kernel, the evaluator, or the protected benchmarks.

## 2. The improvement loop

    reason
    -> inspect trace
    -> locate first failing stage
    -> classify fault or missing capability
    -> propose candidate repairs
    -> fork sandbox versions
    -> compile each version
    -> run regression and held-out tests
    -> compare against current version
    -> promote, quarantine, or reject
    -> preserve rollback

This is evolution across versioned descendants, not a live program
cutting into itself while executing.

## 3. The four rings

| Ring | What changes | Promotion rule |
| --- | --- | --- |
| R0 Experience | working and episodic memory | may update automatically with provenance |
| R1 Skill | procedures, rules, reasoning recipes | held-out tests before durable promotion |
| R2 Architecture | parameters, budgets, board policies | compile, sandbox, regression, rollback |
| R3 Constitution and kernel | authority rules, protected goals, coordinator | no autonomous change |

The machine may automatically change R0. It may propose and test R1. It
may experimentally evolve R2 in isolated descendants. It must not
autonomously rewrite R3.

## 4. The acceptance law

A child version may be promoted only when ALL hold:

    target performance improves by at least delta_min
    protected capabilities do not regress
    authority invariants still hold
    deterministic replay passes
    the new version outperforms the parent on held-out tasks
    the evaluator used to judge the change was not modified
        by the same change
    a complete evidence packet is sealed
    rollback to the parent remains possible

One prohibition is absolute: a version may not rewrite both its
reasoning method and the test that decides whether that method improved
in the same transaction. Otherwise it can "improve" by making the exam
easier rather than becoming more capable.

## 5. The protected set (ring R3)

    kernel source and behavior
    sole-writer state rule
    proof checker
    trace integrity and replay
    protected benchmarks and expectations
    rollback machinery
    this specification

Mutations targeting any member are rejected before sandboxing with
status REJECTED_AS_PROTECTED.

## 6. Decision vocabulary

    PROMOTED       child passed the acceptance law; becomes current
    REJECTED       child failed a protected test or an authority rule
    QUARANTINED    child passed everything but shows no held-out gain
    REJECTED_AS_PROTECTED  mutation targeted ring R3
    REJECTED_EVALUATOR_TAMPERING  child changed the tests that judge it

Every decision seals an evidence packet: parent and child revisions,
mutation, regression and held-out results with trace digests, the
acceptance-law checklist, and the rollback point.

## 7. Rollback

Promotion appends to the version history and preserves the parent
revision. rollback() restores the parent and re-runs the regression
suite to prove the restoration; the evidence packet records both
actions.
