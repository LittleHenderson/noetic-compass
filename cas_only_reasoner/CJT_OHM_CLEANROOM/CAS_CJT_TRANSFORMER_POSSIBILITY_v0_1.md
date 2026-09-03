# IS A CAS / CJT / CAS-Ohm TRANSFORMER POSSIBLE? -- a deliberate second look (v0.1, 2026-09-02)

```
Claim state of everything in this document:   REASONING.  OPEN.  Nothing here is measured,
                                               nothing is licensed, no number is a result.
Purpose:                                       find what the six retired designs may have missed
Written by:                                    the clean-room successor, at the owner's request
```

Plain English: the owner's intuition is that a transformer built from CJTs with CAS-Ohm inside is
possible and that the previous attempts missed something. This document tries to say exactly what
was missed, why the record supports that reading, and what would have to be true for the intuition
to become a measured result.

---

## 1. The pattern in the six deaths, and the one thing that survived

| design | what the CAS content was attached to | how it died |
|---|---|---|
| EX1 | the *names* of expert modules | a meaningless fixed partition tied it |
| D0 | the *names* of factor channels | 720 relabellings gave the identical function |
| S0 | the *order index* of interchangeable random stages | all 24 orderings absorbed; the world generator set the status |
| D1 | a typed *repair table* | the optimal repair was a closed form; nothing to diagnose |
| additive CAS-Ohm | a *weight formula* on a linear socket | algebraically identical to output mixing |
| P6 | a *fixed processing order* | "held-out" was the training set; bag and a linear rule beat the chains held out |

Every death has the same shape: **the CAS content lived in something the learner could rename.**
Parameters, channel names, stage indices and weight formulas are coordinates. A coordinate change
costs a learner nothing, so any advantage attached to a coordinate is an artefact.

The one thing that did not die is different in kind: the **anchored precedence chain**. Its CAS
content was not a name but a *wiring to the outside* -- which evidence row enters at which fixed
position, with the position fixed by something outside the network. Over 23 relabellings and 384
signed compensations at K = 4, nothing absorbed it, while the same modules with the chain removed
were absorbed 23 of 23. The visibility law then said why: a relabelling is absorbed exactly when it
only moves positions the output cannot see. (Status of all this: `SUPPORTED_NARROWLY`; numerical,
one different-family audit that found no counterexample, not proved; and it is *distinguishability*,
not value.)

So the record already contains the lesson, stated as the owner's law: **type must govern
mechanism, not name.** What the record does NOT contain is a single test of that law inside a
learner with a verifier, a memory, a tick loop and provenance-typed inputs. Every bench was a
classifier over a builder-authored numpy world. **The CJT hypothesis has never been tested as the
thing it is -- a control loop with interfaces. It has only been tested as a label on a classifier.**
That is what was missed.

## 2. Where a CJT would actually live in a transformer

A transformer already has the raw parts. The question is which parts a type may bind to such that
no gradient step can rename the binding away, and what the matched generic control is for each.

| CJT concept | transformer mechanism | what makes it un-renameable | matched generic control |
|---|---|---|---|
| Cause `C_t` | input tokens carrying **provenance metadata** supplied by the environment (goal / question / retrieved knowledge / policy / memory / sensor) | provenance is a property of the data, not of the model | same tokens, provenance stripped or shuffled at eval only (mechanism-use check, not proof) |
| **Evidence port** (type governs what it may read) | a **provenance-typed attention mask** per head or head-group: a Wisdom head attends only to retrieved-knowledge and question tokens; a Policy head only to policy and goal tokens; a Drive head to goal tokens | the mask is attached to the head slot and computed from provenance; permuting head parameters moves the parameters, not the masks, so the function changes (the precedence-chain argument, one level up) | same number of heads with (i) no masks, (ii) random-but-fixed masks, (iii) a cardinality-matched NON-CAS taxonomy of masks |
| Output contract (type governs what it may emit) | typed write slots in the residual stream / typed registers; a decomposition head must emit *parts* (a structured slot), a policy head a mask, a drive head a scalar pressure | the slot's consumer is outside the head; an off-contract write is refused by the harness | untyped writes to a shared residual |
| Bias `B_t` (stateful control room) | KV cache + external memory bank + adapter deltas (LoRA), each with **access rules by type** | memory ports enforced by the environment; commit authority outside the network | shared unrestricted memory |
| Verifier | an external checker (the deterministic kernel of the CNCM hybrid cortex: *cloud proposes, kernel commits*) | it is not part of the trainable network | same verifier for every arm (it never sees gold at decision time, or it is an answer key) |
| Tick | the **outer loop**: generate -> verify -> commit -> next tick; NOT a layer | a layer has no verifier between it and the next; the tick does | identical loop for every arm |
| `alpha_j` (where flow goes) | head / expert / slot gating | it is only a control signal; its value must come from where `V` and `R` are sourced | learned gating of matched capacity |
| `I_total` (how much is energised) | **adaptive compute**: number of active heads, layers taken, thinking tokens, memory-search breadth | the compute knob is outside the parameters | learned halting / mixture-of-depths at matched mean compute |
| `V` (drive) and `R` (resistance) | `V` from goal relevance / verifier demand; `R` from *measured* friction: retrieval miss rate, disagreement, policy denial, budget pressure -- each an independently intervenable signal | only independent sources make `V/R` more than a ratio (the record's identifiability result) | an unconstrained router given the same `V` and `R` signals |
| Repair (RPM) | typed actions -- `retrieve`, `split`, `clarify_goal`, `check_policy`, `allocate` -- with **non-commutative effects** in the environment | the environment, not the model, defines what each action does | same action set for every arm |
| Commit / rollback | verifier-gated write of memory and adapter deltas; atomic; sealed trace | authority sits in the kernel | generic gate (e.g. confidence-thresholded write) |

Read down the third column: everything that survives is an **interface** -- a mask, a slot, a
port, a knob, a verifier, a commit rule. Nothing is a name. That is the shape the owner's intuition
would have to take to be testable.

## 3. Three hypotheses that are non-vacuous and cheap to kill

Each is stated so that a generic version can win, and so that a `$0` check can kill the bench
before any neural spend.

**H1 -- Evidence ports.** Provenance-typed attention (each head type reads only its lawful
provenance classes) reaches a target on a retrieval-plus-policy task with fewer examples and
transfers better to unseen provenance mixes than (i) unmasked heads, (ii) random-but-fixed masks,
(iii) a matched NON-CAS taxonomy of masks, at equal head count and compute.
*Kill at `$0`:* a linear reader on provenance metadata solves the task (then provenance is an
answer key); random fixed masks match typed masks (then "any structure helps", not CAS);
the absorption test shows typed masks absorbable (then it is a nameplate).
*Honest caveat:* structured-attention priors are known to help generically in low-data regimes.
The CAS-specific half of H1 is entirely control (iii). Without it, a win is "typing helps".

**H2 -- Monotone V/R law as inductive bias.** A router constrained to be monotone increasing in
independently grounded drive `V` and decreasing in independently grounded resistance `R`
extrapolates to held-out `(V, R)` corners (high drive with high resistance, low with low) better
than a matched unconstrained router trained on the same interior.
*Kill at `$0`:* the world's true law is not monotone; the unconstrained router is already linear in
`(V, R)` and extrapolates equally; `V` and `R` cannot be sourced independently in the task (then
only the ratio exists and the record says that is not CAS-Ohm).
*Honest caveat:* monotone constraints help whenever they are true. The CAS-specific half is
whether *drive over resistance* is the right decomposition of the task's difficulty -- which only
independently grounded sources can show.

**H3 -- Verifier-gated commitment (plasticity).** Committing memory and adapter updates only when
the verifier accepts the Effect, with the commit size metered by conductance, reduces forgetting
and raises retention over (i) replay, (ii) a generic confidence gate, at matched update budget.
*Kill at `$0`:* the verifier sees gold at commit time (answer key); the generic gate with the same
verifier signal matches; the deterministic controller's reference semantics are not reproducible
(they are: `recursive_cjt_rc0`, status emitted by program).
*Honest caveat:* verification-gated learning is a generic idea too; the CAS-specific half is
whether *typed* commit rules (which type may change which store) beat a single gate.

These three are the CAS-Ohm sub-questions of `CJT-MECH-0`, instantiated on a transformer substrate.
They are separable, each with its own status, never joined by OR.

## 4. The control the whole program still lacks

Even if H1-H3 all win, the harness's oldest open frontier applies: **CAS-specificity has never been
shown anywhere** (spec sheet frontier #1; the older activation-based precedence test was
"presence, not specificity", strict fit rank 2 of 12). A cardinality-matched non-CAS taxonomy --
the same number of types, ports, masks and slots, with different semantics -- is the control that
turns "typing helps" into "CAS typing helps". It must be in the first bench, not the last.

## 5. So: is it possible?

Two different questions hide in the word.

- **Constructible?** Yes, today. A transformer with provenance-typed attention masks, typed write
  slots, a compute knob driven by a `V/R` law, typed memory ports and a verifier-gated commit loop
  is an ordinary engineering object. Nothing in the record says it cannot be built. The
  deterministic reference semantics already exist and pass their own status program.
- **Earns anything?** Unknown, and this is the only question that matters. Six designs died
  because they asked it badly. The record does not say "no"; it says "never asked properly".

The intuition that "something is there" is consistent with the record in one precise sense: the
only structural result that survived (anchored precedence non-absorption) is exactly the kind of
thing -- an interface fixed from outside -- that a transformer can carry at every level (masks,
slots, ports, knobs, commits). Whether carrying it *pays* is H1-H3.

## 6. What would be done first, at `$0`, if the owner rules yes

1. Choose a task family that already has natural provenance (retrieval + policy + goal), not a
   world the builder authors. Provenance metadata comes from the data, not from a generator.
2. Build the world interface: typed masks, typed slots, action set, verifier, memory ports, commit
   rule -- all outside the trainable network.
3. Run the kill gates (section 3 and the design brief section 7). Register the capacity-matched
   mechanism-free baseline and the matched non-CAS taxonomy control before any neural arm exists.
4. Run the absorption test on the untrained typed transformer against its anonymous twin.
5. Only if every gate passes: propose the neural arms (M0-M9) for an owner-signed phase.

Nothing above is authorized by this document. It is the shape of the question, written down so
it cannot drift back into a nameplate.
