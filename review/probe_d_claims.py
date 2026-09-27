"""Reviewer probe D: false hardware, simulator and learning claims.

Owner: Q1-DeepSeek (review/). Read-only against builder source.

The directive requires separate labels for fixture engineering, simulator
behavior, real QPU execution, CAS integration and neural learning (shared rule
22). This probe forges each overclaim and confirms the contracts refuse it.

Run:
  python review/probe_d_claims.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import traceback
from pathlib import Path

VENDOR_SDK_TOKENS = ("braket", "qiskit", "qiskit_ibm_runtime", "amazon", "boto3",
                     "botocore", "dwave", "azure.quantum", "pennylane", "cirq")
NETWORK_TOKENS = ("requests", "urllib", "httpx", "socket", "http.client", "aiohttp",
                  "urlopen", "subprocess")


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

    from helm_quantum.admission import admit_offline_fixture
    from helm_quantum.contracts import QuantumRunReceipt, QuantumVerification
    from helm_quantum.verifier import propose, verify
    from helm_quantum.wire import ContractError

    ctx = admit_offline_fixture("add2", "disabled")
    problem = ctx.problem()

    def receipt(**overrides):
        base = dict(schema="helm-q1-receipt/1", problem_digest=problem.problem_digest,
                    binding=problem.binding, mode=problem.mode,
                    requested_backend="offline-classical",
                    actual_backend="offline-classical",
                    execution_kind="CLASSICAL_OFFLINE",
                    device_properties_digest=None, native_circuit_digest=None,
                    compilation_settings=(), measurement_order="NOT_APPLICABLE",
                    shots=0, observed_counts=(), job_ids=(), elapsed_ns=1,
                    candidates_checked=1, quote_id=None, estimated_charges_usd="0.00",
                    reconciled_charges_usd=None, status="COMPLETED",
                    _admission=ctx, _problem=problem)
        base.update(overrides)
        return QuantumRunReceipt(**base)

    def expect_refusal(fn, label):
        try:
            value = fn()
        except ContractError as exc:
            return f"REFUSED: {exc}"
        raise AssertionError(f"{label} was ACCEPTED, returned {value!r}")

    # --- D1: forged hardware execution is refused ---
    def d1():
        forged = {}
        forged["braket_hardware"] = expect_refusal(
            lambda: receipt(requested_backend="aws-braket",
                            actual_backend="aws-braket",
                            execution_kind="QPU_EXECUTED",
                            device_properties_digest="a" * 64,
                            native_circuit_digest="b" * 64,
                            measurement_order="q0q1q2q3q4q5",
                            shots=1000, observed_counts=("000000 1",),
                            job_ids=("task-arn-123",), quote_id="q-1",
                            estimated_charges_usd="7.25"),
            "Braket hardware receipt")
        forged["ibm_hardware"] = expect_refusal(
            lambda: receipt(requested_backend="ibm-open", actual_backend="ibm-open",
                            execution_kind="QPU_EXECUTED", shots=1000,
                            job_ids=("ibm-job-1",)),
            "IBM hardware receipt")
        forged["mismatched_backend"] = expect_refusal(
            lambda: receipt(actual_backend="local-simulator",
                            execution_kind="SIMULATOR"),
            "mismatched backend pair")
        return forged

    report.case("D1", "forged hardware and mismatched-backend receipts are refused", d1)

    # --- D2: false simulator claim is refused ---
    def d2():
        forged = {}
        forged["simulator_kind"] = expect_refusal(
            lambda: receipt(execution_kind="SIMULATOR", requested_backend="local",
                            actual_backend="local"), "simulator execution kind")
        forged["shots_without_execution"] = expect_refusal(
            lambda: receipt(shots=1000), "shots on an offline classical receipt")
        forged["counts_without_measurement"] = expect_refusal(
            lambda: receipt(observed_counts=("00 1",)), "observed counts offline")
        forged["jobs_offline"] = expect_refusal(
            lambda: receipt(job_ids=("job-1",)), "job ids offline")
        return forged

    report.case("D2", "simulator, shot, measurement and job claims are refused offline", d2)

    # --- D3: nonzero charge and non-null quote are refused ---
    def d3():
        forged = {}
        forged["estimated_charge"] = expect_refusal(
            lambda: receipt(estimated_charges_usd="0.01"), "nonzero estimated charge")
        forged["reconciled_charge"] = expect_refusal(
            lambda: receipt(reconciled_charges_usd="0.00"), "reconciled charge present")
        forged["quote_id"] = expect_refusal(
            lambda: receipt(quote_id="q-1"), "quote id present")
        return forged

    report.case("D3", "provider cost and quote fields cannot be populated offline", d3)

    # --- D4: the accepted offline receipt is truthful about what it is ---
    def d4():
        good = receipt()
        assert good.execution_kind == "CLASSICAL_OFFLINE"
        assert good.actual_backend == "offline-classical"
        assert good.shots == 0 and good.observed_counts == () and good.job_ids == ()
        assert good.estimated_charges_usd == "0.00"
        assert good.measurement_order == "NOT_APPLICABLE"
        return good.to_dict()

    report.case("D4", "the admitted receipt claims only offline classical work", d4)

    # --- D5: verification cannot claim retention or a foreign verifier ---
    def d5():
        verification = verify(problem, propose(problem, (1, 1, 0)))
        assert verification.retained is False, "verification claims retention"
        forged = {}
        forged["retained_true"] = expect_refusal(
            lambda: QuantumVerification(
                schema="helm-q1-verification/1", problem_digest=problem.problem_digest,
                binding=problem.binding, mode="disabled", program=(1, 1, 0),
                verifier_digest=problem.verifier_digest, outputs=(2, 3, 0, 1),
                inputs_checked=4, accepted=True, disposition="VERIFIED_OFFLINE_ONLY",
                retained=True, _admission=ctx, _problem=problem),
            "verification with retained=True")
        forged["forged_verifier_digest"] = expect_refusal(
            lambda: QuantumVerification(
                schema="helm-q1-verification/1", problem_digest=problem.problem_digest,
                binding=problem.binding, mode="disabled", program=(1, 1, 0),
                verifier_digest="f" * 64, outputs=(2, 3, 0, 1),
                inputs_checked=4, accepted=True, disposition="VERIFIED_OFFLINE_ONLY",
                retained=False, _admission=ctx, _problem=problem),
            "verification with foreign verifier digest")
        forged["unrecomputed_outputs"] = expect_refusal(
            lambda: QuantumVerification(
                schema="helm-q1-verification/1", problem_digest=problem.problem_digest,
                binding=problem.binding, mode="disabled", program=(1, 1, 0),
                verifier_digest=problem.verifier_digest, outputs=(0, 1, 2, 3),
                inputs_checked=4, accepted=True, disposition="VERIFIED_OFFLINE_ONLY",
                retained=False, _admission=ctx, _problem=problem),
            "verification with unrecomputed outputs")
        return {"true_retained": verification.retained, "refusals": forged,
                "disposition": verification.disposition}

    report.case("D5", "verification refuses retention and forged verifier identity", d5)

    # --- D6: research mode does not grant retention or dispatch ---
    def d6():
        from helm_quantum.eligibility import assess
        rows = {}
        for mode in ("disabled", "shadow", "research"):
            p = admit_offline_fixture("add2", mode).problem()
            e = assess(p)
            assert e.quantum_dispatch_allowed is False, f"{mode} allows dispatch"
            assert e.authoritative_write_allowed is False, f"{mode} allows authority write"
            assert e.retention_allowed is False, f"{mode} allows retention"
            rows[mode] = e.to_dict()
        return rows

    report.case("D6", "no mode grants dispatch, write authority or retention", d6)

    # --- D7: disposition wording separates modes and never says promoted ---
    def d7():
        rows = {}
        for mode in ("disabled", "shadow", "research"):
            p = admit_offline_fixture("add2", mode).problem()
            v = verify(p, propose(p, (1, 1, 0)))
            assert "PROMOTED" not in v.disposition
            assert "RETAINED" not in v.disposition
            rows[mode] = v.disposition
        assert len(set(rows.values())) == 3, f"modes share a disposition: {rows}"
        return rows

    report.case("D7", "mode dispositions are distinct and claim no promotion", d7)

    # --- D8: no provider SDK or network use anywhere in the package ---
    def d8():
        hits = []
        for path in sorted((root / "helm_quantum").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    root_mod = name.split(".")[0]
                    if root_mod in VENDOR_SDK_TOKENS:
                        hits.append((path.name, "SDK", name))
                    if root_mod in ("requests", "urllib", "httpx", "socket", "aiohttp"):
                        hits.append((path.name, "NETWORK", name))
        assert not hits, f"provider/network imports found: {hits}"
        return {"sdk_imports": [], "network_imports": [],
                "files_scanned": len(list((root / "helm_quantum").rglob("*.py")))}

    report.case("D8", "no provider SDK or network import exists in the package", d8)

    # --- D9: no neural/learning or model-training code path exists ---
    def d9():
        hits = []
        for path in sorted((root / "helm_quantum").rglob("*.py")):
            text = path.read_text(encoding="utf-8").lower()
            for token in ("torch", "tensorflow", "jax", "checkpoint_dir", "backprop",
                          "optimizer", "training_step", "finetune", "fine_tune"):
                if token in text:
                    hits.append((path.name, token))
        assert not hits, f"learning-related tokens found: {hits}"
        return {"learning_tokens": [], "neural_learning_implemented": False,
                "note": "No learning capability exists in this packet; any learning "
                        "claim would be unsupported."}

    report.case("D9", "no learning or model-training code exists in this packet", d9)

    # --- D10: inventory and compile honestly report absence ---
    def d10():
        from helm_quantum.backends.offline import OfflineBackend
        backend = OfflineBackend()
        caps = backend.capabilities()
        assert caps.compile_available is False
        assert caps.execution_kind == "NO_QUANTUM_EXECUTION"
        estimate = backend.estimate(problem)
        assert estimate["status"] == "UNAVAILABLE_COMPILER_RESOURCE_ESTIMATE"
        assert estimate["qubits"] is None and estimate["gates"] is None
        # The inventory command must fail honestly while the file is absent.
        import subprocess
        proc = subprocess.run([sys.executable, "-m", "helm_quantum", "inventory", "--read-only"],
                              cwd=str(root), capture_output=True, text=True, timeout=120)
        inventory_absent = not (root / "SOURCE_INVENTORY.json").exists()
        payload = json.loads(proc.stderr.strip().splitlines()[-1]) if proc.returncode else None
        return {"capabilities": caps.to_dict(), "estimate": estimate,
                "source_inventory_file_exists": not inventory_absent,
                "inventory_exit_code": proc.returncode,
                "inventory_response": payload}

    report.case("D10", "unimplemented capabilities report absence, not success", d10)

    # --- D11: quantum compiler work is genuinely absent ---
    def d11():
        compiler = root / "helm_quantum/compiler"
        if not compiler.exists():
            report.skip("D11", "reversible compiler: predicate parity, superposition, ancilla cleanup",
                        "NOT_RUN: helm_quantum/compiler/ does not exist in this handoff. "
                        "Q1-Claude has issued ACK/START not observed. Six selection qubits, "
                        "total qubit count, depth and ancilla cleanup cannot be reviewed "
                        "because no compiler source has been published.")
            return None
        raise AssertionError("compiler appeared; write the parity/ancilla probes")

    if d11() is not None:
        report.case("D11", "compiler present", lambda: {"present": True})

    payload = {"probe": "D-claims-integrity", "reviewer": "Q1-DeepSeek",
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
