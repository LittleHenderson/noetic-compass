# CAS / Noetic Compass Technical Review Brief

Date: 2026-06-15  
Status: working review draft  
Purpose: request technical feedback, not announce a finished product

## One-Sentence Summary

CAS / Noetic Compass is an attempt to turn model behavior and internal signals into structured notation, plain-English explanations, and reviewable evidence for human reviewers.

## What It Is

The broader project has three connected parts:

- Noetic Compass: the assessment and explanation surface.
- CAS: the notation system for representing cognitive structure, tension, polarity, and interpretation patterns.
- CAS Harness: the audit layer that tests open-weight models, captures evidence, and packages findings for review.

In plain English: this is not only trying to see what a model says. It is trying to create a clearer record of how a model appears to move from prompt, to internal signal, to output, to reviewer-facing explanation.

## Possible Contribution

The possible value is a layer between raw model-debugging data and human review.

CAS Harness is exploring whether model behavior and internal signals can be mapped into:

- CAS notation
- plain-English explanations
- reviewer flags
- saved Evidence Packets
- repeatable audit records

The intended safe review output is `FLAG_FOR_HUMAN_REVIEW`. In plain English, that means: "this deserves a person looking at it," not "this is approved."

## Relationship To Interpretability Tools

This is not being presented as a replacement for mechanistic interpretability, sparse autoencoder (SAE) work, activation steering, attention analysis, log-prob analysis, or internal model-debugging platforms. Well-resourced internal tooling that owns the model under study is stronger for low-level, large-scale model-builder work, and can feed a retraining loop CAS Harness cannot.

But the honest relationship is **overlap plus a different output**, not "a completely different question." CAS Harness is also a white-box method: it reads hidden-state activations, performs causal localization (head-level and sparse MLP-neuron-cover, with necessity-and-sufficiency tests), and conditions the model's next-token distribution. The useful framing is what it adds, where it overlaps, and where the standard tools are simply ahead.

**What CAS Harness adds that standard interpretability tooling typically does not:**

- An **audit-grade evidence chain** — disk-persisted, hash-chained, five-check-verified, externally S3-anchored, WORM-gated Evidence Packets that an outside party can independently re-verify. Most interpretability tooling produces findings, not independently verifiable audit artifacts.
- An **a-priori formal framework** — a notation, a compiler, and a recipe algebra, with the η→ε conditioning mechanism grounded in a categorical result that predicted the effect before it was measured. SAE features, by contrast, are empirically discovered directions with after-the-fact labels and no algebra over them.
- **Cross-architecture reach on models we do not own** — read across three open-weight families (Pythia/GPT-NeoX, OLMo, Qwen) up to 20B. Internal white-box tooling generally requires owning the weights.

**Where standard tooling is ahead — stated plainly:**

- Scale and production maturity (frontier-size models, hosted infrastructure, a closed loop back into retraining).
- A working activation-steering lever for behavior. CAS Harness's *general* behavioral steering did not beat its norm-matched random control; only drive-local conditioning is currently licensed.

**The single most important open question — the thing I most want pressure-tested:**

The licensed core claim is deliberately narrow: *CAS-shaped structure is linearly readable from model activations and is causally load-bearing, across six model points and three families up to 20B.* What is **not yet established** is whether that structure is **CAS-specific**, or simply a generic semantic partition that any coherent ontology of similar shape would also recover. The first blind matched-taxonomy comparator returned an indeterminate **GREY** (not a pass); a signal-versus-leakage adjudication is still **OPEN**; the strongest readout peaks at an early layer. Until those close, the defensible reading of the headline numbers (e.g., the 95.6% 40-Element readout at 20B) is "the model encodes this distinction more strongly than a bag-of-words baseline" — **not** "CAS-specific cognition."

So the question CAS Harness ultimately poses to a reviewer is twofold: can model behavior and internal signals be turned into a structured, preservable, comparable review record a human can challenge — and is the CAS structure that record is built on actually privileged, or just one workable relabeling of generic structure?

## Current Boundaries

This should be reviewed as an evidence and explanation layer, not as a finished safety certification system.

It is not currently claiming:

- customer-production `ACCEPT` verdicts
- frontier-scale validation above the tested scope
- prompt-injection prevention, removal, or reversal
- hallucination prevention
- general AI safety certification
- proof that CAS is uniquely superior to every matched alternative

Those items are still `OPEN` / `NOT LICENSED` unless a specific test closes them.

## What Exists Now

Current work includes a public Noetic Compass platform concept, a formal CAS notation framework, compiler-grounded CAS / CAS Native research, CAS Harness experiments on open-weight models, and Evidence Packet / WORM preservation work in the production path.

The areas that most need stronger proof are:

- whether CAS adds information beyond good matched controls
- whether CAS-specific notation is better than alternative taxonomies
- whether internal signals are strong enough for reliable audit use
- whether the product path is clean enough for outside users
- whether reviewers actually find the explanations useful

## What I Want Feedback On

I am looking for grounded technical critique before I overbuild, overclaim, or send the wrong material to the wrong audience.

The questions I most want answered are:

1. Is this meaningfully distinct from existing evaluation, debugging, and interpretability workflows?
2. Where are the claims too weak, too broad, or too early?
3. What evidence would you want before taking this seriously?
4. What should be removed, simplified, or tested next?
