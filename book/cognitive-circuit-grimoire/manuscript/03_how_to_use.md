# How to Use This Grimoire

This is a bench manual. It is meant to sit open beside the work, spine cracked,
with your own numbers written in the margins. It is not meant to be read once
and shelved.

That has consequences for how it is built, and knowing them will save you time.

---

## The book has four parts and they are not equally urgent

**Part I — Foundations** is the notation and the physics. Five chapters. You
cannot skip these. Everything after them is written in a language taught here,
and a reader who skips to the board catalog will find themselves looking at
`^3^P_{F7}|T` and guessing. Guessing produces circuits that do not work and,
worse, circuits that appear to work.

**Part II — The Component Library** is the parts bin. Six chapters, one per
component class, each with a datasheet. You do not have to read Part II
straight through. You do have to read Chapter 10 before you design anything,
because the Cognitive Junction Transistor is in every board in this book and
selecting its parameters badly is the single most common way an operation
fails.

**Part III — The Board Catalog** is nine complete boards. Read Chapter 12
first — it teaches you to read a schematic — then go to whichever board you
need. The chapters are deliberately independent. You can read Chapter 20 on
self-programming without having read Chapter 16 on conditioning, and most
readers should.

**Part IV — Operations** is what you do with a board once you have one:
gating it, measuring it, calibrating it, and refusing to run it. Chapter 24,
the Cognitive Safety Board, is the last chapter because it is the one that has
to hold everything before it. It is not optional and it is not an appendix.

---

## Every chapter has the same shape

Once you have read two chapters you will know where to look in all of them.

| Element | What it is for |
|---|---|
| **Cold open** | A concrete thing — an object, a scene, a failure. No throat-clearing. |
| **Numbered sections** | The body. The section numbers match the table of contents exactly. |
| **Bench Notes** | The counterintuitive result, the thing that breaks, or a check you should run by hand. At least two per chapter. These are where the hard-won material lives. |
| **Parameter tables** | Every component and every board has one. Values, ranges, and what fails outside them. |
| **CCDL listings** | The circuit as text. Every listing in this book is one a validator would accept. |
| **Worked example** | Real numbers carried from input to output. Not a sketch. |
| **Failure modes** | A table: the mode, its mechanism, what you observe, and the fix. |
| **Test points** | TP1 through TP4. What each reads, and the expected range. |
| **What This Chapter Established** | Claims, not a summary. If you disagree with one, you know exactly where to argue. |
| **Exercises** | Answered in full in Appendix E. None are left to the reader. |

---

## On the parameters

**Every number in this book is a design choice, not a measurement.** When
Chapter 13 says the amplification stage runs at β=2.4, that is a specified
value with a stated reason and a stated failure mode at other values. It is not
a reading taken off an instrument, and the book never pretends otherwise.

This matters because the alternative — presenting chosen values as measured
ones — is how a framework becomes unfalsifiable. Where something *has* been
measured, the book says what was measured and how. Where it has not, it says
that too.

---

## On the dangerous chapters

Five chapters in Part III analyse systems built to act on people who did not
consent: conditioning, hypnosis applied by an operator, advertising, Overton
progression, and information operations.

They are written as **structural analysis for detection, resistance, and
reversal**, and they are written that way throughout — not with a warning
bolted on the front. Concretely:

- Circuits whose purpose is to act on a non-consenting person carry a
  **DETECTION-ONLY SCHEMATIC — DO NOT BUILD** banner. They are drawn so you can
  recognise one, not so you can build one.
- The book explains **mechanism**, never protocol. You will learn how a trigger
  is architected. You will not find a script, a sequence, or a procedure.
- **Every coercive board ends with its counter-circuit**, and the counter gets
  equal or greater depth. Chapter 16 ends in the Deprogramming Board. Chapter 19
  ends in the hearts-and-minds counter. Chapter 18's payload is consumer-side
  detection.

Self-directed work is a different category and is written differently. Chapter
20, self-hypnosis in Chapter 17, and the desire operations in Chapter 13 act on
the operator's own mind with the operator's own consent, and they are written
fully and practically.

**Nothing in this book is medical or psychiatric advice.** It does not treat
trauma, dissociation, addiction, or mental illness, and it must not be used as
if it did. If you are unwell, or if something in these chapters describes
something that happened to you, see a qualified clinician. Nothing here changes
that, and nothing here substitutes for it.

---

## What you need

Nothing but a pen. There is no software to install, no hardware to buy, and no
membership to join.

You will want a notebook. Chapter 22 introduces a tracking sheet and Appendix H
reproduces it blank; the sheets are where an operation stops being a feeling and
becomes data you can look at three weeks later.

**No electronics background is assumed.** Every electrical concept the book uses
is taught at the point of need, in passing, in a paragraph. If you already know
what a saturating transistor is, those paragraphs will read as review and you
can move through them quickly.

**No CAS background is assumed either.** Chapter 2 teaches the entire notation
from nothing.

---

## The companion volumes

This book is the fourth in a series and does not repeat what the others own.

| Volume | Owns |
|---|---|
| *Thinking in Cognitive Architecture* | the framework itself — the ten Noetics, four Domains, seven Drives, four Registers |
| *CAS PCBA Engineer* | the component library and five reference boards, in engineering depth |
| *Reality Engineering* | the Tootra Kabbalistic System — forty Elements, seven Foundations, twelve Prerequisites |
| **this book** | applied boards for operations the others do not cover |

You do not need any of them to read this one. Where this book restates
something a companion volume owns, it restates it correctly and tells you where
the full treatment lives.
