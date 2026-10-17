# The owner's additions, 2026-10-16: continuity of thought, the disengage ladder, and the 13 posed to the council

Written at the owner's direction. Read with `COUNCIL_STANDING_KNOWLEDGE.md`.

---

## 1. CONTINUITY OF THOUGHT — the owner's own chain, verbatim

> **"THE BRAIN IS SUPPOSED TO HAVE 'CONTINUITY OF THOUGHT' FROM RPA TO CJT THROUGH BIAS TO ASOM TO
> RPM TO AND OR CJT RPA"**

So the intended flow is a **closed loop**, not a straight line:

```
RPA  →  CJT  →  BIAS  →  ASOM  →  RPM  →  CJT  →  RPA  →  ...
```

**Continuity of thought means the loop closes.** The brain does not stop at an answer — the answer
becomes the next link. Every stage hands its state to the next, and the last stage hands back to the
first.

**What the council must establish, from the files and not from guesswork:**

1. **What RPA stands for** in this project and where it is implemented. Do NOT invent a meaning.
2. **What ASOM stands for** and where it is implemented. Do NOT invent a meaning.
3. Whether the chain is a **single loop** or can also branch (`"TO AND OR CJT RPA"` reads as: RPM can
   go to CJT and/or straight back to RPA).
4. **Where the hand-off state is carried** at each arrow — what exactly passes from RPA to CJT, from
   CJT to bias, from bias to ASOM, from ASOM to RPM, and from RPM back to CJT.
5. Whether **continuity is currently preserved or broken** at any arrow, measured rather than asserted.

**Why this matters and must not be lost:** every test run so far measures a single pass. If the loop is
the design, then a single pass can be correct and the *brain* still be discontinuous. That is a
different failure and nothing in the current record tests for it.

---

## 2. The disengage ladder — the owner's addition, and it is a real design change

The owner's words:

> **"NOT DECLARED" → "I'M CONFUSED, I HAVE NO IDEA" → HELM ASK FOR CLARITY, FOR MORE INFORMATION, ETC.
> AND AT SOME POINT, DISENGAGE AFTER GIVING A REASON OF COURSE**

So when the system does not know, the response is **not** a flat refusal. It escalates:

| step | what the system does | maps onto |
|---|---|---|
| 1 | **not declared** — the fact or cost is not on record | treated as the cautious class |
| 2 | **say so plainly** — "I'm confused / I have no idea" | `"I cannot tell."` |
| 3 | **ask** — request clarity, more information, the missing slot by name | `CLARIFY`, naming the exact slot |
| 4 | **disengage, with a reason** | `REFUSE` / `DISENGAGE` with a stated reason |

**Rules this must obey:**

- **Never guess at any step.** Escalation is not permission to fill a gap.
- **The ask must name the actual gap**, not ask vaguely. `CLARIFY` names the slot.
- **The disengage must carry a reason.** Not "no", but "no, because X".
- **Disengage is terminal for that turn.** It does not silently retry.
- **Every step is recorded** in the receipt, so a later reader can see it asked before it gave up.

**This is the same shape as the memory policy's fault ladder**: say what you do not know, try the
bounded search, then refuse with a reason. The two are the same discipline in two places.

---

## 3. The 13 open points — the owner agreed, and asked for the council to examine them

> **"POSE THOSE 13 THINGS TO THE COUNCIL YES, I AGREE"**

The owner agrees with the thirteen decisions recorded in `POLICY_OPEN_POINTS_DECIDED_20261016.md`,
**and wants each one examined by the council** — the ten canonical Noetics — rather than settled only
by the engineer.

**So the status changes:** the 13 are **agreed but not final**. Each must be put to the ten seats and
the council's reading recorded beside the decision. Where the council disagrees with the engineer, the
disagreement goes on the record and the owner decides.

The thirteen, in the order they were decided:

1. The fault vocabulary is the policy's own eight names; anything else is unclassified.
2. A "classified" claim without the evidence to support it stops being classified.
3. **A cost declared as zero, negative or contradictory is treated as undeclared → the cautious class.**
4. Six named nearby-reading operations; distance = number of atomic edits.
5. Per-candidate seed from `sha256(item, version, operator, distance, run_seed)`.
6. Candidates per step = the distance: **1, 2, 4, 8 = 15 total**, which is the policy's own cap.
7. Widen only after every candidate at the current distance has been refused.
8. **Prefer the recorded fingerprint** over last-verified state, and record which was used.
9. Receipts chain by sha256; the first carries 64 zeros.
10. "Exact at this distance" is a derived column, not a new axis.
11. A classified fault with no spare does **not** enter the search; it is `UNKNOWN`.
12. C4's criterion is reported as its own separate line, never folded into another score.
13. Denominators are the matrix's 768 rows; the four floors are **absolute**, rates are **reported**.

---

## 4. What the owner is most keen to see

> **"I'M SUPER EXCITED TO SEE IF IT CAN TALK"**

So the language test is the next thing that matters to the owner after the current work. The route is
short and already known:

1. **Q13 is agreed** — admit a `p/q` number form to CCE, so exact fractions have a way to be written.
   The CCE grammar is still DESIGN ONLY, so this goes into **v0.1** before the grammar freezes.
2. **The disengage ladder above is exactly what the language layer needs** — `CLARIFY` naming the
   slot, `"I cannot tell."`, and disengage with a reason.
3. **Then the talk test**: give it English, get English back, and check the round trip.

**The honest limit to state when it talks:** it will speak *controlled* English — a small, strict
English. Free open conversation is a different and much larger build. Do not let a successful
controlled test read as "it converses".

---

## 5. What was actually verified today, so it is not re-litigated

- **Wave 1 is run, won and settled.** `PASS`, `R1_BEATS_GB3`. Recipe brain **32**, transformer **9**,
  widened transformer **8.5**, bar **4**. Reading is 30,931 bytes, sha256
  `9b1dfdd88568012cabbcfa6d00e97c15dee07d445dfa5daff8be185975f4cf3a`, identical in two places.
  **Do not launch it again** — it already ran at `2026-10-16T17:02:07Z`.
- **The memory test package exists** — 11 files, 768 situations, nothing scored, nothing spent.
- **§7.47 is accurate.** Every claim in it checked true against the file.
