"""Pure JSON/file-system budget checks; no neural imports or provider calls."""
import copy
import importlib.util
import json
import io
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta2_budget_under_test", ROOT / "aws" / "budget.py")
budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        owned = ROOT / "records" / "budget" / "test_tmp"
        owned.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=owned)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.prior = self.base / "prior.json"
        self.approval = self.base / "approval.json"
        self.ledger = self.base / "ledger.json"
        self.prior.write_bytes((ROOT.parent / "CAS_META_1_LEARNED_SELECTION" / "records" / "aws_budget_ledger.json").read_bytes())
        self.approval.write_bytes((ROOT / "records" / "budget" / "OWNER_APPROVAL_SOURCE.json").read_bytes())
        self.plan = {"instance_count": 1, "runtime_seconds_max": 1800, "instance_type": "g7.2xlarge", "account_id": "807562639912", "region": "us-west-2", "automatic_retries": 0, "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "0.74"}

    def initialize(self):
        return budget.initialize_ledger(self.prior, self.approval, self.ledger)

    def reserve(self, job="cas-meta2-test-1", amount="2.00", plan=None):
        return budget.reserve_budget(job, "a" * 40, "b" * 64, amount, self.plan if plan is None else plan, self.ledger)

    def mutate(self, path, change):
        state = json.loads(path.read_bytes())
        change(state)
        path.write_text(json.dumps(state), encoding="utf-8")

    def test_initial_amendment_preserves_prior_reservations(self):
        before = self.prior.read_bytes()
        state = self.initialize()
        # the OPERATING cap, which the owner raised on 2026-09-12; the approved
        # original stays at CAP_ORIGINAL and is asserted separately below
        self.assertEqual(state["owner_task_cap_usd"], str(budget.CAP))
        self.assertEqual(budget.CAP_ORIGINAL, budget.Decimal("400.00"))
        self.assertEqual(state["reservations"], json.loads(before)["reservations"])
        self.assertEqual(budget.amount(state["total_reserved_usd"]), 4)
        self.assertEqual(budget.amount(state["remaining_unreserved_usd"]),
                         budget.CAP - 4)
        self.assertEqual(self.prior.read_bytes(), before)
        self.assertEqual(state["predecessor"]["sha256"], budget.digest(before))

    def test_initialization_is_idempotent_without_reset(self):
        self.initialize()
        self.reserve()
        before = self.ledger.read_bytes()
        state = self.initialize()
        self.assertEqual(state["revision"], 1)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_reservation_is_append_only_and_cost_bounded(self):
        self.initialize()
        result = self.reserve()
        self.assertEqual(budget.amount(result["total_reserved_usd"]), 6)
        self.assertEqual(budget.amount(result["remaining_unreserved_usd"]),
                         budget.CAP - 6)
        state = budget.read_ledger(self.ledger)
        self.assertEqual(len(state["reservations"]), 3)
        self.assertEqual(state["reservations"][-1]["plan"], self.plan)

    def test_duplicate_job_refused_no_retry(self):
        self.initialize()
        self.reserve()
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(budget.BudgetRefused, "ALREADY_RESERVED"):
            self.reserve()
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_prior_job_cannot_be_reserved_again(self):
        state = self.initialize()
        with self.assertRaisesRegex(budget.BudgetRefused, "ALREADY_RESERVED"):
            self.reserve(state["reservations"][0]["job"])

    def test_cap_exhaustion_refused(self):
        """Exhaustion is relative to the OPERATING cap, whatever it is set to.

        Written against budget.CAP rather than a literal, so raising the cap
        cannot silently turn this into a test of nothing: it still proves the
        very next dollar past the ceiling is refused.
        """
        self.initialize()
        # fill the ledger to exactly $1.00 below the operating cap...
        self.reserve(amount=str(budget.CAP - 5))
        # ...then the default $2.00 reservation cannot fit
        with self.assertRaisesRegex(budget.BudgetRefused, "BUDGET_EXHAUSTED"):
            self.reserve(job="cas-meta2-over-cap")

    def test_old_ledger_changed_blocks_continued_spending(self):
        self.initialize()
        self.prior.write_bytes(self.prior.read_bytes() + b"\n")
        with self.assertRaisesRegex(budget.BudgetRefused, "PREDECESSOR_OR_APPROVAL_CHANGED"):
            self.reserve()

    def test_approval_changed_blocks_continued_spending(self):
        self.initialize()
        self.approval.write_bytes(self.approval.read_bytes() + b"\n")
        with self.assertRaisesRegex(budget.BudgetRefused, "PREDECESSOR_OR_APPROVAL_CHANGED"):
            self.reserve()

    def test_predecessor_totals_must_match(self):
        self.mutate(self.prior, lambda value: value.update(total_reserved_usd="0"))
        with self.assertRaisesRegex(budget.BudgetRefused, "INCONSISTENT_PREDECESSOR"):
            self.initialize()

    def test_predecessor_duplicate_job_refused(self):
        self.mutate(self.prior, lambda value: value["reservations"].append(value["reservations"][0]))
        with self.assertRaisesRegex(budget.BudgetRefused, "DUPLICATE_JOB"):
            self.initialize()

    def test_predecessor_refund_forbidden(self):
        self.mutate(self.prior, lambda value: value["reservations"][0].update(status="REFUNDED"))
        with self.assertRaisesRegex(budget.BudgetRefused, "REFUNDS_OR_STATUS"):
            self.initialize()

    def test_wrong_owner_cap_refused(self):
        self.mutate(self.approval, lambda value: value["interpretation"].update(total_task_cap_usd="500.00"))
        with self.assertRaises(budget.BudgetRefused):
            self.initialize()

    def test_missing_explicit_approval_refused(self):
        self.mutate(self.approval, lambda value: value["goal"].update(objective="Please continue"))
        with self.assertRaisesRegex(budget.BudgetRefused, "EXPLICIT_400"):
            self.initialize()

    def test_wrong_owner_task_refused(self):
        self.mutate(self.approval, lambda value: value["goal"].update(threadId="another-task"))
        with self.assertRaisesRegex(budget.BudgetRefused, "OWNER_TASK_IDENTITY"):
            self.initialize()

    def test_missing_ledger_is_never_a_fresh_budget(self):
        with self.assertRaisesRegex(budget.BudgetRefused, "NOT_INITIALIZED"):
            self.reserve()

    def test_lock_contention_and_stale_lock_fail_closed(self):
        self.initialize()
        lock = budget.paths(self.ledger)[1]
        lock.write_text('{"token":"someone-else","pid":1}', encoding="utf-8")
        with self.assertRaisesRegex(budget.BudgetRefused, "LOCKED_FAIL_CLOSED"):
            self.reserve()
        self.assertTrue(lock.exists())

    def test_windows_transient_replace_retry(self):
        self.initialize()
        real_replace = budget.os.replace
        calls = []
        def transient(source, target):
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError("simulated OneDrive file lock")
            return real_replace(source, target)
        with patch.object(budget.os, "replace", side_effect=transient), patch.object(budget.time, "sleep"):
            self.reserve()
        self.assertEqual(len(calls), 2)
        self.assertEqual(budget.read_ledger(self.ledger)["revision"], 1)

    def test_interrupted_replace_prevents_automatic_refund_or_retry(self):
        self.initialize()
        with patch.object(budget, "replace_atomic", side_effect=budget.BudgetRefused("simulated crash")):
            with self.assertRaises(budget.BudgetRefused):
                self.reserve()
        with self.assertRaisesRegex(budget.BudgetRefused, "PENDING_OR_MISSING"):
            self.reserve(job="cas-meta2-test-2")

    def test_rolled_back_ledger_detected_by_history(self):
        self.initialize()
        previous = self.ledger.read_bytes()
        self.reserve()
        self.ledger.write_bytes(previous)
        with self.assertRaisesRegex(budget.BudgetRefused, "PENDING_OR_MISSING"):
            budget.read_ledger(self.ledger)

    def test_head_only_amendment_refused_before_reservation_write(self):
        # Historical states retain the original cap. Raising only the head
        # must fail before reserve_budget can consume a reservation or publish
        # a next revision whose predecessor hash is absent from the history.
        with patch.object(budget, "CAP", budget.CAP_ORIGINAL):
            self.initialize()
        state = budget.decoded(self.ledger.read_bytes())
        amendment_path = budget.CANONICAL_AMENDMENT.resolve()
        amendment_raw = amendment_path.read_bytes()
        state.update(owner_task_cap_usd=str(budget.CAP),
                     remaining_unreserved_usd=str(budget.CAP - 4),
                     amendment={"path": str(amendment_path),
                                "sha256": budget.digest(amendment_raw),
                                "snapshot": budget.decoded(amendment_raw)})
        self.ledger.write_bytes(budget.encoded(state))
        history = budget.paths(self.ledger)[2]
        before_head = self.ledger.read_bytes()
        before_history = {p.name: p.read_bytes() for p in history.iterdir()}
        with self.assertRaisesRegex(budget.BudgetRefused, "LEDGER_HISTORY_MISMATCH"):
            self.reserve()
        self.assertEqual(self.ledger.read_bytes(), before_head)
        self.assertEqual({p.name: p.read_bytes() for p in history.iterdir()},
                         before_history)
        with self.assertRaisesRegex(budget.BudgetRefused, "LEDGER_HISTORY_MISMATCH"):
            budget.read_ledger(self.ledger)

    def test_head_only_metadata_change_refused_before_reservation_write(self):
        self.initialize()
        self.mutate(self.ledger, lambda state: state.update(
            updated_utc="2026-01-01T00:00:00+00:00"))
        before_head = self.ledger.read_bytes()
        history = budget.paths(self.ledger)[2]
        before_history = {p.name: p.read_bytes() for p in history.iterdir()}
        with self.assertRaisesRegex(budget.BudgetRefused, "LEDGER_HISTORY_MISMATCH"):
            self.reserve()
        self.assertEqual(self.ledger.read_bytes(), before_head)
        self.assertEqual({p.name: p.read_bytes() for p in history.iterdir()},
                         before_history)

    def test_deleted_history_detected(self):
        self.initialize()
        self.reserve()
        (budget.paths(self.ledger)[2] / "00000000.json").unlink()
        with self.assertRaisesRegex(budget.BudgetRefused, "PENDING_OR_MISSING"):
            budget.read_ledger(self.ledger)

    def test_changed_prior_reservation_detected(self):
        self.initialize()
        self.mutate(self.ledger, lambda value: value["reservations"][0].update(reserved_usd="0.01"))
        with self.assertRaisesRegex(budget.BudgetRefused, "PRIOR_RESERVATIONS"):
            budget.read_ledger(self.ledger)

    def test_corrupt_ledger_refused(self):
        self.initialize()
        self.ledger.write_text('{"schema":', encoding="utf-8")
        with self.assertRaisesRegex(budget.BudgetRefused, "MALFORMED"):
            budget.read_ledger(self.ledger)

    def test_duplicate_json_keys_refused(self):
        with self.assertRaisesRegex(budget.BudgetRefused, "DUPLICATE_JSON_KEY"):
            budget.decoded(b'{"cap":"400", "cap":"800"}')

    def test_nonfinite_or_negative_or_numeric_money_refused(self):
        for value in ("NaN", "Infinity", "-1", "1e4", 400, True, None):
            with self.subTest(value=value), self.assertRaises(budget.BudgetRefused):
                budget.amount(value)

    def test_t4_plan_refused(self):
        self.initialize()
        for gpu in ("g4dn.xlarge", "g4ad.xlarge", "g5.2xlarge", "t3.micro"):
            with self.subTest(gpu=gpu), self.assertRaisesRegex(budget.BudgetRefused, "NO_T4"):
                self.reserve(plan={**self.plan, "instance_type": gpu})

    def test_modern_blackwell_and_h100_families_allowed(self):
        for gpu in ("g7.2xlarge", "g7e.2xlarge", "g6e.2xlarge", "p5.4xlarge"):
            with self.subTest(gpu=gpu):
                budget.validate_plan({**self.plan, "instance_type": gpu}, "2.00")

    def test_missing_or_zero_ancillary_budget_refused(self):
        for allowance in (None, "0.00"):
            with self.subTest(allowance=allowance), self.assertRaises(budget.BudgetRefused):
                budget.validate_plan({**self.plan, "ancillary_reserved_usd": allowance}, "2.00")

    def test_compute_plus_ancillary_bound_enforced(self):
        with self.assertRaisesRegex(budget.BudgetRefused, "BELOW_DECLARED_COST_BOUND"):
            budget.validate_plan(self.plan, "1.99")

    def test_parallel_instances_retries_and_unbounded_runtime_refused(self):
        for change in ({"instance_count": 2}, {"automatic_retries": 1}, {"runtime_seconds_max": 0}, {"runtime_seconds_max": 43201}, {"runtime_seconds_max": True}):
            with self.subTest(change=change), self.assertRaises(budget.BudgetRefused):
                budget.validate_plan({**self.plan, **change}, "400.00")

    def test_wrong_region_and_account_refused(self):
        for change in ({"region": "us-east-1"}, {"account_id": "000000000000"}):
            with self.subTest(change=change), self.assertRaisesRegex(budget.BudgetRefused, "IDENTITY_MISMATCH"):
                budget.validate_plan({**self.plan, **change}, "2.00")

    def test_changed_totals_detected(self):
        self.initialize()
        self.mutate(self.ledger, lambda value: value.update(remaining_unreserved_usd="400"))
        with self.assertRaisesRegex(budget.BudgetRefused, "INCONSISTENT_CAMPAIGN_TOTALS"):
            budget.read_ledger(self.ledger)

    def test_new_reservation_plan_tampering_detected(self):
        self.initialize()
        self.reserve()
        self.mutate(self.ledger, lambda value: value["reservations"][-1]["plan"].update(runtime_seconds_max=1))
        with self.assertRaisesRegex(budget.BudgetRefused, "PLAN_DIGEST_MISMATCH"):
            budget.read_ledger(self.ledger)

    def test_history_chain_tampering_detected(self):
        self.initialize()
        self.reserve()
        history = budget.paths(self.ledger)[2] / "00000001.json"
        self.mutate(history, lambda value: value.update(previous_state_sha256="0" * 64))
        with self.assertRaisesRegex(budget.BudgetRefused, "BROKEN_BUDGET_HISTORY_CHAIN"):
            budget.read_ledger(self.ledger)

    def test_new_reservation_refund_forbidden(self):
        self.initialize()
        self.reserve()
        self.mutate(self.ledger, lambda value: value["reservations"][-1].update(status="REFUNDED"))
        with self.assertRaisesRegex(budget.BudgetRefused, "REFUNDS_OR_STATUS"):
            budget.read_ledger(self.ledger)

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(budget.BudgetRefused, "NONFINITE_JSON"):
            budget.decoded('{"amount": NaN}')

    def test_evidence_missing_blocks_spending(self):
        self.initialize()
        self.approval.unlink()
        with self.assertRaisesRegex(budget.BudgetRefused, "EVIDENCE_UNAVAILABLE"):
            self.reserve()

    def test_new_job_bad_source_identity_refused(self):
        self.initialize()
        with self.assertRaisesRegex(budget.BudgetRefused, "INVALID_SOURCE_SHA"):
            budget.reserve_budget("cas-meta2-bad-sha", "not-a-commit", "b" * 64, "2.00", self.plan, self.ledger)

    def test_new_job_id_bad_shape_refused(self):
        self.initialize()
        with self.assertRaisesRegex(budget.BudgetRefused, "INVALID_JOB_ID"):
            self.reserve(job="another-project")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--receipt-dir":
        output = Path(sys.argv[2]).resolve()
        if output.exists() or not output.is_relative_to((ROOT / "records" / "budget").resolve()):
            raise ValueError("NEW_OWNED_BUDGET_TEST_RECEIPT_REQUIRED")
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BudgetTests))
        output.mkdir(parents=True)
        raw = output / "raw_output.txt"
        raw.write_text(stream.getvalue(), encoding="utf-8")
        receipt = {"status": "PASS" if result.wasSuccessful() else "FAIL", "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped), "python": sys.version, "executable": sys.executable, "platform": platform.platform(), "command": [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:]], "neural_work_performed": False, "provider_calls": 0, "raw_output_sha256": budget.digest(raw.read_bytes()), "budget_module_sha256": budget.digest((ROOT / "aws" / "budget.py").read_bytes()), "test_module_sha256": budget.digest(Path(__file__).read_bytes())}
        (output / "test_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(stream.getvalue())
        print(json.dumps(receipt, indent=2))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    unittest.main(verbosity=2)
