# Chapter 14: Level 3 Conversational CAS

We briefly touched on Level 3 conversational style in Chapter 11. But as you build applications on top of the CAS compiler, managing the interface between structural rigor and human-like conversation becomes your primary challenge.

## The Three Levels of Interaction

1.  **Level 1 (Raw Code):** The system outputs raw CAS syntax: `^3^C_{F6}|A`. Useful for developers, useless for normal users.
2.  **Level 2 (Paraphrase):** The system outputs a generic translation: "I am using logic to build a structure." It is understandable, but feels robotic and lacks the nuance of the human voice.
3.  **Level 3 (Embodied Conversation):** The system generates natural, flowing English that perfectly reflects the underlying CAS state without explicitly naming it. It sounds human, but its structural intent is mathematically rigorous.

## Writing Level 3 Prompts

To elicit Level 3 behavior from a CAS-Native model (or a standard LLM prompted with CAS), you must enforce strict constraints.

### The "Show, Don't Tell" Rule
Never allow the model to say "I am feeling empathy." It must *demonstrate* `^5^E`. 

*   **Bad (`^2` masquerading as `^5`):** "I understand that you are sad. That is difficult."
*   **Good (True `^5^E`):** "That sounds exhausting. I'm so sorry you had to carry that alone."

### The Register Lock
If the predicted state dictates the `|f` (Affective) register, the vocabulary must be felt, value-laden, and warm. If the state dictates `|A` (Analytical), the vocabulary must be sequential, explicit, and dry.

**Example Task:** Explain why a code deployment failed.
*   **State:** `^6^C_{F6}|A` (Analytical critique)
    *   **Level 3 Output:** "The deployment failed because Module B has a circular dependency on Module A. We need to refactor the import sequence before retrying."
*   **State:** `^6^C_{F6}|f` (Affective critique - frustrated by chaos)
    *   **Level 3 Output:** "This codebase is a mess right now. Module B is tangled up with A, and trying to deploy it like this just feels reckless."

Notice how the *information* is the same, but the *Register* fundamentally changes the tone.

## Handling User Ambiguity

What happens when a user says something ambiguous, like "Whatever"?

A Level 3 system should not guess wildly. It should execute a specific CAS state: `^8^C_{F2}` (Expansion seeking wisdom) or `^5^E_{F4}` (Empathetic alignment seeking connection).

It handles ambiguity by asking clarifying questions that are structurally grounded:
*   **`^8^C` Approach:** "I'm not sure I follow. Are we abandoning the plan, or just pausing it?"
*   **`^5^E` Approach:** "You sound frustrated. Are we moving too fast?"

## Preserving Structure While Sounding Human

The ultimate test of a Level 3 system is the **Recovery Test**. 

If you take the Level 3 English output and feed it back into the CAS extraction pipeline (Chapter 11), does it reliably return the exact CAS state that generated it?

If the output is too poetic or rambling, the extraction pipeline will get confused. If it is too robotic, the user will disengage. The art of Level 3 programming is writing the specific system prompts and decoder weights that thread this needle.