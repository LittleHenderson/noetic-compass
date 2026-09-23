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
