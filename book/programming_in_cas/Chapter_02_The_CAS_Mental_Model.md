# Chapter 2: The CAS Mental Model

Before we write code, we must understand the architecture of the machine we are programming. The "machine" in CAS is the cognitive state space.

A single moment of focused cognition—a "thought"—is called a **Cognitive State**. In the executable syntax of CAS, a state is a typed coordinate composed of specific variables. If any essential variable is missing or invalid, the CAS compiler will reject it.

Let's examine the core components of the CAS mental model.

## 1. Noetics (The Operators)

The Noetic operator (often simply called the "Noetic") is the **verb**. It defines what the mind is mechanically doing. There are 10 Noetic operators, numbered 0 through 9.

In executable syntax, the Noetic is represented by a caret followed by a number: `^k`.

*   **`^0` Identity:** Holding a steady state, recognizing boundaries.
*   **`^1` Differentiation:** Separating, noticing differences, creating categories.
*   **`^2` Abstractification:** Zooming out, theorizing, finding patterns.
*   **`^3` Concretization:** Zooming in, specifying details, building.
*   **`^4` Integration:** Merging parts into a whole, synthesizing.
*   **`^5` Empathetic Alignment:** Resonating, harmonizing, adopting another's state.
*   **`^6` Critical Evaluation:** Judging, auditing, finding flaws.
*   **`^7` Directed Focus:** Pointing attention, committing to a vector.
*   **`^8` Expansion:** Seeking new variables, brainstorming, expanding scope.
*   **`^9` Contraction:** Narrowing focus, tightening boundaries, completing.

## 2. Domains (The Location)

The Domain is the **environment**. It tells us *where* in reality the Noetic verb is firing. Domains are written as an uppercase letter following the Noetic.

*   **`^P` Principled:** The realm of ethics, axioms, and the "Always."
*   **`^C` Cognitive:** The realm of logic, data, maps, and the "How."
*   **`^E` Evaluative:** The realm of subjective value, friction, and the "Weight."
*   **`^O` Operational:** The realm of physical action, physics, and the "Now."

## 3. Drives (The Fuel)

The Drive is the **energy source**. It answers *why* the mind is executing the verb in that domain. Drives are written as an underscore followed by `F` and a number in curly braces: `_{Fk}`.

*   **`F1` Unity:** The drive for wholeness and coherence.
*   **`F2` Wisdom:** The drive to map, understand, and learn.
*   **`F3` Vitality:** The drive for energy, thriving, and life.
*   **`F4` Connection:** The drive to relate to the Other.
*   **`F5` Agency:** The drive to execute, control, and act.
*   **`F6` Structure:** The drive to organize, build rules, and preserve order.
*   **`F7` Purpose:** The drive for meaning and direction.

## 4. Registers (The Modality)

Introduced in CAS v7.5, Registers represent the **modality** or "flavor" of how a Drive expresses itself within a domain. The Register is orthogonal to the Domain but shares a high-to-low abstraction gradient. It is denoted by a pipe character followed by a letter: `|R`.

*   **`|T` Transcendent:** High-abstraction, purpose-orienting, integrative across particulars.
*   **`|A` Analytical:** Explicit, sequential, logical, reason-based.
*   **`|f` Affective:** Value-laden, feeling-toned, somatic resonance.
*   **`|E` Embodied:** Sensorimotor, concrete, direct physical engagement.

*Note: The older conceptual notation often lacked registers entirely. The CAS compiler natively supports and often requires them for rigorous definition.*

## State Literals: Bringing It Together

When we combine these elements, we get a **State Literal**—the fundamental unit of CAS programming.

Let's look at a complete state: `^2^C_{F2}|A`

*   `^2`: Abstractification (Extracting patterns)
*   `^C`: Cognitive Domain (Logic and data)
*   `_{F2}`: Driven by Wisdom (Hunger for knowledge)
*   `|A`: Analytical Register (Explicit, step-by-step reasoning)

**Translation:** "Deliberately abstracting logical patterns step-by-step, driven by a desire to formally understand."

If we changed just the Register: `^2^C_{F2}|T`
**Translation:** "A sudden, high-level flash of integrative insight (Transcendent) into a logical pattern, driven by a desire to understand."

The difference between `|A` (grinding through the math) and `|T` (the "Aha!" moment) is structurally captured by the compiler.

## The Conceptual vs. Executable Map

If you read the older *TKS Cognitive Framework* manuscripts, you will see `CO-2^C_{F2}`.
When writing code for the CAS v7.7 compiler, you write `^2^C_{F2}|A`.

The conceptual model tells you *what* the pieces are. The executable syntax tells you *how to type them* so the machine understands.

***

## Exercises

**Exercise 2.1: State Deconstruction**
Given the state `^6^E_{F6}|f`, identify the:
1. Noetic
2. Domain
3. Drive
4. Register
Write a one-sentence English description of what this state looks like in a human.

**Exercise 2.2: State Construction**
Write the executable CAS state for: "A person physically building a prototype (`^3^O`), driven by a desire to execute and get things done (`F5`), using hands-on embodied skill (`|E`)."