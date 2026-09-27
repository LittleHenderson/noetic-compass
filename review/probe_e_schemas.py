"""Reviewer probe E: JSON Schema versus the Python contract boundary.

Owner: Q1-DeepSeek (review/). Read-only against builder source.

The builder's README says "JSON schemas are transport documentation, not
authority." This probe checks the weaker but still necessary property that the
documentation does not *contradict* the enforcing Python code, because a schema
that promises more than the code enforces invites a caller to rely on it.

Run:
  python review/probe_e_schemas.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import json
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

    schema_dir = root / "schemas"
    if not schema_dir.exists():
        report.skip("E0", "schema/contract agreement",
                    "NOT_RUN: schemas/ absent from this handoff")
        print(json.dumps({"probe": "E-schemas", "counts": report.summary(),
                          "cases": report.cases}, indent=2))
        return 0

    from dataclasses import fields

    from helm_quantum.admission import admit_offline_fixture
    from helm_quantum.contracts import QuantumProblem, QuantumProposal, QuantumRunReceipt
    from helm_quantum.verifier import propose, verify  # noqa: F401 - imported for parity

    # --- E1: schema field sets match the live dataclass field sets ---
    def e1():
        pairs = [("problem.json", QuantumProblem), ("proposal.json", QuantumProposal),
                 ("receipt.json", QuantumRunReceipt)]
        rows = {}
        for filename, cls in pairs:
            schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
            schema_fields = set(schema["properties"])
            live = {f.name for f in fields(cls) if not f.name.startswith("_")}
            assert schema_fields == live, \
                f"{filename}: schema-only={sorted(schema_fields - live)} " \
                f"code-only={sorted(live - schema_fields)}"
            assert set(schema["required"]) == live, \
                f"{filename}: required set differs from live fields"
            assert schema.get("additionalProperties") is False, \
                f"{filename} does not forbid additional properties"
            rows[filename] = {"fields": len(live), "match": True}
        return rows

    report.case("E1", "schema field sets equal the live contract field sets", e1)

    # --- E2: schema constants cannot permit what the code refuses ---
    def e2():
        receipt = json.loads((schema_dir / "receipt.json").read_text(encoding="utf-8"))
        props = receipt["properties"]
        # Every field the Python code forces to a single value must be const in the schema.
        pinned = {
            "requested_backend": "offline-classical", "actual_backend": "offline-classical",
            "execution_kind": "CLASSICAL_OFFLINE", "measurement_order": "NOT_APPLICABLE",
            "quote_id": None, "estimated_charges_usd": "0.00", "reconciled_charges_usd": None,
            "device_properties_digest": None, "native_circuit_digest": None,
            "shots": 0,
        }
        drift = {}
        for key, expected in pinned.items():
            declared = props[key]
            if "const" not in declared or declared["const"] != expected:
                drift[key] = declared
        assert not drift, f"schema permits values the code refuses: {drift}"
        # The status enum must equal the code's allowed statuses.
        assert set(props["status"]["enum"]) == {"COMPLETED", "BUDGET_EXHAUSTED"}, props["status"]
        return {"pinned_fields_checked": len(pinned), "drift": {}, "status_enum": props["status"]["enum"]}

    report.case("E2", "no schema constant contradicts the enforcing code", e2)

    # --- E3: an actual admitted receipt satisfies its own schema's pinned values ---
    def e3():
        from helm_quantum.classical import search
        problem = admit_offline_fixture("add2", "disabled").problem()
        receipt = search(problem, "exhaustive").receipt
        record = receipt.to_dict()
        schema = json.loads((schema_dir / "receipt.json").read_text(encoding="utf-8"))
        for key, declared in schema["properties"].items():
            if "const" in declared:
                assert record[key] == declared["const"], \
                    f"live receipt {key}={record[key]!r} violates schema const {declared['const']!r}"
        assert set(record) == set(schema["required"]), "record keys differ from required"
        return {"live_receipt_agrees_with_schema": True,
                "const_fields_checked": sum(1 for d in schema["properties"].values() if "const" in d)}

    report.case("E3", "a produced receipt satisfies its declared schema", e3)

    # --- E4: schema is documentation, not authority - the Python boundary still rules ---
    def e4():
        # The README claims the schema grants nothing. Prove the code rejects a
        # record that would be schema-valid but has no admitted host state.
        problem_json = admit_offline_fixture("add2", "disabled").problem().to_json()
        from helm_quantum.wire import ContractError
        try:
            QuantumProblem.from_json(problem_json)
        except ContractError as exc:
            return {"refused_without_admission": str(exc),
                    "schema_alone_grants_nothing": True}
        raise AssertionError("a schema-shaped record was admitted without host state")

    report.case("E4", "a schema-valid record still cannot mint authority", e4)

    # --- E5: no schema declares a submission or hardware field as permitted ---
    def e5():
        hits = []
        for path in sorted(schema_dir.glob("*.json")):
            text = path.read_text(encoding="utf-8").lower()
            for token in ("authorization", "trusted_grant", "api_key", "credential",
                          "token", "secret", "endpoint"):
                if token in text:
                    hits.append((path.name, token))
        assert not hits, f"credential/authorization material appears in schemas: {hits}"
        return {"credential_tokens_found": [], "schemas_scanned": len(list(schema_dir.glob("*.json")))}

    report.case("E5", "no schema admits credential or grant material", e5)

    payload = {"probe": "E-schema-contract-drift", "reviewer": "Q1-DeepSeek",
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
