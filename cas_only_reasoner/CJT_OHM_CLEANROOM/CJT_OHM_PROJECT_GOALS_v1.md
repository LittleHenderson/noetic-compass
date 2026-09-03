# CJT / CAS-Ohm PROGRAM -- OBJECTIVES AND ULTIMATE GOALS v1 (2026-09-02)

Written at the owner's request so the program's goal can be set as a standing goal for the
successor. Plain English first, exact terms after. Everything here is a GOAL, not a result: no line
below claims that anything has been achieved unless it says so and names the artifact.

---

## THE ULTIMATE GOAL (one sentence)

> Build a CAS-native neural cognitive machine whose internal organisation IS the Cognitive
> Architecture System: a network of Cognitive Junction Transistors (CJTs) -- recurrent neural
> modules whose TYPE controls what evidence they may read, what transformation they perform, what
> Effect they may emit, how they are verified, what repair they may request and how their
> persistent Bias may change -- with CAS-Ohm as the internal law for relative flow, total
> compute, diagnosis and, later, verified plasticity.

Not the goal: an ordinary transformer with CAS labels and external rules bolted on.

## THE END STATE

```
ordinary neural parameters and matrix operations
        form  local trainable transformations
        form  recurrent CJT modules          (E_t, B_{t+1}) = CJTStep(C_t, B_t)
        form  Cognitive Circuit Boards
        form  the CNCM brain
```

The finished machine can, end to end and with a sealed trace: receive a Cause; route it through
the right CJTs; read persistent Bias and memory; assess Desire / Wisdom / Power readiness; allocate
compute and attention; perform typed transformations; produce candidate Effects; verify them;
diagnose failure; open an RPM repair when needed; propose state or weight updates; commit or roll
back atomically; keep the learned change across a restart; use the changed Bias later; and explain
which CJTs acted, why, and on what evidence.

## THE OBJECTIVES, IN ORDER (each with what "done" means)

| # | objective | done when | state today |
|---|---|---|---|
| O1 | **An honest evidence ledger, kept current** | every claim in the lane has a status from the frozen vocabulary, a committed artifact, a locator, an auditor and a correction field; the spec sheet carries the lane | ledger built 2026-09-02 (`CJT_OHM_CLAIM_LEDGER.json`); second-agent verification incomplete; spec-sheet rows for the lane still only in its change log |
| O2 | **One mechanism-bound neural CJT cell that earns its keep** | a CJT controller beats matched generic recurrent controllers on verified next-tick recovery, examples-to-threshold and held-out fault-combination transfer, on at least two task families, surviving independent audit and one-use protected evaluation | not started; six prior designs retired at `$0`; `CJT-MECH-0` design brief drafted, not authorized |
| O3 | **CAS-Ohm as a control law, each claim separately** | (a) `alpha` beats learned routing; (b) `I_total` improves adaptive compute at matched mean compute; (c) a monotone `V/R` law with independently grounded `V` and `R` extrapolates to unseen combinations better than a matched unconstrained router | all three OPEN; the additive weight-generation reading is RETIRED_BY_IDENTITY; `V`/`R` are not identifiable from routing alone |
| O4 | **Typed diagnosis that changes what happens next** | typed failure causes select better repairs than a generic full-state controller, measured as verified next-tick recovery, never as label accuracy | OPEN, never fairly tested (D1 was trivial) |
| O5 | **Verified, persistent, reversible learning** | persistent Bias survives a process restart; invalid updates roll back; verifier-gated (conductance-metered) plasticity reduces forgetting beyond replay and generic gates | deterministic reference semantics exist (`recursive_cjt_rc0`, status emitted by program); no neural version |
| O6 | **Composition** | several CJTs with genuinely different contracts and authority compose into a board and solve what no single one can | OPEN; the random-cascade bench was NOT CAS evidence |
| O7 | **CAS-specificity** | the CAS type system beats a cardinality-matched NON-CAS taxonomy on the same bench -- otherwise every win is "typing helps", not "CAS helps" | never shown anywhere in the harness (spec sheet frontier #1); mandatory control in every future bench |
| O8 | **The transformer-scale machine** | the CJT network lives inside a real language substrate (CNCM hybrid cortex: cloud proposes, kernel commits) with the full Cause -> Effect -> verified Bias-update loop and explanations of which CJTs acted | not started |

## GO-ALL-IN CRITERIA (owner's handoff §14, kept verbatim in substance)

All eight, not some: a mechanism-bound neural CJT beats matched generic controllers on at least two
task families; the result survives independent audit and protected evaluation; a plasticity or
retention advantage is established; persistent Bias survives a restart; invalid updates roll back;
multiple CJTs compose; the full Cause -> Effect -> verified Bias-update loop works end to end;
compute and parameter budgets remain honest.

## STOP CRITERIA (any one, measured fairly, closes the CAS-Ohm PERFORMANCE lane)

Generic full-state controllers match CAS on sample efficiency and held-out combinations; `alpha`
adds nothing beyond learned routing; `I_total` adds no compute-allocation value; typed diagnosis
does not improve verified next-tick recovery; CAS-Ohm plasticity does not beat replay + generic
gates; type-bound mechanisms collapse into interchangeable modules; or the gain comes from extra
parameters, depth, compute or a shortcut. CAS-Ohm may remain as telemetry and governance even then.

## THE RULES THAT TRAVEL WITH THE GOAL (non-negotiable)

1. **Type must govern mechanism, not name.** Ports, contracts, legal actions, memory access,
   temporal law, authority -- things a parameter relabelling cannot undo.
2. **Fairness.** Same raw evidence, same actions, same simulator, same masks, matched capacity and
   compute for every practical arm; CAS gets a registered factorisation and lawful interfaces, never
   a repair table; a full-state oracle is a ceiling, not a competitor.
3. **Mechanism-free baseline in every table**, capacity-matched. A win by mechanism M means nothing
   until it beats the cheapest method without M.
4. **Held-out means held out.** Separate seed streams, asserted non-identical. (P6 died here.)
5. **Status by program, never by prose.** Controls in the same code path; a failed control means
   no verdict; a failed hard gate is a failure.
6. **Every number has a committed script, digest, raw output and receipt.** No chat-only or
   commit-message-only number carries a claim. Label every figure by who measured it.
7. **Builder is not auditor.** Different-model-family or human audit for any claim-bearing neural
   result; Claude and GLM are recused where they built or authored.
8. **Compute law.** No neural work on local CPU; AWS GPU for claim-bearing runs with cost ceiling,
   watchdog, receipt and auto-termination; Bedrock for language-only audits.
9. **Governance.** The owner approves questions, designs, phases and spend with executable records;
   the successor never promotes a claim, rescues a failed gate, rewrites a receipt or deletes a
   negative.
10. **Dead lanes stay dead:** EX1, D0, S0, D1, P6 and the additive CAS-Ohm weight law are not
    rebuilt. Their negatives are assets.

## THE CURRENT OBJECTIVE (what the successor works on now)

```
Owner ruling on the CJT-MECH-0 QUESTION  (CJT_MECH_0_DESIGN_BRIEF_v0_1.md section 1)
  -> if approved: $0 world family + kill gates + absorption tests (no neural arms, no GPU)
  -> only then: neural arms on AWS GPU under an owner-signed phase record
Meanwhile: keep the ledger current; get the second-agent verification of the ledger completed;
           fold the lane into the spec sheet's capability / negatives / frontier sections.
```

---

## GOAL STATEMENT (paste-ready)

> **GOAL:** Establish, or fairly kill, the claim that a mechanism-bound network of Cognitive
> Junction Transistors with CAS-Ohm as its internal flow, compute, diagnosis and plasticity law
> learns faster, transfers better, recovers better and forgets less than matched generic
> controllers -- and if it survives every gate, grow it into the CNCM brain. Do this under the ten
> rules above: honest ledger, fair controls, held-out that is held out, status by program, receipts
> for every number, independent audit, GPU-only neural compute, owner-approved phases, no dead
> lane rebuilt, no negative deleted. The next step is the owner's ruling on the CJT-MECH-0
> question; nothing is built before it.
