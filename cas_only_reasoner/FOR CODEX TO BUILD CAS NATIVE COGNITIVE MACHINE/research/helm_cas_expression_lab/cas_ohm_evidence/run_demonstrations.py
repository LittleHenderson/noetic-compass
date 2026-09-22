"""Reproduce actual compiler/CLI and prepared-connection examples without models."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

EVIDENCE = Path(__file__).resolve().parent
LAB = EVIDENCE.parent
REPO = LAB.parents[3]
sys.path.insert(0, str(LAB))
import cas_ohm_connections as connections
import historical_compiler

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def save(name, data):
    (EVIDENCE / name).write_text(json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

def expression(operation, a_kind, a, b_kind, b):
    scale = 'ohm_scale("demo-linear", "declared_drive", "declared_attention")'
    return (
        f'{operation}(ohm_{a_kind}("{a}", {scale}, "design", "demo:first"), '
        f'ohm_{b_kind}("{b}", {scale}, "design", "demo:second"))'
    )

def main():
    compiler, _, binding = connections._runtime()
    cases = (
        ("attention_3", expression("ohm_flow", "drive", "12", "constraint", "4"), "3"),
        ("attention_2", expression("ohm_flow", "drive", "12", "constraint", "6"), "2"),
        ("required_drive_12", expression("ohm_required_drive", "attention", "3", "constraint", "4"), "12"),
        ("effective_constraint_4", expression("ohm_effective_constraint", "drive", "12", "attention", "3"), "4"),
        ("invalid_zero_constraint", expression("ohm_flow", "drive", "12", "constraint", "0"), None),
    )
    examples = {}
    for name, source, expected in cases:
        artifact = compiler.compile_expression(source).to_dict()
        assert artifact["valid"] is (expected is not None), (name, artifact)
        if expected is not None:
            assert artifact["result"]["value"] == expected
        else:
            assert "OHM_ZERO_CONSTRAINT" in artifact["error"] and artifact["result"] is None
        examples[name] = {"expression": source, "artifact": artifact}
        (EVIDENCE / (name + ".cas")).write_text(source + "\n", encoding="utf-8", newline="\n")
    save("compiler_examples.json", {"implementation_sha256_lf": binding, "cases": examples})

    scale = {"id": "demo-linear", "drive_unit": "declared_drive", "attention_unit": "declared_attention"}
    board = "board demo { node a: ^8^C|A; resistor r1: Resistor<a,R=4>; }"
    drive = {"value": "12", "scale": scale, "origin": "design", "reference": "demo:drive"}
    resistor = {"scale": scale, "origin": "design", "reference": "demo:resistor-scale"}
    flow = connections.pcba_resistor_flow(board, "r1", drive, resistor)
    assert flow["quantity_report"]["value"] == "3"
    save("pcba_resistor.json", {"board": board, "drive_declaration": drive, "resistance_declaration": resistor, "report": flow})
    pair = connections.make_synthetic_demo(examples["attention_2"]["expression"], "demo:lower-flow")
    save("synthetic_demo.json", pair)
    projection = connections.project_cas_rpa([
        {"node_id": "parent", "parent_id": None, "quantity_report": flow["quantity_report"]},
        {"node_id": "child", "parent_id": "parent", "quantity_report": pair["target"]["quantity_report"]},
    ])
    assert {row["node_id"]: row["quantity_report"]["value"] for row in projection["nodes"]} == {"parent": "3", "child": "2"}
    save("cas_rpa_projection.json", projection)

    parity = {}
    with zipfile.ZipFile(REPO / "dist/cas-offline.zip") as archive:
        for name in ("compiler.py", "cas_ohm.py"):
            main_bytes = (REPO / "noetic-compass-scaffold/noetic-compass/api/notation" / name).read_bytes()
            offline_bytes = (REPO / "dist/cas-offline/api/notation" / name).read_bytes()
            archived = archive.read("api/notation/" + name)
            assert main_bytes == offline_bytes == archived, name
            parity[name] = {"main_sha256_raw": digest(main_bytes), "offline_sha256_raw": digest(offline_bytes), "zip_member_sha256_raw": digest(archived)}
    cli = REPO / "dist/cas-offline/cas.py"
    cli_cases = {}
    for name, expected_code in (("attention_3", 0), ("invalid_zero_constraint", 1)):
        source = examples[name]["expression"]
        run = subprocess.run(
            [sys.executable, str(cli), source, "--json", "--no-color", "--no-terminal-diagram"],
            cwd=cli.parent, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True, encoding="utf-8", check=False, timeout=30,
        )
        assert run.returncode == expected_code, (name, run.returncode, run.stderr)
        if expected_code == 0:
            actual = json.loads(run.stdout[run.stdout.index("{\n"):])
            assert actual["valid"] and actual["result"] == examples[name]["artifact"]["result"]
        else:
            assert "INVALID" in run.stdout and "OHM_ZERO_CONSTRAINT" in run.stdout
        cli_cases[name] = {"expression": source, "exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}
    save("offline_cli.json", {"cases": cli_cases})
    sources = json.loads((EVIDENCE / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    for source in sources["sources"]:
        raw = (LAB / source["snapshot_path"]).read_bytes()
        assert digest(raw) == source["sha256_raw"], source
        assert digest(raw.replace(b"\r\n", b"\n")) == source["sha256_lf"], source
    historical = historical_compiler.source_receipt()
    save("implementation_receipt.json", {
        "status": "ENGINEERING_DEMONSTRATION_ONLY",
        "implementation_sha256_lf": binding,
        "supporting_source_sha256_lf": {
            name: digest((LAB / name).read_bytes().replace(b"\r\n", b"\n"))
            for name in ("cas_ohm_connections.py", "pcba_check.py", "pcba_reader.py",
                         "pcba_component_adapter.py", "historical_compiler.py",
                         "q3_behaviour_records.py", "cas_ohm_evidence/run_demonstrations.py")
        },
        "source_offline_zip_parity": parity,
        "offline_zip_sha256_raw": digest((REPO / "dist/cas-offline.zip").read_bytes()),
        "historical_compiler": historical,
        "source_reference_snapshots": "ALL_MANIFEST_HASHES_MATCH",
        "demonstrations": {"compiler_valid": 4, "compiler_invalid": 1, "offline_cli_valid": 1, "offline_cli_invalid": 1, "pcba_resistor": 1, "synthetic_pair": 1, "rpa_nodes": 2},
        "measurement_status": "NO_MEASUREMENT_PERFORMED",
        "control_status": "NOT_CONNECTED",
        "helm_status": "NOT_TRAINED",
        "frozen_rust_engine": "UNCHANGED",
    })
    print("4 valid compiler cases, 1 invalid compiler case; valid/invalid offline CLI; PCBA, synthetic and RPA examples; source/offline/ZIP parity: PASS")

if __name__ == "__main__":
    main()
