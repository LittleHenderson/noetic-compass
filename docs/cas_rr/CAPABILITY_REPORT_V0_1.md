# CAS-RR v0.1 — Reasoning Capability Report

**Machine:** CAS Reasoning Runtime v0.1 (cas-rr/), CCB-R1 software form.
**Criterion:** docs/cas_rr/REASONING_CAPABILITY_CRITERION.md (executable:
python run.py report; 43 tests green at report date).
**Date:** 2026-08-28.

---

## 1. Executive verdict

    Capability tier: R3 (recursive planner)
    Core levels:     9/9 passed (L0 through L5)
    Frontier:        4/5 probes refused honestly (L6)

CAS-RR v0.1 attains R3 on its own ladder: deterministic recall,
single-step and multi-step deduction, constraint satisfaction with
falsification, fault diagnosis by test-point walk-down, honest refusal
with typed lacunae, depth-2 recursive planning, and memory-dependent
reasoning with full provenance. The R4 frontier (induction, native
arithmetic, probabilistic and hypothetical reasoning) is NOT attained -
and the machine says so, in typed halts, instead of pretending.

## 2. Ladder results (live run)

    L0  fact recall                  CONCLUDED            color(sky,blue)
    L1  modus ponens                 CONCLUDED            mortal(socrates)
    L2  chained deduction            CONCLUDED            precedes(a,d)
    L3  constraint satisfaction      CONCLUDED            viable(P1)
    L4  fault diagnosis              CONCLUDED            first_bad(S3)
    L4  honest refusal               NEEDS_INFORMATION    -
    L5  recursive planning (d=1)     CONCLUDED            executable(P_launch)
    L5  recursive planning (d=2)     CONCLUDED            executable(P_launch)
    L5  memory-dependent             NEEDS_INFORMATION -> CONCLUDED is(b,y)
    L6  arithmetic (data)            CONCLUDED            taller(ada,bo)
    L6  arithmetic (unencoded)       NEEDS_INFORMATION    -
    L6  induction                    NEEDS_INFORMATION    -
    L6  probabilistic                NEEDS_INFORMATION    -
    L6  hypothetical                 NEEDS_INFORMATION    -

Every CONCLUDED row carries its proof path in the provenance packet
(rules used, premises consumed). Every refusal row carries its typed
lacunae. Nothing is asserted without a trace.

## 3. Where this sits against reference language models (honest mapping)

The GPT series is a scale of language models; CAS-RR is a symbolic
reasoning core. A single-number mapping would be a category error, so
here is the capability-by-capability comparison instead:

| Capability | GPT-1/2 | GPT-3 | GPT-4 / o-style | CAS-RR v0.1 |
| --- | --- | --- | --- | --- |
| guaranteed multi-step deduction | no | no | no (CoT helps, still confabulates) | YES (L2, proof in trace) |
| provenance / show-your-work | no | no | approximate, post-hoc | YES (append-only packet) |
| typed refusal when unsure | no | partial | partial | YES (NEEDS_INFORMATION + lacunae) |
| recursive planning with re-measurement | no | fragile | emerging | YES (depth 2, section-retraction) |
| language breadth | weak | large | large | NONE (encoder boundary) |
| learning from data | yes (pretraining) | yes | yes | NO (disabled by design in v0.1) |
| probabilistic reasoning | yes (implicitly) | yes | yes | NO (refuses) |
| arithmetic | weak, implicit | partial | partial | NO (works only when comparison is data) |
| induction | statistical | statistical | statistical | NO (refuses) |

**The composite verdict:** as a REASONING CORE on encoded tasks, CAS-RR
v0.1 does what no GPT-1/2/3 did reliably - deterministic multi-step
deduction with a proof, principled refusal, and self-diagnosed recursive
planning. As a GENERAL INTELLIGENCE its breadth is deliberately narrow
in v0.1: zero language, zero learning, zero probability - each excluded
by design, and each on the roadmap with its own board.

## 4. What the test exposed, and what was fixed this round

1. **Flat recursion (fixed).** The original runtime let subgoals halt
   but not descend further. The criterion's depth-2 task exposed it. Fix:
   scans now report the exact missing prerequisite token, subgoals carry
   their resolving action's own prerequisites, and any goal may descend
   (rpm.descend, runtime phase 9). The depth-2 task
   (capability -> knowledge) now passes: 7 ticks, full ascend/descend
   trace. This was the single most important capability finding of the
   evaluation.
2. **Tier inflation by honesty (fixed).** The first tier computation
   counted L6 refusals as attainment and reported R4. Refusals are
   honesty, not capability; L6 is now excluded from tier computation.

## 5. Fixes and improvements (prioritized roadmap)

    DONE   deep recursion (subgoals descend to depth N)
    1      hypothesis autonomy: ^8 should generate candidates from rule
           conclusions, not only amplify encoder-supplied alternatives
    2      backtracking: collect the full proof set, prefer optimal
           proofs, contradiction-driven retry across rules
    3      arithmetic peripheral: a safe deterministic numeric evaluator
           as an out-of-core CJT (comparison, counting, addition)
    4      induction operator: generalize over episodic records (^7),
           behind the Gate-5 learning controls
    5      uncertainty degrees: evidence weights (needs 3 first)
    6      procedural learning across episodes: versioned, reversible,
           only after repeated verified outcomes
    7      encoders/decoders (English <-> CAS) as peripherals - the
           umbilical cord, kept strictly out of the core
    8      CCDL emit/parse: netlist out, compiled board back (Gate 1)
    9      breakdown-region involution semantics (currently flagged)
    10     memory relevance ranking + lacuna dedupe at the CMB layer
    11     parallel candidate evaluation (currently sequential)

## 6. Insights worth keeping

1. **Refusal is a first-class capability metric.** 4 of the 14 ladder
   rows pass by refusing. An evaluation culture that only rewards
   answers would mis-score this machine as worse than it is; a culture
   that only rewards caution would mis-score it as better. The criterion
   grades each row on its EXPECTED typed halt - that is the honest
   middle.
2. **Ambition cannot bribe the machine.** In the recursive-plan task,
   iteration 1 shows the machine preferring the DEFERRAL plan because
   the launch plan was not yet provable - the goal-channel bias orders
   only provable candidates; it cannot fabricate proof. That is the
   unity-gain firewall working as designed, visible in the trace.
3. **Difficulty lives in the encoding, not the engine.** The L6a/L6b
   pair runs the same engine on the same heights: with gt(5,3) supplied
   as data the machine concludes taller(ada,bo); without it, it refuses.
   One engine, two outcomes, one boundary - exactly where the criterion
   says the boundary is.
4. **Determinism is a superpower with a ceiling.** Every run is
   reproducible and auditable (python run.py check passes on all 12
   battery tasks), which no LLM offers. The ceiling: no creative leaps,
   no surprise hypotheses. The trade is explicit and should stay that
   way.
5. **The tier is trustworthy because the firewall is structural.** The
   same stage that cannot inflate evidence (beta locked to 1.0) is the
   stage being measured. Capability numbers from a machine that can be
   bribed by its own goals are not capability numbers.
6. **The comparison question is a category question.** The machine is
   a reasoning core with a different guarantee profile:
   proof over probability, refusal over fluency, determinism over
   breadth. The next honest milestone is R4 - and the four frontier
   probes are the roadmap, already failing in the most useful possible
   way: typed, traceable, and reproducible.
