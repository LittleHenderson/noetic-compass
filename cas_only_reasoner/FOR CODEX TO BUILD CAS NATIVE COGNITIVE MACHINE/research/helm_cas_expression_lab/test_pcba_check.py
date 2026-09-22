"""End-to-end and bounded-work checks for the PCBA sidecar."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pcba_check as check

VALID = """circuit bounded_example {
  input: prompt;
  output: response;
  node cause: ^8^C_{F2}|A;
  node bias: ^5^P_{F4}|f;
  node effect: ^9^C_{F6}|A;
  cjt stage1: CJT< cause | bias => effect > [beta=0.5];
  feedback effect -> cause [beta=0.2];
  probe result: effect;
}"""


def test_pass_preserves_metadata_and_does_not_claim_execution():
    result = check.check_pcba_document(VALID)
    assert result["parse_status"] == result["structural_status"] == "PASS"
    assert result["valid"]
    state = result["netlist"]["symbols"]["cause"]["state"]
    assert state["operator"] == 8
    assert state["domain"] == "C"
    assert state["drive"] == 2
    assert state["register"] == "A"
    assert result["execution_status"] == "NOT_IMPLEMENTED"
    assert result["helm_status"] == "NOT_TRAINED"
    assert result["netlist"]["loops"][0]["gain_product"] == "1/10"
    assert result["sources"]["compiler_sha256_lf"] == check.COMPILER_SHA256_LF


def test_distinct_node_names_do_not_collapse_identical_state_values():
    source = """circuit distinct {
      input: i; output: o;
      node a: ^8^C; node b: ^5^P; node z: ^9^C;
      node second_a: ^8^C; node second_b: ^5^P;
      cjt first: CJT<a | b => z>;
      cjt second: CJT<second_a | second_b => z>;
      assert: first.bias == second.bias;
      feedback z -> second_a [beta=0.1];
    }"""
    result = check.check_pcba_document(source)
    assert any(d["code"] == "E-PCBA-ASSERT" for d in result["diagnostics"])
    loops = result["netlist"]["loops"]
    assert len(loops) == 1
    assert len(loops[0]["edges"]) == 2


def test_unknown_transfer_in_loop_is_unverified():
    source = """board unknown_transfer {
      node a: ^8^C; node b: ^9^C;
      diode d1: Diode<a -> b>;
      feedback b -> a [beta=0.1];
    }"""
    result = check.check_pcba_document(source)
    assert result["parse_status"] == "PASS"
    assert result["structural_status"] == "UNVERIFIED"
    assert any(d["code"] == "U-PCBA-LOOP-GAIN" for d in result["diagnostics"])


@pytest.mark.parametrize("prefix,type_name,parameter", [
    ("resistor", "Resistor", "R"), ("capacitor", "Capacitor", "C"),
    ("inductor", "Inductor", "L"),
])
def test_passive_influence_cannot_disappear_from_complete_loop_proof(prefix, type_name, parameter):
    source = VALID.replace("beta=0.5", "beta=2").replace("beta=0.2", "beta=0.6")
    source = source.replace("probe result:", f"{prefix} passive1: {type_name}<cause, {parameter}=10>; probe result:")
    result = check.check_pcba_document(source)
    assert result["structural_status"] == "UNVERIFIED"
    assert all(loop["gain_status"] == "UNKNOWN" for loop in result["netlist"]["loops"])
    assert not any(d["code"] == "E-CJT-005" for d in result["diagnostics"])


def test_graph_budget_never_returns_pass_for_partial_search(monkeypatch):
    monkeypatch.setattr(check, "MAX_GRAPH_STEPS", 1)
    result = check.check_pcba_document(VALID)
    assert result["structural_status"] == "UNVERIFIED"
    assert not result["valid"]
    assert any(d["code"] == "U-PCBA-GRAPH-LIMIT" for d in result["diagnostics"])


@pytest.mark.parametrize("gain", ["NaN", "Infinity", "-0.1", "1e309"])
def test_bad_connection_gain_cannot_pass(gain):
    result = check.check_pcba_document(VALID.replace("beta=0.2", f"beta={gain}"))
    assert not result["valid"]


def run_cli(path):
    return subprocess.run([sys.executable, str(Path(check.__file__)), str(path)],
                          capture_output=True, text=True, timeout=20)


def test_cli_valid_and_invalid_have_distinct_exit_codes(tmp_path):
    path = tmp_path / "circuit.ccdl"
    path.write_text(VALID, encoding="utf-8")
    process = run_cli(path)
    assert process.returncode == 0, process.stderr + process.stdout
    assert json.loads(process.stdout)["valid"]
    path.write_bytes(b"\xff")
    process = run_cli(path)
    assert process.returncode == 2
    assert json.loads(process.stdout)["parse_status"] == "FAIL"
    assert "Traceback" not in process.stderr


def test_cli_missing_and_oversized_inputs_fail_cleanly(tmp_path):
    path = tmp_path / "absent.ccdl"
    process = run_cli(path)
    assert process.returncode == 2
    assert json.loads(process.stdout)["diagnostics"][0]["code"] == "E-PCBA-INPUT"
    path.write_bytes(b"x" * 65537)
    process = run_cli(path)
    assert process.returncode == 2
    assert not json.loads(process.stdout)["valid"]


def test_json_reports_never_emit_nonfinite_numbers():
    result = check.check_pcba_document(VALID.replace("0.2", "9" * 500))
    assert not result["valid"]
    json.dumps(result, allow_nan=False)


def test_reusable_macro_cannot_claim_instantiated_execution():
    source = """board macros { let stage1 = CJT< ^8^C | ^5^P => ^9^C >; }"""
    result = check.check_pcba_document(source)
    assert result["parse_status"] == "PASS"
    assert result["structural_status"] == "UNVERIFIED"
    assert not result["valid"]


def test_parallel_stable_paths_do_not_prove_combined_network_stability():
    source = """board parallel {
      node a: ^8^C; node b: ^9^C; node bias: ^5^P;
      cjt first: CJT<a | bias => b> [beta=0.6];
      cjt second: CJT<a | bias => b> [beta=0.6];
      feedback b -> a [beta=1];
    }"""
    result = check.check_pcba_document(source)
    assert result["structural_status"] == "UNVERIFIED"
    assert not result["valid"]
    assert any(d["code"] == "U-PCBA-COUPLED-LOOPS" for d in result["diagnostics"])


def test_all_pinned_book_sources_have_the_reviewed_identity():
    book = Path(check.__file__).parent / "pinned_sources" / "pcba_book"
    hashes = {
        "Appendix_C_CCDL_Language_Reference.md": "452d64308f860b1c0e5b6c3f4d9c8a91760822baa9b9fcd1a6e12a4797983d8f",
        "Chapter_04_Your_First_Cognitive_Circuit.md": "13ef9030ebf9189dbedc31c40332accbaaa1552a1681bb56ac9d354dc368329e",
        "Chapter_17_CCB_Design_Process.md": "ab58f6ef9dcc7a49c262bc9bc41835ec450b344a26340b91ce2feef52cfa5d07",
    }
    import hashlib
    for name, expected in hashes.items():
        assert hashlib.sha256((book / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
