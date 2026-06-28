# Chapter 5: CAS Grammar and Compiler Rules

In any formal programming language, there is a strict difference between *syntax* and *semantics*. 

Syntax dictates whether the compiler can parse your code (e.g., did you put the symbols in the right order?). Semantics dictates whether your code actually means something logically valid within the rules of the system.

The CAS compiler (whether running in Rust or Python) enforces both.

## What the Compiler Accepts (Syntax)

As we saw in Chapter 4, the basic syntax for a state is `^Noetic^Domain_{Drive}|Register`. 
The compiler uses a formal grammar (often defined via pest or a similar parser generator in Rust) to tokenise these expressions. 

It accepts:
- Single states: `^1^E_{F1}|f`
- Syntactic clusters: `^1^E_{F1}|f + ^2^C_{F1}|A`
- Algebraic compositions: `^5^C_{F6} * ^8^C_{F6}`
- Sequences: `Phi< ^1, ^4, ^8 >`
- Recipes: `Θ(Ω_name) = 1.0*^1^E + 2.0*^2^C → Ω_name`
- Meta-logic clusters: `StateCluster{^8^C, ^1^C}` or `RelationCluster{^5^P -> ^5^C}`

## What the Compiler Rejects (Type Constraints)

If you write `^1^P_{F8}`, the parser might read it, but the semantic type-checker will reject it. Why? Because there is no `F8`. The drives are strongly typed from `F1` to `F7`. 

Here are the primary type constraints:
- **Noetic Type:** Must be an integer `0..=9`.
- **Domain Type:** Must be an exact match to the enum `[P, C, E, O]`.
- **Drive Type:** Must be `F1..=F7`.
- **Register Type:** Must be `|T, |A, |f, |E`.

## Domain Descent Rules

One of the most important semantic rules in CAS is **Domain Descent**. 

The domains represent an ontological hierarchy from abstract to concrete:
1.  **P (Principled):** Highest abstraction
2.  **C (Cognitive):**
3.  **E (Evaluative):**
4.  **O (Operational):** Lowest abstraction

When composing a psychological sequence (`->`), the compiler generally expects a valid path of domain descent. A thought usually begins in the abstract and moves toward action.

*   `^P -> ^C -> ^E -> ^O` is a standard, valid descent path.
*   `^O -> ^P` represents a sudden "jump" from physical action back to high principle. Depending on the compiler's strictness settings (e.g., standard vs. "Rule 4" validation), this might be flagged as a discontinuity or require a specific meta-logic transition to be valid.

## Register Rules (Rule 4)

In CAS v7.7, the compiler natively enforces "Rule 4" co-presence for registers.
You can have multiple registers active for the *same* state. This represents a mind fully unified across its modalities.

*   **Valid Rule-4:** `^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E`
    This means the person is executing empathetic connection operationally (`^5^O_{F4}`) through logical steps (`|A`), genuine feeling (`|f`), and physical presence (`|E`).

The compiler checks that the base state (`^5^O_{F4}`) matches across the addition.

## Algebraic Composition

When using the multiplication operator (`*`), you are invoking monoid composition: `^a * ^b = ^((a+b) mod 10)`.

*   `^8 * ^5 = ^3` (8 + 5 = 13 mod 10 = 3)

However, the compiler enforces constraints on the Domain and Drive during multiplication. Usually, you can only multiply states within the *same* Domain to produce an emergent state in that Domain. If you attempt `^8^C * ^5^E`, the compiler will throw a `CrossDomainMultiplicationError` unless you explicitly define a projection or an Omega bind to handle the cross-domain synthesis.

***

## Exercises

**Exercise 5.1: Compiler Error Simulation**
Imagine you are the CAS compiler. What specific error would you throw for the following expression, and why?
`^4^C_{F3}|Q`

**Exercise 5.2: Domain Descent Check**
Is the sequence `RelationCluster{^2^P -> ^3^C -> ^4^E -> ^5^O}` a valid ontological descent? Why?