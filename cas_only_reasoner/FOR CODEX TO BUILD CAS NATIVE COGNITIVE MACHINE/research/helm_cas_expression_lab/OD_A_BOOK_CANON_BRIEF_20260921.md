# OD-A: your PCBA book has two texts. Which one is canon?

**Why this blocks everything.** Six chapters of *CAS PCBA Engineer* have edits that were never committed. They change the exact rules a board checker would enforce. Until one text is named canon, a checker cannot honestly pass or fail a board — it can only report `OPEN:OD-A`. Every other PCBA decision waits behind this one.

- **Committed text** — commit `24f50911` (2026-08-09), also the copy in the worktree `_worktrees/helm3-lab/book/CAS_PCBA_Engineer`.
- **Edited text** — the working copy at `tksCAS/book/CAS_PCBA_Engineer`, uncommitted.

Changed: `Appendix_B` 90 lines, `Chapter_10` 67, `Appendix_C` 23, `Appendix_E` 12, `Chapter_15` 2, `Chapter_18` 2, plus 70 new `CHANGELOG` lines.

## What the edits actually do

They are not scattered. They are one correction, applied in several places: **the committed book describes Boolean logic gates in Noetic vocabulary, and the edits separate the two.**

| the committed text says | the edited text says | is the edit right? |
|---|---|---|
| `XOR` is a "dissonance detector — both `^2` and `^3` firing → conflict flag" (Ch.10:96, 104) | `XOR` fires for **exactly one**; **`AND`** is the both-active detector | **Yes.** The committed text is factually wrong. XOR is true when inputs *differ*, so it does **not** fire when both are active. |
| `NOT` is "the involution operator made discrete: `NOT< ^2^E >` yields `^3^E`" (Ch.10:98, 111) | `NOT` is a Boolean complement; it maps to a Noetic involution **only for a licensed pair** | **Yes.** A logic gate acts on a true/false flag. A Noetic involution acts on a cognitive state. Calling them the same thing is the category error your anti-drift rules exist to catch. |
| Op-amp "inverting" = "flip an interpretation to its involution pair" (Ch.10:46) | a signed arithmetic inversion around a reference; **no automatic Noetic flip** | **Yes.** Same category error. |
| Breakdown: "effect flips to its involution pair (`^2`→`^3`)" | the flip happens **only when that rule is declared** | **Yes.** Consistent with the above. |
| Capacitor stores "the experiential state being stored" | "the `^5` composition whose persistence is modeled" | **Yes.** `^5` Female *is* accumulated experience, per Clarification 1. This ties the datasheet to canon. |
| no `XNOR` | `XNOR` added to the gate production, the type list and the prefix list | **Additive.** An equivalence detector; nothing else changes. |
| `xor dissonance: XOR< attract, averse >;  // fires only when both active` (Appendix_E:327) | `gate conflict: AND< attract, averse >;  // fires only when both are active` | **Yes** — this fixes the wrong example. See the naming note below. |

**My reading: the edits correct real defects in the committed book.** One of them (XOR) is a plain mathematical error. The rest are the drift pattern your project rules name explicitly — describing one kind of operation in another's vocabulary.

## Two things to fix before committing

Both are one-line changes. I found them by reading the edited text against itself.

1. **`Appendix_B_Component_Datasheets.md` line 374** still reads
   `NOT< ^2^E >   // = ^3^E  (involution flip)`
   while the table twelve lines below it (line 386) now says `NOT` is a Boolean complement. The file contradicts itself. `Chapter_10` line 105 already carries the fixed version: `NOT< enable_flag >   // Boolean complement of one flag`. Apply the same here.

2. **`Appendix_A_Notation_Quick_Reference.md` line 137** lists six gates — `AND OR NOT NAND NOR XOR` — with no `XNOR`, and describes them as "Boolean logic on **states**". After the edit, gates act on Boolean **flags**, not states. Add `XNOR< … >` and change "states" to "firing flags".

## A naming point the reader must handle either way

`gate` is **both** a component prefix and a statement leader — **in the committed text already** (`Appendix_C` lines 136–139 list it as a prefix; line 147 lists it as a statement keyword). This is not created by the edits.

What the edits do is make the clash *reachable in a real listing*:

- committed: `gate` appears in listings only as a statement — `gate o_enable: o_rail requires (p_rail within 0.10);` (`Appendix_D`:676–678, `Appendix_E`:463, 766)
- edited: also as a component — `gate conflict: AND< attract, averse >;` (`Appendix_E`:327)

**It is not ambiguous to a parser.** Look at one token past the colon: a type name followed by `<` means a component declaration; anything else is the `gate` statement, which always has `requires`. The reader will do exactly that, whichever text you pick.

## What I recommend

**Commit the edits**, after the two one-line fixes above, and record them in the book's `CHANGELOG.md` (the 70 uncommitted CHANGELOG lines do not mention any of these rule changes). Then name that commit as the one the board reader tests against.

If you would rather keep the committed text as canon, say so and the reader will pin `24f50911` instead. Either way it works — but the checker would then enforce that `XOR` fires when both inputs are active, which is not true.

## What happens next, either way

The board reader carries a **canon pin**: the digest of every book file it read, which text it used, and whether `XNOR` is on. A board checked against one text is never reported as checked against the other. Nothing else in the PCBA build depends on which way you rule — only on your ruling existing.

---

*Prepared 2026-09-21 under owner ruling OD-9 ("close that gap, not remove PCBA from CAS"). Read-only: no book file was edited. Every line number above was read from the file it names.*
