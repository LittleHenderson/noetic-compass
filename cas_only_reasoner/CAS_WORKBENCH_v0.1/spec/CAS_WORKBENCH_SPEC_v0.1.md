# CAS Cognitive Workbench v0.1

## The glass-brain interface over the organ stack

**Status:** FROZEN for Phase 1. The workbench is a RENDERER, never a
reasoner: it draws ten panes from real sealed board output. Nothing it
displays is simulated, decorated, or post-hoc composed - every pane is
a projection of structures the boards already produce (sealed trace
events, state hashes, branch evidence, RPM transitions, acceptance
decisions, checker verdicts, coherence violations).

---

## 1. The ten panes (charter section 3)

    Task and Dialogue    questions asked and the kernel's decoded answers
    Goal Map             active Foundation channel, adapter mixture,
                         D/W/P scan
    Live Board           which components fired per tick
    Branch Tree          candidates with their full WHY (trigger, rules,
                         memories, amplification, verdict, gates)
    RPM Stack            push/return transitions with parent links
    Memory Explorer      retrieved items with provenance and typed lacunae
    Truth and Evidence   semantic claims with truth status and provenance;
                         mathematical verdicts from the checker
    Trace Timeline       every tick: pre/post state hashes, authorized and
                         rejected intents, terminal status
    Learning Dashboard   improvement decisions with verdicts and checks
    Evolution Lab        descendant strategies and repairs: promoted,
                         rejected, rollback preserved

Clicking a candidate shows exactly the charter's questions: why it was
generated, which memories contributed, what rules produced its
conclusion, why it won or lost, what prevented commitment, and what
would change the result.

## 2. The data contract

    generate.py runs the six boards once each, deterministically, and
    emits workbench_data.json plus a self-contained glass_brain.html
    with the data inlined. The bundle carries a digest over the panes;
    regenerating produces the identical digest (conformance-tested).
    The renderer (app.js) contains NO logic beyond projection: it
    reads fields, never computes verdicts.

## 3. Conformance

- every pane is present and non-empty;
- trace hashes chain (post of tick N equals pre of tick N+1);
- evolution decisions include at least one PROMOTED and one REJECTED;
- the truth pane contains both VERIFIED and REJECTED verdicts;
- the RPM pane shows both a push and a return;
- the branch tree carries at least two candidates with the winner's
  proof path;
- app.js passes node --check (syntax conformance);
- regeneration is byte-identical (determinism).

## 4. Non-goals (v0.1)

No live editing of boards, no websockets, no persistence of user
state; the workbench shows a frozen, reproducible snapshot of the
machine's behavior - by design, because the behavior itself is
deterministic and replayable.
