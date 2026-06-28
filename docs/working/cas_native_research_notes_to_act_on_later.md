# CAS-Native — research notes to act on later

Rolling log of external research that could feed CAS-Native at some later stage. Each entry: what it is, why we care, hypothesized capability lift if CAS-Native is developed to its fullest, and counter-considerations (what could go wrong, or tensions with current architecture). Nothing here is committed to the build. Acceptance criteria for promoting an entry to a real proposal go at the bottom of each entry.

Naming convention: keep entries in reverse-chronological order (newest first). Tag entries `[STATUS: parked]` until something promotes them.

---

## 2026-05-22 — "Thinking with Visual Primitives" (DeepSeek)

**Source.** alphaXiv overview page: https://www.alphaxiv.org/overview/visual-primitivesv1 (paper authored by Ruijie Lu, Yiyang Ma, et al., DeepSeek-AI, with Peking / Tsinghua collaborators). PDF was briefly published then pulled from DeepSeek's official channel; archived copies circulate on Hugging Face and GitHub mirrors. Treat as preprint-grade; original withdrawal is unexplained.

[STATUS: parked]

### What the paper proposes (plain version)

Most multimodal models look at an image and then reason in pure language ("the red square on the left of the blue circle..."). The authors argue this leaks information: language is too coarse to point at specific places in a dense scene, so the model loses track of what it just saw. They call this the **Reference Gap** — distinct from the Perception Gap (could the model see it at all). A model can correctly perceive 27 strawberries and still miscount, because language doesn't have enough pointers to keep 27 distinct objects straight.

Their fix: treat **points** and **bounding boxes** as first-class tokens in the chain of thought. The model interleaves spatial primitives with words during reasoning — `"I'll check the red object at <box₁> against the blue object at <box₂>"` — rather than producing them only as a final answer. The training stack is multi-stage: large-scale grounded pretraining, supervised fine-tuning on specialist tasks (counting, mazes, spatial reasoning) with cold-start trajectories, RL with rewards on format + reasoning consistency, then on-policy distillation of multiple specialist experts into one unified model. Backbone reported is DeepSeek-V4-Flash (MoE) with a custom ViT plus aggressive token compression. Reported gains are on counting, maze navigation, path tracing, and topological reasoning vs frontier baselines (GPT-5.4, Gemini-3-Flash). Headline limitation: primitives are activated by explicit trigger words, not autonomously.

### Why we care for CAS-Native

The structural move — promoting non-language objects to first-class tokens of thought, interleaved with language during reasoning — is exactly the bet CAS-Native is making with CAS expressions. The visual-primitives paper is independent confirmation of the more general principle: when language is too coarse to track a structured object, you stop reasoning *about* the object in language and start reasoning *with* the object as a token. Their Reference Gap is our Reference Gap, restricted to images.

This connects to four things already in CAS-Native:
- The **`|E` Embodied Register** (CAS v7.5) — sensorimotor / concrete engagement with material substrate. Visual primitives are the cleanest worked example of an `|E`-Register cognitive operation on visual material. Until now `|E` has been mostly defined for biological / robotic embodiment with no native AI analog.
- The **traceability spine** — every reply walks back to its origin. Visual primitives extend the trace from "what the model said" to "what the model said *about which pixels*."
- **Mode 7 Network Attribution** (Exposure Button) — primitives give a literal spatial referent for attribution claims.
- **SGGS** (Spatial Gesture Graph Spec, v2/v3 backlog) — the spatial-gesture work already anticipates spatial primitives as first-class CAS objects. Visual primitives are the static / 2D / image-grounded cousin of SGGS's dynamic / 3D / gesture-grounded primitives.

### Hypothesized capabilities at full CAS-Native development

Assuming CAS-Native ships v0 (conversational + CAS↔EN + traceability + thought tree + Idea Atlas), survives compiler-fluency curriculum (Path D), and is operating on the simplex redesign (Path C — base manifold + typed fibers). The capabilities the visual-primitives idea could add when CAS-Native is "done":

1. **Native `|E`-Register operations on visual input.** A CAS-Native expression like `^6^C|E({region: <box₁>}) → ^9^C|A(...)` becomes literally executable: the model decomposes (`^6` Male) the visual content inside `<box₁>` in Embodied register, and what comes to Mind (`^9`) downstream is grounded to that region. The Register axis stops being abstract and starts producing actual sensor-grounded computations.
2. **Visual-grounded admissibility.** Right now admissibility relations (`D_k ⊆ I × I`) are checked over CAS expression structure. With visual primitives, admissibility extends to scenes: an operation that claims to operate on `<box₁>` but emits content from `<box₃>` is structurally inadmissible. Hallucination becomes a typed admissibility failure, not a fluency artifact.
3. **Per-pixel traceability.** The 7-mode Exposure Button gains a literal spatial mode. Mode 3 (Per-Utterance Trace) gets pixel coordinates; Mode 7 (Network Attribution) attributes attention not just to source tokens but to source regions. "Show your work" extends from CAS expressions to image regions.
4. **Counting and spatial reasoning without language collapse.** The paper's empirical wins (counting, mazes, topology) translate directly: CAS-Native gets a clean answer to the Reference Gap inside scenes. Counting becomes `^7|E` rhythmic enumeration over enumerable primitive locations instead of language-paraphrase counting.
5. **Living Thought Atlas gets a spatial layer.** The Atlas is currently a thought-tree replay graph. Visual primitives let an atlas node carry a spatial referent (region of an image), so "where did this idea come from" answers in pixel-space when the input was an image.
6. **Inversion replay on visual evidence.** Inversion Replay (flip a CAS axis on a node + replay tree forward) becomes spatially grounded — you can flip an evaluation axis on the spatially-referenced `^3^E|f` node and ask "what would the conclusion be if that region triggered attraction instead of aversion."
7. **SGGS unification.** SGGS (gesture, 3D, dynamic) and visual primitives (image, 2D, static) become two instances of the same general construct: non-language spatial referents as first-class tokens of thought. CAS-Native ends up with one primitive type, two surface forms.
8. **Compiler-fluency curriculum extension.** Path D's six compiler tasks gain a seventh: image → CAS-with-primitives expression (and inverse). The compiler-as-law / model-as-fluent-speaker frame is preserved; the law just grew a spatial clause.
9. **Sample-level eval extension.** Per-sample outcomes (the only true CAS-Native eval metric) extend cleanly: instead of just "did the CAS expression compile and round-trip," now also "do the primitive bounding boxes land where they should." Sample reading remains the gate.

### Counter-considerations (what tensions this creates with CAS-Native at full development)

Listing these explicitly because the user's instruction was to hypothesize capabilities *while accounting for* what could go wrong:

- **No foreign pretrained models is load-bearing.** The DeepSeek paper rides on a 284B MoE backbone with a custom ViT. CAS-Native's commitment is end-to-end native architecture — no Llama, no Qwen, no Mistral, and by extension no V4-Flash. The *idea* (primitives as thought tokens) imports cleanly; the *implementation path* (start from a frontier MoE) does not. Acting on this means building a vision encoder from scratch into the CAS-Native stack, which is on the order of months, not weeks.
- **Schema isn't quality.** Visual primitives look like a small notation extension but they pull in real perception infrastructure: a vision encoder, image tokenizer, position-encoding scheme that survives the simplex Δ°₃₉ redesign, training data curation for grounding. The line-count of changes is small; the substrate is large. Don't propose this as a small PR.
- **Reference Gap is real but trigger-word activation is the same exposure-bias signature we've fought before.** Their primitives fire only when explicit trigger words appear. That's the B3-style memorization risk inside their training mix. Any CAS-Native port has to fix this at the architecture level (primitives are typed-fiber slots that can fire at any token position) rather than at the corpus level (more trigger words in more places).
- **Traceability budget.** Adding primitives doubles the per-token trace payload (CAS expression + spatial referent). Mode 3 and Mode 7 surfaces have to render both without becoming unreadable. Atlas Phase A visual rendering is already specified — primitives need a spec extension that doesn't break it.
- **IP exposure.** USPTO #64/037,173 covers the 40 cognitive states, 7 drives, 4 registers, and 5 generative operations. Visual primitives as *implementation of the `|E` Register over image substrate* are likely covered as application of an existing primitive. Visual primitives as *new primitive type* would need a separate disclosure. Decide framing before any external publication.
- **Compiler authority.** Path D's "compiler is law, model is fluent speaker" frame requires the compiler to be able to validate primitive-bearing expressions. Compiler does not currently know about pixel coordinates. Either the compiler grammar grows a `<region>` literal type with typed-set validation, or primitives live outside compiler-validated CAS (which weakens the traceability spine). The first option is correct; budget the work.
- **`|E` Embodied conflation risk.** Care needed to keep `|E` Register meaning what it means in v7.5 — operational character of a cognitive operation. Visual primitives are evidence *that an operation occurs in `|E`*; they are not themselves the operation. Don't let "visual primitives" become loose vocabulary for "anything spatial."
- **Withdrawn-paper provenance.** The original paper was pulled from DeepSeek's channel with no public explanation. Don't cite as if it were a stable peer-reviewed reference; mirror the archived PDF locally and date-stamp the mirror.

### When to act on this

Not now. Promote to a real proposal when **all** of the following are true:
1. CAS-Native v0 has shipped (conversational + CAS↔EN + traceability + thought tree + Idea Atlas).
2. Path D compiler-fluency curriculum has produced at least one checkpoint passing the 7-dim user-facing eval gate.
3. SGGS v2 design has either been promoted or explicitly deferred (decision needed because the two share substrate).
4. IP attorney has reviewed whether visual primitives over image substrate read on USPTO #64/037,173 as-filed.
5. There is a specific user-facing capability that requires it (most likely: an Atlas demo that needs to ground a thought-tree node back to a region of an input image).

When promoted, the work splits into three tracks:
- **Notation track** — extend compiler grammar with `<region>` typed literal; add admissibility rules for primitive-bearing expressions.
- **Architecture track** — native vision encoder into the simplex stack; primitive tokens as typed-fiber slots; trace payload extension.
- **Curriculum track** — image-grounded CAS↔EN tasks added to Path D; sample-level eval extension for primitive grounding.

Sources for promotion-stage reading:
- alphaXiv overview (above).
- 36Kr Chinese-language coverage with technical detail: https://eu.36kr.com/en/p/3789208597372165
- MindStudio summary (independent rewrite): https://www.mindstudio.ai/blog/what-is-visual-primitives-reasoning-deepseek
- Archived PDF mirror (HF dataset, "deleted-repo"): see search trail in this session's transcript.
