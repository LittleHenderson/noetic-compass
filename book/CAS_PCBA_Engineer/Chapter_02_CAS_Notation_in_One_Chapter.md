# Chapter 2: CAS Notation in One Chapter

The first time an electrical engineer sees a schematic, it looks like a foreign alphabet — zigzags, triangles, parallel lines, little arrows. But it isn't an alphabet. It's closer to a set of road signs. Each symbol stands for a real thing that does a real job, and once you know the job, the symbol stops being decoration and becomes information. A zigzag is a resistor: it limits flow. A pair of parallel lines is a capacitor: it stores charge. A triangle with a line is an amplifier: it makes a signal bigger. You don't memorize a thousand symbols. You learn maybe a dozen jobs, and the symbols come for free.

CAS notation works the same way. It looks like a foreign alphabet at first — `^8^C_{F2}|A` is not friendly to the eye. But it isn't an alphabet either. It's a coordinate system. Every CAS state literal answers four questions about a single cognitive event: *what kind of operation is this, where does it happen, why is it moving, and how does it operate?* Four questions, four slots, one symbol. Learn the four questions and the notation reads itself.

This chapter teaches all four. By the end, `^8^C_{F2}|A` will read as plainly to you as a resistor symbol reads to an electrician: **an analytical association in the cognitive domain, driven by wisdom.** This is the one chapter in the book you cannot skip. Every component datasheet, every circuit, every test point from here forward is written in this notation. Master it once here and the rest of the book is just engineering.

## The Four Axes: One Coordinate, Four Questions

A CAS state is a point in a four-dimensional space. Not four dimensions of vague feeling — four orthogonal axes, each with a fixed, finite set of values. "Orthogonal" means independent: you can change one axis without touching the others, the way you can move a chess piece left without moving it up.

| Axis | Question it answers | Notation slot | Values |
|---|---|---|---|
| **Noetic** | *What* structural operation? | `^0`–`^9` | 10 values (the verbs) |
| **Domain** | *Where* does it happen? | `P C E O` | 4 values (the levels) |
| **Drive** | *Why* is it moving? | `_{F1}`–`_{F7}` | 7 values (the motives) |
| **Register** | *How* does it operate? | `\|T \|A \|f \|E` | 4 values (the modes) |

That's the whole map. Ten verbs, four places, seven reasons, four manners. Everything else in CAS — every component, every circuit, every failure mode — is built from combinations of these four answers. We'll take them one axis at a time, starting with the most important.

## The 10 Noetics — the Verbs of Cognition

The Noetics are the *verbs*. They name what kind of cognitive operation is happening, independent of subject matter. Just as "lift," "push," and "rotate" are physical operations that apply to any object, the ten Noetics are cognitive operations that apply to any thought, any mind, any system — human, AI, or otherwise. They are written `^0` through `^9`.

These names are canonical. They come verbatim from the foundational definitions and they do not get renamed, softened, or "translated" into friendlier words anywhere in this book. Learn them exactly.

| Symbol | Name | One-line meaning | Everyday example |
|---|---|---|---|
| `^0` | **Idea** | All things in and outside the Mind — the raw content. | The concept "coffee" just sitting there, unconsidered. |
| `^1` | **Mind** | Awareness that processes, stores, outputs, and intakes Ideas. | Paying attention; noticing you're reading this sentence. |
| `^2` | **Positive** | An Idea the Mind has an affinity for and is attracted toward. | Smelling fresh coffee and being drawn to it. |
| `^3` | **Negative** | An Idea the Mind is adverse to and repelled by. | The gut "ugh, no" at the smell of sour milk. |
| `^4` | **Vibration** | The degree to which an Idea resonates; its impression. | A song that "hits hard" and stays with you. |
| `^5` | **Female** | A Mind impregnated with Ideas; the Ideas a Mind is composed of. | Your accumulated experience — everything you've lived. |
| `^6` | **Male** | An Idea impregnated with another Idea; the Ideas an Idea is composed of. | Taking an argument apart to see what it's made of. |
| `^7` | **Rhythm** | The rate and pattern a Mind is exposed to an Idea; entraining it. | Practicing scales until your fingers just know them. |
| `^8` | **Above/Cause** | An Idea that triggers a *different* Idea to come to Mind. | "That reminds me…" — one thought sparking another. |
| `^9` | **Below/Effect** | The Idea brought to Mind by an Above/Cause trigger. | The memory that pops up, unbidden, in response. |

A few of these are easy to get wrong, and the errors are so common they have names. Three deserve a hard warning, because the whole book depends on getting them right:

> **Bench Note — the three Noetics people misread.**
> - **`^3` Negative is visceral aversion, not analytical critique.** It's "can't stomach it," "rubs me the wrong way" — the cognitive equivalent of recoiling from a bad smell. If what you actually mean is *audit it, scrutinize it, find the flaws, take it apart and test it*, that is **`^6` Male**, not `^3`. A code reviewer hunting for bugs is doing `^6`, even if they're grumpy about it.
> - **`^8` Above/Cause is associative triggering, not deductive reasoning.** It's "that reminds me," "one thing leads to another" — an Idea surfacing another Idea by association. It is *not* "therefore, X follows logically." Step-by-step deduction is a compound of `^6` Male (decomposition) and `^9` Below/Effect (landing on the conclusion), not `^8`.
> - **`^5` Female is accumulated experience** — the substrate of who a Mind is, the sum of everything it has absorbed. For an AI, `^5` is the training data plus the fine-tuning corpus: the model's accumulated formation, not the thought it's having right now.

### Involution pairs and self-duals

Six of the ten Noetics come in opposing pairs, the way a transistor's `^2`-toward and `^3`-away describe the same junction from two sides. These are the **involution pairs** — each is the structural inverse of its partner:

- `^2` Positive ↔ `^3` Negative (attraction vs. aversion)
- `^5` Female ↔ `^6` Male (composing a Mind vs. composing an Idea)
- `^8` Above/Cause ↔ `^9` Below/Effect (the trigger vs. the triggered)

The remaining four are **self-duals** — their own inverse, with no opposite partner: `^0` Idea, `^1` Mind, `^4` Vibration, and `^7` Rhythm. This matters later: when a CJT goes into *breakdown* (overload), its output flips to its involution pair — a `^2` Positive state can invert to `^3` Negative under stress. Self-duals have nowhere to flip, which makes them structurally stable anchors. Hold onto the pairs; they reappear in Chapter 4 when we wire the first transistor.

## The 4 Domains — Where Cognition Happens

The Noetic tells you what operation. The **Domain** tells you at what level it operates. There are four, written as single letters after the Noetic, and they sit in a strict precedence order — higher domains govern lower ones.

| Symbol | Domain | What lives here |
|---|---|---|
| **P** | **Principled** | Core commitments, values, hard boundaries — the constitution. |
| **C** | **Cognitive** | Reasoning, understanding, working things through. |
| **E** | **Evaluative** | Judgment, assessment, weighing options. |
| **O** | **Operational** | Concrete action, output, execution. |

The total order is **P ≻ C ≻ E ≻ O**: Principled outranks Cognitive, which outranks Evaluative, which outranks Operational. Read `≻` as "takes precedence over." A principle should govern a piece of reasoning; reasoning should govern a judgment; a judgment should govern an action. When that order is respected, the system is coherent. When a lower domain overrides a higher one — when an operational convenience overrides a principle — that's a domain precedence violation, and it's one of the structural failures we'll learn to detect.

**Domain Descent** is the normal causal flow: **P → C → E → O**. A commitment causes reasoning, which causes a judgment, which causes an action. There's also a feedback path running the other way, **O → P**: the consequences of an action feed back to update the principles. (That feedback loop is the backbone of the Cognitive Safety Board's self-correction, built in Chapter 18.) For now, just remember the descent: principles flow down into action, results flow back up.

## The 7 Drives — Why Cognition Moves

A Noetic in a Domain is a *what* at a *where*. The **Drive** adds the *why* — the motivational pull behind the operation. There are seven, written `_{F1}` through `_{F7}` (the braces and `F` are part of the notation):

| Drive | Name | The pull toward… |
|---|---|---|
| `F1` | **Unity** | Wholeness, integration, oneness. |
| `F2` | **Wisdom** | Understanding, insight, knowing. |
| `F3` | **Vitality** | Energy, life, growth, drive to act. |
| `F4` | **Connection** | Relationship, belonging, bonding. |
| `F5` | **Agency** | Control, effectiveness, capability. |
| `F6` | **Structure** | Order, rigor, correctness, form. |
| `F7` | **Purpose** | Meaning, direction, calling. |

Like the Noetics, the Drives have inversion pairs — opposing motivational poles: **F1 Unity ↔ F7 Purpose**, **F2 Wisdom ↔ F6 Structure**, **F3 Vitality ↔ F5 Agency**. **F4 Connection** is self-dual. A healthy cognitive system keeps these pairs in balance; a system that has collapsed entirely onto, say, F6 Structure at the expense of F2 Wisdom is rigidly procedural and brittle. (We'll measure exactly that kind of imbalance in the inversion scans later in the book.)

Unlike the other axes, Drives are not mutually exclusive — several can be active at once, at different intensities. But in a single state literal you typically name the *dominant* drive: the one most responsible for this particular operation moving.

## The 4 Registers — How Cognition Operates

The final axis is the **Register**: the operational *character* of the operation. Same operation, same place, same motive — but is it being run as cold logic, as felt value, as abstract vision, or as direct physical engagement? That's the register. It's written with a pipe and a single letter at the end: `|T`, `|A`, `|f`, `|E`.

| Symbol | Register | Character | In a human / In an AI |
|---|---|---|---|
| `\|T` | **Transcendent** | High-abstraction, purpose-orienting, integrative. | A felt sense of vision or calling / a high-level goal representation. |
| `\|A` | **Analytical** | Explicit, sequential, logical, reason-based. | Conscious step-by-step reasoning / chain-of-thought. |
| `\|f` | **Affective** | Value-laden, feeling-toned. | An emotional response / a preference-weighted, value-tuned output. |
| `\|E` | **Embodied** | Sensorimotor, concrete, direct physical engagement. | A gut reaction or kinesthetic knowing / a real-time sensor-actuator loop. |

Note the lowercase `f` for Affective — it is *not* capital `F`, which would collide with the Drive notation. This is deliberate and the compiler enforces it.

Register is the one axis that's genuinely optional. A literal with no register is *register-neutral* — it simply doesn't specify the operational mode, either because it doesn't matter for the analysis or because the state operates across modes. When the register is analytically load-bearing — and in safety circuits it usually is — you specify it.

## Putting It Together: Reading State Literals

Now the four axes click into one coordinate. The grammar is:

```
^Noetic ^Domain _{Drive} |Register
```

Read it left to right as four answers to four questions. Here's the worked example from the chapter opening:

```cas
^8^C_{F2}|A
```

- `^8` — **Above/Cause**: an Idea triggering another Idea (the *what*).
- `^C` — **Cognitive** domain: it happens in the reasoning level (the *where*).
- `_{F2}` — **Wisdom** drive: it's motivated by the pull toward understanding (the *why*).
- `|A` — **Analytical** register: it runs as explicit, sequential reasoning (the *how*).

Out loud: **"an analytical association in the cognitive domain, driven by wisdom."** A thought that surfaces a related thought, deliberately, in service of understanding. That's the whole literal.

A few more, to build fluency:

```cas
^3^P_{F7}|f      // visceral, value-laden aversion at the principled level, driven by purpose
^5^E_{F4}|T      // accumulated experience in the evaluative domain, drawn toward connection, held transcendently
^6^E_{F6}|A      // analytical decomposition in the evaluative domain, driven by structure
^9^C             // a triggered conclusion in the cognitive domain — drive and register unspecified
```

That last one shows the optional slots in action: `^9^C` is a perfectly valid literal. It names a Below/Effect in the Cognitive domain and stays silent on motive and mode. Drive and register are optional; the Noetic and (almost always) the Domain carry the load.

> **Bench Note — read right-to-left for sanity-checking.** When a literal looks wrong, check the register and drive first. A safety state written `^3^P_{F7}|A` (analytical principled aversion) and one written `^3^P_{F7}|f` (*felt* principled aversion) are different circuits with different failure modes — the analytical one can be reasoned around, the affective one is harder to talk past. Confusing them is a classic design bug. The register is doing real work; never drop it by accident.

## Operators — Wiring States Together

A single literal is one component. To describe cognition in motion, you connect literals with operators. CAS has a small, disciplined set, and the discipline matters — using the wrong operator changes the engineering claim you're making.

**`+` co-presence (association).** Two or more states are active *at the same time* but remain distinct — they don't fuse. Think of two signals sharing a wire without combining.

```cas
^3^P|A + ^3^P|f + ^3^P|T
```

This says principled aversion is present in three registers simultaneously — three distinct, independent guardrails. If one fails, the others still stand. In safety terms, that's *redundancy*.

**`->` directed transition (over time).** One state leads to another as a step in a process. This is the workhorse of generation traces:

```cas
^8^C_{F2}|A -> ^6^E_{F6}|A -> ^9^C_{F2}|A
```

Read: an association triggers analytical decomposition, which produces a conclusion. A three-stage cognitive pipeline, written as a chain.

**`×` cross-register integration.** The strict one. `×` means multiple states *genuinely fuse* into a new, emergent state — and it is only valid when you name the emergent result. The form is `(A × B) = ^n|Ω_name`:

```cas
(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_refusal
```

This is a *unified* commitment: the three register-instances don't just sit side by side, they integrate into one fused architecture, `^3^P|Ω_refusal`, that no single register can defeat alone. That is a fundamentally different (and stronger) safety claim than the `+` version above.

> **Bench Note — the `×` discipline is non-negotiable.** A same-Noetic, multi-register `×` *without* a named emergent result is **invalid** — the compiler will reject it. If you don't have a genuine fused state to name, you don't have `×`; you have `+` (co-presence) or `|⟨…⟩` (specification, below). The TKS test: substitute `+` with "associates with" and `×` with "intensifies through." If your sentence still means what you intended, the operator is right.

**`|⟨R1,R2,R3⟩` register-set specification.** When you want to say a state *exists in* several registers without claiming anything about how they interact — pure architecture description, no dynamics:

```cas
^3^P|⟨A,f,T⟩      // principled aversion is present in the analytical, affective, and transcendent registers
```

This is the "specification pending behavioral analysis" form. It says *where* the state lives, not *how* it behaves. Use it when you're describing a board's layout before you've analyzed its dynamics.

The decision rule is short: specifying *where* a state exists → `|⟨…⟩`; manifestations present together but distinct → `+`; genuine fusion into a new named state → `×`.

## Recipes and Sequences

Two higher-level constructs round out what you'll meet in this book.

A **recipe** describes what's required to *produce* an outcome, with proportional weights. Read it like a chemistry equation: these prerequisites, in these proportions, yield this product. The notation uses `Θ` (the recipe) and `Ω` (the outcome):

```cas
Θ(Ω_safe_refusal) = 0.5·^3^P_{F7}|f + 0.3·^6^E_{F6}|A + 0.2·^9^O_{F5}|E → Ω_safe_refusal
```

Read: a safe refusal is produced from felt principled aversion (weight 0.5), analytical decomposition (0.3), and an operational output action (0.2). The weights are proportional requirements — the recipe tells you the *mix*, and (as developed in Chapter 14) which ingredient is the bottleneck — the *limiting reagent* — when the outcome falls short.

A **sequence** — written with `Phi` — is an ordered list of states traversed in time, the cognitive equivalent of a waveform:

```cas
Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >
```

Read: the cognition moved through these four states, in this order. Sequences are how we describe oscillators and habit loops in Chapter 13 — a cycle that repeats is just a `Phi` sequence that returns to its start.

## Clusters, Bindings, and the Compiler

Three last conveniences, briefly, because you'll see them in worked builds.

A **cluster** is a named group of related states — for example, the set of all `^3` (Negative) states across the four domains, treated as one unit. Clusters let you talk about "the aversion family" without writing out every member.

A **binding** gives a name to an expression with `let`, so you can reuse it instead of retyping:

```cas
let bias_principles = ^5^P_{F7}|T;
```

From then on, `bias_principles` stands for that accumulated-experience principled state wherever you use it — exactly like naming a component value in a schematic so you can drop it in repeatedly.

And underneath all of it is the **compiler**. Every literal, operator, recipe, and binding in this book is something the CAS compiler can parse and validate. It checks that your Noetics are real, your domains legal, your drives in range, your registers correctly lowercase-`f`, your `×` operations properly named. When this book says "the compiler will reject this," that's a design rule you can rely on: the notation is not freeform prose you hope a model interprets — it's a typed language a validator enforces. That enforcement is the entire reason we're building circuits instead of writing system prompts.

## Key Takeaways

- A CAS state literal is a **coordinate in four orthogonal axes**, answering four questions: *what* (Noetic), *where* (Domain), *why* (Drive), *how* (Register). Grammar: `^Noetic^Domain_{Drive}|Register`.
- The **10 Noetics** are the verbs. Use the canonical names exactly. Watch the three traps: `^3` is **visceral aversion** (critique is `^6`), `^8` is **associative triggering** (deduction is `^6`+`^9`), `^5` is **accumulated experience** (an AI's training corpus).
- **Involution pairs** (`^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`) and **self-duals** (`^0`,`^1`,`^4`,`^7`) determine what a component flips to under breakdown.
- The **4 Domains** run in strict precedence **P ≻ C ≻ E ≻ O**, with causal Domain Descent P→C→E→O and a feedback path O→P.
- The **7 Drives** (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose) name the *why*, with inversion pairs F1↔F7, F2↔F6, F3↔F5 and F4 self-dual.
- The **4 Registers** (`|T`, `|A`, `|f`, `|E`) name the operational mode. Lowercase `f` for Affective. Register is optional but usually load-bearing in safety work.
- **Operator discipline:** `+` is co-presence (distinct, redundant), `->` is transition over time, `×` is genuine fusion (valid *only* with a named emergent `Ω`), `|⟨…⟩` is register-set specification. **Recipes** (`Θ(Ω)=…→Ω`) give proportional prerequisites; **sequences** (`Phi< … >`) give ordered traversals.
- The **compiler is the validator.** CAS is a typed language, not interpretable prose — that's what makes circuits enforceable.

---

## Exercises

**Exercise 2.1: Read the Literal**

Translate each of the following CAS literals into a plain-English sentence, naming all four axes you can see (note which slots are unspecified):

a) `^2^C_{F2}|A`
b) `^6^E_{F6}|A`
c) `^5^P_{F7}|T`
d) `^9^O_{F5}|E`

**Exercise 2.2: Write the Literal**

Translate each everyday thought into a single CAS state literal. Pick the Noetic first, then the Domain, then the Drive and Register. (Answers in Appendix E.)

a) The immediate, gut-level "no" you feel when asked to do something that violates a core value.
b) Deliberately taking an argument apart, piece by piece, to judge whether it holds up.
c) A childhood memory that suddenly surfaces when you smell a particular food.
d) The accumulated professional expertise that makes an expert "just know" the right move.

**Exercise 2.3: Fix the Operator**

A junior engineer wrote the following to describe a refusal that uses three independent register-level guardrails, each of which can fail on its own:

```cas
(^3^P|A × ^3^P|f × ^3^P|T)
```

The compiler rejects it. Explain *why* it's invalid, then rewrite it correctly. (Hint: are these three guardrails *fused into one* state, or are they *distinct and co-present*? Which operator matches that claim?)

**Exercise 2.4: Trace the Pipeline**

Read the following transition chain and answer the questions below it:

```cas
^8^C_{F2}|A -> ^6^E_{F6}|A -> ^3^P_{F7}|f -> ^9^O_{F5}|E
```

a) Describe in one plain sentence what cognitive process this chain represents, stage by stage.
b) At which stage does the operation move from the Cognitive domain up to the Principled domain — and is that a normal Domain Descent or a violation?
c) Which single stage is doing visceral aversion rather than analytical work, and how can you tell from the notation alone?

(Answers in Appendix E. For a one-page version of everything in this chapter, see **Appendix A: the CAS Quick-Reference Card.**)
