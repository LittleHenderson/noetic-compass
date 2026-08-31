"""run_mutation_audit.py -- REAL mutation testing (OWNER DIRECTIVE RC-0.3 section 8).

Not adversarial fixtures: this program DELIBERATELY BREAKS the implementation and
proves a named test detects each break. For every registered mutation it:

  1. copies the package into a DISPOSABLE working copy (a scratch tree; the original
     is never touched -- its digest is verified unchanged at the end);
  2. applies the mutation (exact file + exact old/new source lines, recorded);
  3. runs the single named test against the mutated copy;
  4. records the ACTUAL failing outcome (a surviving mutation = an authority hole);
  5. discards the copy (revert by disposal) -- then re-verifies the pristine tree.

Output: rc03_mutation_report.json. The receipt generator reads it; ANY surviving
mutation forces GATE0_REFUTED. Deterministic, CPU-only, no neural code.
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
     "old": "            dcr = self._state_coord.get_commit_receipt(intent.diagnostic_commit_digest)\n            if dcr is None:",
     "new": "            dcr = self._state_coord.get_commit_receipt(intent.diagnostic_commit_digest)\n            if False and dcr is None:",
     "guard": "if the commit-receipt requirement is removed, an intended receipt with no state commit publishes",
     "expected_test": ("test_rc03", "test_publication_requires_diagnostic_commit_receipt")},
    {"name": "publication_base_state_check_removed",
     "file": "sim/rc01_coordinator.py",
     "old": "            if (intent.base_state_version != dcr.pre_state_version\n                    or intent.base_state_digest != dcr.pre_state_digest):",
     "new": "            if False and (intent.base_state_version != dcr.pre_state_version\n                    or intent.base_state_digest != dcr.pre_state_digest):",
     "guard": "if base-state validation is removed, stale-state intents publish",
     "expected_test": ("test_rc03", "test_pub_law_stale_state")},
    {"name": "any_examiner_receipt_accepted",
     "file": "sim/rc01_engine.py",
     "old": "            return (receipt.examiner_id == self.EXAMINER_ID\n                    and issued.get(receipt.receipt_digest) == canonical(receipt.content))",
     "new": "            return receipt.examiner_id == self.EXAMINER_ID",
     "guard": "if registry membership is dropped, a self-built receipt with the right examiner name registers",
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
     "old": "            for cid, v in frame.pending.items():           # cancel unsettled siblings\n                if v is None:\n                    self.cancelled_causes.add(cid)",
     "new": "            pass",
     "guard": "if cancellation is removed, an orphan sibling can run and publish top-level",
     "expected_test": ("test_rc03", "test_split_child_failure_no_orphan_publication")},
    {"name": "cjtstep_snapshot_validation_removed",
     "file": "sim/rc01_engine.py",
     "old": "        if (step.originating_tick != t or step.producer_expert_id != chosen\n                or effect.producer_expert_id != chosen\n                or step.base_state_version != snap_version\n                or step.base_state_digest != snap_digest):",
     "new": "        if False:",
     "guard": "if snapshot validation is removed, a stale step result is laundered into fresh intents",
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
    (failed: bool, detail: str) -- for a mutation run, failed=True means CAUGHT."""
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
        return False, "test passed (mutation NOT caught)"
    tail = (proc.stderr.strip().splitlines() or ["no stderr"])[-1]
    return True, tail[:300]


def main():
    pristine_before = tree_digest(HERE / "sim")
    results = []
    for m in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="rc03_mut_") as tmp:
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
                                "detail": f"mutation target not found exactly once "
                                          f"(count={src.count(m['old'])})"})
                continue
            target.write_text(src.replace(m["old"], m["new"]), encoding="utf-8")
            module, test_name = m["expected_test"]
            caught, detail = run_named_test(work, module, test_name)
            results.append({**{k: m[k] for k in ("name", "file", "guard")},
                            "mutated_lines": m["old"],
                            "expected_test": f"{module}::{test_name}",
                            "applied": True, "caught": caught,
                            "actual_failing_output": detail})
            # revert = the disposable copy is discarded with the TemporaryDirectory
    pristine_after = tree_digest(HERE / "sim")
    report = {
        "report_id": "rc03_mutation_report",
        "mechanism": "disposable working copy per mutation (scratch tree; original "
                     "package never modified; pristine digest verified before/after)",
        "pristine_tree_digest_before": pristine_before,
        "pristine_tree_digest_after": pristine_after,
        "pristine_unchanged": pristine_before == pristine_after,
        "mutations": results,
        "all_caught": all(r["applied"] and r["caught"] for r in results),
    }
    (HERE / "rc03_mutation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(f"{'CAUGHT ' if r['caught'] else 'SURVIVED'} {r['name']} -> {r['expected_test']}")
    print(f"all_caught: {report['all_caught']} | pristine unchanged: {report['pristine_unchanged']}")
    return 0 if report["all_caught"] and report["pristine_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
