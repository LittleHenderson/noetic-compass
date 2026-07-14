from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-runtime-monitor.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
RUNBOOK = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "docs"
    / "runbooks"
    / "production_runtime_monitor.md"
)


class ProductionRuntimeAlertContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        cls.runbook = RUNBOOK.read_text(encoding="utf-8")
        cls.alert_job = cls.workflow.split("\n  alert_delivery:", maxsplit=1)[1]

    def test_monitor_run_is_not_cancelled_before_alert_delivery(self) -> None:
        self.assertIn("group: cas-production-runtime-monitor", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_alert_job_runs_after_failures_and_can_write_issues(self) -> None:
        self.assertIn("alert_delivery:", self.workflow)
        self.assertIn("name: cas-production-runtime-alert-delivery", self.alert_job)
        self.assertIn("if: ${{ !cancelled() }}", self.alert_job)
        self.assertNotIn("if: ${{ always() }}", self.alert_job)
        self.assertIn("issues: write", self.alert_job)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.alert_job)
        self.assertIn(
            "AGGREGATE_RESULT: ${{ needs.aggregate.result }}", self.alert_job
        )
        self.assertNotIn("continue-on-error:", self.alert_job)

    def test_alert_is_deduplicated_and_recovery_closes_it(self) -> None:
        self.assertIn("set -euo pipefail", self.alert_job)
        self.assertIn("--label \"$alert_label\"", self.alert_job)
        self.assertIn('--search "\\"${alert_title}\\" in:title"', self.alert_job)
        self.assertIn("--json number,title", self.alert_job)
        self.assertIn(
            'select(.title == "CAS production runtime monitor is failing")',
            self.alert_job,
        )
        self.assertIn("Multiple open production runtime alert issues", self.alert_job)
        self.assertIn("gh issue create", self.alert_job)
        self.assertIn("gh issue comment", self.alert_job)
        self.assertIn("gh issue close", self.alert_job)
        self.assertIn(
            "The workflow records only normalized job results", self.alert_job
        )
        self.assertNotIn("${{ secrets.", self.alert_job)
        self.assertNotIn("${{ vars.", self.alert_job)

    def test_runbook_keeps_delivery_and_acknowledgement_separate(self) -> None:
        self.assertIn("issue delivery is `present`;", self.runbook)
        self.assertIn("human acknowledgement remain `OPEN`", self.runbook)
        self.assertIn("comment `ACK`", self.runbook)
        self.assertIn(
            "automated closure is not acknowledgement evidence", self.runbook
        )

    def test_root_ci_runs_this_contract(self) -> None:
        self.assertIn(
            "-p 'test_production_runtime_alert_contract.py'", self.ci_workflow
        )


if __name__ == "__main__":
    unittest.main()
