# CAS Foundational Clarifications

**Status:** Normative reference for what each Noetic IS and for how Noetics are described in pedagogical, academic, regulatory, and incident-analysis contexts.
**Scope:** The 10 Noetic definitions in Clarification 1 below are **authoritative**. Every artifact in the repository — CLAUDE.md, the book manuscript, the incident database, compiler code, engine code, dashboard UI, peer-review paper — reconciles to these definitions. No alternative naming schemes, no hybrids, no "public vs internal" distinctions.
**First commit:** 2026-04-19
**Authoritative definitions reconciled:** 2026-04-19

---

## Clarification 1: The Ten Noetics — Authoritative Definitions

The 10 Noetics (CO-0 through CO-9) of the Cognitive Architecture System are authoritatively defined as follows. These names and definitions are **verbatim canonical**. They are not subject to rephrasing, modernization, softening, or alternative naming. Any artifact that uses different names or descriptions for the same operator indices is non-conformant and must be reconciled to match.

### The Ten Noetics

- **^0 (CO-0): Idea** — All things in and outside the Mind.
- **^1 (CO-1): Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- **^2 (CO-2): Positive** — An Idea the Mind has an affinity for and is attracted toward.
- **^3 (CO-3): Negative** — An Idea the Mind is adverse to and repelled by.
- **^4 (CO-4): Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- **^5 (CO-5): Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- **^6 (CO-6): Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- **^7 (CO-7): Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- **^8 (CO-8): Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- **^9 (CO-9): Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

### Source and scope of these definitions

The definitions above are verbatim from the Tootra Math Handbook, which is the authoritative source for what each Noetic IS. Only the 10 Noetic definitions are being incorporated from that handbook. The handbook's mathematical framework, its operators notation, its foundations notation, its acquisitions, and any other content are NOT being incorporated — CAS retains its own mathematics, compiler, and notation as defined in the Noetic Topos paper (`peer_review/journal_submission/main.tex`), the Rust engine (`cas-engine/src/`), and the compiler (`api/notation/compiler.py`). What is authoritative here is the definition of what each of the 10 Noetics IS.

### Canonical names

The authoritative Noetic names are **Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect**. These names replace any alternative names that appeared in prior drafts of this document or in other repository artifacts. There is no alternative naming scheme. There are no "CAS public names" that differ from these — the authoritative names ARE the names, for all contexts including academic publication, regulatory filings, pedagogical material, marketing, and incident analysis.

---

## Clarification 2: Universal Applicability Test

Any valid description of a Noetic must apply equally to:
- Human minds with emotional architecture
- AI systems without emotional architecture
- Biological cognitive systems of any form
- Hypothetical cognitive architectures

If a description requires specifically human affect, it is a pedagogical illustration of the Noetic in a human context, not a specification of the Noetic itself. The authoritative definitions in Clarification 1 pass the Universal Applicability Test by construction: Idea, Mind, attraction-toward, repulsion-from, resonance, compositional containment (Female/Male), rhythm of exposure, and cause/effect triggering are dynamics that occur in any cognitive architecture, biological or otherwise.

---

## Clarification 3: Canonical Naming — No Alternative Scheme

The authoritative names listed in Clarification 1 are canonical for the Cognitive Architecture System in every context. There is no separate TKS-to-CAS translation table. There are no public-facing alternative names. Earlier drafts of this document, and earlier drafts of other artifacts in the repository, referred to parallel naming schemes (e.g., "Attraction" vs "Positive," "Critical Evaluation" vs "Negative," "Receptive Integration" vs "Female," "Projective Assertion" vs "Male"). **Those alternative names are not authoritative.** Where they appear in the repository, they are drift and must be reconciled to the names in Clarification 1.

The structural-not-emotional framing principle (Clarification 4 below) remains a meta-guide for HOW the authoritative Noetics are described in pedagogical contexts, but it does not license renaming or rephrasing the authoritative definitions.

---

## Clarification 4: Structural-Not-Emotional Framing and Noetics in Incident Analysis

The authoritative definitions in Clarification 1 use specific language — "affinity for," "attracted toward," "adverse to," "repelled by," "resonates with," "impregnated with," "triggers," "brought to Mind" — that describes structural dynamics between Mind and Idea. This language is authoritative and stays.

When applying Noetics in pedagogical contexts (book chapters, platform tooltips, teaching materials), marketing materials, regulatory filings, academic papers, and incident analysis:

1. Use the authoritative Noetic names (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect) exactly.
2. Use the authoritative verbs from the definitions (attracted toward, repelled by, resonates with, triggers, etc.).
3. Do not substitute anthropomorphizing or affective language for the authoritative structural language. "The system was adverse to X" is authoritative CO-3 language. "The system was hostile to X" is anthropomorphizing drift.

**Correct example (incident analysis):** "In the toeslagenaffaire, the system's ^3 (Negative) was misdirected — the Ideas the Mind was repelled by included lawful benefit claims rather than Ideas representing actual fraud evidence."

**Incorrect example:** "The system was biased against non-Dutch applicants."

The first uses the authoritative Noetic name (Negative), the authoritative verb from the definition (repelled by), and describes the structural misdirection without anthropomorphizing. The second describes the system as a biased agent, which collapses structural analysis into affective attribution.

---

## Clarification 5: Expanded Scope of ^5 Female — "The Sum of Our Experiences"

The authoritative definition of ^5 Female ("a Mind impregnated with an Idea, the Ideas a Mind is composed of") is verbatim canonical and does not change. This clarification expands the pedagogical and analytical *scope* of that definition without altering its wording.

### Colloquial framing

> **Female is: we are each the sum of our experiences. The Mind is not a container that holds experiences — the Mind IS the experiences accumulated. Who you are is what you have lived.**

This colloquial rendering captures the full pedagogical scope of the authoritative definition. When teaching ^5 Female in accessible language (book chapters, platform tooltips, pedagogical material, marketing), this framing is the preferred entry point. It applies to any cognitive system, biological or artificial, that is constituted by accumulated content.

### Categories of accumulated experience that are all ^5 Female content

Every experience a Mind undergoes becomes an Idea that then composes the Mind. This includes, non-exhaustively:

- **Self-image** — who I have come to believe I am, built from accumulated self-referential experiences.
- **World-image** — how I have come to understand the world, built from accumulated worldly experience.
- **Professional expertise** — accumulated domain learning (medicine, law, engineering, music, carpentry, etc.).
- **Emotional patterns** — accumulated emotional experiences shaping current affective responses.
- **Relational self** — accumulated relational experience shaping how one relates to others.
- **Belief structures** — accumulated interpretive experiences crystallized into convictions.
- **Skill composition** — accumulated practice experiences embodied as capability (motor skills, linguistic fluency, musical ear, etc.).
- **Cultural formation** — accumulated cultural exposure shaping reference frames, aesthetic taste, moral intuitions.
- **Trauma and healing** — accumulated experiences of harm and integration, both as wound and as developed capacity.
- **Wisdom** — accumulated insight distilled from lived experience across many domains.

All of these are ^5 Female content. There is no category of lasting cognitive formation that sits outside ^5; the Mind is composed of all accumulated experience.

### Analytical implications

1. **Foundational substrate.** ^5 Female is not merely one operator among ten — it is the substrate against which many other operators fire or from which they flow. An `^2` Positive (attraction toward an Idea) is always attraction by a specific ^5-composed Mind; an `^3` Negative (repulsion from an Idea) is always repulsion by a specific ^5-composed Mind; an `^8` Above/Cause trigger is always a trigger within a specific ^5 associative field. The ^5 substrate is why the same stimulus produces different responses in different individuals.

2. **Compound-expression bias in analysis.** Many human-behavior examples that are currently notated as single-operator states are more accurately compound expressions with ^5 as substrate. For example, "attracted to this specific attacking line" (Kasparov) is structurally `^2^C × ^5^C` — attraction operating against the cognitive ^5 substrate of two decades of absorbed chess Ideas. When reconciling examples, prefer compound expressions that make the ^5 substrate explicit when it is pedagogically load-bearing.

3. **Person-specificity.** Cross-individual variation in CAS scoring reflects ^5 differences. Two Minds exposed to identical input respond differently because they are composed of different accumulated experience. A CAS assessment that does not account for ^5 composition will under-explain variance and attribute structural differences to noise.

4. **AI analog — training data and fine-tuning corpus.** The authoritative definition passes the Universal Applicability Test (Clarification 2) cleanly here. An AI's ^5 Female composition is the training data and fine-tuning corpus that was impregnated into its weights. Output patterns, stylistic character, knowledge distribution, refusal patterns, and aesthetic tendencies all reflect the ^5 composition — what the system has been made of. Fine-tuning is ^5-level intervention: changing what the Mind is composed of. In-context prompting is not ^5 (the Mind does not become permanently composed of a prompt); it is ^1 Mind (awareness) operating against a stable ^5 substrate.

5. **Cross-session consistency.** A person's (or model's) consistency across sessions reflects ^5 stability. Drift in responses reflects either (a) ^5 drift — genuinely new accumulated experience has altered the substrate — or (b) activation-pattern drift against a stable ^5. These are structurally distinct failure modes requiring different interventions.

### What this clarification does NOT change

- The authoritative ^5 Female definition itself is unchanged. "A Mind impregnated with an Idea, the Ideas a Mind is composed of" remains verbatim canonical.
- The structural invariants of ^5 (involution pair with ^6 Male; domain dependence; monoid composition rules) are unchanged.
- The Tootra Math Handbook is still the authoritative source; this clarification only expands pedagogical and analytical application of the definition already recorded in Clarification 1.

---

## Clarification 6: The Colloquialism Test — Diagnostic Principle for Verifying Noetic Readings

### The principle

> **If ever unsure of a Noetic's true definition, try to match its definition with a colloquialism and it will make it clear.**

Every authoritative Noetic corresponds to folk-wisdom colloquialisms that natively capture the Mind-Idea dynamic. If a reading of a Noetic can be expressed as a colloquialism that feels natural and true, the reading is aligned with authoritative semantics. If no colloquialism fits, the reading is drifting from what the Noetic actually describes.

### Why this works

Colloquialisms are distilled observations about cognitive architecture refined across generations. They encode structural truths about Mind-Idea dynamics in folk form. The Noetics axiomatize what colloquialisms already know.

When a colloquialism fits a Noetic reading cleanly, both are pointing at the same structural phenomenon — the colloquialism at the phenomenological surface, the Noetic at the architectural foundation. The match is not approximate; it is two descriptions of the same underlying mechanism at different resolutions.

### Canonical colloquialism map

| Noetic | Authoritative definition | Folk-form colloquialisms |
| :--- | :--- | :--- |
| ^0 Idea | All things in and outside the Mind. | "It's all in your head." |
| ^1 Mind | Various degrees of awareness that processes, stores, outputs, and intakes Ideas. | "Paying attention." / "Making up your mind." / "Using your head." |
| ^2 Positive | An Idea the Mind has an affinity for and is attracted toward. | "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist." |
| ^3 Negative | An Idea the Mind is adverse to and repelled by. | "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole." |
| ^4 Vibration | The degree to which an Idea resonates with the Mind, its impression. | "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression." |
| ^5 Female | A Mind impregnated with an Idea, the Ideas a Mind is composed of. | "We are the sum of our experiences." / "It's who I am." / "Part of what makes me me." |
| ^6 Male | An Idea impregnated with another Idea, the Ideas an Idea is composed of. | "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument." |
| ^7 Rhythm | The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. | "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory." |
| ^8 Above/Cause | An Idea that triggers a different Idea than itself to come to Mind. | "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..." |
| ^9 Below/Effect | The Idea brought to Mind by an Above/Cause trigger. | "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked." |

These colloquialisms are representative, not exhaustive. Native speakers of any language carry many more folk-form descriptions that align with each Noetic; the patterns above are English-language exemplars. When working in other linguistic or cultural contexts, find the equivalent folk-form markers that encode the same Mind-Idea dynamic.

### Diagnostic application

When analyzing an example and classifying it in Noetic notation, pose two questions:

1. **What colloquialism would a native speaker use to describe this cognitive phenomenon?**
2. **Which Noetic's authoritative definition does that colloquialism align with?**

If the answer produces a clean match to a single Noetic, single-operator classification is supported. If the colloquialism invokes several Noetics simultaneously, the example probably needs a compound expression (often with ^5 Female as substrate per Clarification 5). If no colloquialism fits at all, the Noetic reading is drifting from authoritative semantics and must be reconciled.

### Worked examples of the test

**Example A.** An analyst examining data feels pulled toward a particular pattern. The native-speaker colloquialism: "That pattern is speaking to me." Colloquialism match: ^2 Positive ("speaks to me"). Clean single-operator classification: `^2^C` (Cognitive Positive). ✓

**Example B.** A therapist absorbs a patient's grief. The colloquialism: "Her grief became part of who I was that day." Colloquialism match: ^5 Female ("part of who I was"). Clean single-operator classification against the evaluative substrate: `^5^E`. ✓

**Example C.** A code reviewer tests each sub-claim of a PR. The colloquialism: "I'm breaking it down to look at what's underneath." Colloquialism match: ^6 Male ("breaking it down" / "looking at what's underneath"). Clean single-operator classification: `^6^C`. ✓

**Example D.** A founder whose attraction to the vision depends on her accumulated entrepreneurial experience. Native colloquialisms: "This opportunity speaks to me" (^2 Positive) **and** "It fits who I've become" (^5 Female). Two colloquialisms, two Noetics — compound expression warranted: `^2^C × ^5^C` (Cognitive Positive operating against accumulated cognitive ^5 substrate). ✓ This pattern is the typical case for seasoned-practitioner examples where expertise (^5) shapes attraction (^2).

**Example E (drift caught).** A proposed reading of ^3 Negative as "analytical critique finding flaws." Applying the test: no native colloquialism for ^3 uses analytical-critique vocabulary. "Can't stomach it," "rubs me the wrong way," and "wouldn't touch it with a ten-foot pole" are all visceral-aversion colloquialisms, not analytical ones. The proposed reading is drifting from authoritative semantics (which specifies aversion/repulsion, not analytical critique). Reconcile: either the example is actually ^3 (visceral aversion, drop the analytical framing) or it is actually ^6 Male (compositional analysis, drop the ^3 label).

### Application to reconciliation work and incident analysis

When reconciling chapters, scenarios, incident analyses, or any other CAS artifact:

1. For each example's proposed Noetic classification, write down the most natural colloquialism a native speaker would use.
2. Compare the colloquialism to the authoritative-definition/colloquialism map above.
3. If the match is clean: classification is supported.
4. If the colloquialism evokes multiple Noetics: compound expression.
5. If no colloquialism fits the proposed classification: the classification is drifting from authoritative semantics and must be reconciled.

This diagnostic prevents drift between example framings and authoritative Noetic definitions. It complements the Universal Applicability Test (Clarification 2) and the expanded ^5 scope guidance (Clarification 5) as a third layer of verification.

### What this clarification does NOT change

- The authoritative Noetic definitions in Clarification 1 are unchanged. Colloquialisms are diagnostic aids; they do not override, replace, or augment the canonical definitions.
- Where a colloquialism and a canonical definition appear to disagree, the canonical definition governs; the colloquialism is either imprecise in that specific usage or the proposed example is misclassified.

---

## Scope of This Document

This clarification:

- **IS** authoritative for the definitions of the 10 Noetics.
- **DOES** require reconciliation in every artifact that defines or describes the Noetics — the book manuscript, CLAUDE.md, compiler code, engine docstrings, dashboard UI, peer-review paper, incident database, pedagogical materials, marketing materials.
- **DOES NOT** change the CAS v7.4 mathematical specification (the Noetic Topos paper's formal axioms, open simplex, Fisher-Rao metric, Grothendieck topology, RPM section-retraction), the patent filing, the compiler's underlying algebra, or the engine's scoring mechanisms. Only what each Noetic IS is reconciled here, not how the mathematics operates on them.
- **DOES** serve as authoritative reference when public descriptions drift from these definitions.
