# Open questions — the owner's decisions for the cube oscillation packet v1 (2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.** Each item is the owner's.
Each has one recommendation and the cost of each option. Operational details (folders, instance sizes) are not here.

1. **How a quoted correction is scored** (carried from TEACH-1, §7.121). TEACH-1 counted "eight; I said seventeen
   before" as WRONG, because the old value lacked "not".
   Options: (a) the current-value rule of pre-code §5: right when the old value is marked as replaced by "not",
   "instead of", "was … before", "earlier I said", "used to be" or "replaced"; (b) keep TEACH-1's "not"-only rule;
   (c) answers must state one value only. All 0 USD.
   Recommendation: (a). It scores what a person means, and it is still a frozen word list.

2. **Go or hold.** Build v2 now behind `HELM_CUBE_OSC` (default OFF), laptop, 0 USD; or hold.
   Recommendation: build, behind the switch; the training and the exam each still need their own line.

3. **The Eye and the rounds.** (a) report-only beside a fixed cap of 3 rounds (as written); (b) a separate reported arm
   where the Eye controls the rounds in EYE-ACT-1's `HOLD` mode (it may stop early and make HELM ask, never add a round,
   never write a cube), deciding nothing; (c) the Eye decides the rounds in the arm under test.
   Recommendation: (a) for TEACH-2, (b) added if you want it measured now; (c) only after an Eye-acting word earned on
   its own test. The Eye's acting is `NOT LICENSED` today.

4. **The keep rule.** 2 agreeing rounds within 3 (as written), or 1 within 2 (faster, riskier), or 3 within 4.
   Recommendation: 2 within 3.

5. **The fading sweep.** Every 4 turns (as written), or every 2, or by bytes over a budget.
   Recommendation: every 4 turns, bytes reported; a byte trigger in v3 with a fixed size table so replay stays exact.

6. **The traps.** 4 trap lines per world (as written), or 0 (cleaner, but shared mistakes go untested), or 8.
   Recommendation: 4. Two readers agreeing on the same wrong value is the risk this design exists to catch.

7. **Retraining the CTT.** Needed: it was trained on kitchen English only. Options: (a) SDG rows of the two subject
   templates + an `LLM_WRITTEN` stratum, three copies, `CUBE TRAIN at 3 USD` (expected about 2 USD); (b) no retraining
   (0 USD; the forecast is that I18 then fails and the word is `INCONCLUSIVE`).
   Recommendation: (a), after the build passes its tests.

8. **Where the exam runs.** The CTT cannot run on the laptop (§7.82): one CPU host, `CUBE EXAM at 1 USD` (expected under
   0.20 USD). No alternative at 0 USD without leaving the CTT out.
