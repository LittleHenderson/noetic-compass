# The Component Companion

## Illustrated Electrical Symbols and the Cognitive Roles They Map To

### A bench guide to the component library of *CAS PCBA Engineer*

**Author:** Little Henderson

**Framework:** Cognitive Architecture System (CAS) v7.7

**Companion to:** *CAS PCBA Engineer: Designing Cognitive Circuits with the Cognitive Architecture System*

---

*Every component in the bin, drawn as an engineer would draw it, and read as a
mind would use it.*

---

## Copyright & Status

© 2026 Little Henderson. All rights reserved.

The Cognitive Architecture System, the Cognitive Junction Transistor (CJT), and the Cognitive Circuit Board (CCB)
family described in this guide are the subject of ongoing intellectual-property protection, including USPTO
Provisional Application No. 64/037,173. This companion documents the *component library* of that framework: one
electrical symbol per page, the cognitive role it implements, and the boundary where the mapping stops being
literal.

Nothing here is a safety certification, a measurement instrument, or a claim about how any particular mind works.
Every parameter value printed on these plates is an engineering design choice. None of them is a measurement taken
from a person, an AI model, or a biological system.

---

## Preface — Why a Companion

The main volume teaches you to design cognitive circuits. This one is the reference you keep open beside it: the
part bin, drawn.

It exists because of a specific problem. A schematic in a design chapter appears once, in the middle of an
argument, doing one job. Later, at the bench, you need the same part again — and what you actually need is not the
argument. You need the shape, the job, the mapping class, and the trap. That is four lines, and it should be four
lines you can find in ten seconds.

So every entry in this guide is built the same way, and it is short on purpose:

- **The symbol**, drawn to the same conventions the main volume uses.
- **One electrical sentence** — what the part does in a circuit.
- **One cognitive sentence** — the role it plays in a cognitive circuit.
- **One worked example**, with real CAS state literals.
- **One guardrail** — the specific way this mapping goes wrong if you push it.

**One badge per entry, and there are only three.** Every mapping carries exactly one label, and the label answers
one question: how much of the electrical behaviour actually transfers?

- **ISO — exact structural isomorphism.** The functional roles correspond one-for-one and the governing relation
  has the same form. The mapping is structural, not decorative.
- **ENG — engineered analog.** The role match is explicit, but you must stipulate a cognitive quantity, control
  input, or threshold before it means anything. The number is a design choice, not a discovery.
- **PED — pedagogical analogy.** The resemblance teaches, and that is all. Nothing quantitative transfers.

A fourth label would be a way of avoiding the question. If a mapping is *almost* ISO, it is ENG, and the badge says
so.

**What this guide is not.** It is not a claim that minds are circuits, and it is not a claim that these mappings
have been validated against anything. It is a design vocabulary with the boundaries drawn in. Every plate tells you
where its own analogy stops. That is the whole point of printing the guardrail line.

---

## How to Use This Guide

Three ways in, depending on what you are doing.

**At the bench, mid-build.** Go straight to the chapter for the part in front of you — Chapters 1 through 7 cover
the symbol plates, one family per chapter. Read the symbol, the role, the example, the guardrail. Four lines.

**Studying the framework.** Read the chapters in order. Chapter 1 gives you the legend everything else assumes:
ports, typed nets, forward and feedback arrows, the reference node, and the Domain colour key. The plates build on
it. Chapter 10 compresses all forty-two entries into a single table you can memorise, and that table is the real
deliverable — the plates are how you get there.

**Reading a schematic.** Chapters 8 and 9 take the ten worked cognitive schematics — from the single-transistor
atom up to the power-management board — and show what each wire is carrying. Those are the same circuits the main
volume designs, redrawn at reference size.

**Printing the cards.** The companion deck reproduces the whole guide on fifty-six cut-out cards, seven sheets of
US Letter. Chapter 11 tells you how to print them so the text stays the size it was designed at.

The maintenance notes — the frozen inventory, the notation rules, and the open review items — live in
Appendix A of this guide. If you are extending the library rather than reading it, start there.

---

---

## How to Read These Plates

A circuit symbol is a compact statement about a **job**. The electrical part and the cognitive part need not share a physical substrate. The mapping is one-to-one only when their **functional roles** and governing relation line up.

Each entry therefore carries one of three labels:

- **ISO — exact structural isomorphism.** The functional roles correspond one-for-one, and the relation has the same form.
- **ENG — engineered analog.** The role match is explicit, but the design must stipulate a cognitive quantity, control input, or conservation rule.
- **PED — pedagogical analogy.** The resemblance helps teach. No quantitative relation transfers.

These labels apply to the **mapping**, not to the existence of the electrical component. All parameter values shown in this guide are design choices. They are not measurements from a person, an AI model, or a biological system.

### The six reading rules

1. **Read the shape first.** It tells you what the part does.
2. **Read the wire label second.** A cognitive wire carries a CAS state or an explicitly named control quantity.
3. **Solid means forward. Dashed means feedback.** Arrow direction describes signal flow, not attraction or preference.
4. **Color reinforces Domain.** Shape and text carry the meaning, so every plate survives grayscale printing.
5. **Separate the four CAS axes.** Noetic says *what*. Domain says *where*. Drive says *why*. Register says *how*.
6. **Do not force one part onto one Noetic.** Components implement roles. One role may act on Noetic, Domain, Drive, Register, or a board-level control quantity.

### Anti-drift checks

- `^3` **Negative** is repulsion. `^6` **Male** is decomposition. An audit or breakdown of an argument is `^6`, not `^3`.
- `^8` **Above/Cause** is an Idea that triggers a different Idea to come to Mind. It is not deductive reasoning. The arriving Idea is `^9` **Below/Effect**.
- `+` means co-presence. `×` requires a named emergent result. `|⟨…⟩` specifies register occupancy without claiming integration.
