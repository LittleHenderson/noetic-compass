# Cooperation — a lesson told to CAS-RPU, carried in the envelope, used by the Codex CNCM kernel

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 7 (built together), roadmap step 6; the cooperation outcome type of §2 ("independently developed components exchange a correctly interpreted lesson or state and produce a behavior neither showed alone"). Draft it executes: `docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md` (envelope `helm.interchange/0.1`, fixtures F01–F13).
**Code:** `scripts/cas_memory/cncm_interchange.py`; tests `scripts/tests/test_cncm_interchange.py` (12, run in CI against the mounted commit). The CNCM kernel is the frozen Codex reference implementation at `eb9985566bd11a89f485d627186ef0efa7177f02`, imported from the read-only mount and pinned by content (`CNCM_MODULES_SHA256`); nothing in it was changed, and its `AGENTS.md` boundaries were respected.
**Label:** a development demonstration plus a first-look run on three seeds the builder had not generated before. Not the frozen result. One direction (CAS-RPU → CNCM); the DeepSeek sibling is not touched; **neural change: none**.

## Gate answer (written before the runs)

Ability 7. Before: the CNCM kernel, given a chain that runs through an edge of a foreign relation, returns NEEDS_INFORMATION; CAS-RPU, told the lesson "`rel_a` entails `leads_to`", answers YES, but CNCM has never heard the lesson and has no `entails` concept. After: the lesson, exported from the organism's accepted history as an envelope event and imported into CNCM as a modus-ponens rule over a declared predicate, lets CNCM conclude the same question and a never-seen instance; the untaught twin stream (the lesson replaced by an unrelated fact) leaves CNCM at NEEDS_INFORMATION. Control: the whole-stream Revision Streams oracle, which neither engine shares, scores both. Criterion: on every lesson probe of the generated set, CNCM's mapped verdict equals the oracle's on primaries and twins; over all probes, every disagreement is accounted for by a divergence predicted in the fixtures draft before the run (F06, locality of conflict) and none is mapped away. What it will not show: cooperation with DeepSeek's engine; CNCM's own persistence (packets are stateless); closed-world verdicts or lacunae (CNCM has neither); any neural outcome.

## What crosses, and how it is interpreted

| CAS-RPU accepted event | envelope | CNCM packet |
|---|---|---|
| `FACT s -[leads_to]-> o` | FACT, polarity true | fact `leads_to(s,o)`, asserted, provenance = source event id |
| `NEGATION s -[leads_to]-> o` | FACT, polarity false | fact `leads_to(s,o)` polarity false |
| `FACT s -[r]-> o` (foreign r) | FACT, relation r | fact `r(s,o)` |
| `FACT r entails leads_to` (a lesson) | LESSON | rule `INFER_MODUS_PONENS: r(?x,?y) → leads_to(?x,?y)` |
| `RETRACT` (accepted) | RETRACT | the given is dropped from the state |
| `HYPOTHESIS` | rejected `E-IX-PROPOSED` | never a fact (F10) |
| `FACT s -[co_occurs]-> o` | rejected `E-IX-RELATION` | CNCM has no association (F13) |
| transitivity of `leads_to` | implicit in CAS-RPU | rule `INFER_TRANSITIVE`, always sent |

Verdict mapping, two CNCM runs per question: CONCLUDED on P → YES; CONFLICT_UNRESOLVED → INADMISSIBLE; otherwise CONCLUDED on ¬P → NO; otherwise UNKNOWN. Any other terminal status is UNMAPPED and counted, never guessed. Polarity is required on every envelope; a negative retract is refused (`E-IX-NEG-RETRACT`); a defaulted polarity is refused (`E-IX-POLARITY`).

**Scoping.** A packet carries only the token-connected component of the asked pair. Two measured properties of CNCM force this: it refuses every question while any contradiction exists anywhere in the packet, and its inference budget is exhausted by a whole 500-event history (whole-stream scope on seed 0: 2 of 110 probes agreed, 104 BUDGET_EXHAUSTED, the rest CONFLICT_UNRESOLVED). A fact outside the component cannot lie on any route in either engine, so scoping changes no oracle verdict; the whole-stream scope stays available for the record.

## Results

Lesson streams (`generate_session_set(..., lessons=True)`, open world), primaries and untaught twins, component scope. Per stream: 110 probes, 28 of them class-L designed or balancing probes, 39 envelopes rejected (associations and guesses, as designed).

| set | streams | probes | agree | disagree | unmapped | lesson probes | lesson agree | disagreements all F06 |
|---|---|---|---|---|---|---|---|---|
| development seeds 0–2, primaries + twins | 6 | 660 | 630 | 30 | 0 | 168 | **168** | yes (30 of 30, `conflict_elsewhere=True`) |
| first-look seeds 3000–3002, primaries + twins | 6 | 660 | 630 | 30 | 0 | 168 | **168** | yes (30 of 30) |

Every stream gave the same counts: 105/110, with the 5 disagreements on the same three variants — C-blocked's sound-half probe, C-bypassed's main and reverse probes, C-unrelated's main and reverse probes. In each, a disputed link exists in the component but not on the queried route; the oracle answers YES or UNKNOWN, CNCM refuses. That is fixture F06 exactly as written before the run ("locality divergence; adapter must not map"). Excluding those, 660/660 on each set.

The hand-built §13 stream (`test_cas_rpu_lessons.STREAM`, 13 probes: before/after the lesson, a new instance, retractions, revival, a denied entailed pair, a lesson for another relation, a guess) agrees on every probe.

**The cooperation behavior, in one line:** a rule that exists only because it was told to CAS-RPU, with no counterpart in CNCM's vocabulary, was carried across as data and made the independent CNCM kernel conclude questions it answers NEEDS_INFORMATION to without it, on 168 of 168 lesson probes over six streams the builder had not seen, while the untaught twins stayed unanswered. Neither engine showed this alone: CNCM has no `entails`; CAS-RPU produces no CNCM evidence bundle or replayable trace.

## What this does not show, said plainly

- Nothing about DeepSeek's engine (`CAS_RRK_v0.1`), whose negation interface is unreconciled; the envelope has been exercised between two explicit-polarity engines only.
- The reverse direction (CNCM → CAS-RPU) is not run here; the draft's worked example A remains a draft.
- CNCM is used statelessly through packets; its journals and recovery (v0.2–v0.6) are not exercised, so no CNCM-side retention is claimed.
- Closed-world NO and lacunae are not compared (CNCM has neither).
- The locality divergence is real and unresolved: which engine is right about a conflict off the route is a meaning question for the owners (fixtures draft §5), not something an adapter may settle.
- First-look, not custody: the same builder generated and ran the seeds.

## Next

1. Put the F06 question to the owners of both engines and record the answer in the fixtures draft; until then the adapter keeps reporting it.
2. The reverse direction with CNCM's own provenance, then a CNCM journal round-trip so a retained lesson can be shown on both sides.
3. The DeepSeek interface, when its lead is confirmed.
