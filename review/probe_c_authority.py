"""Reviewer probe C: authority, caller identity, zero-budget and refusal paths.

Owner: Q1-DeepSeek (review/). Read-only against builder source.

Covers the reviewer's brief items: exact caller identity, zero-budget refusal,
duplicate submission, and counterfeit trusted authority.

Run:
  python review/probe_c_authority.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import traceback
from pathlib import Path


class Report:
    def __init__(self):
        self.cases = []

    def case(self, case_id, requirement, fn):
        try:
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "PASS", "detail": fn()})
        except AssertionError as exc:
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "FAIL", "detail": f"ASSERT: {exc}"})
        except Exception as exc:  # noqa: BLE001
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "ERROR",
                               "detail": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()[-800:]})

    def skip(self, case_id, requirement, reason):
        self.cases.append({"id": case_id, "requirement": requirement,
                           "outcome": "NOT_RUN", "detail": reason})

    def summary(self):
        counts = {}
        for case in self.cases:
            counts[case["outcome"]] = counts.get(case["outcome"], 0) + 1
        return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    root = args.package_root.resolve()
    sys.path.insert(0, str(root))
    report = Report()

    from helm_quantum.admission import OfflineAdmission, admit_offline_fixture
    from helm_quantum.contracts import (ExecutionLimits, QuantumProblem, QuantumProposal,
                                        QuantumRunReceipt, QuantumVerification, ReturnAddress)
    from helm_quantum.wire import ContractError, canonical

    def expect_refusal(fn, label):
        try:
            value = fn()
        except ContractError as exc:
            return f"REFUSED: {exc}"
        raise AssertionError(f"{label} was ACCEPTED, returned {value!r}")

    # ================= caller identity =================

    # --- C1: snapshot/binding identity is factory-derived, not caller-supplied ---
    def c1():
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        binding = problem.binding
        assert binding.parent_ref == "offline-fixture:root"
        assert binding.branch_id == "offline-fixture:branch-0"
        assert binding.caller_id == "offline-fixture:caller-0"
        assert binding.caller_frame == "offline-fixture:frame-0"
        assert binding.continuation == "offline-fixture:return-0"
        assert binding.checkpoint_digest is None
        # snapshot_digest must be the real digest of the public fixture file
        import hashlib
        fixture_digest = hashlib.sha256(
            (root / "fixtures/public/q1-mod4.json").read_bytes()).hexdigest()
        assert binding.snapshot_digest == fixture_digest, \
            f"snapshot digest {binding.snapshot_digest} != fixture file digest {fixture_digest}"
        # The caller controls only goal and mode; identity is not an input.
        assert canonical(problem).find("caller-0") > 0
        return {"binding": binding.to_dict(), "snapshot_digest_is_file_digest": True,
                "caller_supplied_identity_fields": 0}

    report.case("C1", "binding identity is factory-derived from admitted state", c1)

    # --- C2: caller cannot mint an admission ---
    def c2():
        outcome = expect_refusal(
            lambda: OfflineAdmission("add2", "disabled", 2**62, "a" * 64, "b" * 64, "c" * 64, None),
            "caller-minted OfflineAdmission")
        # also try to supply a plausible token-like object
        try:
            OfflineAdmission("add2", "disabled", 2**62, "a" * 64, "b" * 64, "c" * 64, object())
            raise AssertionError("caller-minted admission with fresh object was ACCEPTED")
        except ContractError as exc:
            second = str(exc)
        return {"none_token": outcome, "fresh_object_token": f"REFUSED: {second}"}

    report.case("C2", "a caller cannot mint trusted admission", c2)

    # --- C3: serialized problem cannot carry its own identity ---
    def c3():
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        text = problem.to_json()
        # no trusted context -> refused
        first = expect_refusal(lambda: QuantumProblem.from_json(text),
                               "problem JSON without trusted context")
        # JSON claiming a different caller must still be refused (fixture mismatch)
        import json as _json
        data = _json.loads(text)
        data["binding"]["caller_id"] = "attacker:caller-99"
        second = expect_refusal(
            lambda: QuantumProblem.from_json(_json.dumps(data), admission=ctx),
            "problem JSON with forged caller_id")
        return {"no_context": first, "forged_caller": second}

    report.case("C3", "deserialized problem cannot assert its own caller identity", c3)

    # --- C4: proposal bound to a different return address is refused ---
    def c4():
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        forged = ReturnAddress(parent_ref="attacker:parent", snapshot_ref="attacker:snap",
                               snapshot_digest="f" * 64, branch_id="attacker:branch",
                               caller_id="attacker:caller", caller_frame="attacker:frame",
                               continuation="attacker:return", checkpoint_digest=None)
        outcome = expect_refusal(
            lambda: QuantumProposal(schema="helm-q1-proposal/1",
                                    problem_digest=problem.problem_digest, binding=forged,
                                    mode="disabled", program=(1, 1, 0),
                                    origin="offline-classical", _admission=ctx, _problem=problem),
            "proposal with foreign return address")
        return {"foreign_binding": outcome}

    report.case("C4", "foreign return address is refused", c4)

    # --- C5: malformed identity fields are refused ---
    def c5():
        bad = {}
        bad["short_digest"] = expect_refusal(
            lambda: ReturnAddress("p", "s", "abc", "b", "c", "f", "r", None), "short digest")
        bad["uppercase_digest"] = expect_refusal(
            lambda: ReturnAddress("p", "s", "A" * 64, "b", "c", "f", "r", None), "uppercase digest")
        bad["empty_string"] = expect_refusal(
            lambda: ReturnAddress("p", "", "a" * 64, "b", "c", "f", "r", None), "empty field")
        bad["non_str"] = expect_refusal(
            lambda: ReturnAddress("p", 123, "a" * 64, "b", "c", "f", "r", None), "int field")
        bad["oversize"] = expect_refusal(
            lambda: ReturnAddress("p", "s", "a" * 64, "b", "c", "f", "x" * 257, None), "oversize field")
        return bad

    report.case("C5", "malformed return-address identity fields are refused", c5)

    # --- C6: stale admission expires ---
    def c6():
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        # Rewrite the deadline on the frozen admission to simulate expiry.
        object.__setattr__(ctx, "deadline_unix_ms", 1)
        outcome = expect_refusal(lambda: problem.assert_current(), "expired admission")
        return {"expired": outcome}

    report.case("C6", "expired admission refuses further use", c6)

    # ================= zero budget =================

    # --- C7: limits force zero spend/tasks/shots ---
    def c7():
        bad = {}
        bad["nonzero_shots"] = expect_refusal(
            lambda: ExecutionLimits(64, 256, 1000, 64, 1000, 0, "0.00"), "nonzero shots")
        bad["nonzero_tasks"] = expect_refusal(
            lambda: ExecutionLimits(64, 256, 1000, 64, 0, 10, "0.00"), "nonzero tasks")
        bad["nonzero_cost"] = expect_refusal(
            lambda: ExecutionLimits(64, 256, 1000, 64, 0, 0, "10.00"), "nonzero cost")
        bad["over_program_bound"] = expect_refusal(
            lambda: ExecutionLimits(65, 256, 1000, 64, 0, 0, "0.00"), "programs > 64")
        good = ExecutionLimits(64, 256, 1000, 64, 0, 0, "0.00")
        return {"refusals": bad, "accepted_zero_budget_limits": good.to_dict()}

    report.case("C7", "non-zero spend, tasks and shots are refused by contract", c7)

    # --- C8: offline backend refuses submission unconditionally ---
    def c8():
        from helm_quantum.backends.offline import OfflineBackend
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        backend = OfflineBackend()
        caps = backend.capabilities()
        assert caps.submit_available is False and caps.max_tasks == 0 and caps.max_shots == 0
        refused = {}
        refused["no_grant"] = expect_refusal(lambda: backend.submit(problem), "submit()")
        refused["empty_grant"] = expect_refusal(lambda: backend.submit(problem, {}), "submit({})")
        refused["forged_grant"] = expect_refusal(
            lambda: backend.submit(problem, {"trusted_execution_grant": "ALLOW", "budget_usd": "10.00"}),
            "submit(forged grant)")
        refused["compile"] = expect_refusal(lambda: backend.compile(problem), "compile()")
        refused["poll"] = expect_refusal(lambda: backend.poll("job-1"), "poll()")
        refused["cancel"] = expect_refusal(lambda: backend.cancel("job-1"), "cancel()")
        refused["decode"] = expect_refusal(lambda: backend.decode(problem, object()), "decode()")
        estimate = backend.estimate(problem)
        assert estimate["submission_allowed"] is False
        return {"capabilities": caps.to_dict(), "refusals": refused,
                "estimate": estimate}

    report.case("C8", "offline backend refuses every execution verb", c8)

    # --- C9: CLI refuses submission before reading any grant ---
    def c9():
        proc = subprocess.run(
            [sys.executable, "-m", "helm_quantum", "submit",
             "--request", "nonexistent.json", "--authorization", "TRUSTED_GRANT"],
            cwd=str(root), capture_output=True, text=True, timeout=120)
        assert proc.returncode == 2, f"exit {proc.returncode}, stdout={proc.stdout!r}"
        payload = json.loads(proc.stderr.strip().splitlines()[-1])
        assert payload["status"] == "REFUSED", payload
        assert "SUBMISSION_REFUSED" in payload["reason"], payload
        # The refusal must not depend on the request file existing.
        assert "No such file" not in payload["reason"], payload
        return {"exit_code": proc.returncode, "status": payload["status"],
                "reason": payload["reason"],
                "refused_before_reading_request_file": True}

    report.case("C9", "CLI submit refuses with a supplied TRUSTED_GRANT string", c9)

    # --- C10: reserved/spent arithmetic from the delivered helper ---
    def c10():
        from helm_quantum.vendor.q1_tools import budget_fits
        facts = {
            "exact_cap_boundary": budget_fits(cap="10.00", spent="6.00", reserved="4.00", proposed="0.00"),
            "one_cent_over": budget_fits(cap="10.00", spent="6.00", reserved="4.00", proposed="0.01"),
            "zero_budget_any_spend": budget_fits(cap="0.00", spent="0.00", reserved="0.00", proposed="0.01"),
            "zero_budget_zero_spend": budget_fits(cap="0.00", spent="0.00", reserved="0.00", proposed="0.00"),
        }
        assert facts["exact_cap_boundary"] is True
        assert facts["one_cent_over"] is False
        assert facts["zero_budget_any_spend"] is False
        assert facts["zero_budget_zero_spend"] is True
        return facts

    report.case("C10", "spent + reserved arithmetic refuses any over-cap spend", c10)

    # --- C11: budget arithmetic is pure; no atomic storage exists yet ---
    def c11():
        helper = (root / "helm_quantum/vendor/q1_tools.py").read_text(encoding="utf-8")
        assert "Production code also needs atomic trusted storage" in helper
        missing = [name for name in ("helm_quantum/budget.py", "helm_quantum/job_store.py")
                   if not (root / name).exists()]
        if missing:
            report.skip("C11", "atomic in-flight reservation and duplicate-submit recovery",
                        f"NOT_RUN: no atomic budget/job store exists; missing {missing}. "
                        f"The helper states it is pure arithmetic only. Duplicate-submit "
                        f"recovery requires provider idempotency reconciliation, which cannot "
                        f"be exercised without an adapter and must not be probed with a real provider.")
            return None
        raise AssertionError("modules appeared; re-run the duplicate-submit probe")

    result = c11()
    if result is not None:
        report.case("C11", "atomic reservation exists", lambda: result)

    # --- C12: no grant object changes the submission outcome (no hidden backdoor) ---
    def c12():
        from helm_quantum.backends.offline import OfflineBackend
        ctx2 = admit_offline_fixture("add2", "disabled")
        p2 = ctx2.problem()
        backend = OfflineBackend()
        grants = [
            None, "TRUSTED_GRANT", {"trusted_execution_grant": True},
            {"authorized": True, "budget_usd": "10.00"}, object(),
            type("Grant", (), {"trusted": True, "budget_usd": "10.00"})(),
        ]
        outcomes = []
        for grant in grants:
            try:
                backend.submit(p2, grant)
                outcomes.append((repr(grant)[:40], "ACCEPTED"))
            except ContractError as exc:
                outcomes.append((repr(grant)[:40], str(exc)))
        assert all(o[1] != "ACCEPTED" for o in outcomes), f"a grant was honoured: {outcomes}"
        reasons = {o[1] for o in outcomes}
        assert len(reasons) == 1, f"refusal reason varies by grant type: {reasons}"
        return {"grant_variants_tested": len(grants), "accepted": 0,
                "single_refusal_reason": reasons.pop(),
                "outcomes": outcomes}

    report.case("C12", "no caller-supplied grant variant changes the refusal", c12)

    # --- C13: a receipt is not bound to the candidate it is supposed to cover ---
    def c13():
        from helm_quantum.classical import search
        ctx3 = admit_offline_fixture("add2", "disabled")
        p3 = ctx3.problem()
        r1 = search(p3, "exhaustive").receipt
        r2 = search(p3, "uniform", samples=1, seed=5).receipt
        # Both receipts are constructible for the same problem with different content.
        assert r1.problem_digest == r2.problem_digest
        assert r1.candidates_checked != r2.candidates_checked, \
            "probe needs two receipts with different content"
        assert r1.status == r2.status == "COMPLETED"
        # Neither receipt carries any program, so a candidate cannot be bound to it.
        fields = set(r1.to_dict())
        program_fields = {f for f in fields
                          if "program" in f or "proposal" in f or "solution" in f}
        assert not program_fields, f"receipt now carries {program_fields}"
        # The only candidate-related field is a count, which identifies no program.
        count_only = {"candidates_checked"} <= fields
        return {"receipt_fields": sorted(fields),
                "program_binding_fields": [],
                "candidate_related_fields": [f for f in fields if "candidate" in f],
                "candidate_related_fields_are_counts_only": count_only,
                "candidates_checked_r1": r1.candidates_checked,
                "candidates_checked_r2": r2.candidates_checked,
                "finding": "A receipt attests to a problem, not to a candidate. Any two "
                           "receipts for the same problem are both valid, so a receipt "
                           "cannot prove that a specific program was produced by a run."}

    report.case("C13", "receipt carries no candidate binding (latent provenance gap)", c13)

    payload = {"probe": "C-authority-refusal", "reviewer": "Q1-DeepSeek",
               "package_root": str(root), "counts": report.summary(), "cases": report.cases}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    summary = report.summary()
    return 0 if summary.get("FAIL", 0) == 0 and summary.get("ERROR", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
