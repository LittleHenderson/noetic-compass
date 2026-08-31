"""run_mutation_audit.py -- REAL mutation testing (RC-0.3 section 8, hardened RC-0.4).

Not adversarial fixtures: this program DELIBERATELY BREAKS the implementation and
proves a named test detects each break. For every registered mutation it:

  1. copies the package into a DISPOSABLE working copy (a scratch tree; the original
     is never touched -- its digest is verified unchanged at the end);
  2. applies the mutation (exact file + exact old/new source lines, recorded);
  3. runs the single named test against the mutated copy;
  4. records the ACTUAL failing outcome (a surviving mutation = an authority hole);
  5. discards the copy (revert by disposal) -- then re-verifies the pristine tree.

RC-0.4 hardenings (owner audit majors 1-2 of 846f323f):
  - SEMANTIC failure required: a mutation counts as CAUGHT only when its named test
    fails with an AssertionError (the authority law's own assertion), NOT via a crash
    (AttributeError/ImportError/SyntaxError). A crash proves the code broke, not that
    the law's absence was detected.
  - The report binds source_tree_digest (sim/) and test_tree_digest (tests/) so the
    status law can refuse a report generated from a different tree.
  - `--emit-stdout` prints the report as one MUTATION_REPORT_JSON: line and writes
    NOTHING (used by the receipt generator's --check-only mode).

Output: rc03_mutation_report.json (unless --emit-stdout). The receipt generator
DELETES any prior report before invoking this program and reads ONLY a freshly created
one; ANY surviving or non-semantic mutation forces GATE0_REFUTED. Deterministic,
CPU-only, no neural code.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

MUTATIONS = [
    {"name": "publication_without_diagnostic_commit",
     "file": "sim/rc01_coordinator.py",
     "old": "            self._require_diagnostic_commit(intent)",
     "new": "            pass  # MUTATED: diagnostic-commit requirement removed",
     "guard": "if the commit-proof call is removed, an intended receipt with NO state "
              "commit publishes; the program stays operational and the named test must "
              "fail on the unauthorized publication itself",
     "expected_test": ("test_rc03", "test_publication_requires_diagnostic_commit_receipt")},
    {"name": "diagnostic_eligibility_bypassed",
     "file": "sim/rc01_coordinator.py",
     "old": "            if effect_context is not None:\n"
            "                self._require_dcr_eligibility(intents, tick, effect_context, pre)",
     "new": "            if effect_context is not None:\n"
            "                pass  # MUTATED: eligibility law bypassed",
     "guard": "if the eligibility law is bypassed, a memory-only commit mints a "
              "DiagnosticCommitReceipt and the Effect publishes; the named test must "
              "fail on the unauthorized publication",
     "expected_test": ("test_rc04", "test_memory_only_commit_cannot_mint_diagnostic_receipt")},
    {"name": "publication_base_state_check_removed",
     "file": "sim/rc01_coordinator.py",
     "old": "        if (intent.base_state_version != dcr.pre_state_version\n"
            "                or intent.base_state_digest != dcr.pre_state_digest):",
     "new": "        if False and (intent.base_state_version != dcr.pre_state_version\n"
            "                or intent.base_state_digest != dcr.pre_state_digest):",
     "guard": "if base-state validation is removed, stale-state intents publish",
     "expected_test": ("test_rc03", "test_pub_law_stale_state")},
    {"name": "any_examiner_receipt_accepted",
     "file": "sim/rc01_engine.py",
     "old": "            return (receipt.examiner_id == self.EXAMINER_ID\n"
            "                    and issued.get(receipt.receipt_digest) == canonical(receipt.content))",
     "new": "            return receipt.examiner_id == self.EXAMINER_ID",
     "guard": "if registry membership is dropped, a self-built receipt with the right "
              "examiner name registers",
     "expected_test": ("test_rc03", "test_old_public_seal_formula_rejected")},
    {"name": "op_kind_verification_removed",
     "file": "sim/rc01_engine.py",
     "old": "        elif effect.op_kind not in EXPECTED_OPS.get(effect.producer_expert_id, ()):",
     "new": "        elif False and effect.op_kind not in EXPECTED_OPS.get(effect.producer_expert_id, ()):",
     "guard": "if the op check is removed, a wrong-operation Effect with the right payload passes",
     "expected_test": ("test_rc03", "test_wrong_op_kind_refused")},
    {"name": "stale_effect_tick_accepted",
     "file": "sim/rc01_engine.py",
     "old": "        elif effect.originating_tick != tick:",
     "new": "        elif False and effect.originating_tick != tick:",
     "guard": "if the tick check is removed, an old Effect earns a fresh receipt",
     "expected_test": ("test_rc03", "test_stale_effect_tick_refused")},
    {"name": "consumed_receipts_omitted_from_seal",
     "file": "sim/rc01_engine.py",
     "old": "            \"publication_consumed\": self.pubcoord.consumed_registry_digest(),",
     "new": "",
     "guard": "if the consumed registry leaves the snapshot, the seal goes blind to it",
     "expected_test": ("test_rc03", "test_seal_binds_consumed_receipts")},
    {"name": "split_sibling_cancellation_removed",
     "file": "sim/rc01_engine.py",
     "old": "            for cid, v in frame.pending.items():           # cancel unsettled siblings\n"
            "                if v is None:\n"
            "                    self.cancelled_causes.add(cid)",
     "new": "            pass",
     "guard": "if cancellation is removed, an orphan sibling can run and publish top-level",
     "expected_test": ("test_rc03", "test_split_child_failure_no_orphan_publication")},
    {"name": "verifier_finalization_gate_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if self.__gate is not None:\n"
            "            self.__gate.require_open(\"verifier.verify\")",
     "new": "        if self.__gate is not None:\n"
            "            pass  # MUTATED: verifier gate removed",
     "guard": "if the verifier gate is removed, verify() issues receipts after "
              "finalization -- the receipt press keeps running in the sealed room "
              "(owner audit RC-0.4C finding 1)",
     "expected_test": ("test_rc04c", "test_verifier_verify_refused_after_finalization")},
    {"name": "verifier_configuration_preflight_removed",
     "file": "sim/rc01_engine.py",
     "old": "        self.__gold_digest, self.__expected_digest = self._preflight()",
     "new": "        self.__gold_digest, self.__expected_digest = "
            "\"PREFLIGHT_SKIPPED\", \"PREFLIGHT_SKIPPED\"",
     "guard": "if configuration preflight is removed, an unused poison entry is "
              "accepted and the engine can work -- and publish -- before a delayed "
              "seal failure (owner audit RC-0.4C finding 2)",
     "expected_test": ("test_rc04c", "test_unused_poison_gold_entry_rejected_before_first_tick")},
    {"name": "constructor_schema_bypassed",
     "file": "sim/rc01_engine.py",
     "old": "        cfg = _validated_constructor_config(\n"
            "            causes=causes, gold_table=gold_table, states=states, budget=budget,\n"
            "            taus=taus, episode_id=episode_id,\n"
            "            rpm_enforcement_enabled=rpm_enforcement_enabled, ohm_enabled=ohm_enabled,\n"
            "            commit_verdicts=commit_verdicts, repair_requires=repair_requires,\n"
            "            max_total_branches=max_total_branches,\n"
            "            max_active_branches=max_active_branches, reopen_events=reopen_events,\n"
            "            invalidation_events=invalidation_events,\n"
            "            expected_payloads=expected_payloads)",
     "new": "        cfg = dict(\n"
            "            causes=tuple(causes), gold_table=dict(gold_table), states=states,\n"
            "            budget=budget, taus=tuple(taus), episode_id=episode_id,\n"
            "            rpm_enforcement_enabled=rpm_enforcement_enabled, ohm_enabled=ohm_enabled,\n"
            "            commit_verdicts=commit_verdicts,\n"
            "            repair_requires=dict(repair_requires) if repair_requires else {},\n"
            "            max_total_branches=max_total_branches,\n"
            "            max_active_branches=max_active_branches,\n"
            "            reopen_events=dict(reopen_events),\n"
            "            invalidation_events=set(invalidation_events),\n"
            "            expected_payloads=dict(expected_payloads) if expected_payloads else {})",
     "guard": "if the one-schema call is bypassed, a sealable-but-illegal value (int 1 "
              "as commit_verdicts) constructs an engine; the named test must fail on "
              "the accepted poison (owner audit RC-0.4D critical 1)",
     "expected_test": ("test_rc04d", "test_nonbool_commit_flag_rejected")},
    {"name": "final_publication_barrier_removed",
     "file": "sim/rc01_engine.py",
     "old": "        try:\n"
            "            self._void_provisional_publications(force=True)\n"
            "        except FinalizedControllerError:\n"
            "            # unreachable in practice (the gate trips only after the installed==\n"
            "            # planned check); pure terminal defense -- flip the rows directly so no\n"
            "            # provisional or premature PUBLISHED row can ever survive a fault\n"
            "            for row in self.publications:\n"
            "                if row[\"status\"] in (\"PROVISIONAL_PUBLICATION\", \"PUBLISHED\"):\n"
            "                    row[\"voided_from\"] = row[\"status\"]\n"
            "                    row[\"status\"] = \"VOIDED_UNSEALED\"\n"
            "            for row in self.pubcoord.ledger:\n"
            "                if row[\"decision\"] in (\"PROVISIONAL_PUBLICATION\", \"PUBLISHED\"):\n"
            "                    row[\"voided_from\"] = row[\"decision\"]\n"
            "                    row[\"decision\"] = \"VOIDED_UNSEALED\"\n"
            "            self._provisional_pub_indices = []\n"
            "            self.metrics[\"published\"] = 0",
     "new": "        pass  # MUTATED: terminal void removed",
     "guard": "if the terminal void is removed, an unsealed/faulted run leaves its "
              "provisional publication STRANDED (owner audit RC-0.4D critical 2 + "
              "third-party F-01)",
     "expected_test": ("test_rc04d", "test_unsealed_run_has_zero_published")},
    {"name": "asom_zero_score_action_dispatch_removed",
     "file": "sim/rc01_engine.py",
     "old": "            acted = self._dispatch_zero_score_actions(t, cause, candidates, actions,\n"
            "                                                      states, latent)",
     "new": "            acted = False",
     "guard": "if the zero-score dispatch is removed, cutoff and breakdown fall back "
              "to silent HALT and the ASOM actions are decorative again (owner audit "
              "RC-0.4D critical 3)",
     "expected_test": ("test_rc04d", "test_cutoff_region_dispatches_repair_not_halt")},
    {"name": "snapshot_whole_object_detach_removed",
     "file": "sim/rc01_engine.py",
     "old": "        # MUTATION-TARGET: snapshot-whole-object-detach\n"
            "        return copy.deepcopy(snap)",
     "new": "        # MUTATION-TARGET: snapshot-whole-object-detach\n"
            "        return snap",
     "guard": "if whole-object detachment is removed, the snapshot aliases live "
              "engine state (the fault record, events, metrics) (owner audit "
              "RC-0.4D major 4)",
     "expected_test": ("test_rc04d", "test_fault_record_is_detached_from_runtime_snapshot")},
    {"name": "scheduler_tick_capability_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if self.phase not in (\"RUNNING\", \"FINALIZING\"):\n"
            "            raise ControllerLifecycleError(\n"
            "                f\"{entry_point} refused: phase is {self.phase}; execution internals \"\n"
            "                \"run only inside run()'s lifecycle\")",
     "new": "        if False:\n"
            "            raise ControllerLifecycleError(\n"
            "                f\"{entry_point} refused: phase is {self.phase}; execution internals \"\n"
            "                \"run only inside run()'s lifecycle\")",
     "guard": "run()'s ownership of execution is enforced by the lifecycle phase "
              "guard on EVERY execution internal plus the tick() scheduler token "
              "(defense-in-depth). Removing the phase guard lets the token-free "
              "internals (_repair, _execute_verify_commit, _do_split, "
              "_publish_or_refuse) run outside run(); the named test attacks exactly "
              "those (owner audit RC-0.4E section 1 + internal round-2 MAJOR)",
     "expected_test": ("test_rc04e", "test_prerun_internal_execution_refused")},
    {"name": "publication_finalization_permit_removed",
     "file": "sim/rc01_coordinator.py",
     "old": "        # MUTATION-TARGET: publication-finalization-permit\n"
            "        self._require_finalization_permit(permit)\n"
            "        self.__consumed_permits.add(permit.permit_digest)",
     "new": "        # MUTATION-TARGET: publication-finalization-permit\n"
            "        pass  # MUTATED: permit requirement removed",
     "guard": "if the permit requirement is removed, the PROMOTE button works for "
              "anyone holding the engine (owner audit RC-0.4E section 2)",
     "expected_test": ("test_rc04e",
                       "test_public_promotion_without_finalization_permit_refused")},
    {"name": "result_finalization_requirement_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if self.phase not in (\"FINALIZED\", \"FAULTED\"):\n"
            "            raise ControllerLifecycleError(\n"
            "                f\"result() refused: phase is {self.phase}; a result exists only in a \"\n"
            "                \"terminal phase (FINALIZED or FAULTED)\")",
     "new": "        if False:\n"
            "            raise ControllerLifecycleError(\n"
            "                f\"result() refused: phase is {self.phase}; a result exists only in a \"\n"
            "                \"terminal phase (FINALIZED or FAULTED)\")",
     "guard": "if the terminal-phase requirement is removed, pre-final evidence is "
              "emitted as a result (owner audit RC-0.4E section 1)",
     "expected_test": ("test_rc04e", "test_result_before_finalization_is_refused")},
    {"name": "finalization_fault_boundary_removed",
     "file": "sim/rc01_engine.py",
     "old": "        # MUTATION-TARGET: finalization-fault-boundary\n"
            "        # (no exception carve-outs -- RC-0.4E round-2: ANY exception in FINALIZING,\n"
            "        # domain-typed included, must void and terminate FAULTED)\n"
            "        try:\n"
            "            return self._finalize_and_result()\n"
            "        except BaseException as exc:  # noqa: BLE001\n"
            "            self._terminal_fault(\"finalize\", t, exc)\n"
            "            raise ControllerFault(self.fault, self.seal_digest) from exc",
     "new": "        # MUTATION-TARGET: finalization-fault-boundary\n"
            "        return self._finalize_and_result()",
     "guard": "if the finalization fault boundary is removed, an environmental error "
              "escapes UNTYPED with a stranded provisional (third-party F-01)",
     "expected_test": ("test_rc04e", "test_finalization_runtimeerror_is_typed")},
    {"name": "split_active_branch_check_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if (self.total_branches_opened + n_children > self.max_total_branches\n"
            "                or active_children + n_children > self.max_active_branches\n"
            "                or own_open + n_children > gov.max_branches):",
     "new": "        if False and (self.total_branches_opened + n_children > self.max_total_branches\n"
            "                or active_children + n_children > self.max_active_branches\n"
            "                or own_open + n_children > gov.max_branches):",
     "guard": "if the split branch cages are removed, an overload Cause opens children "
              "past every ceiling (owner audit RC-0.4E section 4)",
     "expected_test": ("test_rc04e", "test_split_refused_when_max_active_branches_zero")},
    {"name": "global_cause_id_check_removed",
     "file": "sim/rc01_engine.py",
     "old": "            child_id, k = base_id, 0\n"
            "            while child_id in self.used_cause_ids:\n"
            "                k += 1\n"
            "                child_id = f\"{base_id}.g{k}\"",
     "new": "            child_id, k = base_id, 0",
     "guard": "if the id reservation is removed, a generated child id collides with "
              "an unrelated top-level Cause (owner audit RC-0.4E section 5)",
     "expected_test": ("test_rc04e",
                       "test_top_level_id_cannot_collide_with_generated_child")},
    {"name": "cutoff_self_clear_guard_removed",
     "file": "sim/rc01_engine.py",
     "old": "                    self.metrics[\"cutoff_unresolved\"] += 1\n"
            "                    self.events.append({\"tick\": t, \"event\": \"CUTOFF_CAUSE_UNRESOLVED\",\n"
            "                                        \"expert\": e, \"cause\": cause.cause_id})\n"
            "                    self._drop_cause(t, cause.cause_id, \"cutoff_unresolved\")\n"
            "                    acted = True",
     "new": "                    reassessed = RegionRecord(\n"
            "                        region_posterior=UNIFORM4, committed_region=\"unassessed\",\n"
            "                        response_model_status=\"unassessed\", stability_status=\"stable\",\n"
            "                        semantic_outcome=\"unassessed\")\n"
            "                    if self._commit([self._intent(e, \"record\", reassessed, t,\n"
            "                                                  \"MUTATED: self-clear\")], t):\n"
            "                        self.metrics[\"repairs_completed\"] += 1\n"
            "                        requeue = True\n"
            "                    acted = True",
     "guard": "if the self-clear guard is removed, a ready-but-cutoff route repaints "
              "its own gauge needle and conducts (owner audit RC-0.4E section 6)",
     "expected_test": ("test_rc04e",
                       "test_ready_cutoff_cannot_self_clear_without_new_evidence")},
    {"name": "cjtstep_snapshot_validation_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if (step.originating_tick != t or step.producer_expert_id != chosen\n"
            "                or effect.producer_expert_id != chosen\n"
            "                or step.base_state_version != snap_version\n"
            "                or step.base_state_digest != snap_digest\n"
            "                or effect.originating_tick != step.originating_tick\n"
            "                or effect.base_bias_version != step.base_state_version\n"
            "                or effect.base_bias_digest != step.base_state_digest\n"
            "                or step.authoritative_bias_version != step.base_state_version):",
     "new": "        if False:",
     "guard": "if snapshot validation is removed, a stale step result is laundered "
              "into fresh intents and an Effect can carry false Bias provenance",
     "expected_test": ("test_rc03", "test_stale_cjtstep_result_rejected")},
]

COPY_ITEMS = ("sim", "tests")


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def run_named_test(pkg_dir: Path, module: str, test_name: str):
    """Run ONE named test in the (possibly mutated) package copy. Returns
    (failed, semantic, tail): failed=True means the test failed (mutation noticed);
    semantic=True means it failed with an AssertionError -- the authority law's own
    assertion -- not an incidental crash (RC-0.4 major 2)."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, r'{pkg_dir / 'sim'}')\n"
        f"sys.path.insert(0, r'{pkg_dir / 'tests'}')\n"
        f"from {module} import {test_name}\n"
        f"{test_name}()\n"
        "print('TEST_PASSED')\n")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=str(pkg_dir), timeout=300)
    if proc.returncode == 0 and "TEST_PASSED" in proc.stdout:
        return False, False, "test passed (mutation NOT caught)"
    tail = (proc.stderr.strip().splitlines() or ["no stderr"])[-1]
    semantic = tail.startswith("AssertionError")
    return True, semantic, tail[:300]


def build_report():
    src_before = tree_digest(HERE / "sim")
    tst_before = tree_digest(HERE / "tests")
    results = []
    for m in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="rc04_mut_") as tmp:
            work = Path(tmp) / "pkg"
            work.mkdir()
            for item in COPY_ITEMS:
                shutil.copytree(HERE / item, work / item,
                                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
            target = work / m["file"]
            src = target.read_text(encoding="utf-8")
            if src.count(m["old"]) != 1:
                results.append({**{k: m[k] for k in ("name", "file", "guard")},
                                "mutated_lines": m["old"],
                                "expected_test": "::".join(m["expected_test"]),
                                "applied": False, "caught": False,
                                "semantic_failure": False,
                                "detail": f"mutation target not found exactly once "
                                          f"(count={src.count(m['old'])})"})
                continue
            target.write_text(src.replace(m["old"], m["new"]), encoding="utf-8")
            module, test_name = m["expected_test"]
            failed, semantic, detail = run_named_test(work, module, test_name)
            results.append({**{k: m[k] for k in ("name", "file", "guard")},
                            "mutated_lines": m["old"],
                            "expected_test": f"{module}::{test_name}",
                            "applied": True,
                            "caught": failed and semantic,
                            "test_failed": failed,
                            "semantic_failure": semantic,
                            "actual_failing_output": detail})
            # revert = the disposable copy is discarded with the TemporaryDirectory
    src_after = tree_digest(HERE / "sim")
    tst_after = tree_digest(HERE / "tests")
    return {
        "report_id": "rc04_mutation_report",
        "phase": "RC-0.4",
        "mechanism": "disposable working copy per mutation (scratch tree; original "
                     "package never modified; pristine digests verified before/after); "
                     "CAUGHT requires the named test to fail with an AssertionError -- "
                     "the semantic law's own assertion -- not an incidental crash",
        "source_tree_digest": src_before,
        "test_tree_digest": tst_before,
        "pristine_tree_digest_before": src_before,
        "pristine_tree_digest_after": src_after,
        "pristine_unchanged": (src_before == src_after) and (tst_before == tst_after),
        "mutations": results,
        "all_caught": all(r["applied"] and r["caught"] for r in results),
    }


def main():
    emit_stdout = "--emit-stdout" in sys.argv
    report = build_report()
    if emit_stdout:
        print("MUTATION_REPORT_JSON:" + json.dumps(report))
    else:
        (HERE / "rc03_mutation_report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in report["mutations"]:
        tag = "CAUGHT " if r["caught"] else "SURVIVED"
        print(f"{tag} {r['name']} -> {r['expected_test']}"
              + ("" if r["caught"] else f" [{r.get('actual_failing_output', r.get('detail', ''))}]"))
    print(f"all_caught: {report['all_caught']} | pristine unchanged: {report['pristine_unchanged']}")
    return 0 if report["all_caught"] and report["pristine_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
