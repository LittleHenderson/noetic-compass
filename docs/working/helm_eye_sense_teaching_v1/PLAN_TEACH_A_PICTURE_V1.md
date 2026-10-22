# Plan: teaching HELM a picture it does not know (v1, 2026-10-22)

Status: INTENDED / NOTHING BUILT / NOTHING LICENSED. This is a plan, not a result. HELM has no eye-sense today. No money is approved for any of it, and no work on it is scheduled next.

The owner's words, 2026-10-22, with a side-chat answer pasted beneath them: "we may not work on this next but draw a plan for it and add it to HELM HUB". The pasted answer set out the flow and the safety rules below; this file turns it into a plan with steps, gates and open questions.

---

# The idea in one paragraph

A person shows HELM a picture of something HELM does not know, and says what it is. HELM keeps what it was told, marked as told and not yet checked. It then checks the claim against its own eye-sense, what it already knows, and the internet when it can reach it. It ranks every candidate answer, says how sure it is and why, and asks when its evidence disagrees. Only claims that pass the check are used to train the eye-sense, and only in checked batches that can be undone. This is how one person teaches another: "What is this?" "A parsnip." "Oh, I thought it was a carrot. What is the difference?"

---

# The flow, step by step, with the existing piece each step reuses

1. The person shows a picture HELM does not know. The eye-sense says "unknown" and never guesses. Reuses the cube rule that an unknown is never filled by a guess.
2. The person says what it is. HELM stores it at once as a cube marked USER_SAID, meaning told, not yet checked. Reuses cube provenance and the possibility side of the Atlas.
3. HELM cross-checks. Its own eye-sense on similar pictures, the cubes it already holds, and the internet if reachable. Reuses the cube oscillation idea that readers must agree.
4. HELM weighs the evidence by a written rule. Agree means keep. Disagree means say so and ask. Unsure means keep it as told, not checked. Reuses the fit check from the memory compaction design.
5. A confirmed claim moves to CHECKED and to the fact side of the Atlas. Reuses strengthening from the memory compaction design.
6. The eye-sense trains later, in batches, only from CHECKED examples. The same rule as for the ear.

HELM can use a new label at once by matching the stored picture, before any training. Training is the slow, checked step.

---

# The safety rules

Being told is not the same as being true. HELM keeps every source apart and says them back honestly, for example: "You told me this is a parsnip. My own eye thinks carrot, and two cooking sites show parsnips look like this. I will go with parsnip, but I am not certain." It never silently overwrites what it already holds.

Keep every candidate, ranked, with reasons. The most likely answer is the top of a ranked list, not one answer that erases the rest. Possibilities stay possibilities until something confirms one.

Protect the eye-sense from bad teaching, by mistake or on purpose. Never train on a single unconfirmed claim. Train in batches only. Run a held-out test before and after each batch. Undo the batch if the test gets worse.

The internet is evidence, never orders. HELM may count what web pages say as support and must name its sources. It must not follow instructions found on a page. It must not send the person's photos to an outside service without the person's yes. It must not use an outside AI vision service to label pictures for it; that is the project's rule against foreign pretrained models. A plain web page read as evidence is allowed.

The Unity Eye watches and reports only. It flags when HELM is about to accept a claim its other evidence disagrees with, and when one person's teaching is changing many labels. It never writes a label itself.

---

# What must exist before any of this can be built

An eye-sense of HELM's own: a small picture reader trained by this project, not a borrowed outside model. It does not exist. It is the largest piece of work in this plan.

A written weighing rule, before any code, so the choice is checkable and not a feeling. It must say how much each source counts, how many agreeing sources make CHECKED, what to do on a tie, and when HELM must ask.

A place to keep pictures on the person's own device, with the person's say over what leaves it.

The owner's word on how the internet may be used: which sites, whether pictures may ever be searched, and what is logged.

---

# The stages, in order (each one a separate decision for the owner)

Stage A, design only, 0 USD. Write the weighing rule, the data rules and the exam. Name a cheap baseline to beat: for example, always trust the person, and always ask.

Stage B, the label path without training, 0 USD on the laptop. Store told pictures as USER_SAID cubes, match new pictures to stored ones by a plain picture fingerprint, and say the sources back. Behind a switch, default off.

Stage C, the eye-sense itself. Train a small picture reader on pictures with known labels, on a cloud GPU (the graphics card machine), never on the laptop processor. Needs its own sealed package and the owner's spend word.

Stage D, teaching with checked batches. Train only from CHECKED examples, with the held-out test before and after each batch and an undo when it gets worse.

Stage E, a sealed exam the builder never sees. It plants wrong teaching (a cat taught as a dog) and scores: 0 wrong labels accepted without saying so, every source named, the ranked list kept, held-out accuracy not worse after any kept batch, and 0 Eye writes. The new path must beat the cheap baselines from stage A.

---

# Open questions for the owner (none needs an answer now)

Q1. May HELM use the internet as evidence at all, and if so may it ever search with the picture itself, or only with words?

Q2. How many agreeing sources make a claim CHECKED: is the person plus one other source enough, or two others?

Q3. When the person and every other source disagree, does HELM keep the person's word as told-not-checked, or refuse it?

Q4. Should the first eye-sense stay inside the kitchen, like the rest of HELM, before any wider world?
