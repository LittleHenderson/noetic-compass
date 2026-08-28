# CAS Cognitive Workbench v0.1 — the glass-brain interface

Ten panes over the organ stack. The workbench is a RENDERER, never a
reasoner: every pane is a projection of real sealed board output -
sealed trace events, state hashes, branch evidence, RPM transitions,
acceptance decisions, checker verdicts, coherence violations. Nothing
is simulated or post-hoc composed.

## Run

    cd cas_only_reasoner/CAS_WORKBENCH_v0.1
    python -m pytest                     # 13 tests
    python workbench/generate.py         # writes output/glass_brain.html

Then open output/glass_brain.html in any browser - it is a single
self-contained file (the data is inlined; no server, no dependencies).

## The ten panes

    1. Task and Dialogue   kernel answers decoded to English
    2. Goal Map            Foundation channel, adapter, D/W/P scan
    3. Live Board          components fired per tick
    4. Branch Tree         clickable candidates with their full WHY:
                           trigger, rules, memories, amplification,
                           proof path, elimination reason, commitment gates
    5. RPM Stack           push/return transitions with parents
    6. Memory Explorer     retrieved items with provenance + typed lacunae
    7. Truth and Evidence  semantic claims with truth statuses and
                           provenance; the CCB-M1 checker verdicts
    8. Trace Timeline      every tick: pre/post state hashes (chained),
                           authorized/rejected intents, terminal status
    9. Learning Dashboard  improvement decisions and revisions
    10. Evolution Lab      strategy descendants: promoted / rejected,
                           checks, budget, rollback

## Conformance

- trace hashes chain: post of tick N equals pre of tick N+1;
- the branch tree carries at least two candidates with the winner's
  proof path;
- the truth pane contains both VERIFIED and REJECTED verdicts;
- the evolution lab shows at least one PROMOTED and one REJECTED;
- app.js passes node --check (syntax conformance);
- regeneration is byte-identical (determinism).

## Honest boundary

No live editing, no websockets, no user-state persistence. The
workbench shows a frozen, reproducible snapshot - by design, because
the behavior itself is deterministic and replayable.
