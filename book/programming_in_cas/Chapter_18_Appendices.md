# Chapter 18: Appendices

This appendix serves as a quick reference guide for programming in CAS.

## A. Symbol Reference

### Noetic Operators (The Verb)
*   **`^0`** Identity (Holding boundaries)
*   **`^1`** Differentiation (Separating, categorizing)
*   **`^2`** Abstractification (Theorizing, patterns)
*   **`^3`** Concretization (Specifying, building)
*   **`^4`** Integration (Merging, synthesizing)
*   **`^5`** Empathetic Alignment (Resonating)
*   **`^6`** Critical Evaluation (Judging, auditing)
*   **`^7`** Directed Focus (Pointing attention)
*   **`^8`** Expansion (Brainstorming, seeking)
*   **`^9`** Contraction (Narrowing, completing)

### Domains (The Location)
*   **`^P`** Principled (Ethics, Axioms)
*   **`^C`** Cognitive (Logic, Maps)
*   **`^E`** Evaluative (Value, Subjectivity)
*   **`^O`** Operational (Physics, Action)

### Drives (The Fuel)
*   **`F1`** Unity
*   **`F2`** Wisdom
*   **`F3`** Vitality
*   **`F4`** Connection
*   **`F5`** Agency
*   **`F6`** Structure
*   **`F7`** Purpose

### Registers (The Modality)
*   **`|T`** Transcendent (High-abstraction, integrative)
*   **`|A`** Analytical (Explicit, logical)
*   **`|f`** Affective (Value-laden, feeling)
*   **`|E`** Embodied (Sensorimotor, physical)

## B. Syntax Cheatsheet

### Standard State Literal
`^Noetic^Domain_{Drive}|Register`
*Example:* `^3^C_{F6}|A`

### Syntactic Co-Presence
`State1 + State2`
*Example:* `^4^O_{F6}|A + ^4^E_{F7}|f`

### Algebraic Multiplication
`State1 * State2`
*Example:* `^8^C_{F6} * ^5^C_{F6}`

### Directed Transition
`State1 -> State2`
*Example:* `^5^C_{F1} -> ^6^E_{F1}`

### Omega Bind (Emergent Integration)
`(State1 × State2) = ^Noetic|Ω_Name`
*Example:* `(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence`

### Theta Recipe
`Θ(Ω_Name) = w1*State1 + w2*State2 → Ω_Name`
*Example:* `Θ(Ω_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A → Ω_refusal`

### Phi Sequence (Fractal)
`Phi< State1, State2, State3 >`
*Example:* `Phi< ^1^P, ^4^C, ^8^O >`

### Meta-Logic Clusters
`StateCluster{ State1, State2 }`
`RelationCluster{ State1 -> State2 }`

## C. Compiler CLI Commands

*   `cas chat`: Launch interactive REPL.
*   `cas notation "EXPR"`: Compile and validate a specific CAS expression.
*   `cas predict "TEXT"`: One-shot structured prediction on English text.

## D. Common Error Catalog

*   **`MissingRegisterWarning`:** Thrown when a state literal lacks a `|R` suffix.
*   **`CrossDomainMultiplicationError`:** Thrown when attempting to multiply states across different domains without an explicit projection or Omega bind.
*   **`InvalidDriveTypeError`:** Thrown when using an unrecognized drive label (e.g., `F8`).
*   **`DiscontinuousDescentWarning`:** Thrown when a `->` transition skips expected ontological layers (e.g., `^O -> ^P` without a bridging state).