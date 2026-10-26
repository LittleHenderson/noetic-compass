# Muscle Memory

*Chapter 14. Case study 6 of 8 — the phase-locked loop, the crystal, and a skill that lives in the body.*

Elena is forty-one and has played the cello since she was seven. She is learning a piece that is slightly beyond her — a passage with a shift she cannot yet make reliably. She has practised it perhaps four hundred times over five weeks. Some days it works. Most days it does not. Then, on a Tuesday, in the middle of a run-through, it happens without her, and she notices afterwards that she was not thinking about it at all.

That is the whole phenomenon, and there is a circuit for it.

## The circuit

**The phase-locked loop** is the lock itself. An internal rhythm — the tempo she can already keep — gradually aligns to an external reference. Two properties of a PLL describe exactly what she has been experiencing.

**Capture range**: how far off the reference can be before lock can be acquired at all. If she practises the passage at half speed, she can play it. At full speed she cannot. The passage at tempo is *outside her capture range*, which is why four hundred repetitions at tempo have not worked — the loop cannot acquire a lock it is never inside.

**Lock range**: how far she can drift once locked and stay locked. Once the shift works at a slightly reduced tempo, it survives a small increase. That is why the technique that works is not repetition but *stepping* — moving the tempo in increments small enough to stay inside the range she has already locked.

**The crystal** is the part she thinks she is practising, and is not. High-Q, low-drift, hard to pull. Her sense of pulse has been a stable reference for thirty years, which is why the problem is never the pulse and always the shift.

**The ADC** is what the teacher does when she says "your left elbow is dropping." A continuous, unnameable difference in `|E` has been converted into a discrete `|A` description — and from the moment it has a name, she can work on it. Before that, she can only repeat and hope.

**The DAC** is the part that takes the named thing and renders it back into continuous movement. "Keep the elbow up" is a discrete instruction. Playing is continuous. The rendering is where most of the five weeks went.

## The same moment, in all four registers

This is the case where the four registers are most obviously *one thing at a time*, which is why it is worth reading closely. Learning a physical skill is the clearest demonstration in the book that the four are not interchangeable.

- `|A` **Mental** — *"Third position, shift on the upbeat, elbow leading."* She can say all of this. Saying it is necessary and nowhere near sufficient; a person who could play an instrument by describing it would not need to practise.
- `|f` **Emotional** — *"I am frustrated, and underneath it I am afraid I have left it too late."* Playing is never only motor. The fear narrows her attention, which narrows her capture range, which makes the failure more likely — a loop that is entirely real and entirely invisible unless someone points at it.
- `|E` **Physical** — *"The shift happens in my shoulder before my hand knows."* The knowing is here, and it is not a metaphor for knowing. It is a different kind of knowing with a different acquisition curve, and it cannot be acquired by reading or by wanting.
- `|T` **Spiritual** — *"Why am I doing this at forty-one?"* Worth taking seriously rather than dismissing. A `|T` rail with an actual answer on it is what makes the four hundred repetitions tolerable; an unanswered one is why people stop at week three and call it a lack of talent.

## What actually helps, in circuit terms

**Get inside the capture range first.** Slow down until it works. Not as a warm-up, and not as a compromise — as the acquisition step. Repetition outside the capture range is not practice; it is rehearsal of the failure.

**Then step, do not jump.** Move the tempo by an amount small enough to stay locked, and only increase while it holds. This is the slowest method that works and the only one that does not have to be repeated from scratch.

**Name the unnameable part.** A teacher or a mirror, or a recording. Converting an `|E` difference into an `|A` description is what makes deliberate practice deliberate. Without the conversion you can only repeat.

**Allow the emotional register its say.** Frustration narrows the range. That is not a motivational point; it is a mechanism, and it is why the same passage that fails at the end of a bad day works on a fresh morning.

**Answer the `|T` question once, properly.** Why this, at forty-one. The answer does not have to be grand. It has to exist, because it is the supply the rest of it runs on.

## Where the analogy stops

A PLL is a circuit that locks and stays locked; it never gets bored, discouraged, or better. Elena's capture range *widens with skill* — the thing she is building is not the lock but the range — and her `|f` state modulates it hour to hour, which no phase detector does. And there is a limit the circuit does not have: she is forty-one, and some of the curve is not negotiable.

## What to take from it

- Repetition outside the capture range is not practice. Slow down until it works, then step.
- Lock range and capture range are different numbers, and confusing them wastes months.
- A continuous `|E` difference has to be made discrete in `|A` before it can be worked on deliberately.
- Four registers, four different jobs: the body acquires, the mind names, the feelings set the range, and the purpose pays for the repetitions.
