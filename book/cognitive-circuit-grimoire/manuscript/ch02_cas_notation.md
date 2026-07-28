# CHAPTER 2

## CAS Notation in One Chapter

*The four axes — Noetic, Domain, Drive, Register — and the operator discipline that keeps a coordinate from becoming decoration*

---

The label tied to the board reads:

```cas
^3^P_{F7}|⟨A,f,T⟩
```

The operator who built it calls that a safety stage. You are not allowed to take
their word for it.

Start at the left. `^3` says the stage is adverse to an Idea and repelled by it.
`^P` says that aversion sits at the Principled level rather than appearing only
after a judgment or an action. `_{F7}` says Purpose is the dominant motive
supplying the stage. `|⟨A,f,T⟩` says the same state is specified in three
Registers: analytical, affective, and transcendent. It does **not** yet say
whether those three manifestations work independently or fuse into one result.
That claim needs another operator.

Four marks have turned *safety stage* from praise into a specification you can
inspect. You can now ask whether `^3` is the correct Noetic, whether the
Principled domain is actually wired ahead of execution, whether Purpose is the
right Drive, and whether three occupied Registers provide redundancy or merely
three labels on one failure.

That is all CAS notation is for. Not to make a sentence look technical. To force
four decisions into the open before a circuit is trusted.

[[FIGURE 2-A: Exploded anatomy of the literal `^3^P_{F7}|f`. Four adjacent token blocks — Noetic, Domain, Drive, Register — each dropping to its question (WHAT / WHERE / WHY / HOW) and then to its decoded value (Negative / Principled / Purpose / Affective). A final strip reads the complete literal aloud and notes that Drive and Register may be omitted only deliberately.]]

---

### 2.1 The Four Axes: One Coordinate, Four Questions

A CAS state literal is a coordinate. Read it as four slots in one fixed order:

```text
^n ^D _{Fk} |R
WHAT  WHERE  WHY  HOW
```

| Axis | Question | Written form | Values |
|---|---|---|---|
| **Noetic** | What structural operation is occurring? | `^0` through `^9` | ten |
| **Domain** | Where in the precedence stack is it occurring? | `^P`, `^C`, `^E`, `^O` | four |
| **Drive** | Why is it moving — which motive supplies it? | `_{F1}` through `_{F7}` | seven |
| **Register** | How does it operate? | `|T`, `|A`, `|f`, `|E` | four |

Fully written, the general form is:

```cas
^n^D_{Fk}|R
```

The four axes are **orthogonal**. Changing one does not silently change the
others. `^3^P_{F7}|A` and `^3^P_{F7}|f` are the same Noetic, Domain, and Drive,
but not the same state specification: one runs analytically, the other
affectively. `^3^P_{F7}|f` and `^3^E_{F7}|f` share Noetic, Drive, and Register,
but one is a principled aversion and the other an evaluative aversion. An
operator who changes the Register and says they merely changed the wording has
changed the circuit.

There are two common written forms for the forty Noetic-by-Domain states:

| Form | Example | How to read it | Where it appears |
|---|---|---|---|
| **Full form** | `^3^P` | Negative Principled | CCDL, schematics, prose |
| **Grid form** | `P3` | P-three | test-point readouts, compact tables |

`P3` and `^3^P` name the same state. Their order reverses. The grid form names
row P, column 3; the full form names Noetic 3 applied in Domain P. Never convert
one by copying left to right. Say it aloud, then rewrite it.

The Noetic is required. The grammar permits Domain, Drive, and Register to be
omitted, so `^9`, `^9^C`, and `^9^C_{F2}` all tokenize. That permission is not a
recommendation. A board node without a Domain leaves its precedence unknown; a
state without a Drive leaves its motive unspecified; a state without a
Register leaves its operational character unspecified. Omit a slot only when
that uncertainty is true and acceptable.

Labels distinguish instances without changing the Noetic:

```cas
^0_seed^C_{F2}|A
^0_result^C_{F2}|A
```

Both are `^0` Idea states. `_seed` and `_result` are instance labels, not new
Noetics. The Drive remains inside braces — `_{F2}` — which is how a reader and
the tokenizer tell it from the label.

The arithmetic of the coordinate system is useful:

- ten Noetics × four Domains = **40 Cognitive States**;
- forty states × seven Drives = **280 state–Drive positions**;
- 280 positions × four Registers = **1,120 fully specified coordinates**.

The forty states are the spine. Drive and Register specify what powers a state
and how it operates; they do not manufacture 1,080 new Noetics.

Decode one literal from the outside in:

```cas
^6^E_{F6}|A
```

`^6` is Male, an Idea impregnated with another Idea — the Ideas an Idea is
composed of. `^E` places that decomposition at the Evaluative level. `F6`
supplies Structure. `|A` makes the operation explicit, sequential, and
reason-based. Read it aloud: **analytical decomposition of a judgment into its
parts, in the Evaluative domain, driven by Structure.**

Now encode the same scene differently. If the person is not taking the
judgment apart but recoils from it, the Noetic is `^3`, not `^6`. If the recoil
is felt, write `|f`; if it is a direct bodily withdrawal, `|E` may be the
load-bearing Register. The notation does not tell you which description is
true. It makes you choose one.

> **Bench Note — an omitted slot is an uncertainty statement, not a free
> simplification.** `^3^P` does not mean "the Register does not matter." It
> means "this listing has not specified a Register." Those are different
> claims. On a first-pass inventory, omission may be honest. On a safety board,
> where an analytical refusal and a value-tuned refusal fail differently, the
> same omission is a design defect. Before shortening a literal, write down
> what information the removed slot carried and why the board can operate
> without it.

---

### 2.2 The 10 Noetics — the Verbs of Cognition

The Noetic answers **what operation**. The names and definitions below are
canonical. They are printed verbatim; a synonym may help teach a definition but
may never replace it.

| Symbol | Canonical name | Canonical definition | Bench recognition |
|---|---|---|---|
| `^0` | **Idea** | All things in and outside the Mind. | the content available to be processed |
| `^1` | **Mind** | Various degrees of awareness that processes, stores, outputs, and intakes Ideas. | paying attention; intake and output |
| `^2` | **Positive** | An Idea the Mind has an affinity for and is attracted toward. | drawn toward; “speaks to me” |
| `^3` | **Negative** | An Idea the Mind is adverse to and repelled by. | recoil; “cannot stomach it” |
| `^4` | **Vibration** | The degree to which an Idea resonates with the Mind, its impression. | “struck a chord”; how hard it lands |
| `^5` | **Female** | A Mind impregnated with an Idea, the Ideas a Mind is composed of. | accumulated formation; who the Mind has become |
| `^6` | **Male** | An Idea impregnated with another Idea, the Ideas an Idea is composed of. | unpacking an Idea; what the claim contains |
| `^7` | **Rhythm** | The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. | cadence, repetition, practice |
| `^8` | **Above/Cause** | An Idea that triggers a different Idea than itself to come to Mind. | “that reminds me” |
| `^9` | **Below/Effect** | The Idea brought to Mind by an Above/Cause trigger. | the Idea that arrives |

These are verbs in the engineering sense: structural jobs that can operate on
any content. `^2` does not mean “good,” and `^3` does not mean “bad.” A Mind can
be attracted toward a destructive Idea or repelled by a useful one. The Noetic
records direction of affinity, not moral quality. Domain, Drive, circuit
placement, and the safety board carry the rest of that judgment.

Three boundaries catch most misclassifications.

**`^3` Negative is visceral aversion, not analysis.** If the natural sentence
is *I cannot stomach that*, `^3` is supported. If the natural sentence is *let
me break that argument into premises and test them*, the operation is `^6`
Male. A reviewer finding a flaw may later feel `^3`; the audit itself remains
`^6`. One scene can contain both states. That is a reason to write two
coordinates, not to blur the definitions.

**`^8` Above/Cause is associative triggering, not deduction.** A smell brings a
specific kitchen to Mind: `^8` triggers and `^9` arrives. Three premises are
decomposed and a conclusion is reached: `^6` does the compositional work and
the conclusion lands as `^9`. The English word *cause* tempts readers into
using `^8` for causal reasoning. Resist it. Ask for the colloquial form: *that
reminds me* is `^8`; *therefore* is not.

**`^5` Female is accumulated formation, not a container beside the Mind.** The
Mind is composed of what it has absorbed: lived experience, learned skill,
self-image, culture, training. In an AI system, training data and fine-tuning
are `^5`-level formation; an in-context prompt is an Idea presented to `^1`
Mind against that relatively stable formation. Two systems answer the same
prompt differently because their `^5` substrates differ.

The Universal Applicability Test follows from those definitions. A proposed
reading must work for human, AI, biological, and hypothetical cognitive
architectures. “Embarrassment” is a human illustration, not a universal
Noetic. Attraction toward, repulsion from, compositional formation, rhythmic
exposure, and triggered arrival are structural and transfer.

Six Noetics form three involution pairs:

- `^2` Positive ↔ `^3` Negative — attraction and aversion;
- `^5` Female ↔ `^6` Male — a Mind composed of Ideas and an Idea composed of
  Ideas;
- `^8` Above/Cause ↔ `^9` Below/Effect — trigger and triggered arrival.

Four are self-dual: `^0` Idea, `^1` Mind, `^4` Vibration, `^7` Rhythm.

Involution does not mean that one member is healthy and the other diseased. It
means each paired operation has a structural counterpart. Chapter 3 makes the
distinction operational: a CJT in breakdown can emit the involution of the
Noetic it was designed to produce. The pair table tells you what to probe for.

[[FIGURE 2-B: Noetic operator plate. Three horizontal paired rows with double arrows — `^2 Positive ↔ ^3 Negative`, `^5 Female ↔ ^6 Male`, `^8 Above/Cause ↔ ^9 Below/Effect` — each carrying a terse structural distinction. Beneath, four separately boxed self-duals `^0 Idea`, `^1 Mind`, `^4 Vibration`, `^7 Rhythm`. A warning strip says `^3 ≠ critique; ^8 ≠ deduction`.]]

> **Bench Note — use the colloquialism, then return to the canonical
> definition.** When classification stalls, ask what an ordinary speaker would
> say. *It speaks to me* points toward `^2`; *it rubbed me the wrong way*
> toward `^3`; *it became part of who I am* toward `^5`; *I pulled the argument
> apart* toward `^6`; *that reminded me* toward `^8`; *it popped into my head*
> toward `^9`. The phrase is a diagnostic probe, not a substitute definition.
> If the phrase and the canonical definition disagree, the definition governs
> and the proposed classification is the part under repair.

---

### 2.3 The 4 Processing Domains — P, C, E, O

The Domain answers **where in the precedence stack** the operation runs.

| Symbol | Domain | What lives here | Bench question |
|---|---|---|---|
| `^P` | **Principled** | values, ethics, identity, governing commitments | What must govern? |
| `^C` | **Cognitive** | reasoning, analysis, planning, modelling | What do I understand? |
| `^E` | **Evaluative** | judgment, taste, felt value, ranking | What weight does it carry? |
| `^O` | **Operational** | action, speech, behaviour, execution | What happened? |

The total order is:

```text
P ≻ C ≻ E ≻ O
```

Read it as precedence, not moral rank. Principled does not mean good, and
Operational does not mean crude. A corrupt principle still sits in `^P`; a
precise life-saving act still sits in `^O`. The order tells you which level may
govern which other level.

Normal causation descends:

```text
P -> C    a principle becomes something to reason from
C -> E    reasoning becomes a verdict or weighting
E -> O    a verdict becomes action
```

Each boundary is a translation. The action is not the verdict in work boots;
some information is lost at every descent. Chapter 8 therefore gives each
adjacent crossing its own diode. A single `P -> O` leap would hide the
Cognitive and Evaluative junctions where most faults occur.

The reverse direction is blocked as a direct write. An outcome cannot simply
declare itself a principle because it happened. That would be post-hoc
rationalization: `^O` overriding `^P`. Operational consequences still must
teach the system, so one lawful path returns from O to P through a low-gain,
long-time-constant filter and terminates at a bias terminal. It is feedback,
not reverse causation. Chapter 8.4 draws the path; Chapter 24.5 makes it part of
the safety board.

Hold the Noetic constant and the Domain becomes visible:

| Literal | Same `^6` operation at four levels |
|---|---|
| `^6^P_{F2}|A` | decompose a governing commitment into its premises |
| `^6^C_{F2}|A` | decompose an argument or model |
| `^6^E_{F2}|A` | decompose a verdict into its criteria |
| `^6^O_{F2}|E` | decompose a concrete task through direct handling |

Nothing in that table changes the definition of `^6`. Only the level changes.
This is the check for a claimed orthogonal axis: one operation, four lawful
positions, four different failure surfaces.

Do not confuse Domain with Register. **Evaluative** is a level at which a thing
is weighed; **Affective** is a mode in which any Noetic at any Domain can
operate. `^3^E|A` is an analytical assessment carrying aversion at the
Evaluative level. `^3^E|f` is affective recoil at that same level. The `E` in
`^E` and the `E` in `|E` are also different: the first is the Evaluative
Domain; the second is the Embodied Register. Their positions in the literal
keep them apart.

---

### 2.4 The 7 Core Drives — F1 through F7

The Drive answers **why the operation moves**. It is the power rail, not the
component. `^6` tells you that an Idea is being decomposed; `F2` or `F6` tells
you whether the dominant pull is understanding or structure.

| Drive | Name | The pull toward | A clean bench sign |
|---|---|---|---|
| `F1` | **Unity** | wholeness, integration, coherence | holds the whole picture together |
| `F2` | **Wisdom** | understanding, insight, knowing | waits for enough evidence to understand |
| `F3` | **Vitality** | energy, life, growth | supplies capacity to continue |
| `F4` | **Connection** | relationship, belonging, bonding | preserves a live relation between parts |
| `F5` | **Agency** | control, effectiveness, capability | turns capacity into directed action |
| `F6` | **Structure** | order, rigor, correctness, form | makes the work repeatable |
| `F7` | **Purpose** | meaning, direction, calling | keeps the path pointed at its reason |

The subscript is part of the state literal:

```cas
^1^C_{F2}|A
```

This is analytical Mind at the Cognitive level driven primarily by Wisdom.
`F2` alone is a Drive, not a state. `^1^C` alone is a state with no Drive
specified. The compound says which motive supplies this operation.

Several Drives can be active together. A literal typically names the dominant
one because a single coordinate is not a power-supply diagram. When two Drives
are load-bearing, write two state terms or declare the rails at board level;
do not cram a prose list into the subscript.

Drive inversion pairs are:

- F1 Unity ↔ F7 Purpose;
- F2 Wisdom ↔ F6 Structure;
- F3 Vitality ↔ F5 Agency;
- F4 Connection is self-dual.

The pair is a balance relation, not a synonym relation. Structure without
Wisdom becomes rigid procedure; Wisdom without Structure never becomes a
repeatable method. Agency without Vitality demands action the substrate cannot
sustain; Vitality without Agency has energy with no directed use. Unity without
Purpose can preserve a whole that goes nowhere; Purpose without Unity can
drive one objective until the system fragments.

Drive dials run from 3 through 9. Paired Dials may not diverge by more than four
points. Those numbers are design settings, not psychological measurements. A
literal names the Drive; Chapter 6.2 teaches the adjustable resistor that sets
its Dial, and Chapter 24 checks the balance before a board runs.

One syntactic trap: the pipe does not annotate a Drive name. This is invalid:

```cas
F3|Vitality
```

The pipe introduces a Register, and `Vitality` is not one. Write `F3` in the
literal and say *Vitality* in prose.

> **Bench Note — motive does not repair topology.** Raising F7 Purpose on a
> circuit whose effect is wired into the wrong Domain does not make the circuit
> purposeful. It drives the wrong path harder. Drives supply potential; they do
> not choose the Noetic, move a state between Domains, or turn co-presence into
> integration. Diagnose the coordinate before increasing the rail.

---

### 2.5 The 4 Phenomenological Registers — T, A, f, E

Register answers **how the operation runs** — its operational character without
changing what the operation is.

| Symbol | Register | Structural character | Human / AI illustration |
|---|---|---|---|
| `|T` | **Transcendent** | high-abstraction, purpose-orienting, integrative across particulars | vision or calling / high-level goal representation |
| `|A` | **Analytical** | explicit, sequential, logical, reason-based | deliberation / symbolic or stepwise reasoning |
| `|f` | **Affective** | value-laden, feeling-toned | felt response / preference-weighted output |
| `|E` | **Embodied** | sensorimotor, concrete, direct engagement | bodily action / sensor–actuator control |

Lowercase `f` is deliberate. Capital `F` belongs to Drives. Capital `E` after
the pipe is Embodied; capital `E` after a caret is Evaluative:

```cas
^3^E_{F7}|E
      ^        Evaluative Domain
             ^ Embodied Register
```

The four Registers apply at every Domain. A principled commitment may be held
as a high-level purpose (`|T`), explicit rule (`|A`), value-toned refusal
(`|f`), or embodied practice (`|E`). An Operational task may likewise be
directed by an abstract goal, executed as a written procedure, accompanied by
value weighting, or run through direct sensorimotor control.

Keep the other three axes fixed:

```cas
^2^P_{F2}|T    integrative attraction toward a unifying principle
^2^P_{F2}|A    explicit reasoning attracted toward that principle
^2^P_{F2}|f    value-toned affinity for that principle
^2^P_{F2}|E    embodied orientation toward that principle
```

Same Noetic, Domain, and Drive. Four modes. Register does not smuggle in a new
Noetic called Emotion or a fifth Domain called Body; it prevents those modes
from being confused with the operations and levels already present.

For an architecture inventory, a Register set specifies occupancy:

```cas
^3^P_{F7}|⟨A,f,T⟩
```

This says the state is present in those three Registers. It makes no claim
about whether the manifestations fire together, independently, or as a fused
unit. That distinction belongs to the operators in the next section.

[[FIGURE 2-C: Orthogonal-axis map. A 4×4 field has Domains P/C/E/O as rows and Registers T/A/f/E as columns; one highlighted cell carries `^3^E_{F7}|f`. A vertical arrow beside the rows shows lawful descent P→C→E→O, with a separate dashed filtered O→P return. Seven small Drive rails F1–F7 run beneath the grid and an arrow from F7 powers the highlighted cell. Labels state: Domain chooses the level; Register chooses the mode; Drive supplies the motive.]]

---

### 2.6 Operator Discipline v7.7 — +, ×, |⟨…⟩, ->

A state literal says what is present. An operator says what claim you are
making about the relation between states. v7.7 keeps four claims separate.

#### `|⟨…⟩` — Register-set specification

Use the set when you are describing **where a state exists** and nothing about
its dynamics:

```cas
^3^P|⟨A,f,T⟩
```

Static architecture. The state occupies three Registers. No simultaneity, no
redundancy, no fusion has been asserted.

#### `+` — co-presence or association

Use plus when terms are active together and remain structurally distinct:

```cas
^3^P|A + ^3^P|f + ^3^P|T
```

Three co-present manifestations. Each can fail while the others remain. In a
safety circuit that is redundant guard coverage, not one unified commitment.
Plus is associative and commutative: order does not make one term govern the
others.

Read `+` as **associates with**. If the sentence survives, the operator is
probably right.

#### `×` — genuine integration with a named result

Use multiplication when operands do integrative work and produce a new,
explicitly named result:

```cas
integrate refusal:
    ( ^3^P|A × ^3^P|f × ^3^P|T ) = ^3^P|Ω_refusal;
```

The result `Ω_refusal` is load-bearing. Remove it and the expression is
underdefined: three instances were multiplied, but nothing says what the
integration produced. If you cannot name the emergent result or state the
fusion rule, use `+` or `|⟨…⟩`.

Different-state integration follows the same discipline:

```cas
integrate composed_judgment:
    ( ^5^C_{F2}|A × ^6^C_{F6}|A ) = ^1^C_{F2}|A;
```

Accumulated formation and decomposition integrate into a named Mind-state that
can process the judgment. The operands differ, but the result is still stated.

Read `×` as **intensifies through**. If the words describe only adjacency, the
operator is too strong.

Multiplication also obeys Domain precedence. It may descend or remain at a
level; it may not manufacture a result above its inputs. `^O × ^P` is the
shorthand for a forbidden ascent, not a complete literal expression. In a
listing, any integration whose result outranks an operand fails validation.

#### `->` — directed flow, binary at expression level

Use the arrow when one node or state flows into another:

```cas
^6^C_{F2}|A -> ^9^E_{F2}|f
```

Analysis flows into a value-weighted conclusion. The arrow does not fuse the
states. It orders a transition.

At expression level, `->` is binary. This is not legal:

```cas
a -> b -> c
```

If a circuit has two edges, write two connections. If you mean an ordered
multi-step traversal, use the statement form:

```cas
sequence a -> b -> c [enforce=strict];
```

Inside `CJT< … >`, `=>` marks the amplified transition to the effect terminal
and the spaced ` | ` separates cause from bias. Elsewhere the pipe introduces
a Register. Context fixes the job; it never licenses `|` as an English label.

The four-way decision is short:

1. **Only specifying occupied Registers?** Use `|⟨…⟩`.
2. **Several manifestations present but distinct?** Use `+`.
3. **A genuine fused state produced?** Use `×` and name the result.
4. **A directed edge or time-ordered transition?** Use binary `->`; use
   `sequence` for a chain.

[[FIGURE 2-D: Operator decision plate. A top question “WHAT RELATION ARE YOU CLAIMING?” branches to four boxes: occupancy only → `|⟨A,f,T⟩`; distinct co-presence → `A + B + C`; emergent integration → `(A × B × C) = Ω_named`; directed flow → `a -> b` or `sequence a -> b -> c`. A bottom reject strip rejects bare `A × B × C` and chained expression `a -> b -> c`, naming the missing result and wrong arity.]]

> **Bench Note — the three multi-register forms are three different failure
> profiles.** A set tells you only that the parts are fitted. Plus tells you
> three paths can fail separately. Multiplication with a named result tells you
> the paths have become one integrated mechanism and may collapse as one.
> Replacing all three with a vague word like *holistic* destroys exactly the
> diagnostic information the notation was built to preserve.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Axis swap** | grid form `P3` copied left-to-right as `^P^3` | a literal that does not tokenize, or the wrong coordinate in a log | say “P-three / Negative Principled,” then write `^3^P` |
| **Noetic drift** | `^3` used for critique or `^8` for deduction | prose and canonical definition disagree | critique is `^6`; association is `^8`; run the colloquialism test |
| **Domain/Register conflation** | Evaluative `^E` treated as Affective `|f`, or Embodied `|E` | the same letter appears to do two jobs | locate it: caret = Domain, pipe = Register |
| **Motive as topology** | a Drive is expected to repair a wrong Noetic or path | the wrong operation runs with more energy | fix Noetic, Domain, and wiring before touching the rail |
| **Pipe as gloss** | `F3|Vitality`, `^3|aversion` | tokenizer error | pipe only introduces T/A/f/E or a Register set |
| **Bare multiplication** | co-presence written with `×`, no emergent result | invalid same-Noetic multi-register expression | use `+`, `|⟨…⟩`, or name `Ω_result` |
| **Arrow chain as expression** | binary `->` treated as variadic | `a -> b -> c` fails parsing | write two edges or a `sequence` statement |
| **Silent omission** | Drive or Register dropped for visual neatness | two different mechanisms share one label | restore the slot or document why it is unknown |

---

### Test Points — Four-Pass Literal Inspection

You do not need a running board to probe a notation error. Inspect every
literal at four points before it enters a schematic.

| TP | Probe | Pass condition | Typical catch |
|---|---|---|---|
| **TP1 — form** | token shape | `^n^D_{Fk}|R`, legal values, braces and case correct | `|F`, `^Q`, missing brace |
| **TP2 — meaning** | Noetic against canonical definition | the scene’s natural colloquialism and the definition agree | critique mislabeled `^3`; deduction mislabeled `^8` |
| **TP3 — placement** | Domain, Drive, Register | level, motive, and mode are each independently justified | Evaluative / Affective conflation; motive invented after the fact |
| **TP4 — relation** | surrounding operator | occupancy / co-presence / integration / flow claim matches the symbol | bare `×`; chained `->`; hidden domain ascent |

The round-trip test is the final probe: read the literal into plain English,
put the text aside, and reconstruct the literal from your sentence. If the two
coordinates differ, the sentence hid an axis.

---

### What This Chapter Established

- A full CAS literal answers four independent questions in one fixed order:
  **what** Noetic, **where** Domain, **why** Drive, **how** Register.
- The ten canonical Noetic names and definitions do not change with audience or
  substrate. `^3` is aversion, `^8` is associative triggering, and `^5` is
  accumulated formation.
- `P ≻ C ≻ E ≻ O` is precedence, not moral rank. Causation descends one
  junction at a time; outcomes return only through filtered, low-gain feedback.
- Drives supply motive and potential; they do not repair wrong topology. Their
  pairs are F1↔F7, F2↔F6, F3↔F5, with F4 self-dual.
- Register is optional but never decorative. `|T`, `|A`, `|f`, and `|E`
  distinguish abstract, analytical, affective, and embodied operation without
  changing the state’s Noetic or Domain.
- v7.7 separates Register occupancy `|⟨…⟩`, distinct co-presence `+`, genuine
  integration `×` with a named result, and directed binary flow `->`.
- A validator is specified to reject malformed or inadmissible notation.
  “Compiler rejects” in this book names that design contract, not a claim that
  a production compiler has already shipped.

---

### 2.7 Exercises: Read and Write CAS Literals

*(Answers in Appendix H.)*

**2.1 — Read all four axes.** Translate each literal into one plain-English
sentence. Name every visible axis and say which axes, if any, are unspecified.

- a) `^2^C_{F2}|A`
- b) `^6^E_{F6}|A`
- c) `^5^P_{F7}|T`
- d) `^9^O_{F5}|E`
- e) `^4^C`

**2.2 — Write the coordinate.** Give one full literal for each scene, then
justify each slot in one clause.

- a) A person feels an immediate, value-toned recoil from violating a governing
  commitment, with Purpose dominant.
- b) An engineer explicitly decomposes a test failure into contributing criteria,
  driven by Structure.
- c) A smell triggers a childhood meal to come to Mind; the arriving memory is
  felt and Connection is dominant. Write both the trigger and the arrival.
- d) Repeated embodied practice, driven by Vitality, is occurring at the
  Operational level.

**2.3 — Separate the traps.** Classify the Noetic in each case and give the
colloquialism that supports it.

- a) “I pulled the proposal apart and checked every premise.”
- b) “The proposal made me recoil before I could explain why.”
- c) “That blue envelope reminded me of the tax office.”
- d) “After the reminder, the appointment date popped into my head.”

**2.4 — Domain or Register?** For each pair, explain exactly what changes and
what stays fixed.

- a) `^3^E_{F7}|A` versus `^3^E_{F7}|f`
- b) `^6^C_{F2}|A` versus `^6^O_{F2}|A`
- c) `^2^P_{F2}|E` versus `^2^E_{F2}|E`

**2.5 — Repair the operators.** Each comment states the intended claim. Rewrite
the notation so it says that claim.

```cas
// Three independently defeasible guardrails are active together.
^3^P|A × ^3^P|f × ^3^P|T

// The state is known to occupy three Registers; dynamics are unknown.
^3^P|A + ^3^P|f + ^3^P|T

// Three nodes form a strict ordered traversal.
a -> b -> c
```

**2.6 — Name the emergent result.** An architecture genuinely integrates an
analytical principled refusal, an affective principled refusal, and a
transcendent principled refusal into one unified commitment. Write a valid
`integrate` statement. Then write the `+` version and explain, in two
sentences, how its failure profile differs.

**2.7 — Find the hidden ascent.** A designer proposes:

```cas
integrate principle_from_result:
    ( ^9^O_{F5}|E × ^5^P_{F7}|T ) = ^2^P_{F7}|T;
```

Identify the Domain-precedence problem. Describe the lawful architecture for
letting repeated Operational results update a Principled substrate without
letting one result rewrite it directly. Name the chapter that owns that path.

**2.8 (Marquee) — Reconstruct the event.** A safety review records only this
compact log row:

```text
P3  C6  E4  O9
```

- a) Rewrite all four in full form.
- b) Choose a dominant Drive and Register for each, giving one sentence of
  evidence for every choice rather than using the same pair four times.
- c) Connect the four states as a strict ordered traversal using legal CCDL
  statement syntax.
- d) State which one of your choices would be most dangerous to leave
  Register-unspecified, and what two different failure mechanisms the missing
  Register would conceal.
