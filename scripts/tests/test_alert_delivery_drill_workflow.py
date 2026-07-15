from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "alert-delivery-drill.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
RUNTIME_WORKFLOW = ROOT / ".github" / "workflows" / "production-runtime-monitor.yml"
RUNTIME_RUNBOOK = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "docs"
    / "runbooks"
    / "production_runtime_monitor.md"
)


class AlertDeliveryDrillWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.ci = CI_WORKFLOW.read_text(encoding="utf-8")
        cls.runtime = RUNTIME_WORKFLOW.read_text(encoding="utf-8")
        cls.runbook = RUNTIME_RUNBOOK.read_text(encoding="utf-8")

    def test_drill_is_manual_serial_and_not_a_runtime_monitor_mutation(self) -> None:
        trigger = self.workflow.split("permissions:", maxsplit=1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        for forbidden in ("schedule:", "push:", "pull_request:"):
            self.assertNotIn(forbidden, trigger)
        self.assertIn("group: cas-alert-delivery-drill", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertNotIn("issues: write", self.workflow)
        self.assertNotIn("gh issue", self.workflow)
        self.assertNotIn("cas-production-runtime-alert", self.workflow)
        self.assertNotIn("deliver_alert_delivery_drill.py", self.runtime)

    def test_dispatch_requires_exact_protected_deploy_and_typed_confirmation(self) -> None:
        for required in (
            'test "$DISPATCH_REF" = "refs/heads/master"',
            'test "$DISPATCH_REF_PROTECTED" = "true"',
            'test "$DISPATCH_SHA" = "$EXPECTED_MASTER_HEAD"',
            '[[ "$EXPECTED_DEPLOY_ID" =~ ^dep-[a-z0-9]{20}$ ]]',
            'test "$CONFIRMATION" = "RUN-NON-DISRUPTIVE-P1-DRILL"',
            "collect_root_ci_protected_deploy_facts.py",
        ):
            self.assertIn(required, self.workflow)
        self.assertLess(
            self.workflow.index("collect_root_ci_protected_deploy_facts.py"),
            self.workflow.index("deliver_alert_delivery_drill.py"),
        )

    def test_all_four_provider_roles_are_configured_without_echoing_secrets(self) -> None:
        for role in ("INCIDENT", "PRIMARY", "ACK", "SECONDARY"):
            self.assertIn(
                f"CAS_ALERT_DRILL_{role}_WEBHOOK_URL: ${{{{ secrets.",
                self.workflow,
            )
            self.assertIn(
                f"CAS_ALERT_DRILL_{role}_WEBHOOK_TOKEN: ${{{{ secrets.",
                self.workflow,
            )
        self.assertNotIn("echo $CAS_ALERT_DRILL", self.workflow)
        self.assertNotIn("printenv", self.workflow)

    def test_artifacts_remain_open_unpublished_and_ci_covered(self) -> None:
        for required in (
            "build_alert_delivery_gate_payload.py",
            "alert-delivery-drill-safe-receipts.json",
            "alert-delivery-gate-evidence-OPEN.json",
            "safe receipts and gate payload remain unpublished and `OPEN`",
            "cannot publish authority",
            "test_alert_delivery_drill.py",
            "test_build_alert_delivery_gate_payload.py",
            "test_alert_delivery_drill_workflow.py",
        ):
            location = self.ci if required.startswith("test_") else self.workflow
            self.assertIn(required, location)

    def test_runbook_separates_runtime_incidents_from_acceptance_drills(self) -> None:
        for required in (
            "Dedicated non-disruptive acceptance drill",
            ".github/workflows/alert-delivery-drill.yml",
            "cannot satisfy\nthe standalone customer-production `alert_delivery` gate",
            "RUN-NON-DISRUPTIVE-P1-DRILL",
            "remain unpublished and\n`OPEN`",
        ):
            self.assertIn(required, self.runbook)


if __name__ == "__main__":
    unittest.main()
