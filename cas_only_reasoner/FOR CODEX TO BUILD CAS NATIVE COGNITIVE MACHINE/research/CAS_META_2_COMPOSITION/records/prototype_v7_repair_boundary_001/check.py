"""Small source-extracted repair predicate fixture; not native/GPU execution.

Only standard-library imports. No runtime import, checkpoint load, tensor,
SQLite open, provider call, or changes to any source/evidence input.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "42f9164754312f12850d9b8789c062fa7fb8069f"
ARCHIVE_SHA = "f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9"
RECEIPT_SHA = "bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f"
MESSAGE = "repair cannot open without a durable distinct ^6 round trip"
PINS = {
    "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py": "5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187",
    "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/network.py": "748ef8585c84e64e00de99c8b5b320fedb5ef738d7947afb008a2cf250fe1d1f",
    "CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py": "0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735",
    "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py": "c1604059580a553e131233ecdbb5b1de8439edbba03865f7985a71b0dfdfb736",
    "CAS_META_2_COMPOSITION/cas_meta2/native.py": "16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512",
    "CAS_META_2_COMPOSITION/cas_meta2/curriculum.py": "c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384",
    "CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py": "4570dec76d8f204c7fccb3d54a71b917b160da072322acb609fc8730ce4fa9df",
    "CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/compiler.py": "49f7f917e97b8748237034e4c920d7fcd21ae1d705ab2b73d14e47a69589eb78",
}


def method(tree, class_name, name):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return deepcopy(next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name))


def main():
    archive = ROOT / "records/aws_prototype_v7_source_001"
    receipt_path = ROOT / "records/prototype_v7_partial_native_001/run_001/partial_native_receipt.json"
    assert sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
    receipt_bytes = receipt_path.read_bytes()
    assert sha256(receipt_bytes).hexdigest() == RECEIPT_SHA
    data = json.loads(receipt_bytes)
    assert data["source_sha"] == SOURCE_SHA
    sources = {}
    with ZipFile(archive) as zipped:
        for relative, expected in PINS.items():
            payload = (ROOT.parent / relative).read_bytes()
            assert sha256(payload).hexdigest() == expected, relative
            assert payload == zipped.read("research/" + relative), relative
            sources[relative] = ast.parse(payload)
    runtime = sources["CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py"]
    viability = method(runtime, "NeuralCJTRuntime", "_viable_repair_cjts")
    prepare = method(runtime, "NeuralCJTRuntime", "_prepare_inference")
    guard = next(n for n in ast.walk(prepare) if isinstance(n, ast.If)
                 and isinstance(n.test, ast.UnaryOp)
                 and isinstance(n.test.operand, ast.Call)
                 and isinstance(n.test.operand.func, ast.Attribute)
                 and n.test.operand.func.attr == "_viable_repair_cjts")
    assert ast.literal_eval(guard.body[0].exc.args[0]) == MESSAGE
    # The actual guard body is compiled unchanged, in a three-argument wrapper.
    wrapper = ast.parse("def repair_guard(self, state, bias):\n    pass\n").body[0]
    wrapper.body = [deepcopy(guard), ast.Return(value=ast.Constant(True))]
    edge = method(sources["CAS_CJT_TRANSFORMER_v0_2/cas_cjt/network.py"],
                  "NeuralCJTNetwork", "edge_permitted")
    error = deepcopy(next(n for n in runtime.body if isinstance(n, ast.ClassDef)
                          and n.name == "RuntimeContractError"))
    coordinator = next(ast.literal_eval(n.value) for n in runtime.body
                       if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "COORDINATOR_ID" for t in n.targets))
    namespace = {
        "OperatingRegion": NS(BREAKDOWN="BREAKDOWN", NON_OHMIC="NON_OHMIC", UNSTABLE="UNSTABLE"),
        "CauseKind": NS(RPM_SUBGOAL="RPM_SUBGOAL"), "COORDINATOR_ID": coordinator,
    }
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                              error, viability, wrapper, edge], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "<pinned-source-predicate-only>", "exec"), namespace)
    topology = data["outcomes"]["runtime_identity"]["topology"]
    edges = {(r["source_cjt_id"], r["target_cjt_id"]): r["permitted"] for r in topology["edges"]}
    fixture = sources["CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py"]
    topology_ast = next(n.value for n in fixture.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "TOPOLOGY" for t in n.targets))
    fixture_edges = {(ast.literal_eval(call.args[0]), ast.literal_eval(call.args[1])): True
                     for call in topology_ast.elts}
    assert edges == fixture_edges == {("A", "B"): True, ("B", "C"): True,
                                      ("C", "R"): True, ("R", "C"): True}
    # Deliberately synthetic, maximally eligible non-topology attributes.
    biases = [NS(cjt_id=n, stable=NS(registered_operation_id="^6"),
                 governance=NS(topology_permissions=("cascade",), hard_permissions=("execute", "publish_effect"),
                               effect_publication_authorities=(coordinator,), quarantined=False),
                 rpm=NS(readiness=NS(hard_open=True)), operating=NS(region="OHMIC")) for n in ("A", "B", "C", "R")]
    state = NS(biases=biases, by_cjt_id={b.cjt_id: b for b in biases})
    network = NS(_specs={b.cjt_id: None for b in biases}, _topology=edges)
    network.edge_permitted = lambda a, b: namespace["edge_permitted"](network, a, b)
    contract = NS(operation_id="^6", ontology_status=NS(value="CANONICAL_ADMITTED"),
                  accepted_cause_kinds=("RPM_SUBGOAL",), legal_actions=("PROPOSE_EFFECT",))
    runtime_stub = NS(network=network, contracts={"^6": contract})
    runtime_stub._viable_repair_cjts = lambda s, n: namespace["_viable_repair_cjts"](runtime_stub, s, n)
    actual = {n: list(runtime_stub._viable_repair_cjts(state, n)) for n in ("A", "B", "C", "R")}
    assert actual == {"A": [], "B": [], "C": ["R"], "R": ["C"]}
    refused = []
    for n in ("A", "B"):
        try:
            namespace["repair_guard"](runtime_stub, state, state.by_cjt_id[n])
        except namespace["RuntimeContractError"] as exc:
            assert str(exc) == MESSAGE
            refused.append(n)
        else:
            raise AssertionError("missing expected guard refusal")
    for n in ("C", "R"):
        assert namespace["repair_guard"](runtime_stub, state, state.by_cjt_id[n]) is True
    # A two-node, one-way development fixture rejects; reciprocal edge admits.
    network._topology = {("A", "B"): True}
    assert runtime_stub._viable_repair_cjts(state, "A") == ()
    network._topology[("B", "A")] = True
    assert runtime_stub._viable_repair_cjts(state, "A") == ("B",)
    state.by_cjt_id["B"].governance.quarantined = True
    assert runtime_stub._viable_repair_cjts(state, "A") == ()
    witnesses = []
    for case in data["outcomes"]["cases"]:
        for arm, row in case["arms"].items():
            if row["execution_status"] == "POST_ADMISSION_RUNTIME_FAILURE":
                nxt = row["next_sealed_run"]
                assert nxt["cjt_id"] == "B" and nxt["input_node"] == -1
                assert nxt["node"] == row["partial_work"]["committed_native_runs"]
                witnesses.append({"case_index": case["case_index"], "arm": arm,
                                  "committed_runs": nxt["node"], "next_sealed_run": nxt})
    assert [(r["case_index"], r["arm"], r["committed_runs"]) for r in witnesses] == [
        (19, "cas_trained", 3), (32, "generic_trained", 9), (51, "generic_trained", 1),
        (66, "generic_trained", 3), (71, "generic_trained", 2)]
    for relative, expected in PINS.items():
        assert sha256((ROOT.parent / relative).read_bytes()).hexdigest() == expected
    assert sha256(receipt_path.read_bytes()).hexdigest() == RECEIPT_SHA
    forbidden = ("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "boto3", "sqlite3")
    assert not any(k == f or k.startswith(f + ".") for k in sys.modules for f in forbidden)
    print(json.dumps({"status": "PURE_REPAIR_BOUNDARY_CHECKED", "source_sha": SOURCE_SHA,
                      "source_archive_sha256": ARCHIVE_SHA, "source_files": PINS,
                      "partial_native_receipt_sha256": RECEIPT_SHA,
                      "actual_source_predicate_on_synthetic_state": actual,
                      "exact_guard_refusals": refused, "predicate_and_guard_cases_checked": 11,
                      "known_failure_witnesses": witnesses, "native_execution": False,
                      "neural_modules_imported": False, "original_database_opened": False,
                      "provider_calls": False, "failed_candidate_semantic_content": None,
                      "boundary": "Exact source predicate and guard on synthetic state; no new native execution or failed-tick reconstruction."}, indent=2))


if __name__ == "__main__":
    main()
