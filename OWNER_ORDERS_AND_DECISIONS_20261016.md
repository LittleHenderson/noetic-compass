# OWNER ORDERS AND COUNCIL DECISIONS — 2026-10-16

**Companion to `COUNCIL_STANDING_KNOWLEDGE.md`. Read both. This file records what the owner ORDERED
and what the council DECIDED, with the reasoning, so an instance after a compaction can act instead of
re-asking.**

---

## 1. The owner's orders, this session, verbatim in substance

1. **C15 — YES.** The M1 memory test **may run**.
2. **C4 — the council must find the answer in the files and establish which option is better.** Not
   handed back to the owner. Justify it.
3. **C5 — the same.** Find it, decide it, justify it.
4. **Q13 — do whatever unblocks English actually working.** And always justify decisions **with the
   intention of making HELM better and CAS unique.**
5. **Launch the run. Build v0.2. W1 first** — all three ordered, in that priority.
6. **Make sure the next instance, especially after a thread compaction, remembers EVERYTHING**, so any
   transition is seamless.

---

## 2. C15 — DECIDED: the M1 test may run

Owner's word: **YES.** The memory lane is open. Build the versioned package, freeze the matrix, run.

---

## 3. C4 — "what drives fading?" — DECIDED: **BY TIME**, with recall deferred

**The sources, as recorded in `CONFLICTS.md` C4:**

- **By time** — the book's forgetting curve (`Ch6:83`, `Ch21:234`); CABS's wall-clock half-life
  (`vibration.py:15-18`).
- **By event** — the organism's heartbeat after every event (`organism.py:305-321`).
- **By recall** — `cmb.py`'s "Leakage per recall step" (`cmb.py:31`, applied `:92-97`).
- Default already recorded: **by time, in logged day-ticks** (`FADING_RULES.md` 3).

**DECISION: by time, counted in logged day-ticks. Recall becomes a separate, named switch in v0.2,
not silently mixed in.**

**Justification:**

1. **Both sources the book cites are curves.** `Ch6:83` and `Ch21:234` are forgetting *curves*, and a
   curve is a function of time. That is the canonical CAS/TKS position, and it is the only drive with
   textual authority behind it rather than a code convention.
2. **Time is the only drive that is reproducible and auditable.** A logged day-tick replays exactly.
   "Per event" makes the result a function of traffic volume. "Per recall" makes it a function of
   usage, which is not recorded per item at this stage — so it cannot be checked, and an uncheckable
   term in a frozen test is worse than no term.
3. **It is the only drive the test worlds can express.** The M1 test worlds run *"ticks 0 to 29. One
   tick is one day."* Time is the world's own clock. Event- and recall-driven fading would need
   fixtures the test does not have.
4. **One variable at a time is the project's own discipline.** C4 and C6 (does a read decay or refresh)
   are entangled. Freezing time-only first isolates the mechanism and gives C6 a clean baseline to be
   measured against later. Adding both at once would make a failure unattributable.
5. **Recall must not be dropped forever.** A memory system where a consulted item fades exactly as
   fast as an untouched one is wrong. So recall is **deferred, not rejected**: it becomes a named
   v0.2 switch with its own frozen test, exactly as `cmb.py` intends.

---

## 4. C5 — "how fast?" — DECIDED: **1/20 per day-tick (0.05) for unpinned, 0 for pinned**

**The sources, as recorded in `CONFLICTS.md` C5** — and they disagree wildly:

| source | rates |
|---|---|
| the book | `P3` 0.001, `E6` 0.02, `C8` **0.05**; fast/slow 0.10 and 0.005; worked policy 0.0, 0.01, 0.5 |
| `cmb.py` | WORKING 0.35, **EPISODIC 0.05**, CONSTITUTIONAL 0.002 — per recall |
| `cas-rr` | 1.0, 0.25, 0.01 — **declared but never applied** |
| CABS | a 30-day half-life |

**DECISION: `fade_rate = 1/20` per logged day-tick for unpinned items, `0` for pinned items.**

**Justification:**

1. **This is the one number two independent sources agree on.** The book's `C8` is **0.05** and
   `cmb.py`'s EPISODIC is **0.05**. That is not an average or a compromise — it is a coincidence of
   two sources, which is the strongest evidential position available in a file where six sources give
   six different answers. Choosing it **adds no invented number to the project.**
2. **Its half-life is checkable arithmetic.** `ln(0.5) / ln(0.95) = 13.51 days`. Anyone can verify
   that against the test's 30 ticks: an item is down to about 21% of its mass by tick 29. A rate whose
   consequence can be computed by hand is a rate the owner can sanity-check without running anything.
3. **The competing rates are not credible as a single global rate.** `cas-rr`'s **1.0** means the item
   is gone in one step. The book's worked policy **0.5** halves every tick. And `cas-rr`'s numbers are
   **"declared but never applied"**, so they carry no evidence weight at all — they are a comment in
   code, not a measurement.
4. **Tiering is the right answer and the wrong first answer.** `cmb.py`'s 0.35 / 0.05 / 0.002 is the
   design's real intent — working memory fast, constitutional nearly permanent. But tiering is a
   **second variable**. A first frozen run with one global rate isolates the mechanism; a first run
   with three rates cannot say which rate caused what. **Record the tiered schedule as the v0.2
   successor** — the same deferral pattern as C4, made explicit rather than silent.
5. **`0` for pinned is required by the project's own rule.** "Never delete" and constitutional
   memory's role both need an item that cannot fade out from under the system.

---

## 5. Q13 — DECIDED: **admit a `p/q` number form to CCE**

**The gap.** `CCE compares exact Decimals; RB uses exact Fractions`
(`helm_language_faculties_circuit_design_v1\OPEN_QUESTIONS.md:22`). A non-terminating coefficient has
no CCE form, so the skin renders nothing. **This is what read `SKIN_FORM_BROKEN` in the wave-1 run.**

**DECISION: admit `p/q` as a first-class number form in CCE, through the L3 loop with receipts.**

**Justification, against the owner's own test — does it make HELM better and CAS unique?**

- **It makes HELM better** because it is the only thing standing between a working translator and a
  broken one. The translator already measured **576/576** on the CAS side and **233 of 439** on
  English; nothing else blocks it.
- **It makes CAS unique in exactly the right way.** A transformer cannot carry an exact fraction — it
  carries a float and loses the exactness. **The `p/q` form preserves exactness end to end**, so CAS
  can say `1/3` where a float says `0.333…`. Rounding to fit a decimal would import the very weakness
  CAS exists to beat. **`p/q` is therefore not a workaround; it is the CAS advantage expressed in the
  surface language.**
- **It removes a lossy step rather than adding one.** The alternative — rounding to 28 digits — would
  put a *false exact* number into a sentence, breaking the rule that a language layer never invents a
  fact. `p/q` keeps the "does not lie" discipline intact.
- **It is already in the test plan.** TAP-4 counts station kinds with no CCE form as LACUNA cells at
  weight **+5**, so admitting `p/q` will move measured cells out of LACUNA — the improvement is
  measurable in the project's own ledger.

**Note:** the CCE spec is still **DESIGN ONLY**, so this can go into **v0.1** rather than waiting for a
v0.2 successor. Do it before the grammar is frozen.

---

## 6. The work order the owner gave

**W1 first. Then build v0.2. The run is authorised.**

1. **W1** — the head-to-head race. Exam correct and pinned, controller reading `BUILD_MECHANICS_OK`
   with `PROBLEMS []`, window 240 minutes, `$9.50` hold already placed (`105.31 → 114.81` of
   `200.00`). Remaining steps in `W1_LAUNCH_RUNBOOK_20261016.md`. **Launch it.**
2. **v0.2** — build and freeze the `m1_h8_creative_reconstruction_v0_2` package (receipt fields, fault
   classification, anchor inventory, mutation operators, scorer), freeze the matrix with `NO_ANCHOR`
   rows, define the arms, then run the **$0** laptop pass.
3. **C15 is open**, so the M1 test itself may proceed under the frozen v0.2 policy once built.

**The `20×` consequence threshold stands unless the owner changes it.** It is the one adopted default
that is a real judgement rather than a mechanical choice.

---

## 7. What the council still owes, honestly

1. **Fix the §7.47 headline.** It reads *"HELM-R1 wave 1 SCORED … beat it"* with 7 of 7 hard gates,
   while the same section records `CCE_SKIN` = `SKIN_FORM_BROKEN`, `LACUNA_CADENCE` =
   `CADENCE_MIXED`, and `RESTART_FALLBACK` not exercised on gate_b/task_b. **The headline must match
   the switch table.**
2. **Settle the two-gate-sets question** before rewriting anything: is `TEST_PLAN_HELM_R1.md`'s
   H1–H7 the same set that `FROZEN.precode.json` defines and §7.47 evaluated? Unresolved; do not
   assert either way.
3. **Do not rebuild `R1-RT`.** It is an unnumbered optional row, and HELM's verifier abstains on it.
4. **Read `COUNCIL_STANDING_KNOWLEDGE.md` before touching anything.** It carries the goal, the vision,
   the path, the translator's exact state, and the reporting format.
