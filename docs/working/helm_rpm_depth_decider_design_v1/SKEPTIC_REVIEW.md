**DEPTH-V skeptic review.** I read the code at `origin/claude/project-thread-pmbzd6` (5dcbf23c) with `git show` and changed nothing. I also read these off-repo files, without writing: `compose.py`, `cascade_w3.py`, `DESIGN_R1W3.md`, `UNITY_EYE.md` and `OWNER_APPROVALS_20261018.md`. I did not open any sealed exam file.

**A. Claims about the code that are wrong**

1. **"Today flatten at exactly 12 can never be reached" is false.** This is the reason the design gives for repair 1.
   - The gate names a flatten fix in step 5, which handles a blocked node with an empty `unsatisfied` at depth 12 (`docs/working/noetic_council/the_loop_v3/rpm_gate.py:780-797`). Its own tests check this (`the_loop_v3/test_all.py:1619-1622`, `:1728-1732`).
   - The repair path never names flatten. At depth 12, step 4 refuses with `NO_DEEPER_SUB_GOAL` and `fix=None` (`rpm_gate.py:671-688`). Making the actor agree with the gate does not change that.
   - **Fix:** restate repair 1 as "the actor checks `check_depth(parent depth)`, as the gate does." `depth.py:142-143` defines that check as "may a block AT d spawn deeper". With that change a child may sit at depth 12, which `assert_within_horizon` allows (`depth.py:291-305`). Drop the flatten reason.

2. **`SKIP_AT_HORIZON` copies the actor bug the design calls a bug.**
   - The gate answers REPAIR only when d ≤ 11. So `check_depth(d+1)` can fire only at d = 11, and the word skips exactly the legal depth-12 child.
   - The fix it names, flatten, refuses any chain that is not blocked or not at exactly 12 (`depth.py:247-255`).
   - **Fix:** delete `SKIP_AT_HORIZON`, because the gate's `NO_DEEPER_SUB_GOAL` already covers the horizon. If it is kept, use `check_depth(d)` and name no fix.

3. **`SKIP_TURN_UNANSWERABLE` rests on a half-true premise.** The fact sheet's §4 line "any stock found is thrown away" carries the same error.
   - Glued stock never reaches `self.stock` (`helm_end_to_end_loop.py:840-843`). But it does change the spoken line. `still_absent = [c for c in absent if c not in glued]` (`:822`) picks `format_unlearned` when every stock gap was found and `format_missing` when one was not (`:824-828`). The glued values are also recorded (`:819`).
   - So on the 30 mixed turns where the store holds both amounts, A4 says "How much Flour and Water is there?", asking for amounts the store already has. A0 instead asks about the unlearned requirement.
   - By the design's own label rule (a child is useful if it changes the spoken line), A4 loses 30 answers. The result is `DEPTH_RULE_LOST_ANSWERS` by construction.
   - "The question it asks is the one today's loop would have asked" cannot hold unless the rule does the store lookup itself, and that lookup is the child's whole job.
   - **Fix:** drop this word from A4. Test asking about the requirement first only as design item 5, a separate switch whose line changes are reported on their own. Correct the §4 fact line.

4. **The cost per skipped gap is overstated.**
   - A refused child costs 1 gate call (`repair_performer/actor.py:97`). The after-glue call at `:145` runs only when the child succeeds (`:128-131`).
   - That one call repeats the loop's own call at `helm_end_to_end_loop.py:347` with the same request.
   - `SKIP_NOTHING_STORED` must call `_stored_amount`, which is the stock child's entire work (`:772-775`).
   - The net saving is about one duplicate gate call and about 3 ledger lines.
   - **Fix:** state the cost word by word. Note that handing the `:347` verdict to the actor saves the same call with no rule at all.

5. **SKIP means two different things.** The design says every SKIP "ends the turn the way CHILD_REFUSED does". But a non-limiting child is skipped because the parent can answer without it. Ending that turn UNDETERMINED loses the answer every time. Letting the parent go on with the stored value is a different action, and the design does not describe it.
   - **Fix:** define two outcomes. STOP: the child cannot help, so end the turn as today. TRUST_STORED: the parent goes on with the stored value. Give each its own failure analysis.

6. **`SKIP_NOT_LIMITING` reads a number the brain never uses, so the rule is circular.**
   - Under compose's CHAIN rule, the slot cell's stock is ignored. The yield is `Y = min(Y(R_a;x)/a_slot, …)` (`C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3\rb2\compose.py:9-12`). Whether X limits depends on Y(R_a;x), and computing that is the descent.
   - The live loop sends only SINGLE orders (`helm_brain_canonical.py:271`, `:280`). An order holds at most 2 recipes (`compose.py:58-83`). `DEPTH_CAP` refuses any depth above 5 (`compose.py:212-213`).
   - So Part N depths 6-12 cannot run through HELM's brain.
   - **Fix:** say Part N runs on a separate harness, define its nested child and recursive gate calls, or drop this word.

7. **The incumbent rule already exists, is stricter, and is not in the live loop.**
   - The owner's decoupling stop is an exact-arithmetic depth rule. It is built in `C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\HELM_R1_W3_20261019\r1w3\cascade_w3.py:30-31` and was scored `DECOUPLING_EARNED` (203 vs 609 descents; spec:2369-2371).
   - It skips a child only when all three hold: share ≥ (1 + 1/20)·Y_T, a passing consolidation receipt, and every face at Peak (`docs/working/r1_wave3/DESIGN_R1W3.md:120-128`).
   - `SKIP_NOT_LIMITING` drops the 1/20 margin and the receipt check. Those two are the guards against the C3 drift family and the C4 stale-consolidation family.
   - "Like that rule, it never skips a binding child" is false. The incumbent counts a child within the margin as binding (`DESIGN_R1W3.md:125`), and this word skips such a child.
   - "A3 reads NOT_EXERCISED if it cannot be ported" is not credible, because A3's code exists.
   - No in-repo `.py` file implements the decoupling stop, so "run beside it in the live loop" has nothing to sit beside.
   - **Fix:** make A3 mandatory, using `cascade_w3.py` on fresh seeds from its generator (never the sealed X2 exam). Adopt the incumbent's margin and receipt check.

8. **"A wrong SKIP gives a question, never a wrong number" is false in two ways.**
   - (a) A TRUST_STORED skip on an inflated stored value gives a wrong yield. That is the C4 family.
   - (b) The wide brain is ON by default (`helm_end_to_end_loop.py:236-243`). When the licensed path ends `UNDETERMINED_CLARIFY` with no writes on a question about a product the wide book holds, the wide path takes over and answers (`helm_wide_turn.py:914`, `:923-925`, `:980-990`).
   - **Fix:** score the final answer with `WIDE_BRAIN` ON, or limit every claim to OFF. Delete the sentence or give its exact scope.

9. **"The wide brain always gets OPEN" means nothing.** The wide path opens no child. A REPAIR verdict simply ends its turn (`helm_wide_turn.py:1310-1318`).
   - **Fix:** say "the rule never runs on the wide path".

10. **Part L cannot have depths 10-12.** The loop hard-codes `depth=0` (`helm_end_to_end_loop.py:337`, `:368`).
    - **Fix:** remove those items, or add a test-only depth hook with a hard gate that the trace is bit-identical when the hook is OFF.

11. **The stale-number guard has no data to read.**
    - `_stored_amount` returns only an amount (`:411-425`). A branch carries only `{"amount","unit"}` (`:406`). `turn_index` is a per-loop tick that restarts each session. There is no session id and no clock.
    - So "USER_SAID or CHECKED this session" cannot be read from the store.
    - A stock amount the user stated has nothing to re-derive from, so the Eye's Body scan cannot flag it as stale.
    - **Fix:** define "this session" as `name in self.stock`, or propose a session-id/time field as a separate, tested store change.

12. **"One word for each gap the gate named" is ambiguous.** The gate names only `unsatisfied[0]` per call (`rpm_gate.py:671`). The forecast audit count depends on this: about 18 descents if every entry is worded, about 6 if only the named gap is.
    - **Fix:** word each entry of `cause.unsatisfied`, and freeze the audit denominator.

13. **`depth_voi` lines in the actor ledger push other lines out of the trace.** Only `ledger[-6:]` reaches the trace (`:356`). Extra lines shift `parent_gate` and others out of the receipt hash.
    - **Fix:** emit each word as its own S5 trace row.

14. **Shadow labels and audits write to the brain.** `evaluate` writes board 1 into the brain's memory (`helm_brain_canonical.py:283`).
    - **Fix:** run every shadow child and audit on deep copies of the brain and the store. Add a hard gate that the live brain's memory, its `learned_digest` and the store's `write_history` do not change.

15. **"Any change to the child code → OPEN" has no mechanism.**
    - **Fix:** pin the sha256 of the `_stock_child` source in the rule, treat a mismatch as OPEN, and add a test for it.

16. **Repair 2 has no observable effect.** The gate never reads `bias_digest` when it decides, and the actor's request is not written to the trace.
    - **Fix:** call it record hygiene, not a repair, and do not list it as a precondition.

**B. The Eye gates or acts without the ruling being stated**

17. **Stage 1 does need an owner ruling, despite "no new ruling needed".**
    - No Eye is wired to the live chat. `helm_chat.py:58` builds the loop with no `trace_path`, so receipts live only in memory. Eye A's tap reads a folder on disk (`faculties_v2/eye/tap.py:147-174`).
    - Existing approvals name tests only (LM-T4 report-only, U1, the wave 4 and wave 5 packages).
    - Whether the Eye's log may go to disk is UNDECIDED (`eye.py:66`).
    - The owner's purpose for the Eye is "ONLY ... DESIRE UNITY". Auditing a depth rule is not obviously Unity work.
    - **Fix:** request an owner line for "Eye report-only on the live chat", specify the on-disk trace and the tap that reads it, and mark the Unity question FLAG_FOR_HUMAN_REVIEW for Stage 1 as well.

18. **Stage 2 gives the Eye a gate role inside an awake turn.**
    - The wave 4 whisper sits outside the loop and "calls no loop, store, triad or brain" (`PREREGISTRATION_R1W4.md:60-77`, `:200-210`). DEEPEN instead changes, at S5, whether a child opens.
    - That breaks the rule "Randomness may only propose; the verifier, the receipts and the RPM Gate always decide" (`faculties_v2/guard.py:8-10`).
    - "That the Eye may act outside tests" is NOT LICENSED (spec:2839).
    - The Eye's own remedy table prescribes "ask for the missing stock by name" for a starved station and says "recursing harder is not a fix" (`UNITY_EYE.md:131-139`). DEEPEN appears nowhere in it.
    - The Eye design reads "depth n against 5", not 12 (`UNITY_EYE.md:124`).
    - **Fix:** say all of this in the ruling request, name the new route, and reconcile 5 with 12 in the Eye's reading.

19. **A SKIP overrides the gate's REPAIR verdict.** "The gate still makes every decision" hides that.
    - **Fix:** write "the rule can veto the gate's REPAIR" into ruling request #2.

**C. Tests that cannot tell the design from a baseline**

20. **Part L's savings are tautologies.**
    - `SKIP_CANNOT_FILL` skips a child that is coded to fail (`:778-786`). `SKIP_NOTHING_STORED` repeats the child's own lookup.
    - Counting "children opened" leaves out the rule's own work.
    - **Fix:** add arm A0R, which is today's loop with the dead requirement child and the duplicate gate call removed. Require A4 to beat A0R. Count work units (store scans, gate calls, Chain records, `teach_step_b` replays), not children.

21. **The comparison with the incumbent is optional.** A4 can earn KEEP with a 25% cut against ALWAYS, while the incumbent already cut 203 vs 609.
    - **Fix:** make A3 required. If it is not exercised, cap the verdict at INCONCLUSIVE. Require A4 to use no more descents than A3 and to lose 0 answers against A3.

22. **The flatten hard gate tests the gate, not the design.** It reads the same in every arm. It also fails by construction on the repair path, and a Desire-blocked chain at depth 12 gets no fix (`the_loop_v3/test_all.py:1673`).
    - **Fix:** "the gate names flatten on every W- or P-blocked step-5 cause at depth 12, and nowhere else". Keep it as a regression check only.

23. **"100% of words re-derive" is the same function run on the same recorded inputs, so it cannot fail.**
    - **Fix:** re-derive the inputs from the store's write history up to `writes_before` and from `declared_absent` at that tick.

24. **Stage 2 has no arm without the Eye.**
    - "An audit saw a miss of kind K, so whisper DEEPEN K" is a simple counter.
    - With about 3 gap kinds, the random arm A7 often picks the right kind.
    - DEEPEN-by-kind switches the rule off for a whole kind. So whether "recover half" and "at most 10% extra descents" can both pass depends on the family the custodian picks, not on the Eye.
    - Item order and the idle windows are not frozen.
    - **Fix:** add A8 (the audit counter, no Eye) and A9 (a CHECKLIST, as in U1/U3/wave 4). Freeze the order and the idle schedule. Require A6 > A8.

**D. Forecasts or opinions stated as results**

25. **"85% that A4's answers equal A0's" contradicts item 3,** which changes 30 lines by construction.
    - **Fix:** recompute it after the word set is fixed.

26. **"Any doubt gives OPEN, exactly today's behavior" is stated as fact, but it is false for the records.** The receipt hash changes on every recipe turn.
    - **Fix:** add a hard gate that with the switch OFF the trace is bit-identical to today's.

27. **The score table is the author's own opinion.** Its "Gain 6" contradicts the design's own statement that a depth decider reads VACUOUS in the live chat.
    - **Fix:** label it as opinion, or drop it.

**E. Words that overclaim**

28. **"Depth faculty".** faculties_v2 has a fixed set, `FACULTIES = ("wondering","pondering","imagination","self_notice")` (`faculties.py:74`). This is a plain arithmetic function.
    - **Fix:** call it a "depth rule".

29. **"Depth rule" on Part L.** Every Part L child is a sibling at depth 1, so this is sideways pruning, not depth.
    - **Fix:** report Part L as "sibling-gap pruning".

30. **"The repairs change no claim".** Repair 1 changes what the actor does at depth 11 → 12.
    - **Fix:** say that no recorded claim rests on it, and re-run `repair_performer/test_all.py` and `the_loop_v3/test_all.py`.

**Overall verdict:** DEPTH-V should not go to the owner as written. In the live loop it saves nothing that deleting dead code would not save. Its nesting rule is a weaker copy of the owner's decoupling stop, which is already built. One of its words loses 30 answers by construction. Its "fails safe" claim ignores the wide brain, which is on by default.