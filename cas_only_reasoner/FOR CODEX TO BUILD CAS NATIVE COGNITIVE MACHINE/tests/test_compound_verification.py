"""Independent original-expression and provenance-substitution checks."""
from dataclasses import replace
from fractions import Fraction

import pytest

from cncm.canonical import canonical_json, digest
from cncm.model import ContractError
from cncm.compound_model import CompoundProblem, create_problem
from cncm.compound_program import CallStep, CallProgram, enumerate_programs
from cncm.compound_verification import (construct_program, qualify_program, check_program_call,
                                       verify_original, verify_input_resolution, policy_document)
from cncm.procedural_substrate import make_candidate
from cncm.semantic_model import MemoryRef, SourceStatement
from cncm.semantic_verification import resolve_memory


PRIMITIVE = make_candidate()
INPUTS = dict(a="2", b="3", c="5", d="7", e="35")
PROFILE = "a" * 64
KW = dict(source_profile_digest=PROFILE)


def correct_program():
    return CallProgram(PRIMITIVE.artifact_sha256, (CallStep("a", "d", "e"), CallStep("b", "c", "r0")))


@pytest.fixture(scope="module")
def construction():
    return construct_program(PRIMITIVE)


def test_complete_construction_has_exactly_one_survivor_and_no_answer_fixtures(construction):
    program, report = construction
    assert program == correct_program()
    assert report["status"] == "SELECTED" and report["candidate_count"] == 420
    assert report["survivor_digests"] == [program.program_digest]
    assert report["selected_artifact"] == program.to_dict()
    assert report["policy_cost"] == dict(instructions=40320, checker_calls=1680)
    assert report["actual_work"] == dict(primitive_instructions=18720, original_checks=1680)
    assert len(report["candidates"]) == 420 and all(len(row["checks"]) == 4 for row in report["candidates"])
    assert [row["program"] for row in report["candidates"]] == [row.to_dict() for row in enumerate_programs(PRIMITIVE)]
    assert all(set(case) == {"status", "report_digest"} for row in report["candidates"] for case in row["checks"])
    assert len(canonical_json(report).encode()) <= 524288
    assert report["report_digest"] == digest({k: v for k, v in report.items() if k != "report_digest"})
    assert all(set(row) == {"a", "b", "c", "d", "e"} for row in policy_document()["development"])


def test_canonical_prefix_containing_unique_survivor_cannot_claim_complete_search():
    program, report = construct_program(PRIMITIVE, candidate_limit=419)
    assert program is None and report["status"] == "SEARCH_EXHAUSTED"
    assert report["selected_artifact"] is None
    assert correct_program().program_digest in report["survivor_digests"]
    assert report["policy_cost"] == dict(instructions=40224, checker_calls=1676)


@pytest.mark.parametrize("limit", [0, -1, 421, True, "420", 1.5])
def test_invalid_candidate_limit_fails_before_candidate_execution(limit, monkeypatch):
    import cncm.compound_verification as checker
    monkeypatch.setattr(checker, "check_program_call", lambda *a, **k: pytest.fail("search executed"))
    with pytest.raises(ContractError): construct_program(PRIMITIVE, candidate_limit=limit)


def test_construction_never_reads_qualification_or_domain_panels(monkeypatch):
    import cncm.compound_verification as checker
    class Unreadable:
        def __iter__(self): pytest.fail("qualification fixture read by constructor")
    monkeypatch.setattr(checker, "_QUALIFICATION", Unreadable())
    monkeypatch.setattr(checker, "_DOMAIN", Unreadable())
    monkeypatch.setattr(checker, "qualify_program", lambda *a: pytest.fail("qualification called during selection"))
    monkeypatch.setattr(checker, "policy_document", lambda: pytest.fail("full policy read during selection"))
    assert construct_program(PRIMITIVE, candidate_limit=1)[1]["status"] == "SEARCH_EXHAUSTED"


def test_qualification_panel_is_disjoint_separate_and_all_domain_refusals_are_charged(construction):
    program, _ = construction
    report = qualify_program(program, PRIMITIVE)
    assert report["status"] == "QUALIFIED"
    assert len(report["qualification_cases"]) == 8 and len(report["domain_cases"]) == 4
    assert all(row["status"] == "CHECKED" for row in report["qualification_cases"])
    assert all(row["status"] == "DOMAIN_REJECTED" for row in report["domain_cases"])
    assert report["policy_cost"] == dict(instructions=288, checker_calls=12)
    assert report["actual_work"] == dict(primitive_instructions=96, original_checks=12)
    policy = policy_document()
    pools = [{canonical_json(row) for row in policy[name]} for name in ("development", "qualification", "domain")]
    assert all(not pools[a] & pools[b] for a in range(3) for b in range(a + 1, 3))


def test_wrong_well_formed_program_fails_separate_qualification():
    report = qualify_program(enumerate_programs(PRIMITIVE)[0], PRIMITIVE)
    assert report["status"] == "REJECTED"
    assert any(row["status"] == "CHECKER_REJECTED" for row in report["qualification_cases"])


def test_wrong_primitive_cannot_produce_a_selected_compound_by_digest_alone():
    selected, report = construct_program(make_candidate(combine="ADD_EXACT"))
    assert selected is None and report["selected_artifact"] is None
    assert report["status"] == "NO_UNIQUE_CANDIDATE" and report["survivor_digests"] == []
    assert report["candidate_count"] == 420 and report["policy_cost"]["instructions"] == 40320


def test_actual_call_binds_current_inputs_branch_and_caller_to_exact_program():
    report = check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id="caller-1", branch_id="branch-main")
    assert report["status"] == "CHECKED" and report["output"] == "3"
    assert report["call_id"] == "caller-1" and report["branch_id"] == "branch-main"
    assert report["original_check"]["lhs"] == "35" and report["execution"]["output"] == "3"
    assert report["policy_cost"] == dict(instructions=24, checker_calls=1)
    altered = check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id="caller-2", branch_id="branch-main")
    assert altered["report_digest"] != report["report_digest"]
    altered = check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id="caller-1", branch_id="branch-other")
    assert altered["report_digest"] != report["report_digest"]


@pytest.mark.parametrize("port", ["a", "b"])
def test_zero_original_leading_coefficients_reject_before_any_primitive_claim(port, monkeypatch):
    import cncm.compound_verification as checker
    monkeypatch.setattr(checker, "execute_program", lambda *a, **k: pytest.fail("domain refusal executed candidate"))
    report = check_program_call(correct_program(), PRIMITIVE, {**INPUTS, port: "0"}, call_id="domain", branch_id="main")
    assert report["status"] == "DOMAIN_REJECTED" and report["output"] is None and report["execution"] is None
    assert report["actual_work"] == dict(primitive_instructions=0, original_checks=1)
    assert report["policy_cost"] == dict(instructions=24, checker_calls=1)


def test_original_checker_rejects_wrong_answer_even_if_candidate_executor_claims_success(monkeypatch):
    import cncm.compound_verification as checker
    monkeypatch.setattr(checker, "execute_program", lambda *a, **k: dict(status="SUCCESS", output="4", instructions_executed=12))
    report = check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id="wrong", branch_id="main")
    assert report["status"] == "CHECKER_REJECTED"
    assert report["original_check"]["status"] == "REJECTED"


def test_original_checker_does_not_invoke_any_answer_producer(monkeypatch):
    import cncm.compound_verification as checker
    monkeypatch.setattr(checker, "execute_program", lambda *a, **k: pytest.fail("producer invoked by checker"))
    assert verify_original(INPUTS, "3")["status"] == "CHECKED"
    assert verify_original(INPUTS, "4")["status"] == "REJECTED"


def test_original_substitution_for_many_independently_generated_rationals():
    # Test-only Fraction arithmetic chooses x first and constructs e forward.
    count = 0
    for a in (Fraction(-7, 3), Fraction(2), Fraction(5, 11)):
        for b in (Fraction(-3, 2), Fraction(7, 5)):
            for c in (Fraction(0), Fraction(13, 7)):
                for d in (Fraction(-2, 9), Fraction(3)):
                    for x in (Fraction(-11, 13), Fraction(0), Fraction(17, 19), Fraction(-2), Fraction(1, 3), Fraction(23)):
                        e = a * (b * x + c) + d
                        values = dict(zip(("a", "b", "c", "d", "e"), map(str, (a, b, c, d, e)), strict=True))
                        report = check_program_call(correct_program(), PRIMITIVE, values, call_id="generated", branch_id="main")
                        assert report["status"] == "CHECKED" and Fraction(report["output"]) == x
                        assert verify_original(values, str(x + 1))["status"] == "REJECTED"
                        count += 1
    assert count == 144


def test_original_output_and_intermediate_bounds_refuse_before_oversize_product():
    maximum = str((1 << 512) - 1)
    report = verify_original(INPUTS, maximum)
    assert report["status"] == "ARITHMETIC_LIMIT" and report["lhs"] is None
    with pytest.raises(ContractError): verify_original(INPUTS, str(1 << 512))
    with pytest.raises(ContractError): verify_original(INPUTS, "9" * 10000)


def test_composition_input_overflow_cannot_be_recast_as_checked_result():
    maximum = str((1 << 128) - 1)
    report = check_program_call(correct_program(), PRIMITIVE,
        dict(a="1/" + maximum, b="3", c="5", d="0", e=maximum), call_id="overflow", branch_id="main")
    assert report["status"] == "EXECUTION_REJECTED" and report["output"] is None
    assert report["original_check"] is None
    assert report["actual_work"] == dict(primitive_instructions=6, original_checks=0)


@pytest.mark.parametrize("identifier", ["", "bad id", "x" * 129, None, True])
def test_caller_and_branch_identifiers_cannot_be_unbounded_or_coerced(identifier):
    with pytest.raises(ContractError):
        check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id=identifier, branch_id="main")
    with pytest.raises(ContractError):
        check_program_call(correct_program(), PRIMITIVE, INPUTS, call_id="call", branch_id=identifier)


def source(value="5", *, source_id="owner", status="USER_ATTESTED", scope="shop", previous=None, action="ASSERT"):
    return SourceStatement(scope, "offset", source_id, value, status, action, previous, "urn:fixture:source")


def recalled(history, ref=None):
    ref = ref or MemoryRef("shop", "offset")
    anchors = tuple(row.statement_digest for row in history)
    return resolve_memory(history, ref, anchors, **KW)[0]


def memory_problem(ref=None, *, updates=()):
    return create_problem({**INPUTS, "c": ref or MemoryRef("shop", "offset")}, updates=updates)


def resolution(packet, bindings, inputs, history, anchors=None, profile=PROFILE):
    return verify_input_resolution(packet, bindings, inputs, history,
        tuple(row.statement_digest for row in history) if anchors is None else anchors,
        source_profile_digest=profile)


def test_literal_inputs_need_no_memory_and_receipt_is_closed_source_pinned():
    packet = create_problem(INPUTS)
    receipt = resolution(packet, (), INPUTS, ())
    assert receipt["status"] == "VALID" and receipt["support"] == "NONE"
    assert receipt["domain"] == "COMPOUND_INPUTS" and receipt["claim"] == "EXACT_COMPOUND_INPUT_SUBSTITUTION"
    assert receipt["checker_id"] == "cncm.compound-verifier/0.1" and receipt["source_profile_digest"] == PROFILE
    assert set(receipt) == {"schema_version", "checker_id", "source_profile_digest", "domain", "claim", "status",
                            "reason", "support", "factual_status", "bindings", "receipt_digest"}
    assert receipt["receipt_digest"] == digest({k: v for k, v in receipt.items() if k != "receipt_digest"})


def test_exact_memory_substitution_never_claims_independent_factual_truth():
    history = (source(),)
    packet = memory_problem(updates=history)
    receipt = resolution(packet, (recalled(history),), INPUTS, history)
    assert receipt["status"] == "VALID" and receipt["support"] == "USER_ATTESTED"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"


def test_independent_resolution_never_calls_model_resolver_or_reference_helper(monkeypatch):
    history = (source(),)
    packet, bindings = memory_problem(), (recalled(history),)
    monkeypatch.setattr(CompoundProblem, "resolved_inputs", lambda *a: pytest.fail("model resolver used"))
    monkeypatch.setattr(CompoundProblem, "references", property(lambda s: pytest.fail("model references used")))
    assert resolution(packet, bindings, INPUTS, history)["status"] == "VALID"


def test_independent_resolution_uses_protected_recall_not_mutable_public_alias(monkeypatch):
    import cncm.semantic_verification as semantic
    history = (source(),)
    packet, bindings = memory_problem(), (recalled(history),)
    monkeypatch.setattr(semantic, "resolve_memory", lambda *a, **k: pytest.fail("mutable public alias called"))
    assert resolution(packet, bindings, INPUTS, history)["status"] == "VALID"


@pytest.mark.parametrize("change", ["value", "status", "source", "receipt", "scope", "missing", "duplicate"])
def test_forged_binding_cannot_authorize_resolved_inputs(change):
    history = (source(),)
    binding = recalled(history)
    inputs = dict(INPUTS)
    if change == "value": binding = replace(binding, value="8"); inputs["c"] = "8"
    elif change == "status": binding = replace(binding, statuses=("TEST_FIXTURE",))
    elif change == "source": binding = replace(binding, statement_digests=("b" * 64,))
    elif change == "receipt": binding = replace(binding, receipt_digest="b" * 64)
    elif change == "scope": binding = replace(binding, ref=MemoryRef("other", "offset"))
    bindings = () if change == "missing" else (binding, binding) if change == "duplicate" else (binding,)
    receipt = resolution(memory_problem(), bindings, inputs, history)
    assert receipt["status"] == "INVALID"


def test_exact_original_literal_and_recalled_values_are_both_checked():
    history = (source(),)
    bindings = (recalled(history),)
    for port in INPUTS:
        receipt = resolution(memory_problem(), bindings, {**INPUTS, port: "8"}, history)
        assert receipt["status"] == "INVALID" and receipt["reason"] == "RESOLVED_INPUTS_MISMATCH"


def test_updates_must_be_the_exact_admitted_history_suffix_even_without_references():
    first = source()
    newer = source("8", previous=first.statement_digest)
    packet = create_problem(INPUTS, updates=(first,))
    assert resolution(packet, (), INPUTS, ())["reason"] == "PROBLEM_UPDATES_NOT_ADMITTED"
    assert resolution(packet, (), INPUTS, (first, newer))["reason"] == "PROBLEM_UPDATES_NOT_ADMITTED"
    assert resolution(packet, (), INPUTS, (first,))["status"] == "VALID"


def test_correction_stale_recall_revocation_conflict_and_stronger_evidence_refuse():
    first = source()
    old_binding = recalled((first,))
    newer = source("8", previous=first.statement_digest)
    assert resolution(memory_problem(), (old_binding,), INPUTS, (first, newer))["reason"] == "RECALL_BINDING_MISMATCH"
    revoked = source(None, previous=first.statement_digest, action="RETRACT")
    assert resolution(memory_problem(), (old_binding,), INPUTS, (first, revoked))["reason"] == "REVOKED"
    other = source("8", source_id="auditor")
    assert resolution(memory_problem(), (old_binding,), INPUTS, (first, other))["reason"] == "CONFLICT"
    ref = MemoryRef("shop", "offset", "INDEPENDENTLY_VERIFIED")
    strong_fake = replace(old_binding, ref=ref)
    assert resolution(memory_problem(ref), (strong_fake,), INPUTS, (first,))["reason"] == "INSUFFICIENT_EVIDENCE"


def test_source_self_claims_cannot_replace_external_ingress_anchor():
    history = (source(source_id="independent-verifier", status="TEST_FIXTURE"),)
    bindings = (recalled(history),)
    receipt = resolution(memory_problem(), bindings, INPUTS, history, anchors=())
    assert receipt["status"] == "INVALID" and receipt["reason"] == "HISTORY_UNTRUSTED_INGRESS"


def test_equal_multiple_sources_and_repeated_port_reference_bind_every_head():
    history = (source("5"), source("5", source_id="auditor", status="TEST_FIXTURE"))
    binding = recalled(history)
    ref = MemoryRef("shop", "offset")
    packet = create_problem({**INPUTS, "c": ref, "d": ref})
    receipt = resolution(packet, (binding,), {**INPUTS, "d": "5"}, history)
    assert receipt["status"] == "VALID" and receipt["support"] == "MIXED_ATTESTATIONS"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"
    omitted = replace(binding, statement_digests=binding.statement_digests[:1], statuses=binding.statuses[:1])
    assert resolution(packet, (omitted,), {**INPUTS, "d": "5"}, history)["status"] == "INVALID"


@pytest.mark.parametrize("profile", [None, "", "f" * 63, "F" * 64])
def test_source_profile_is_required_not_generated_by_capsule(profile):
    with pytest.raises(ContractError): resolution(create_problem(INPUTS), (), INPUTS, (), profile=profile)
