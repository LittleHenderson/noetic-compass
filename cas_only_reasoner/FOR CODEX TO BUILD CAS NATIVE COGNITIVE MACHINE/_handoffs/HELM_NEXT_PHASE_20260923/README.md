> **2026-09-24 superseding preparation notice:** The owner's latest direct instruction is preparation only, with actual informative-case counts and prerequisite results before main training. The revised [controlled-study draft](PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md) and `records/helm_controlled_prelaunch_20260924/` hold the new C limitations, state/output policy, A2 statistics, manifest and complete job envelope. Final approval remains held on missing empirical receipts; this notice authorizes no launch. The earlier assignments and approval records below remain chronological history. Q4 stays separate.

# Helm next phase: handoff index (Claude to Codex), 2026-09-23

**Branch and fetch.** Everything below is on `research/helm-integration-20260923` (pushed). Fetch it read-only.
Please do not work in Claude's folder, `D:/tksCAS-worktrees/helm-integration`.

**Read in this order:**

1. `COORDINATION_CLAUDE.md`. It covers:
   - the roles;
   - the one-owner-per-file table;
   - the conflict report (Claude's pre-division rescorer change, kept as a reference implementation);
   - the acceptance table for your rescorer repair.

   Please answer with `COORDINATION_CODEX.md` on your own branch.
2. `records/helm_integration_20260923/INTEGRATION.md`: the two investigations, read as complementary
   evidence.
3. `records/helm_integration_20260923/HISTORICAL_CORRECTIONS.md`: C1 to C10. These are the notes to add, as
   dated additive notes, to `BRAIN_LINEAGE.md` and `AUDIT_PACK.md`. If you accept the single-writer proposal,
   you add them.
4. `records/helm_eval_design_20260923/EVALUATION_DESIGN_v0_2.md` (`PROPOSED_FOR_AGREEMENT`).
   - It supersedes v0.1, which was broken by a read-only review: see `REVIEW_20260923.md`.
   - It has two stages. Stage 1 is reach, parts and edge_account, which the frozen checker can score now.
     Stage 2 is analogy and correspondence at 5 or more nodes, which needs a new checker version: owner
     decision D-1.
   - Nothing may be tuned against it until it is agreed.
5. `records/helm_eval_design_20260923/analogy_wiring_probe/`. Use **v0.2**:
   `PREREG_ANALOGY_WIRING_PROBE_v0_2.md`, `analogy_wiring_probe_v0_2.py` and `preservation_digest.py`. v0.1
   produced no reading (see `RUN_LOG.md`). Your analogy repair must pass:
   - **Switch ON, every trained checkpoint that is read:** `PRESENT_GRAPH_AND_DOMAIN`. This means the ranking
     changes and the favoured set moves toward the new isomorphs, for both the graph and the domain.
     Rewiring a bystander world must leave the other candidates unmoved.
   - **Switch OFF:** the preservation digest on all 564 records, bit-identical to unchanged `20208c92`, for
     all 9 reference models.
   - **A read-only boolean switch attribute** on the container (pass `--switch-attr`).
   - **Switch placement.** The probe passes `--container-kwargs` to `_build_container`. If your switch is
     exposed another way, say how, and Claude will adapt only the probe's call site.
6. `records/typed_pointer_001/trusted_rescore_reference_claude_v0_3.py` and its two `*.v0_3.json` anchors
   and readings: Claude's reference implementation of the historical rule. The active `trusted_rescore.py`
   (0.2) and its anchors and readings are unchanged. Repairing the active tool is yours.

**Experiments. Each has one runner:**

| Id | Runner |
|---|---|
| `HELM-ANALOGY-REPAIR-1` | Codex |
| `HELM-REACH-LATE-1` | Codex |
| `Q4-RECON-2` | Codex |
| `HSET-1` sealed-test scoring | Claude |

Receiving the same recommendation does not mean both agents launch the same job.

**Update 2026-09-23: owner decision D-1 APPROVED.** Read `OWNER_DECISION_D1_20260923.md` and
`D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`. Checker version 2 is yours to build, as a new version with the frozen
files untouched. Claude's acceptance tools are in `records/helm_eval_design_20260923/d1_acceptance/`.

**Update 2026-09-23: probe reference and self-test DONE, on AWS (T4).** See
`records/helm_eval_design_20260923/analogy_wiring_probe/BEFORE_READING_RESULT.md`.
- Unchanged Helm 2.0 reads `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` on all 9 models, all zeros.
- The probe self-test met all 3 expectations.
- The T4 preservation reference is complete.
- The switch-OFF check must run on a T4 with a same-job control (prereg amendment A3). The reusable launcher is
  `records/helm_eval_design_20260923/aws_probe_job/`.

**Update 2026-09-23: checker v2 ACCEPTED; Stage 1 cells built (AWS).**
- **D-1 acceptance of Codex's checker v2 (`7f85af1e`): ACCEPTED.** All of A1 to A6 pass, plus the extra check X.
  See `records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md`. Checker v2 may now score
  Stage 2 cells.
- **The Stage 1 cells are built.** See `records/helm_eval_design_20260923/hset1a/HSET1A_BUILD_RESULT.md`.
  - **No Stage 1 cell can carry a claim.** On TEST, the no-learning two-hop rule is wrong on only 2 reach clusters.
    A pass needs at least 7.
  - This is a limit of 5-node worlds, not a result about Helm. The owner decides the next cut (the options are
    listed in that file).
- **What Codex may use.** The public cells in `records/helm_eval_design_20260923/hset1a_aws_job/results/`
  (`HSET1A_CELLS_PUBLIC.json`: FAMILIAR_RELABELLED, NEW_SHAPE_4, DEV_NEW_5), for development only.
- **The rule for the builder, unchanged from design section 1.4.** No update and no development evaluation may use
  a 5-node shape outside DEV_NEW_5. TEST_NEW_5 stays sealed with Claude.
