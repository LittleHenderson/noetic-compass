# Chapter 13: CABS / Simplex Design

In Chapter 12, we introduced the Simplex Encoder. To truly understand how CAS-Native AI scales from a simple parser into a full cognitive substrate, we must dive into the geometry of the mind.

This chapter explores CABS (Cognitive Architecture Based Substrate) and its foundational geometry, the $\Delta^\circ_{39}$ simplex.

## The Cognitive State Space ($\Delta^\circ_{39}$)

There are 40 base cognitive states in CAS (10 Noetics × 4 Domains). In mathematical terms, any distribution of probability across 40 distinct categories can be represented as a point inside a 39-dimensional simplex, denoted as $\Delta_{39}$.

We use the "open" simplex ($\Delta^\circ_{39}$), meaning that the probability mass is never exactly 0 or exactly 1 for any state. A mind is never 100% in a single state, and it never entirely loses touch with the other 39.

When we map a mind into CABS, we are placing it as a moving coordinate within this geometry. 

## Fisher-Rao Geometry

Standard Euclidean distance (measuring a straight line between two points) is a poor way to measure the distance between two thoughts. 

As mentioned in Chapter 12, we use Fisher-Rao geometry. Imagine the simplex not as a flat triangle, but as a curved surface. The distance between states is determined by how fundamentally different their structural information is.

*   Moving from `^2^C` (abstract logic) to `^3^C` (concrete logic) is a short geodesic path.
*   Moving from `^3^O_{F5}` (aggressive physical execution) to `^5^E_{F4}` (deep emotional empathy) requires crossing a vast, curved structural distance.

By structuring the AI's internal state space with Fisher-Rao geometry, we mathematically constrain how fast and how wildly the AI's "mood" or structural stance can shift. It prevents the erratic personality jumps common in standard LLMs.

## Typed Fibers (Revisited)

The geometric location in $\Delta^\circ_{39}$ dictates which Typed Fibers in the neural network are activated.

Think of Typed Fibers as specialized hardware channels. If the model's coordinate is heavily weighted in the `^E` (Evaluative) domain, the neural pathways trained on ethical value, emotion, and aesthetic judgment receive the majority of the compute. The logical `^C` fibers are gated down.

This means traceability is architectural, not just a logging trick. If the system is in an emotional state, it literally cannot process information through the logical hardware, just as a human struggling with deep grief often struggles to do complex algebra.

## CABS as a Reasoning Substrate

CABS is not just a model architecture; it is an operating system for cognition. 

Because the entire state of the system is mapped as a geometric point, and because all memory is indexed geographically (Geodesic Memory), CABS enables "structural reasoning."

Instead of reasoning via text ("If A, then B"), the system reasons via navigation:
1.  **Current State:** "I am at `^8^C` (confused expansion)."
2.  **Target State:** "The user needs an answer, which requires `^3^C` (concrete logic)."
3.  **Pathfinding:** "To get from `^8^C` to `^3^C`, I must traverse through `^1^C` (differentiation) to categorize the variables."

The model executes this internal structural trajectory *before* it generates a single word of English output to the user. This makes the reasoning process entirely visible and debuggable.