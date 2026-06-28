# Chapter 4: Writing Basic CAS Programs

Now that we can read CAS, it's time to write it. Writing CAS requires precision. The compiler is unforgiving of syntax errors, ambiguous domains, or invalid combinations.

We will start with the foundational building blocks and work our way up to compiling our first valid expressions.

## 1. State Literals

The core of any CAS program is the state literal. As a reminder, the strict syntax is:
`^Noetic^Domain_{Drive}|Register`

**Rule of Thumb:** Always write the components in this exact order.

**Example Task:** Write a state representing a project manager meticulously creating a spreadsheet of tasks, driven by a need for order.
1.  **Verb:** Meticulous detail creation = Concretization = `^3`
2.  **Location:** Spreadsheets and data = Cognitive Domain = `^C`
3.  **Fuel:** Need for order = Structure Drive = `_{F6}`
4.  **Flavor:** Explicit, step-by-step = Analytical Register = `|A`
**Result:** `^3^C_{F6}|A`

## 2. Binary Composition

Often, we want to express the relationship between two states.

### Co-presence (Addition)
When a system or person is holding two states simultaneously without resolving them into a single action, use the `+` operator.

**Example Task:** A user is writing Python code while listening to an emotionally moving podcast.
*   State 1 (Coding): `^3^C_{F5}|A`
*   State 2 (Listening): `^5^E_{F4}|f`
**Result:** `^3^C_{F5}|A + ^5^E_{F4}|f`

### Directed Transition (Arrow)
When a mind moves sequentially from one state to the next, use the `->` operator.

**Example Task:** A person realizes a fundamental ethical truth, and immediately takes physical action based on it.
*   State 1 (Ethical realization): `^2^P_{F1}|T`
*   State 2 (Physical action): `^3^O_{F5}|E`
**Result:** `^2^P_{F1}|T -> ^3^O_{F5}|E`

## 3. Recipes (The Theta Constructor)

Recipes are how we define complex, multi-component psychological states or "Attractors" in CAS. A recipe defines the ingredients and their relative weights.

**Syntax:** `Θ(Ω_Name) = weight1*State1 + weight2*State2 → Ω_Name`

**Example Task:** Define a recipe for "Methodical Review." It requires a heavy dose of critical evaluation, a moderate amount of structure-driven logic, and a small amount of purposeful focus.
1.  **Define the output:** `Ω_methodical_review`
2.  **Define ingredients:**
    *   Critical evaluation: `^6^C_{F2}|A`
    *   Structure logic: `^0^C_{F6}|A`
    *   Purposeful focus: `^7^P_{F7}|A`
3.  **Assign arbitrary weights (for illustration):** 2.0, 1.5, 0.5.
**Result:** `Θ(Ω_methodical_review) = 2.0*^6^C_{F2}|A + 1.5*^0^C_{F6}|A + 0.5*^7^P_{F7}|A → Ω_methodical_review`

*Note: In production CAS-Native models, these weights are often derived via Fisher-Rao geometry from training data, rather than being guessed.*

## Common Beginner Mistakes

When writing CAS, beginners frequently make these errors that the compiler will catch:

1.  **Missing the Register:** In modern CAS v7.7, omitting the register (e.g., writing `^1^E_{F1}`) is sometimes permissible as a shorthand, but it is considered poor practice and may trigger a warning in strict validation modes. Always strive for full specification (`^1^E_{F1}|f`).
2.  **Domain Mismatch in Multiplication:** Algebraic multiplication (`*`) traditionally requires states to be in the *same* domain, or follow specific domain descent rules. You cannot directly multiply `^P` and `^O` without defining the projection path.
3.  **Using Conceptual Notation:** Attempting to feed `CO-4` into the compiler will result in a syntax error. Use `^4`.
4.  **Confusing Drives and Noetics:** Remembering that `^F` is invalid. Carets `^` are for Noetics and Domains. Underscores `_` are for Drives.

## Valid vs. Invalid Expressions

*   **VALID:** `^9^P|A` (Valid domain-omitted state with register)
*   **INVALID:** `^9_{F2}` (Missing domain entirely)
*   **VALID:** `^4^O_{F6}|A + ^4^E_{F7}|f` (Valid co-presence)
*   **INVALID:** `CO-4^O + CO-4^E` (Legacy notation)

In the next chapter, we will dive deeper into the rules the CAS compiler uses to validate these expressions.

***

## Exercises

**Exercise 4.1: Write the Equation**
Write the executable CAS equation for a transition from "evaluative expansion driven by vitality" to "operational concretization driven by agency." Assume embodied (`|E`) registers for both.

**Exercise 4.2: Debug the Code**
The following CAS expression failed to compile. Why?
`Θ(Ω_joy) = ^8_E_{F3} + ^4_E_{F4}`