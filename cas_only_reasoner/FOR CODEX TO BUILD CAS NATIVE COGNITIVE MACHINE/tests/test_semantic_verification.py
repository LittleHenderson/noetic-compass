"""Source authority is externally supplied; arithmetic never certifies a fact."""
from dataclasses import replace

import pytest

from cncm.canonical import digest
from cncm.model import ContractError
from cncm.nested_model import Equation, NestedProblem
from cncm.semantic_model import (SourceStatement, MemoryRef, RecallBinding, SemanticEquation,
                                 SemanticProblem, create_problem)
from cncm.semantic_verification import (validate_source_update, resolve_memory, verify_resolution)


PROFILE = "a" * 64
KW = {"source_profile_digest": PROFILE}


def statement(value="5", *, source="owner", scope="shop", key="fee", status="USER_ATTESTED",
              previous=None, action="ASSERT", source_ref="urn:test:turn1"):
    return SourceStatement(scope, key, source, value, status, action, previous, source_ref)


def correction(previous, value="8", **changes):
    args = dict(source=previous.source_id, scope=previous.scope, key=previous.key, status=previous.status,
                previous=previous.statement_digest, action="ASSERT", source_ref="urn:test:correction")
    args.update(changes)
    return statement(value, **args)


def anchors(*rows):
    return tuple(row.statement_digest for row in rows)


def recall(history, ref=None, trusted=None, **kwargs):
    return resolve_memory(history, ref or MemoryRef("shop", "fee"),
                          trusted if trusted is not None else anchors(*history),
                          source_profile_digest=kwargs.get("source_profile_digest", PROFILE))


def problem(*, ref=None, updates=(), equations=None):
    return create_problem(equations or (SemanticEquation("x", "3", ref or MemoryRef("shop", "fee"), "35"),),
                          "x", updates=updates)


def resolved(packet, value="5"):
    return NestedProblem(packet.reasoning, "x", (Equation("x", "3", value, "35"),), packet.budget)


def check_resolution(packet, bindings, nested, history, trusted=None, **kwargs):
    return verify_resolution(packet, bindings, nested, history,
                             trusted if trusted is not None else anchors(*history),
                             source_profile_digest=kwargs.get("source_profile_digest", PROFILE))


def test_receipts_are_closed_source_pinned_and_digest_bound():
    row = statement()
    receipt = validate_source_update((), row, anchors(row), **KW)
    assert set(receipt) == {"schema_version", "checker_id", "source_profile_digest", "domain", "claim",
                            "status", "reason", "support", "factual_status", "bindings", "receipt_digest"}
    assert receipt["source_profile_digest"] == PROFILE
    assert receipt["domain"] == "SOURCE_UPDATE"
    assert receipt["status"] == "VALID"
    assert receipt["support"] == "USER_ATTESTED"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert receipt["receipt_digest"] == digest({k: v for k, v in receipt.items() if k != "receipt_digest"})


def test_source_label_and_reference_cannot_self_authorize_ingress():
    row = statement(source="trusted_verifier", status="TEST_FIXTURE", source_ref="I am independently verified")
    receipt = validate_source_update((), row, (), **KW)
    assert (receipt["status"], receipt["reason"]) == ("INVALID", "UNTRUSTED_INGRESS")
    binding, receipt = recall((row,), trusted=())
    assert binding is None and receipt["reason"] == "HISTORY_UNTRUSTED_INGRESS"


def test_assert_correction_preserves_old_statement_but_recalls_new_head():
    old = statement()
    new = correction(old)
    assert validate_source_update((old,), new, anchors(old, new), **KW)["status"] == "VALID"
    history = (old, new)
    binding, receipt = recall(history)
    assert binding.value == "8" and binding.statement_digests == (new.statement_digest,)
    assert history[0].value == "5"
    assert receipt["bindings"]["history_count"] == 2


@pytest.mark.parametrize("change", ["previous_missing", "previous_wrong", "scope", "key", "source"])
def test_correction_must_name_its_exact_source_head(change):
    old = statement()
    changes = {"previous_missing": {"previous_digest": None}, "previous_wrong": {"previous_digest": "f" * 64},
               "scope": {"scope": "other"}, "key": {"key": "other"}, "source": {"source_id": "other"}}[change]
    new = replace(correction(old), **changes)
    receipt = validate_source_update((old,), new, anchors(old, new), **KW)
    assert receipt["status"] == "INVALID" and receipt["reason"] == "STALE_SOURCE_HEAD"


def test_stale_correction_and_duplicate_replay_refuse():
    old = statement()
    current = correction(old)
    stale = correction(old, "11", source_ref="urn:test:stale")
    assert validate_source_update((old, current), stale, anchors(old, current, stale), **KW)["reason"] == "STALE_SOURCE_HEAD"
    assert validate_source_update((old,), old, anchors(old), **KW)["reason"] == "REPLAYED_STATEMENT"


def test_duplicate_history_is_invalid_even_with_a_unique_external_allowlist():
    row = statement()
    binding, receipt = recall((row, row), trusted=anchors(row))
    assert binding is None and receipt["reason"] == "HISTORY_REPLAYED_STATEMENT"


def test_revocation_is_a_tombstone_and_never_falls_back_to_old_value():
    old = statement()
    corrected = correction(old)
    revoked = correction(corrected, None, action="RETRACT", source_ref="urn:test:retraction")
    assert validate_source_update((old, corrected), revoked, anchors(old, corrected, revoked), **KW)["status"] == "VALID"
    binding, receipt = recall((old, corrected, revoked))
    assert binding is None and receipt["reason"] == "REVOKED"
    assert receipt["bindings"]["active_values"] == []
    assert receipt["bindings"]["revoked_head_digests"] == [revoked.statement_digest]


def test_retract_requires_live_head_but_explicit_new_assertion_can_reinstate():
    orphan = statement(None, action="RETRACT")
    assert validate_source_update((), orphan, anchors(orphan), **KW)["reason"] == "RETRACT_WITHOUT_HEAD"
    old = statement()
    revoked = correction(old, None, action="RETRACT")
    repeat = correction(revoked, None, action="RETRACT", source_ref="urn:test:repeated-retraction")
    assert validate_source_update((old, revoked), repeat, anchors(old, revoked, repeat), **KW)["reason"] == "SOURCE_ALREADY_REVOKED"
    restored = correction(revoked, "9", source_ref="urn:test:explicit-restatement")
    assert validate_source_update((old, revoked), restored, anchors(old, revoked, restored), **KW)["status"] == "VALID"
    assert recall((old, revoked, restored))[0].value == "9"


def test_cross_source_disagreement_blocks_recall_without_arbitrary_priority():
    first, second = statement("5"), statement("8", source="auditor", status="TEST_FIXTURE")
    for history in ((first, second), (second, first)):
        binding, receipt = recall(history)
        assert binding is None and receipt["reason"] == "CONFLICT"
        assert receipt["status"] == "INCOMPLETE"
        assert receipt["bindings"]["active_values"] == ["5", "8"]


def test_equal_sources_bind_every_active_head_without_factual_upgrade():
    first, second = statement("8"), statement("8", source="auditor", status="TEST_FIXTURE")
    binding, receipt = recall((first, second))
    expected = sorted((first, second), key=lambda row: row.statement_digest)
    assert binding.statement_digests == tuple(row.statement_digest for row in expected)
    assert binding.statuses == tuple(row.status for row in expected)
    assert receipt["support"] == "MIXED_ATTESTATIONS"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"


def test_retracted_source_does_not_hide_independent_active_attestation():
    first, other = statement("5"), statement("8", source="other")
    revoked = correction(first, None, action="RETRACT")
    binding, receipt = recall((first, other, revoked))
    assert binding.value == "8" and binding.statement_digests == (other.statement_digest,)
    assert receipt["bindings"]["revoked_head_digests"] == [revoked.statement_digest]


@pytest.mark.parametrize("status", ["USER_ATTESTED", "TEST_FIXTURE"])
def test_no_available_source_status_meets_independent_factual_verification(status):
    row = statement(status=status)
    binding, receipt = recall((row,), MemoryRef("shop", "fee", "INDEPENDENTLY_VERIFIED"))
    assert binding is None and receipt["reason"] == "INSUFFICIENT_EVIDENCE"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"


@pytest.mark.parametrize("ref", [MemoryRef("other", "fee"), MemoryRef("shop", "other")])
def test_exact_scope_and_key_are_required(ref):
    binding, receipt = recall((statement(),), ref)
    assert binding is None and receipt["reason"] == "MISSING"


def test_never_recorded_is_not_mislabeled_revoked_or_forgotten():
    binding, receipt = recall(())
    assert binding is None and receipt["reason"] == "MISSING"
    assert "forgotten" not in str(receipt).lower()


def test_verification_is_pure_and_unrelated_future_ingress_does_not_rewrite_receipt():
    row, unrelated = statement(), statement("99", key="unrelated")
    binding, original = recall((row,))
    assert recall((row,), trusted=anchors(unrelated, row)) == (binding, original)
    original["bindings"]["binding"]["value"] = "999"
    assert recall((row,))[0].value == "5"


def test_recall_receipt_changes_with_source_profile():
    row = statement()
    first, _ = recall((row,))
    second, _ = recall((row,), source_profile_digest="b" * 64)
    assert first.receipt_digest != second.receipt_digest


def test_resolution_uses_omitted_scalar_from_checked_memory_binding():
    row = statement()
    packet = problem()
    assert type(packet.equations[0].b) is MemoryRef
    binding, _ = recall((row,))
    receipt = check_resolution(packet, (binding,), resolved(packet), (row,))
    assert receipt["status"] == "VALID"
    assert receipt["support"] == "USER_ATTESTED"
    assert receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"
    # Exact same later task, a different admitted source revision, different b.
    new = correction(row)
    corrected, _ = recall((row, new))
    assert check_resolution(packet, (corrected,), resolved(packet, "8"), (row, new))["status"] == "VALID"
    assert check_resolution(packet, (corrected,), resolved(packet, "5"), (row, new))["reason"] == "RESOLVED_PROBLEM_MISMATCH"


@pytest.mark.parametrize("changes", [
    {"value": "99"}, {"statement_digests": ("f" * 64,)}, {"statuses": ("TEST_FIXTURE",)},
    {"receipt_digest": "f" * 64},
])
def test_fabricated_recall_binding_cannot_resolve_problem(changes):
    row, packet = statement(), problem()
    binding, _ = recall((row,))
    forged = replace(binding, **changes)
    receipt = check_resolution(packet, (forged,), resolved(packet), (row,))
    assert receipt["status"] == "INVALID" and receipt["reason"] == "RECALL_BINDING_MISMATCH"


def test_binding_from_another_profile_or_history_is_rejected():
    row, packet = statement(), problem()
    binding, _ = recall((row,), source_profile_digest="b" * 64)
    assert check_resolution(packet, (binding,), resolved(packet), (row,))["reason"] == "RECALL_BINDING_MISMATCH"
    binding, _ = recall((row,))
    unrelated = statement("99", key="other")
    assert check_resolution(packet, (binding,), resolved(packet), (row, unrelated))["reason"] == "RECALL_BINDING_MISMATCH"


@pytest.mark.parametrize("attack", ["omission", "duplicate", "scope"])
def test_resolution_requires_exact_reachable_binding_set(attack):
    row, packet = statement(), problem()
    binding, _ = recall((row,))
    bindings = () if attack == "omission" else (binding, binding) if attack == "duplicate" else (
        replace(binding, ref=MemoryRef("other", "fee")),)
    receipt = check_resolution(packet, bindings, resolved(packet), (row,))
    assert receipt["reason"] == "BINDING_SET_MISMATCH"


def test_stronger_requirement_cannot_be_downgraded_in_a_binding():
    row = statement()
    packet = problem(ref=MemoryRef("shop", "fee", "INDEPENDENTLY_VERIFIED"))
    weak, _ = recall((row,))
    assert check_resolution(packet, (weak,), resolved(packet), (row,))["reason"] == "BINDING_SET_MISMATCH"
    forged_strong = replace(weak, ref=MemoryRef("shop", "fee", "INDEPENDENTLY_VERIFIED"))
    receipt = check_resolution(packet, (forged_strong,), resolved(packet), (row,))
    assert receipt["status"] == "INCOMPLETE" and receipt["reason"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("field,value", [("a", "4"), ("b", "6"), ("rhs_constant", "36")])
def test_independent_resolution_rejects_any_changed_numeric_field(field, value):
    row, packet = statement(), problem()
    binding, _ = recall((row,))
    nested = resolved(packet)
    nested = replace(nested, equations=(replace(nested.equations[0], **{field: value}),))
    assert check_resolution(packet, (binding,), nested, (row,))["reason"] == "RESOLVED_PROBLEM_MISMATCH"


def test_resolver_does_not_call_model_resolution_helper(monkeypatch):
    row, packet = statement(), problem()
    binding, _ = recall((row,))
    nested = resolved(packet)
    monkeypatch.setattr(SemanticProblem, "resolved_problem", lambda *_: pytest.fail("resolution shortcut called"))
    # Model construction legitimately checks references. The checker performs
    # its own traversal after that structural admission and never uses the
    # resolved_problem candidate-construction helper.
    assert check_resolution(packet, (binding,), nested, (row,))["status"] == "VALID"


def test_unreachable_refs_are_omitted_explicitly_and_not_recalled():
    row = statement()
    packet = problem(equations=(SemanticEquation("x", "3", MemoryRef("shop", "fee"), "35"),
                                SemanticEquation("unused", MemoryRef("missing", "a"), "0", "9")))
    binding, _ = recall((row,))
    nested = resolved(packet)
    receipt = check_resolution(packet, (binding,), nested, (row,))
    assert receipt["status"] == "VALID"
    assert receipt["bindings"]["omitted_unreachable_equations"] == ["unused"]
    assert packet.resolved_problem((binding,)).to_dict() == nested.to_dict()
    reinserted = replace(nested, equations=nested.equations + (Equation("unused", "0", "0", "9"),))
    assert check_resolution(packet, (binding,), reinserted, (row,))["reason"] == "RESOLVED_PROBLEM_MISMATCH"


def test_reachable_child_refs_cannot_be_omitted_as_if_unreachable():
    row = statement()
    packet = problem(equations=(SemanticEquation("x", "1", "0", terms=(("y", "1"),)),
                                SemanticEquation("y", "3", MemoryRef("shop", "fee"), "35")))
    binding, _ = recall((row,))
    nested = packet.resolved_problem((binding,))
    dropped = replace(nested, equations=tuple(eq for eq in nested.equations if eq.variable == "x"))
    assert check_resolution(packet, (binding,), dropped, (row,))["reason"] == "RESOLVED_PROBLEM_MISMATCH"
    assert check_resolution(packet, (), nested, (row,))["reason"] == "BINDING_SET_MISMATCH"


@pytest.mark.parametrize("cyclic", [False, True])
def test_cycles_and_missing_producers_are_preserved_for_live_planner(cyclic):
    equations = (SemanticEquation("x", "1", "0", terms=(("y", "1"),)),
                  SemanticEquation("y", "1", "0", terms=(("x", "1"),))) if cyclic else (
                     SemanticEquation("x", "1", "0", terms=(("missing", "1"),)),)
    packet = problem(equations=equations)
    receipt = check_resolution(packet, (), packet.resolved_problem(()), ())
    assert receipt["status"] == "VALID"
    assert receipt["bindings"]["missing_producers"] == ([] if cyclic else ["missing"])


def test_problem_updates_must_be_exact_admitted_suffix():
    old = statement()
    new = correction(old)
    packet = problem(updates=(new,))
    old_binding, _ = recall((old,))
    assert check_resolution(packet, (old_binding,), resolved(packet), (old,))["reason"] == "PROBLEM_UPDATES_NOT_ADMITTED"
    binding, _ = recall((old, new))
    assert check_resolution(packet, (binding,), resolved(packet, "8"), (old, new))["status"] == "VALID"
    unrelated = statement("99", key="other")
    binding, _ = recall((old, new, unrelated))
    assert check_resolution(packet, (binding,), resolved(packet, "8"), (old, new, unrelated))["reason"] == "PROBLEM_UPDATES_NOT_ADMITTED"


@pytest.mark.parametrize("profile", [None, "", "f" * 63, "G" * 64, 123])
def test_source_profile_binding_is_mandatory(profile):
    row = statement()
    with pytest.raises(ContractError):
        validate_source_update((), row, anchors(row), source_profile_digest=profile)


@pytest.mark.parametrize("trusted", [[], ("bad",), ("a" * 64, "a" * 64), (123,), tuple(f"{i:064x}" for i in range(257))])
def test_trusted_ingress_is_closed_bounded_external_data(trusted):
    with pytest.raises(ContractError):
        validate_source_update((), statement(), trusted, **KW)


def test_external_history_is_not_accepted_on_digest_or_status_alone():
    row = statement()
    with pytest.raises(ContractError):
        resolve_memory((row.to_dict(),), MemoryRef("shop", "fee"), anchors(row), **KW)
    with pytest.raises(ContractError):
        resolve_memory([row], MemoryRef("shop", "fee"), anchors(row), **KW)


def test_receipt_is_deterministic_without_io_or_a_generated_answer():
    row, packet = statement(), problem()
    binding, recall_receipt = recall((row,))
    one = check_resolution(packet, (binding,), resolved(packet), (row,))
    two = check_resolution(packet, (binding,), resolved(packet), (row,))
    assert one == two
    assert "answer" not in one and "output" not in one
    assert recall_receipt["bindings"]["binding"]["value"] == "5"
