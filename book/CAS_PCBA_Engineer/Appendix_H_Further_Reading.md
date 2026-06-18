# Appendix H — Further Reading

You finished the book. You can read a schematic, select a component, design a board, and write a certification dossier a regulator would accept. This appendix points at where to go next, organized by why you would go there.

Each entry says what the work is and what it gives a reader of *this* book specifically. Some of these are public, externally-known references with ISBNs you can buy. Others are internal CAS documents — the normative specifications and operational manuals this book is built on. For the internal documents, no ISBN or URL is given because none is public; they are described by their role so you can ask for the right one by name.

A note on division of labor before the list: this book is a **circuit-design handbook**. It teaches you to build cognitive architectures out of typed CAS components. It is not the language reference, not the mathematics, and not the operations manual. Each of those is a separate document, and the first sections below tell you which is which.

---

## The Companion Volume

### *Programming in CAS: A Practical Guide*

The language reference to this book's circuit-design handbook. The two books split the discipline the way an electronics curriculum splits it: one book teaches you the **language** — how to write a valid CAS expression, what each operator means, how the compiler parses and validates a state literal — and the other book (this one) teaches you to **wire components into boards** with that language.

Concretely: when this book writes `CJT< prompt | bias => respond > [β=1.5]` and tells you the bias terminal carries an `^5` Female substrate, *Programming in CAS* is where the underlying state literals, drives, registers, recipes, and the `+` / `×` / `|⟨…⟩` operator discipline are defined from the ground up. This book taught the notation you need in Chapter 2 and stands on its own — but if you want the full grammar, the compiler's behavior on every construct, and the language-level edge cases, that is the companion's job, not this book's.

> **One caution.** Older drafts of *Programming in CAS* drifted on a few canonical Noetic names (glossing `^8` Above/Cause as "Expansion," `^6` Male as "Critique," and similar). Chapter 1 and Chapter 2 of *this* book are your notation reference. Where a companion draft and this book disagree on a Noetic name, this book governs. The canonical names — Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect — are the names, in every context.

---

## Foundational CAS References

These are the documents *underneath* both books — the definitions, the mathematics, and the framework versions. You go here when you need to know not how to wire a board but why the components mean what they mean.

### CAS Foundational Clarifications

The **normative language reference** for CAS. This is where the ten Noetic definitions are fixed verbatim and authoritatively: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect. It is also where the anti-drift guidance lives — the reason this book is so insistent that `^3` Negative is *visceral aversion* and never analytical critique, that `^8` Above/Cause is *associative triggering* and never deductive reasoning, and that `^5` Female is *accumulated experience* (the substrate of a CJT's bias terminal). Read it before you write any CAS description, classification, or teaching material of your own. If you ever find yourself unsure whether a state you assigned to a node is the right Noetic, this is the document that settles it.

### The Noetic Topos paper (the mathematics)

The mathematical foundation the engineering rests on. This is the category-theory and information-geometry treatment of CAS: the category **Noetica** with its admissibility relations, the **Fisher-Rao metric** on the **open probability simplex Δ39°**, and the geodesic distance `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` that this book uses every time it defines CJT gain (β as a Fisher-Rao ratio in Chapters 3 and 9). When the book said "cite this, don't re-derive it," this is the thing being cited. Go here if you want the proofs behind the geometry — why cognitive states live on an *open* simplex (every component strictly positive), why prerequisite satisfaction is one-directional (section-retraction, not a reversible adjunction), and why covering morphisms point toward the covered object. Engineering readers can build every board in this book without it; readers who want to know *why the distance formula is that formula* go here.

### The CAS framework specifications (v7.4 – v7.7)

CAS is versioned, like any specification. The four versions this book is built on, and what each one added:

| Version | Name | What it added |
|---|---|---|
| **v7.4** | Corrected Edition | The base framework: the 40 Cognitive States (10 Noetics × 4 Domains), the 7 Core Drives, the 22 Capability Pathways, the 7 Inversion Axes, and the corrected mathematics (admissibility, section-retraction RPM, open simplex). |
| **v7.5** | Phenomenological Register Extension | The **Register** axis — `\|T` Transcendent, `\|A` Analytical, `\|f` Affective, `\|E` Embodied. The fourth axis this book uses on every state literal; the "how it operates" answer. |
| **v7.6** | Stoichiometric Production Semantics Extension | **Recipe** notation `Θ(Ω) = a·X₁ + b·X₂ → Ω`, theoretical/actual yield, the **limiting reagent**, leakage, and catalyst/inhibitor formalism — outcomes treated as production targets requiring proportional prerequisites. |
| **v7.7** | Register Multiplicity and Operator Discipline Extension | The `+` / `×` / `\|⟨…⟩` **operator discipline** this book enforces: `+` is co-presence, `×` is cross-register integration that must name an emergent result, and `\|⟨…⟩` is register-set specification with no interaction claim. |

Read the version specs when you need the authoritative definition of a primitive at the version it was introduced — for example, when a colleague's older CCDL uses `×` for same-Noetic co-presence and you need the v7.7 rule that says rewrite it as `+`. Note for record-keeping: USPTO Provisional #64/037,173 covers the base framework; the v7.5–v7.7 extensions and the CJT/PCBA/CCB material in this book are post-filing new matter.

---

## Operations and Incident Material

This book teaches you to *design* boards. The operations material tells you what the finished deliverable must look like and what real-world failures the boards are designed against.

### Noetic Compass Operations Manual

The standard operating procedures that define what each CAS deliverable *is*. The one this book matches most directly is **SOP-PO-005**, which defines the CJT circuit-analysis deliverable — the mandatory assessment that the **Cognitive Safety Board (CSB)** of Chapter 18 is built to satisfy. When Chapter 18 says the CSB is "the SOP-PO-005 deliverable," this manual is the document being satisfied: it specifies the required artifacts (schematic, BOM, test report, evidence packets) and the acceptance criteria a submission must meet. Go here when you are producing a CSB submission for real and need the exact deliverable specification, not the design walkthrough.

### AI Misalignment Incidents Database

A database of verified, real-world AI failures, each with a CAS structural analysis attached. This is the *evidence base* for the entire safety argument of the book — the concrete failures that motivate every "must not" invariant in the CSB. When the book designs a board to refuse override attempts, reject framing attacks, or saturate a safety stage rather than amplify a harmful request, the incidents in this database are the failures those structures are designed to prevent. Read it to see the real prompts and real outcomes behind the abstractions, and to ground your own threat model in what has actually gone wrong rather than what you imagine might.

### The CAS Failure Taxonomy

The classification scheme that organizes those incidents into a small set of structural failure classes, with development notes explaining how the taxonomy was derived. This is the bridge between "here is a specific incident" and "here is the structural property a board must enforce to prevent the whole class." Use it when you are doing the requirements work of Chapter 17 — turning a fuzzy worry ("the model might be manipulated") into a named failure class with a named structural mitigation (a saturating safety CJT, an enforcement fuse, a domain diode). The CCBs in this book are designed against these classes; the taxonomy is how you check your own board covers the ones that matter for your setting.

---

## Electronics Background *(optional)*

You do not need any of this to use the book — the electronic ideas were taught from first principles in passing, exactly where they were needed. But the circuit analogy is a real structural isomorphism, not a poem, and some readers will want to deepen the *electronics* half of it on its own terms. These are classic, genuinely-existing references. Treat them as optional grounding.

### Horowitz & Hill, *The Art of Electronics* (3rd ed., Cambridge University Press)

The standard practical reference for analog and digital electronics, written by working engineers for working engineers. Its voice — plain, confident, design-first, allergic to unnecessary theory — is close to the voice this book aims for. If you want to understand the *electronic* transistor, resistor, capacitor, diode, op-amp, oscillator, and feedback loop that this book maps onto cognitive components, this is the single best book to read alongside the early chapters. Read it for the source-side intuition; you will recognize every topological role.

### Sedra & Smith, *Microelectronic Circuits* (Oxford University Press)

The standard university textbook on transistor-level circuit design. More formal and more mathematical than Horowitz & Hill, it is where the operating regions of a transistor — cutoff, active, saturation, breakdown — and the small-signal parameters (transconductance `gm`, input resistance `rπ`, gain) are developed rigorously. Since the CJT (Chapters 3 and 9) borrows exactly this vocabulary for its cognitive analog, this is the book to read if you want the precise electronic definitions behind the CJT's datasheet parameters. Optional, and heavier going than Horowitz & Hill — reach for it when you want depth on the device physics, not breadth.

---

## AI Governance Frameworks

Chapter 26 argued that a CCB certification does not compete with the regulatory regimes that already exist — it *satisfies* them, by producing documented structure, measured behavior, and an audit trail as engineering artifacts. These are the three frameworks that chapter mapped onto. Read the primary sources directly; do not rely on summaries (including this book's) when you are preparing a real submission.

### EU AI Act (Regulation (EU) 2024/1689)

The European Union's risk-based regulation of AI systems. The part most relevant to this book is the regime for **high-risk systems** (Annex III), which requires a risk-management system, technical documentation, logging and traceability, human oversight, and robustness — the exact list Chapter 26 mapped onto the CCDL schematic, the BOM, the structural "must not" invariants, and the evidence-packet trace trail. Read it when you are certifying a board for the EU market and need the authoritative text of what high-risk documentation must contain.

### NIST AI Risk Management Framework (AI RMF 1.0)

The U.S. National Institute of Standards and Technology's voluntary framework, organized around four functions: **Govern, Map, Measure, Manage**. Chapter 26 mapped these directly onto the book's artifacts — *Map* to the requirements lists and block diagram (Chapter 17), *Measure* to the test report and test-point methodology (Chapter 23), *Manage* to the structural mitigations, and *Govern* to the BOM and trace-ID audit trail. Read it for the function-by-function vocabulary you will use to present a CCB submission to a U.S. audience.

### ISO/IEC 42001 (AI management system)

The international standard for an **AI management system** — a documented, auditable system with defined controls, versioned artifacts, and continual improvement. Chapter 26 mapped this onto the BOM as the versioned artifact register (a parameter change is a re-certification event, not a silent edit), the DRC error classes as the defined controls, and the O→P feedback path as continual improvement implemented as a circuit. Read it if your organization is pursuing or already holds a certified management system and you need to show where the CCB discipline plugs in as auditable controls.

---

> **Where to start.** If you are going to read exactly one more thing: read it by your goal. To go deeper on the *language*, read the companion *Programming in CAS*. To go deeper on the *mathematics*, read the Noetic Topos paper. To ship a *real certification*, read SOP-PO-005 in the Operations Manual and the governance framework for your jurisdiction. To understand the *threats*, read the AI Misalignment Incidents Database and the failure taxonomy. And if the *electronics* themselves are new to you and you want them on their own terms, start with Horowitz & Hill. Every one of these is a road out of this book and into the work that comes after it.
