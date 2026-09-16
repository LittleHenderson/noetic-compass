"""Pure candidate-executor checks; no kernel, model, or provider execution."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from itertools import permutations
import json
from pathlib import Path

import pytest

from cncm.canonical import digest
from cncm import procedural_substrate as p


def inputs(a="3", b="5", c="26"):
    return {"a": a, "b": b, "c": c}


def test_input_dependent_exact_rational_execution_and_replay():
    candidate = p.make_candidate()
    result = p.execute_procedure(candidate, inputs())
    assert (result.status, result.output, result.instructions_executed) == ("SUCCESS", "7", 6)
    changed = p.execute_procedure(candidate, inputs("-4", "7", "13"))
    assert changed.output == "-3/2"
    assert changed.inputs_sha256 != result.inputs_sha256
    assert p.replay_execution(candidate, inputs(), result)
    assert not p.replay_execution(candidate, inputs("-4", "7", "13"), result)
    assert result.to_dict()["claim_boundary"] == "SUBSTRATE_CANDIDATE_ONLY"


def test_twelve_closed_candidates_are_distinct_without_correctness_claim():
    candidates = [p.make_candidate(order, operation) for order in permutations(("a", "b", "c"))
                  for operation in ("ADD_EXACT", "SUBTRACT_EXACT")]
    assert len({item.artifact_sha256 for item in candidates}) == 12
    wrong = p.make_candidate(("b", "c", "a"))
    result = p.execute_procedure(wrong, inputs())
    assert result.status == "SUCCESS" and result.output == "-7"


def test_artifact_roundtrip_binds_program_limits_contract_and_provenance():
    artifact = p.make_candidate()
    wire = artifact.to_dict()
    assert p.ProcedureArtifact.from_dict(wire) == artifact
    for field, value in (("revision", 2), ("provenance", {"source_id": "changed", "source_revision": "1"}),
                         ("limits", {"input_bits": 64, "intermediate_bits": 256})):
        changed = deepcopy(wire)
        changed[field] = value
        with pytest.raises(p.ProcedureContractError, match="DIGEST_MISMATCH"):
            p.ProcedureArtifact.from_dict(changed)
    assert p.make_candidate(provenance=p.ProposalProvenance("teacher-proposal", "2")).artifact_sha256 != artifact.artifact_sha256
    with pytest.raises(FrozenInstanceError):
        artifact.revision = 2


@pytest.mark.parametrize("operation", ["EMIT_LITERAL", "SOURCE_LOOKUP", "EVAL", "IMPORT", "LOAD_CONSTANT"])
def test_answer_literal_and_dynamic_operations_rejected_even_when_rehashed(operation):
    wire = p.make_candidate().to_dict()
    wire["program"][-1]["operation"] = operation
    wire["artifact_sha256"] = digest({key: value for key, value in wire.items() if key != "artifact_sha256"})
    with pytest.raises(p.ProcedureContractError, match="OPERATION_INVALID"):
        p.ProcedureArtifact.from_dict(wire)


@pytest.mark.parametrize("mutate", [
    lambda wire: wire.update({"approved": True}),
    lambda wire: wire["program"].append(wire["program"][-1]),
    lambda wire: wire["program"][1].update({"arguments": ["c"]}),
    lambda wire: wire["program"][3].update({"arguments": ["r0", "r4"]}),
    lambda wire: wire["program"][5].update({"arguments": ["7"]}),
    lambda wire: wire["limits"].update({"input_bits": True}),
    lambda wire: wire.update({"revision": True}),
])
def test_malformed_programs_and_authority_fields_are_rejected(mutate):
    wire = p.make_candidate().to_dict()
    mutate(wire)
    with pytest.raises(p.ProcedureContractError):
        p.ProcedureArtifact.from_dict(wire)


@pytest.mark.parametrize("value", ["+1", "01", "-0", "0/2", "2/4", "2/1", "1/-2", "1/0",
                                   "1.5", "nan", " 1", True, 1, 1.0, "9" * 10000])
def test_noncanonical_or_unbounded_input_fails(value):
    with pytest.raises(p.ProcedureContractError):
        p.execute_procedure(p.make_candidate(), inputs(a=value))


def test_input_bit_ceiling_is_checked_before_execution(monkeypatch):
    monkeypatch.setattr(p, "_arithmetic", lambda *args: pytest.fail("arithmetic must not run"))
    with pytest.raises(p.ProcedureContractError, match="BIT_BOUND"):
        p.execute_procedure(p.make_candidate(), inputs(a=str(1 << 128)))


def test_growth_refusal_occurs_before_any_multiplication(monkeypatch):
    candidate = p.make_candidate(limits=p.ProcedureLimits(input_bits=8, intermediate_bits=8))
    monkeypatch.setattr(p, "_multiply", lambda *args: pytest.fail("multiplication must not run"))
    result = p.execute_procedure(candidate, inputs("1", "-127", "127"))
    assert (result.status, result.output, result.instructions_executed) == ("ARITHMETIC_LIMIT", None, 4)


def test_division_growth_refusal_occurs_before_crossproducts(monkeypatch):
    monkeypatch.setattr(p, "_multiply", lambda *args: pytest.fail("multiplication must not run"))
    with pytest.raises(p._ArithmeticLimit):
        p._arithmetic("DIVIDE_EXACT", (127, 1), (1, 127), 8)


def test_zero_denominator_is_typed_without_output():
    result = p.execute_procedure(p.make_candidate(), inputs(a="0"))
    assert (result.status, result.output, result.instructions_executed) == ("DIVISION_BY_ZERO", None, 5)
    assert p.replay_execution(p.make_candidate(), inputs(a="0"), result)


def test_short_budget_does_not_execute_any_instruction(monkeypatch):
    monkeypatch.setattr(p, "_arithmetic", lambda *args: pytest.fail("arithmetic must not run"))
    for budget in range(6):
        result = p.execute_procedure(p.make_candidate(), inputs(), instruction_budget=budget)
        assert (result.status, result.output, result.instructions_executed) == ("BUDGET_EXHAUSTED", None, 0)


def test_resealed_wrong_result_fails_full_replay():
    artifact = p.make_candidate()
    wire = p.execute_procedure(artifact, inputs()).to_dict()
    wire["outputs"]["x"] = "8"
    wire["report_sha256"] = digest({key: value for key, value in wire.items() if key != "report_sha256"})
    parsed = p.ProcedureExecution.from_dict(wire)
    assert parsed.output == "8"  # Shape/digest validation does not prove execution.
    assert not p.replay_execution(artifact, inputs(), parsed)


def test_wire_schemas_cover_valid_reports_and_reject_extra_fields():
    jsonschema = pytest.importorskip("jsonschema")
    root = Path(__file__).resolve().parents[1] / "schemas"
    artifact = p.make_candidate()
    rows = [
        ("procedure_substrate_artifact.schema.json", artifact.to_dict()),
        ("procedure_substrate_execution.schema.json", p.execute_procedure(artifact, inputs()).to_dict()),
        ("procedure_substrate_execution.schema.json", p.execute_procedure(artifact, inputs(a="0")).to_dict()),
        ("procedure_substrate_execution.schema.json", p.execute_procedure(artifact, inputs(), instruction_budget=0).to_dict()),
    ]
    for filename, value in rows:
        schema = json.loads((root / filename).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(value, schema)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**value, "authority": "installed"}, schema)
