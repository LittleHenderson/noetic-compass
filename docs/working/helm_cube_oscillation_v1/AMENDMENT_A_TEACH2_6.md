
## Amendment A-TEACH2-6 (2026-10-21 PDT) — widen a batch until it saves space; the exam limit is set at the seal; written before the code

Status: appended after A-TEACH2-5 (`257a8145…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L1 or L2, this governs.

**Measured before any code (laptop, the v1 compactor as built, lines of 31–49 bytes, about 38 on average):**

| lines in one batch | their bytes | one capsule's bytes |
|---|---|---|
| 8 | 305 | 769 |
| 16 | 603 | 794 |
| 24 | 920 | 818 |
| 32 | 1,225 | 842 |

A capsule costs about 760 bytes plus about 3 bytes per line. A batch of 16 short lines therefore makes memory bigger, so L2 as written would raise `BATCH_NO_GAIN` on every batch of a short-line chat. A 32-line world holds about 1,216 bytes of lines, so the 2,048-byte exam limit of L1 would never be crossed.

**W1. A batch widens until it saves space.** A batch starts with the 16 oldest unprotected consecutive lines. If its capsule would not be smaller than its lines, it widens by 16 more lines, up to all the unprotected old lines. `BATCH_NO_GAIN` is raised only when even the widest batch does not save space. Then the lines stay and nothing is written.

**W2. The exam limit is not frozen here.** The 2,048 bytes of L1 is withdrawn. The TEACH-2 seal sets the working limit and the local limit from the drawn worlds' measured line bytes, so that every world crosses the working limit at least once and the local limit at least once. The rule and the two numbers go into the sealed package. The real-life defaults stay 53,370 bytes and 50 MB.

**W3. Reported, not hidden.** The record states how many lines each capsule took and the bytes before and after every batch. A limit at which no batch can save space is reported as such, and is not a pass.
