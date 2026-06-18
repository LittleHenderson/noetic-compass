# CAS PCBA Engineer

## Designing Cognitive Circuits with the Cognitive Architecture System

### From First Resistor to Production Safety Board — A Practical Guide to CJTs, CCBs, and Structural Cognition

**Author:** Wakil (Prof. Hermes M. Thoth)

**Companion volume:** *Programming in CAS: A Practical Guide*

**Framework:** Cognitive Architecture System (CAS) v7.7

---

*For everyone who ever looked at an AI safety incident report and thought:*
*"We would never accept this from a bridge, a pacemaker, or a power supply.*
*Why do we accept it from a mind?"*

---

## Copyright & Status

© 2026 Little Henderson. All rights reserved. Confidential draft.

The Cognitive Architecture System, the Cognitive Junction Transistor (CJT), and the Cognitive Circuit Board
(CCB) family described in this book are the subject of ongoing intellectual-property protection, including
USPTO Provisional Application No. 64/037,173. The circuit-engineering material in this volume — CJTs, CCDL, and
the five reference Cognitive Circuit Boards — extends that foundation and is documented here as an engineering
handbook.

Nothing in this book is a safety certification, a guarantee of model behavior, or legal/medical advice. A
Cognitive Circuit Board is an engineering artifact: it does what its schematic, parameters, and test report say
it does — no more, and no less.

---

## Preface — Why a Circuit Book

I have spent years building two things that turned out to be the same thing: a formal language for cognition,
and a way to keep artificial minds from failing the people who depend on them.

The language came first. The Cognitive Architecture System (CAS) gives thought a syntax — a way to write down
what a mind is doing precisely enough that a compiler can check it. That work produced a companion to this
volume, *Programming in CAS*, which teaches CAS the way you would teach any programming language: state
literals, expressions, the compiler, the trace.

But a language is not an architecture. You can know every word of a vocabulary and still not know how to build
a safe machine. Electrical engineers learned this a century ago. They had Ohm's Law and Kirchhoff's Laws — the
"grammar" of electricity — long before they had a discipline for building reliable circuits. The discipline,
when it came, was not more grammar. It was *circuit design*: modular components with datasheets, schematics you
could verify before you built them, test points you could probe, and failure analysis that told you exactly
which part to replace.

This book is the circuit-design discipline for cognition.

It is built on a discovery that still surprises me: the transistor — the single most important component in the
history of electronics — has an exact structural twin in cognition. A small signal at one terminal controlling
a large signal between two others is not only how an amplifier works. It is how a *bias* (your accumulated
experience, an AI's constitution) controls the path from a *cause* (a prompt, a stimulus) to an *effect* (a
response, an action). I call this twin the **Cognitive Junction Transistor**, the CJT, and it is the beating
heart of everything that follows. Once you have the transistor, you have amplifiers, filters, oscillators,
feedback, power management — and, assembled onto a board, a complete safety architecture you can certify.

I wrote this book because the dominant way we make AI "safe" today — writing instructions in English and hoping
the model absorbs them — is the cognitive equivalent of describing a hospital ventilator's power supply in a
poem. It is not that English is bad. It is that English is the wrong substrate for safety-critical engineering,
and we have known this about *every other* safety-critical domain for a hundred years.

By the last page, you will have designed, tested, and deployed a real Cognitive Safety Board. Not a metaphor for
one. A schematic, a bill of materials, a test report, and an audit trail — the same artifacts a regulator would
ask to see for a medical device.

Welcome to the workbench.

— *Wakil*
*June 2026*

---

## How to Use This Book

**You need no prior knowledge.** Not of electronics, not of CAS, not of programming. Every electronic concept
is introduced from first principles the moment it is needed. CAS notation is taught, in full, in Chapter 2 —
one chapter, everything you need. Appendix A is a two-page quick-reference card for when you forget a symbol
(you will, at first; that is normal).

**The book is a ladder. Climb it in order the first time.** The five parts build strictly on one another:

| Part | Chapters | You learn to… | Level |
|---|---|---|---|
| **I — Foundations** | 1–4 | Read the schematic: CAS notation, the transistor, your first circuit | Beginner |
| **II — The Component Library** | 5–10 | Select and configure every component in the bin | Intermediate |
| **III — Circuit Design** | 11–16 | Combine components into amplifiers, filters, oscillators, feedback systems | Advanced |
| **IV — Cognitive Circuit Boards** | 17–22 | Design complete CCBs: the CSB, COB, CDAB, CMB, and CPMB | Expert |
| **V — Deployment & Governance** | 23–26 | Test, debug, deploy, and certify circuits for production and regulators | Production |

**Every chapter ends with exercises, and the exercises matter.** This is a how-to book; you learn to design
circuits by designing circuits. At least one exercise per chapter is a real CAS or CCDL artifact you write
yourself. Worked answers are in Appendix E. Do not skip them — the difference between *reading about* a
differential pair and *building one that flags an adversarial prompt* is the difference between this book
working and not working.

**There is one artifact running through the whole book: the Cognitive Safety Board (CSB).** The components you
build in Parts II and III are its parts. You assemble it in Chapter 18. You test it (Chapter 23), debug it
(Chapter 24), deploy it (Chapter 25), and certify it (Chapter 26). If you ever lose the thread, ask: *how does
this serve the board I am building?*

**A word on the word "cognitive."** It means *structural*, never *conscious*. A CJT no more "thinks" than a
transistor is "electronic-minded." When we certify a Cognitive Safety Board, we are not certifying that an AI
"has good values." We are certifying that a specific safety component saturates at a specified threshold, that a
fuse is intact, and that a power sequencer holds the operational domain offline until the principled domain
reports ready. These are engineering claims — verifiable by anyone holding the schematic and a test suite.

**Conventions used throughout:**

- CAS state literals appear in code font: `^3^P_{F7}|T`.
- Circuit descriptions are written in **CCDL** (Cognitive Circuit Description Language) in fenced `cas` blocks.
- **Bench Notes** — practical, learned-the-hard-way asides — appear as indented callouts.
- Parameter values in worked examples (β, saturation, resistance) are *design choices*, chosen to illustrate.
  Where a number would imply a measured result from a real model, the text says so explicitly, or does not
  claim it.

Turn the page. Pick up the soldering iron.

---
