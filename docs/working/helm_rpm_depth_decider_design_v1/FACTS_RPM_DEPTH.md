**What "more RPM depth" means in HELM today.** Source is commit `5dcbf23c` (`origin/claude/project-thread-pmbzd6`), read with `git show`. Nothing was checked out, written or run.

## 0. Two different "depths"
1. **RPM recursion depth** is `RpmCause.depth` (`the_loop_v3/rpm_gate.py:262`). The root is 0. A child opened by a REPAIR sits at depth+1. The limit is `HORIZON = 12` (`dwp/depth.py:103`).
2. **The brain's recipe-expression depth** is how many recipes are chained inside one order. The limit is `MAX_DEPTH = 5` and the refusal code is `DEPTH_CAP`. This lives in the sealed package, outside the repo: `C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3\rb2\compose.py:39,212-213`.
   - The live loop always sends a single-recipe order (`helm_brain_canonical.py:280`). So expression depth is always 1.
   - The order code can name at most 2 recipes (`compose.py:58-83`). So depth 2 is the most any order can reach, and the cap of 5 is never reached.

Everything below is about depth 1 (RPM recursion depth).

## 1. What one extra level computes for a recipe question
- `_run_request` lists two kinds of gap (`helm_end_to_end_loop.py:812-813`). Missing stock comes first (`"the stock of Ω_X"`). Unlearned requirements come second (`"the requirement of Ω_X for Ω_P"`).
- The gate answers REPAIR and names a sub-goal `"RPM(<gap>)@<depth+1>"` (`rpm_gate.py:689-705`).
- The actor opens a child at `child_depth = depth + 1`, which is always 1 (`repair_performer/actor.py:115`).
- The child is `_stock_child.open_child` (`helm_end_to_end_loop.py:764-788`). It accepts `depth` but never reads it (line 765).
  - **Stock gap:**
    - If the user said X is gone this session, the child refuses (lines 769-771).
    - Otherwise it reads the latest verified amount of X from the cube store, glues it, and returns `ok: True` (lines 772-777). "Verified" means source `USER_SAID`/`CHECKED`, the newest `contains` branch, not marked absent (`_stored_amount`, lines 411-425).
  - **Requirement gap:** it replays every witnessed batch of that product on a fresh brain. It always returns `ok: False` with "a requirement cannot be made up" (lines 778-786).
  - **Anything else:** `ok: False` (line 787).
- On success the actor removes the gap from `unsatisfied`, clears `blocked_node`, adds 1 to the Bias version, and asks the parent's gate again (`actor.py:140-155`).
- `REPAIRED` means the parent's own gate then answered PROCEED (`actor.py:150`). It does not just mean the child succeeded.
- **Teaching path** (`helm_end_to_end_loop.py:951-977`): this child is `replay_child` (lines 960-963), which also ignores `depth`. Even when the replay agrees, the turn ends `REPAIRED_RETEACH_NEEDED` and nothing changes (lines 968-970).

## 2. What decides whether a deeper level opens, and what stops it
- **Nothing chooses depth.** The gate decides only from the cause it is handed. Its own docstring says it "does NOT decide ... what the depth is" (`rpm_gate.py:28-29`).
- The loop hard-codes `depth=0` on every request (`helm_end_to_end_loop.py:337` and `:368`). The actor copies that depth when it re-checks (`actor.py:141`).
- **What opens a child:** at least one named unsatisfied requirement. That makes the gate answer REPAIR at step 4 (`rpm_gate.py:670-705`). Otherwise it answers PROCEED at step 3 (`:650-665`).
- **What stops it, in order:**
  - **Gate step 1:** an invalidated ("dirty") ancestor line → REFUSE `ANCESTOR_DIRTY` (`:576-609`).
  - **Gate step 2:** a returning thread whose Bias is not strictly newer → REFUSE `STALE_BIAS` (`:615-638`).
  - **Gate step 4:** `check_depth(cause.depth)` at or above 12 → REFUSE `NO_DEEPER_SUB_GOAL` (`:672-688`).
  - **Actor:** sub-goal is `None` → `REPAIR_WITHOUT_A_TARGET` (`actor.py:110-113`).
  - **Actor:** `check_depth(child_depth)` is not OK → `CHILD_WOULD_EXCEED_HORIZON` (`:115-122`).
  - **Actor:** the child returns `ok: False` → `CHILD_REFUSED` (`:128-131`).
  - **Loop:** one `perform_repair` per named gap, up to `len(unsatisfied)` rounds. It stops at the first child that fails (`helm_end_to_end_loop.py:353-362`).
- **Gate and actor disagree by one level.** The gate checks the parent's depth. The actor checks the child's depth.
  - At parent depth 11 the gate answers REPAIR and names `@12`.
  - The actor then refuses to open it, because `check_depth(12)` is `STRUCTURAL_DEADLOCK`.
  - So the deepest child the actor will ever open is depth 11. `depth.py` itself lets a chain sit at depth 12 (`assert_within_horizon`, `:291-305`).
- **The gate's block path is never reached in the live loop.** That path is step 5: `dwp.resolve`, the Desire loop, deadlock and flatten (`rpm_gate.py:710-856`).
  - The loop sets `blocked_node="P"` only when `unsatisfied` is non-empty, so step 4 always answers first.
  - `ancestor_dirty` is always False. `resume_from_version` is always None.

## 3. What the live loop actually uses
- **Licensed recipe path:** gate at depth 0. On REPAIR, one child per gap, each at depth 1, one after another (sideways across gaps, never deeper). No child asks the gate itself, so there is never a grandchild.
- **Teaching conflict:** one replay child at depth 1.
- **Recording stock, recording absence, and an ordinary teaching batch** call the gate with no repair (`:678-682`, `:710-714`, `:918-924`).
- **Wide brain** (ON by default, `:472-475`): `_wide_question` and `wide_witness` call `rpm_gate` directly with no repair. A REPAIR verdict just ends the turn as `UNDETERMINED_CLARIFY` (`helm_wide_turn.py:1308-1318`, `:1413-1420`). The wide brain only gets turns the licensed path did not bind, and those turns get zero levels of depth.
- **Outside the chat loop:** `prereq_planner/plan_executor.py:131-142` is the only code that feeds a non-zero `RpmCause.depth` (a plan node's depth, `plan_graph.py:343-364`). It treats REPAIR as `PLAN_ORDER_VIOLATION` (`plan_executor.py:159-164`). It is wired only to `helm_ui/plan_runner.py` with `runner=None`.

## 4. What a deeper look can and cannot change in an answer
**It can change:**
- **Unknown stock:** yes, if the store holds a verified amount and the user has not said it is gone this session.
  - The turn goes from `UNDETERMINED_CLARIFY` ("how much X?") to `SUCCESS_EVALUATED` with a yield and a limiting reagent (`:840-873`).
  - The live trace shows this at ticks 9-10: a later session gets Water from the store (`:1006-1010`).
  - The child never checks how old the stored amount is.
- **Limiting reagent:** only indirectly. The glued amount joins the brain's exact `min(x_i / a_i)` (`compose.py:132-145`). The child does not compute the limiting reagent. It turns "no answer" into an answer.
  - It never changes the limiting reagent of a turn whose stock was already complete. Such a turn passes straight through (PROCEED) and opens no child.

**It can never change:**
- **A missing requirement.** That child always returns `ok: False` (`:778-786`).
  - Because stock gaps come first and the loop stops at the first failure, any unlearned requirement ends the turn `UNDETERMINED_CLARIFY` with the unlearned message (`:827-828`).
  - Any stock already found in that turn is thrown away. Glued values reach `self.stock` only after PROCEED (`:821-842`).
- The requirement book.
- The brain's arithmetic.
- The brain's own gates: `G1` missing requirement, `G2` no stock or zero yield, `G3` tie, `G4` dirty recipe, `G5` chain overlap, `DEPTH_CAP` (`compose.py:17-20`). These still apply after any glue (`helm_end_to_end_loop.py:857-860`).
- A user's statement that something is gone (`:769-771`).
- An amount the user stated this session. Only names missing from `self.stock` get gaps (`:804`).
- The valve, which runs again after a glue (`:846-852`).
- The gate's verdict for a given cause. The gate is a pure function of the cause and Bias version, and reads no clock, file or network (`rpm_gate.py:49-50`).
- An invented quantity.
- RPM itself has no G1–G4. G1–G5 are the brain's gate codes. The gate's own four ordered checks are listed at `rpm_gate.py:556-562`.

## 5. What each level costs
Nothing was measured. This is read from the code. It is all in-process standard-library Python: no GPU, no network, no LLM call, 0 USD.

- **Per gap:**
  - 2 calls to `rpm_gate`: the parent check and the check after the glue (`actor.py:97`, `:145`).
  - The loop's first gate call (`helm_end_to_end_loop.py:347`) is paid once per turn, not per gap.
  - Each gate call builds a chain of `depth+1` Chain records (`_spine`, `rpm_gate.py:505-526`), so gate cost grows in a straight line with depth.
  - **Stock child:** one dict lookup plus a scan of every cube-store branch (`helm_end_to_end_loop.py:419-422`).
  - **Requirement and replay children:** they re-run the brain's writer `teach_step_b` once per witnessed batch of that product on a fresh brain (`helm_brain_canonical.py:334-343`).
- **Records:**
  - 4-5 ledger lines per gap: parent_gate, depth_check, child_run, then after_glue and outcome, or disengage.
  - One `S5 RPM link` trace row per gap, carrying the last 6 ledger lines (`helm_end_to_end_loop.py:355-357`).
  - All of these go into the turn's `receipt_hash` (`:457-460`) and the trace file.
- **Bias version:** +1 on the actor's re-check request, +1 on the loop's rebuilt request (`:366`), and +1 when the glue is committed (`:843`).

## 6. Guards any new depth decider must keep
1. **`HORIZON = 12`.** It is the owner's ruling, not derived from canon; canon says 5 (`depth.py:103`; `OWNER_RULING_DEPTH_12_20261016.md:13-19,23-26`).
   - `check_depth(d)` returns `STRUCTURAL_DEADLOCK` for `d >= 12` (`depth.py:142-166`).
   - No chain may sit deeper than 12 (`assert_within_horizon`).
   - "The fix is to flatten ... NOT to raise the number" (`depth.py:22-26`).
2. **Flatten.** It is allowed only on a blocked chain at exactly depth 12. It returns same-level `HORIZONTAL` siblings with `child_depth=None` and `vertical_levels_added=0` (`depth.py:231-276`). It is refused below the horizon (U5).
   - The gate names the fix and never performs it (`rpm_gate.py:46-47`, `:783-809`).
   - Deadlock codes: `STRUCTURAL_DEADLOCK` at exactly 12, `HORIZON_BREACHED` beyond (`:831`).
3. **`DESIRE_BOUND = 12`** (`dwp.py:180`). It is a separate number with a separate job.
   - A Desire loop adds no depth (`dwp.py:842-857`).
   - Its refusal word `DESIRE_BOUND_EXHAUSTED` must never become `STRUCTURAL_DEADLOCK` (`rpm_gate.py:126-129`, `:721-748`).
   - The ruling warns the two 12s are "one typo apart"; two tests guard depths 0-12 (`OWNER_RULING...md:48-51`).
4. **No readout reaches the gate.**
   - `GateRequest` has exactly 7 fields (`rpm_gate.py:195-203`) and `RpmCause` exactly 12 (`:206-219`). A request with any other field is refused (`:375-401`).
   - There is no field for an ASOM label, region, outcome or saturation flag (`:21-24`). The 150-row forced-label matrix test is in `the_loop_v3/test_all.py:759`, `:1947`.
   - So a reasoning part (the Eye or any other) could decide depth only by changing `depth` or `unsatisfied` upstream, as an int ≥ 0 and non-empty name strings (`:402-406`, `:437-443`). It could not hand its readout to the gate.
5. **The actor decides nothing.** It reads `blocked_node`, `depth`, `gap`, `sub_goal` and `unsatisfied`, and passes the gate's own sub-goal to the child, "never a target the actor chose" (`actor.py:3-5`, `:87-104`). `REPAIRED` means the parent's own gate passed afterwards (`:94-95`).
6. **Ancestor line first.** An invalidated chain is a permanent REFUSE that nothing later can override (`rpm_gate.py:570-609`).
7. **Bias must be strictly newer** for a returning thread (`bias.check_version_increase`, `:615-644`). The version must go up on every glue.
8. **Glue rules:**
   - Glue only after PROCEED.
   - Throw child results away when the gate does not pass.
   - Never glue a name the user said is gone.
   - Never invent a quantity or a requirement (`helm_end_to_end_loop.py:23-24`, `:769-787`, `:821-842`).
9. **Receipts:**
   - CCE round trip (`:303-332`).
   - Gate before any store write.
   - The brain's eta/epsilon read-back (`helm_brain_canonical.py:282-297`).
   - Cube read-back (`:407-409`, `:438-440`).
   - Per-turn `receipt_hash` and trace rows (`:268-279`, `:450-465`).
10. **The brain's own `MAX_DEPTH = 5` / `DEPTH_CAP`** is a separate limit (`compose.py:39`, `:212-213`).
11. **Claim ceilings in code are unchanged:**
    - Gate: "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM." (`rpm_gate.py:106`).
    - Actor: "THE FAILURE IS PLANTED, NOT DETECTED. THE GLUE IS MODELLED, NOT CANON." (`actor.py:44-47`).
    - The live loop now uses both for real lookups and replays (`helm_end_to_end_loop.py:15-17`, `:26-33`), so these ceiling strings are out of date.
12. **One more detail:** the actor's re-check request uses placeholder values: `turn="ANSWER"`, `coordinator="cjt-1"`, `bias_digest="digest-1"` (`actor.py:74-84`). So the "after glue" verdict in the ledger was computed on a request that does not carry the loop's real digest.