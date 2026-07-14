from __future__ import annotations

from pathlib import Path
import re
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

    def test_github_issue_readback_supplies_stable_incident_identity(self) -> None:
        self.assertIn("id: github_incident", self.alert_job)
        self.assertIn("--json createdAt,url,title,labels", self.alert_job)
        self.assertEqual(self.alert_job.count('gh issue view "$issue_number"'), 1)
        self.assertIn("issue_readback_url", self.alert_job)
        self.assertIn("issue_readback_title", self.alert_job)
        self.assertIn("issue_label_count", self.alert_job)
        self.assertIn("issue_created_at_utc=${issue_created_at}", self.alert_job)
        self.assertIn(
            "ALERT_EMITTED_AT_UTC: ${{ steps.github_incident.outputs.issue_created_at_utc }}",
            self.alert_job,
        )
        self.assertIn('--emitted-at-utc "$ALERT_EMITTED_AT_UTC"', self.alert_job)
        self.assertNotIn(
            "--emitted-at-utc '${{ steps.github_incident.outputs", self.alert_job
        )

    def test_optional_provider_configuration_is_bounded_and_secret_safe(self) -> None:
        expected_secrets = {
            "CAS_ALERT_PRIMARY_WEBHOOK_URL",
            "CAS_ALERT_PRIMARY_WEBHOOK_TOKEN",
            "CAS_ALERT_ACK_WEBHOOK_URL",
            "CAS_ALERT_ACK_WEBHOOK_TOKEN",
            "CAS_ALERT_SECONDARY_WEBHOOK_URL",
            "CAS_ALERT_SECONDARY_WEBHOOK_TOKEN",
        }
        observed_secrets = set(
            re.findall(r"\$\{\{ secrets\.([A-Z0-9_]+) \}\}", self.alert_job)
        )
        self.assertEqual(observed_secrets, expected_secrets)
        self.assertEqual(
            re.findall(r"\$\{\{ vars\.([A-Z0-9_]+) \}\}", self.alert_job),
            ["CAS_ALERT_PROVIDER_MODE"],
        )
        self.assertIn(
            '--mode "${CAS_ALERT_PROVIDER_MODE:-disabled}"', self.alert_job
        )
        self.assertIn(
            "python scripts/deliver_production_runtime_alert.py", self.alert_job
        )
        self.assertNotRegex(self.alert_job, r"echo .*CAS_ALERT_.*WEBHOOK")
        self.assertNotRegex(self.alert_job, r"--(?:url|token) .*CAS_ALERT_")

    def test_provider_receipt_hashes_are_preserved_even_after_adapter_failure(
        self,
    ) -> None:
        self.assertIn("if: ${{ always() &&", self.alert_job)
        self.assertIn("actions/upload-artifact@v7", self.alert_job)
        self.assertIn(
            "cas-runtime-alert-provider-receipts.json", self.alert_job
        )
        self.assertIn("if-no-files-found: error", self.alert_job)
        self.assertIn("retention-days: 30", self.alert_job)

    def test_runbook_keeps_delivery_and_acknowledgement_separate(self) -> None:
        self.assertIn("issue delivery is `present`;", self.runbook)
        self.assertIn("human acknowledgement remain `OPEN`", self.runbook)
        self.assertIn("comment `ACK`", self.runbook)
        self.assertIn(
            "automated closure is not acknowledgement evidence", self.runbook
        )
        self.assertIn("custom receipt-contract bridge", self.runbook)
        self.assertIn("not a direct Slack", self.runbook)
        self.assertIn("does not claim a human", self.runbook)
        self.assertIn("does not publish acceptance", self.runbook)

    def test_root_ci_runs_this_contract(self) -> None:
        self.assertIn(
            "-p 'test_production_runtime_alert_contract.py'", self.ci_workflow
        )
        self.assertIn(
            "-p 'test_production_runtime_alert_delivery.py'", self.ci_workflow
        )


if __name__ == "__main__":
    unittest.main()
