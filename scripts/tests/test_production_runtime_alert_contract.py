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
        self.assertLess(
            self.alert_job.index("id: github_incident"),
            self.alert_job.index("uses: actions/checkout@v6"),
        )

    def test_alert_is_deduplicated_and_recovery_closes_it(self) -> None:
        self.assertIn("set -euo pipefail", self.alert_job)
        inventory = self.alert_job.split(
            'issue_inventory="$(gh issue list', maxsplit=1
        )[1].split('if ! jq -e', maxsplit=1)[0]
        self.assertIn("--state all", inventory)
        self.assertNotIn('--label "$alert_label"', inventory)
        self.assertIn(
            '--search "\\"${alert_title}\\" in:title sort:created-desc"',
            inventory,
        )
        self.assertIn("--json number,title,state,createdAt", inventory)
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
        self.assertIn("--json createdAt,url,title,labels,state", self.alert_job)
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
        self.assertIn(
            "steps.github_incident.outputs.provider_action_required == 'true'",
            self.alert_job,
        )

    def test_recovery_cannot_erase_enabled_provider_obligation(self) -> None:
        self.assertIn(
            "provider_obligation_label='cas-production-provider-obligation'",
            self.alert_job,
        )
        self.assertIn('--add-label "$provider_obligation_label"', self.alert_job)
        self.assertIn("provider_obligation_count=", self.alert_job)
        self.assertIn("provider_obligation_history_count=", self.alert_job)
        self.assertIn(
            'if [[ "$provider_obligation_count" == \'1\' || "$provider_obligation_history_count" -gt 0 ]]; then',
            self.alert_job,
        )
        self.assertIn("provider_obligation='true'", self.alert_job)
        self.assertIn("provider_obligation=${provider_obligation}", self.alert_job)
        self.assertIn("provider_action_required=${provider_action_required}", self.alert_job)
        self.assertIn("--require-provider-obligation", self.alert_job)
        self.assertIn("alert_state=recovery_pending", self.alert_job)
        self.assertIn(
            "Exact ACK readback or required secondary escalation must finish before automated closure.",
            self.alert_job,
        )
        self.assertIn(
            "ALERT_LIFECYCLE: ${{ steps.github_incident.outputs.alert_state }}",
            self.alert_job,
        )
        self.assertIn('--lifecycle "$ALERT_LIFECYCLE"', self.alert_job)
        self.assertIn(
            "provider_obligation_satisfied=${provider_obligation_satisfied}",
            self.alert_job,
        )
        self.assertIn(
            "steps.provider_alert.outputs.provider_obligation_satisfied == 'true'",
            self.alert_job,
        )
        upload_index = self.alert_job.index("uses: actions/upload-artifact@v7")
        marker_index = self.alert_job.index(
            "Record machine provider satisfaction after artifact preservation"
        )
        close_index = self.alert_job.index(
            "Close the recovered incident after its provider obligation"
        )
        self.assertLess(upload_index, marker_index)
        self.assertLess(marker_index, close_index)
        self.assertIn("machine_satisfaction_recorded=true", self.alert_job)
        self.assertIn(
            "steps.provider_satisfaction.outputs.machine_satisfaction_recorded == 'true'",
            self.alert_job,
        )
        self.assertIn(
            "Keep recovered incident open while the ACK window is active",
            self.alert_job,
        )

    def test_disabled_mode_preserves_immediate_github_only_recovery(self) -> None:
        self.assertIn(
            'if [[ "$provider_obligation" == \'false\' || "$provider_satisfied" == \'true\' ]]; then',
            self.alert_job,
        )
        self.assertIn(
            "No unsatisfied provider obligation remains on this incident.",
            self.alert_job,
        )

    def test_incident_history_is_bounded_and_manual_closure_cannot_hide_work(
        self,
    ) -> None:
        self.assertIn("--state all", self.alert_job)
        self.assertIn("--limit 1000", self.alert_job)
        self.assertIn("exact_issue_count", self.alert_job)
        self.assertIn("-gt 50", self.alert_job)
        self.assertIn("events?per_page=100&page=1", self.alert_job)
        self.assertIn("events?per_page=100&page=2", self.alert_job)
        self.assertIn(
            "timeline exceeds the bounded complete-read limit", self.alert_job
        )
        self.assertIn("unsatisfied_closed_numbers", self.alert_job)
        self.assertIn(
            "Multiple closed production incidents have unsatisfied provider obligations.",
            self.alert_job,
        )
        self.assertIn('gh issue reopen "$issue_number"', self.alert_job)
        self.assertIn(
            "Unsatisfied provider-obligated incident did not reopen.", self.alert_job
        )
        self.assertIn(
            "exact-incident inventory has an invalid record.", self.alert_job
        )

    def test_provider_markers_require_history_actor_and_event_order(self) -> None:
        self.assertIn(
            "provider_satisfied_label='cas-production-provider-satisfied'"
            if "provider_satisfied_label=" in self.alert_job
            else "cas-production-provider-satisfied",
            self.alert_job,
        )
        self.assertIn('.actor.login == "github-actions[bot]"', self.alert_job)
        self.assertIn("provider_obligation_first_id", self.alert_job)
        self.assertIn("provider_satisfied_first_id", self.alert_job)
        self.assertIn(
            '[[ "$provider_satisfied_first_id" -le "$provider_obligation_first_id" ]]',
            self.alert_job,
        )
        self.assertIn("obligation event identifier is invalid", self.alert_job)
        self.assertIn("satisfaction event identifier is invalid", self.alert_job)
        self.assertIn('--remove-label "$satisfaction_label"', self.alert_job)
        self.assertIn('--add-label "$satisfaction_label"', self.alert_job)
        self.assertIn(
            "expected Actions actor", self.alert_job
        )

    def test_provider_obligation_precedes_comments_and_provider_execution(self) -> None:
        provider_create = re.search(
            r"gh issue create \\\s+--repo .*?--label \"\$alert_label\" \\\s+"
            r"--label \"\$provider_obligation_label\"",
            self.alert_job,
            re.DOTALL,
        )
        self.assertIsNotNone(provider_create)
        marker_edit_index = self.alert_job.index(
            'gh issue edit "$issue_number"',
            self.alert_job.index("provider_mode_requested"),
        )
        comment_index = self.alert_job.index('gh issue comment "$issue_number"')
        self.assertLess(marker_edit_index, comment_index)
        self.assertGreaterEqual(
            self.alert_job.count(
                "steps.github_incident.outputs.provider_action_required == 'true'"
            ),
            4,
        )
        self.assertNotIn(
            "steps.github_incident.outputs.provider_obligation == 'true'",
            self.alert_job,
        )

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
        normalized_runbook = " ".join(self.runbook.split())
        self.assertIn("issue delivery is `present`;", normalized_runbook)
        self.assertIn("human acknowledgement remain `OPEN`", normalized_runbook)
        self.assertIn("comment `ACK`", normalized_runbook)
        self.assertIn(
            "automated closure is not acknowledgement evidence", normalized_runbook
        )
        self.assertIn("custom receipt-contract bridge", normalized_runbook)
        self.assertIn("not a direct Slack", normalized_runbook)
        self.assertIn("does not claim a human", normalized_runbook)
        self.assertIn("does not publish acceptance", normalized_runbook)

    def test_root_ci_runs_this_contract(self) -> None:
        self.assertIn(
            "-p 'test_production_runtime_alert_contract.py'", self.ci_workflow
        )
        self.assertIn(
            "-p 'test_production_runtime_alert_delivery.py'", self.ci_workflow
        )


if __name__ == "__main__":
    unittest.main()
