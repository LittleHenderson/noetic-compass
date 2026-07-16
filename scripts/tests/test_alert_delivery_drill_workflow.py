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

    def test_dispatch_requires_exact_protected_deploy_receipt_and_confirmation(self) -> None:
        for required in (
            'test "$DISPATCH_REF" = "refs/heads/master"',
            'test "$DISPATCH_REF_PROTECTED" = "true"',
            'test "$DISPATCH_SHA" = "$EXPECTED_MASTER_HEAD"',
            '[[ "$EXPECTED_DEPLOY_ID" =~ ^dep-[a-z0-9]{20}$ ]]',
            "root_ci_receipt_run_id:",
            "root_ci_receipt_artifact_name:",
            "root_ci_receipt_sha256:",
            '[[ "$ROOT_CI_RECEIPT_RUN_ID" =~ ^[1-9][0-9]*$ ]]',
            'test "$ROOT_CI_RECEIPT_ARTIFACT_NAME" = "root-ci-protected-deploy-receipt-$ROOT_CI_RECEIPT_RUN_ID"',
            '[[ "$ROOT_CI_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]]',
            'test "$CONFIRMATION" = "RUN-NON-DISRUPTIVE-P1-DRILL"',
            "verify_pinned_root_ci_receipt.py",
        ):
            self.assertIn(required, self.workflow)
        self.assertLess(
            self.workflow.index("verify_pinned_root_ci_receipt.py"),
            self.workflow.index("deliver_alert_delivery_drill.py"),
        )

    def test_root_ci_is_downloaded_and_verified_without_branch_protection_token(self) -> None:
        for required in (
            "actions/download-artifact@v8",
            "github-token: ${{ github.token }}",
            "repository: LittleHenderson/noetic-compass",
            "run-id: ${{ inputs.root_ci_receipt_run_id }}",
            "receipts/root-ci-protected-deploy.json",
            "receipts/root-ci-protected-deploy.sha256",
            '--receipt-sha256 "$ROOT_CI_RECEIPT_SHA256"',
            'test "$(git_bootstrap rev-parse HEAD)" = "$EXPECTED_MASTER_HEAD"',
        ):
            self.assertIn(required, self.workflow)
        self.assertNotIn("collect_root_ci_protected_deploy_facts.py", self.workflow)
        self.assertNotIn("GITHUB_TOKEN:", self.workflow)
        self.assertNotIn("GH_TOKEN:", self.workflow)
        self.assertNotIn("RENDER_API_KEY:", self.workflow)

    def test_provider_secrets_exist_only_in_the_delivery_step(self) -> None:
        delivery_marker = "      - name: Deliver the distinct non-disruptive P1 drill"
        build_marker = "      - name: Build the unpublished OPEN gate-evidence candidate"
        before_delivery, delivery_and_after = self.workflow.split(
            delivery_marker, maxsplit=1
        )
        delivery, _ = delivery_and_after.split(build_marker, maxsplit=1)
        self.assertNotIn("CAS_ALERT_DRILL_PROVIDER_MODE:", before_delivery)
        self.assertIn(
            "CAS_ALERT_DRILL_PROVIDER_MODE: ${{ vars.CAS_ALERT_DRILL_PROVIDER_MODE }}",
            delivery,
        )
        for role in ("INCIDENT", "PRIMARY", "ACK", "SECONDARY"):
            for kind in ("URL", "TOKEN"):
                variable = f"CAS_ALERT_DRILL_{role}_WEBHOOK_{kind}"
                self.assertNotIn(f"{variable}:", before_delivery)
                self.assertIn(f"{variable}: ${{{{ secrets.{variable} }}}}", delivery)
                self.assertEqual(
                    self.workflow.count(f"${{{{ secrets.{variable} }}}}"), 1
                )
        self.assertNotIn("echo $CAS_ALERT_DRILL", self.workflow)
        self.assertNotIn("printenv", self.workflow)

    def test_immutable_receipt_bootstrap_is_recreated_immediately_before_delivery(self) -> None:
        bootstrap_marker = (
            "      - name: Bootstrap immutable exact-head verification environment"
        )
        pre_delivery_marker = (
            "      - name: Recreate immutable exact-head environment immediately before delivery"
        )
        delivery_marker = "      - name: Deliver the distinct non-disruptive P1 drill"
        bootstrap = self.workflow.split(bootstrap_marker, maxsplit=1)[1].split(
            pre_delivery_marker, maxsplit=1
        )[0]
        pre_delivery = self.workflow.split(pre_delivery_marker, maxsplit=1)[1].split(
            delivery_marker, maxsplit=1
        )[0]
        delivery = self.workflow.split(
            delivery_marker,
            maxsplit=1,
        )[1].split(
            "      - name: Build the unpublished OPEN gate-evidence candidate",
            maxsplit=1,
        )[0]
        self.assertEqual(self.workflow.count("--minimum-remaining-validity-seconds 1200"), 2)
        self.assertIn("timeout-minutes: 20", self.workflow)
        for block in (bootstrap, pre_delivery):
            for dangerous_name in (
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_COMMON_DIR",
                "GIT_REPLACE_REF_BASE",
                "GIT_NAMESPACE",
            ):
                self.assertIn(f"'{dangerous_name}'", block)
            self.assertIn("compgen -A variable GIT_CONFIG_", block)
            self.assertIn("export GIT_NO_REPLACE_OBJECTS=1", block)
            self.assertIn("command git", block)
            self.assertIn("-c core.hooksPath=/dev/null", block)
            self.assertIn("-c core.autocrlf=false", block)
            self.assertIn("-c core.eol=lf", block)
            self.assertIn("for-each-ref --format='%(refname)' refs/replace", block)
            self.assertIn("rev-parse --git-path info/grafts", block)
            self.assertIn("git_bootstrap worktree add --detach", block)
            self.assertIn("hash-object --no-filters --", block)
            self.assertNotIn("hash-object --path=", block)
            self.assertIn("ls-files --others --ignored --exclude-standard", block)
            self.assertIn("python -I -B -S -c", block)
            self.assertIn("verify_pinned_root_ci_receipt.py", block)
            self.assertLess(
                block.index("git_bootstrap worktree add --detach"),
                block.index("python -I -B -S -c"),
            )
            self.assertNotIn("CAS_ALERT_DRILL_INCIDENT_WEBHOOK_TOKEN", block)
        self.assertNotIn("verify_pinned_root_ci_receipt.py", delivery)
        self.assertIn(
            '"$EXACT_HEAD_WORKTREE/scripts/deliver_alert_delivery_drill.py"',
            delivery,
        )
        self.assertNotIn("python scripts/verify_pinned_root_ci_receipt.py", self.workflow)
        self.assertNotIn("python scripts/deliver_alert_delivery_drill.py", self.workflow)
        self.assertNotIn("python scripts/build_alert_delivery_gate_payload.py", self.workflow)
        tests = self.workflow.index("Run the fail-closed drill and evidence tests")
        first_verification = self.workflow.index(bootstrap_marker)
        self.assertLess(tests, first_verification)

    def test_artifacts_remain_open_unpublished_and_ci_covered(self) -> None:
        for required in (
            "build_alert_delivery_gate_payload.py",
            "alert-delivery-drill-safe-receipts.json",
            "alert-delivery-gate-evidence-OPEN.json",
            "safe receipts and gate payload remain unpublished and `OPEN`",
            "cannot publish authority",
            "test_alert_delivery_drill.py",
            "test_build_alert_delivery_gate_payload.py",
            "test_verify_pinned_root_ci_receipt.py",
            "test_alert_delivery_drill_bootstrap.py",
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
            "root_ci_receipt_run_id",
            "verify_pinned_root_ci_receipt.py",
            "strictly more than 1,200 seconds",
            "before importing any repository Python",
            "`python -I -B -S`",
            "replacement refs or legacy grafts",
            "clean/smudge attributes and filters",
            "dangerous `GIT_*` repository overrides",
            "both immutable\nverification/bootstrap steps never inherit them",
            "remain unpublished and\n`OPEN`",
        ):
            self.assertIn(required, self.runbook)


if __name__ == "__main__":
    unittest.main()
