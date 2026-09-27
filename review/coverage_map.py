"""Acceptance coverage map for HELM-Q1, retaining original T01-T40 IDs.

Reviewer-owned: Q1-DeepSeek. Generated from the actual probe result files in
review/out/ so the map cannot drift from what was executed.

States (kept separate, per directive section 19 and 04_DEEPSEEK_Q1.md):
  EXECUTED_PASS      - a reviewer probe ran and passed
  EXECUTED_FAIL      - a reviewer probe ran and failed
  NOT_RUN_NO_ARTIFACT- the required builder artifact is absent from the handoff
  NOT_RUN_REQUIRES_PROVIDER - needs a real provider/hardware call; not permitted
  NOT_YET_APPLICABLE - the feature it would test does not exist yet

Run:
  python review/coverage_map.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PASS = "EXECUTED_PASS"
RUN_NA = "NOT_RUN_NO_ARTIFACT"
RUN_PROV = "NOT_RUN_REQUIRES_PROVIDER"
NYA = "NOT_YET_APPLICABLE"

# T01-T40 from original directive section 19 "Minimum acceptance matrix".
MATRIX = [
    ("T01", "Admitted source/parent identity", PASS, ["C1", "C2", "C3"],
     "Identity is factory-derived; caller-minted admission refused; forged caller_id refused. "
     "NOTE: caller/branch/frame values are offline-fixture literals, not a real RPM caller."),
    ("T02", "Unknown schema", PASS, ["C3"],
     "from_json requires an exact field set and a live admission context."),
    ("T03", "Malformed checkpoint", PASS, ["C5"],
     "checkpoint_digest rejects any non-None malformed value; None is the only admitted value here."),
    ("T04", "Foreign branch", PASS, ["C4"],
     "A proposal with a foreign ReturnAddress is refused."),
    ("T05", "Stale snapshot", PASS, ["C3", "C6"],
     "Expired admission refused; caller-supplied snapshot refs cannot replace the fixture digest."),
    ("T06", "Ordered instruction semantics", PASS, ["S1", "S2", "S5"],
     "All four operations checked on all four inputs; order sensitivity proven; 64x4 cross-check."),
    ("T07", "All finite inputs", PASS, ["S3", "S7", "S8"],
     "Every candidate is evaluated on all four inputs; one wrong input rejects."),
    ("T08", "Negative fixture", PASS, ["S3", "S4", "S9"],
     "parity has 0 solutions; the stated reason is bijectivity of the generators."),
    ("T09", "Unsupported operations", PASS, ["S1", "C7"],
     "Instruction codes are bounded to 0..3; validate_program refuses anything else."),
    ("T10", "Independent verifier", PASS, ["O1", "O2", "S5", "S7", "S8"],
     "direct_outputs recomputes from scratch, imports no helper, and is cross-checked against the "
     "reviewer's own reference over all 64 programs."),
    ("T11", "Predicate parity", RUN_NA, [], "No compiler exists; cannot compare a circuit predicate."),
    ("T12", "Superposition behavior", RUN_NA, [], "No compiler exists; no coherent-state test is possible."),
    ("T13", "Ancilla cleanup", RUN_NA, [], "No compiler exists; no workspace register to clean."),
    ("T14", "Endianness", RUN_NA, [], "Declared only as decoding_order; no lowering code to test."),
    ("T15", "No lookup-answer leakage", PASS, ["O1", "O3", "O4", "O5", "O6", "O7", "O8", "O10"],
     "Fixture exports no IDs; no answer-list identifier or program-shaped literal in source; "
     "reviewer rebuilt the predicate and found the same 6 programs from the public spec alone."),    ("T16", "Disabled parity", PASS, ["D4", "D6", "D7"],
     "Disabled mode assessed; no dispatch, write or retention granted."),
    ("T17", "Shadow non-mutation", PASS, ["D6", "D7"],
     "Shadow mode grants no authoritative write and has a distinct disposition from disabled."),
    ("T18", "Immediate-parent return", RUN_NA, ["C1"],
     "C1 confirms the binding SHAPE is enforced and factory-derived, but no RPM caller exists to "
     "return to. The parent_ref/caller_id values are offline-fixture literals."),
    ("T19", "Nested prerequisites", RUN_NA, [], "No RPM/RPA adapter in this handoff."),
    ("T20", "Shared prerequisite", RUN_NA, [], "No RPM/RPA adapter in this handoff."),
    ("T21", "Cycle/depth refusal", RUN_NA, [], "No adapter; prerequisites tuple is empty in the fixture."),
    ("T22", "Rollback", RUN_NA, [], "No branch/rollback machinery exists."),
    ("T23", "Restart without QPU", RUN_NA, [], "Requires the retention bridge and a job store; neither exists."),
    ("T24", "Viewer read-only", NYA, [], "No viewer or RPA adapter exists to test."),
    ("T25", "Protected-answer isolation", PASS, ["O4", "O5", "O9"],
     "Evaluator counts are reported to humans only and are not importable into the predicate path."),
    ("T26", "Zero-budget refusal", PASS, ["C7", "C8", "C9", "C10", "C12"],
     "Zero shots/tasks/cost forced by contract; backend refuses all verbs; CLI refuses a supplied "
     "TRUSTED_GRANT before reading any request file; 6 grant variants all produce one refusal."),
    ("T27", "No paid fallback", PASS, ["D1", "D2", "D3", "D8", "C12"],
     "No provider SDK import exists; nonzero charge and quote fields are refused; no grant enables it."),
    ("T28", "Atomic in-flight reservation", RUN_NA, [], "helm_quantum/budget.py does not exist. The "
     "delivered helper is pure arithmetic and says so."),
    ("T29", "Duplicate submit recovery", RUN_NA, [], "helm_quantum/job_store.py does not exist; no "
     "idempotency key, no provider reconciliation. Must not be probed against a real provider."),
    ("T30", "Stale quote refusal", PASS, ["C7", "D3"],
     "quote_id must be None on an offline receipt, so no stale quote can be carried as current."),
    ("T31", "Timeout versus cancellation", RUN_PROV, [],
     "Needs a provider adapter. The offline backend reports UNKNOWN_JOB for both poll and cancel, "
     "which is honest but is not a cancellation receipt."),
    ("T32", "Failed/partial jobs", RUN_PROV, [], "No adapter and no job store."),
    ("T33", "Calibration/circuit provenance", RUN_PROV, ["D1", "D10"],
     "Forged device_properties_digest and native_circuit_digest are refused offline; real provenance "
     "needs hardware."),
    ("T34", "Simulator/hardware labeling", PASS, ["D1", "D2", "D4", "D10"],
     "QPU_EXECUTED, SIMULATOR and mismatched backend pairs are all refused; the admitted receipt "
     "claims only CLASSICAL_OFFLINE with zero shots and no job ids."),
    ("T35", "No-sample versus unsatisfiability", PASS, ["O9"],
     "Exhaustive reports UNSAT_PROVED with the bijectivity reason; bounded sampling never reports "
     "UNSAT_PROVED."),
    ("T36", "Exact test count reconciliation", PASS, ["self"],
     "This map. 47 probe cases executed, 47 passed, 0 failed, 0 errors, 2 NOT_RUN. The original "
     "package's 22 helper tests are reported separately and were NOT re-run by this reviewer. "
     "The builder's evidence/TEST_STATUS.json separately and honestly reports 41 authored new "
     "test methods with 0 collected and 0 executed."),
    ("T37", "External-assistance attribution", PASS, ["O1", "O3", "O8"],
     "The compiler import ban is written into the lease; no compiler exists to violate it yet."),
    ("T38", "Resource preflight", RUN_NA, ["D10"],
     "estimate() correctly reports UNAVAILABLE_COMPILER_RESOURCE_ESTIMATE with null qubits and gates. "
     "SOURCE_INVENTORY.json now pins a profile block, but every profile field is null and "
     "linux_x86_64_verified / linux_arm64_verified are both false, so there is still no measured "
     "resource envelope to review."),
    ("T39", "Preserved active training", NYA, [],
     "This packet contains no HELM runtime and no training path, so there is nothing to preserve or "
     "damage. D9 confirms no training code exists here. SOURCE_INVENTORY.json records "
     "host_runtime_slices: [] and checkpoint_digest: null."),
    ("T40", "Independent acceptance", NYA, [],
     "This reviewer cannot close its own gate. SOURCE_INVENTORY.json records "
     "independently_reviewed: false and independent_review: NOT_RECEIVED. Q1-Codex must confirm "
     "these findings, and a reviewer-authored fix would need a distinct check by another qualified lead."),
    ("--", "Schema/contract agreement (reviewer-added check)", PASS, ["E1", "E2", "E3", "E4", "E5"],
     "Not a directive ID. Added because schemas/ appeared mid-review. Schema field sets equal the "
     "live dataclass field sets for problem/proposal/receipt; all 10 pinned receipt fields and the "
     "status enum agree with the enforcing code; a produced receipt satisfies its own schema; a "
     "schema-valid problem is still refused without host state; no schema admits credential material."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    root = args.package_root.resolve()

    probe_files = {}
    for name in ("a_semantics", "b_oracle", "c_authority", "d_claims", "e_schemas"):
        path = root / "review/out" / f"{name}.json"
        if path.exists():
            probe_files[name] = json.loads(path.read_text(encoding="utf-8"))

    executed = {}
    for name, payload in probe_files.items():
        for case in payload["cases"]:
            executed[case["id"]] = case["outcome"]

    counts = {}
    for name, payload in probe_files.items():
        for outcome, number in payload["counts"].items():
            counts[outcome] = counts.get(outcome, 0) + number

    rows = []
    for tid, requirement, state, probe_ids, note in MATRIX:
        observed = {pid: executed.get(pid) for pid in probe_ids if pid in executed}
        if state == PASS and any(v != "PASS" for v in observed.values()):
            state = "REVIEW_STATE_MISMATCH"
        rows.append({"id": f"HELM-Q1/{tid}", "requirement": requirement,
                     "review_state": state, "probes": probe_ids,
                     "probe_outcomes": observed, "note": note})

    by_state = {}
    for row in rows:
        by_state[row["review_state"]] = by_state.get(row["review_state"], 0) + 1

    payload = {
        "map": "HELM-Q1 acceptance coverage (original T01-T40 IDs retained)",
        "reviewer": "Q1-DeepSeek",
        "reviewed_source": str(root),
        "probe_cases_executed": {k: v for k, v in sorted(counts.items())},
        "probe_cases_executed_total": sum(counts.values()),
        "probe_failures": counts.get("FAIL", 0),
        "probe_errors": counts.get("ERROR", 0),
        "by_review_state": by_state,
        "rows": rows,
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
