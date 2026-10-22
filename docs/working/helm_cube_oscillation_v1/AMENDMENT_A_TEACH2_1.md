
## Amendment A-TEACH2-1 (2026-10-21 PDT) — the owner's rulings on OPEN_QUESTIONS Q1–Q8; written before any code

Status: appended below the pre-code (sha256 `f7b6183bba5f8a1a241e3c64c8930f6a2c6df06fbe8c5845c0207f6d2a84c855`), which is not edited. Hashed on its own (`AMENDMENT_A_TEACH2_1.sha256`). Where they disagree, this amendment governs. Nothing was built, trained or run when it was written.

**The owner's words (verbatim):** "1.A, 2.A, 3.A.(WE MAY NEED MORE THAN 3 ROUNDS SO JUST KEEP THAT IN MIND), 4.A,5.A FOR TEST THEN C FOR REAL LIFE, 6.A,7.A, 8.CUBE EXAM at 1 USD"

1. **Scoring (Q1 a).** The current-value rule of pre-code §5 stands as written.
2. **Build (Q2 a).** Build v2 behind `HELM_CUBE_OSC`, default OFF, laptop, 0 USD, tests first.
3. **Rounds (Q3 a, with the owner's note).** The keep rule and the cap are unchanged: keep after 2 agreeing rounds within at most 3 (Q4 a); the Eye REPORT-ONLY. New, **reported only, deciding nothing:** for every line that has not agreed by round 3, the harness runs rounds 4, 5 and 6 in a **shadow** — the same propose / check / say-back / re-read loop, on a copy — and records the round at which it would first have reached 2 agreements, or "never". **Nothing from a shadow round is ever stored or answered from.** New reported rows: `SHADOW_AGREE_AT_4`, `_AT_5`, `_AT_6`, `SHADOW_NEVER`, and among the shadow agreements `SHADOW_WOULD_BE_WRONG` (the value it would have kept differs from the key). Purpose: to tell the owner, with a number, whether a higher cap would keep more facts and at what cost in wrong ones. A later cap change needs its own amendment and owner word.
4. **Keep rule (Q4 a).** Unchanged.
5. **Fading (Q5).** The exam sweeps every 4 turns (a). For real-life HELM the owner chose (c), fading by a byte budget: recorded as the v3 design requirement (a byte trigger with a frozen per-item size table, so replay stays exact); not part of TEACH-2.
6. **Traps (Q6 a).** 4 trap lines per world, as written.
7. **Retraining (Q7 a).** The CTT is retrained on SDG rows of the two subject templates plus an `LLM_WRITTEN` stratum, three copies. The money line `CUBE TRAIN at 3 USD` has **not** been typed; it is asked for once the build passes its tests. No GPU is used before it.
8. **The exam line (Q8).** The owner typed `CUBE EXAM at 1 USD` (18 UTF-8 bytes). It is recorded as the owner's pre-approval of the exam host, **cap 1 USD**, bound to the future sealed TEACH-2 zip, and as the exam's seed source by the house rule (sha256 of the line + ":" + the sealed zip's sha256). It approves nothing else: not the training, not any paid model call.
