"""Slice-1 tests for frozen_model_interface (owner task SEED18-INTERFACE-IMPLEMENT-02).

EVERY object built here is a TEST DOUBLE. No HELM model, checkpoint, run, answer key or private body exists
behind any value; every digest is the SHA-256 of a labeled string; every record carries the provenance
``CLAUDE_TEST_DOUBLE_NOT_A_HELM_RUN``. Nothing here is a HELM run or a HELM result.
"""
import hashlib
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import frozen_model_interface as fmi  # noqa: E402

TEST_DOUBLE = "CLAUDE_TEST_DOUBLE_NOT_A_HELM_RUN"
UTC = "2026-09-27T13:30:00Z"


def h(label):
    """A labeled test-double digest. It is the hash of the label, not of any model, body or key."""
    return hashlib.sha256(("TEST_DOUBLE:" + label).encode()).hexdigest()


def double_identity(**over):
    base = dict(checkpoint_sha256=h("checkpoint"), checkpoint_bytes=4096, cursor=2940, model_revision=2940,
                model_state_identity=h("model_state"), optimizer_state_identity=h("optimizer_state"),
                encoder_state_identity=h("encoder_state"), rng_state_identity=h("rng_state"),
                run_identity_digest=h("run_identity"))
    base.update(over)
    return fmi.FrozenModelIdentity(**base)


def double_item(seq, panel="development"):
    return fmi.ItemRef(item_id="double-item-%d" % seq, inputs_sha256=h("inputs-%d" % seq), panel=panel,
                       depth=1, sequence=seq)


def double_prediction(ledger_seq, item_seq, *, model=None, raw_label=None, provenance=TEST_DOUBLE):
    return fmi.PredictionRecord(
        schema=fmi.PREDICTION_RECORD_SCHEMA, model=model or double_identity(), item=double_item(item_seq),
        raw_output_sha256=h(raw_label or "raw-%d" % item_seq), raw_output_bytes=64,
        private_body_ref="private://test-double-store/" + h("body-%d" % item_seq),
        device_name="test-double-no-device", torch_version="test-double-no-torch", produced_utc=UTC,
        prediction_sequence=ledger_seq, provenance=provenance)


def double_budget(**over):
    base = dict(prediction_calls_max=3, native_calls_max_per_item=1, evaluator_calls_max=3, wall_seconds_max=60)
    base.update(over)
    return fmi.EpisodeBudget(**base)


def double_evaluator(**over):
    base = dict(evaluator_sha256=h("evaluator"), answer_key_sha256=h("answer-key-digest-only"), panel="development")
    base.update(over)
    return fmi.EvaluatorIdentity(**base)


def double_admission(identity, **over):
    base = dict(schema=fmi.ADMISSION_BINDING_SCHEMA, identity_digest=fmi.identity_digest(identity),
                admitted_by="CODEX_RUNNER_ADMISSION", admission_ref="test-double-admission-ref-1",
                admitted_utc=UTC, provenance=TEST_DOUBLE)
    base.update(over)
    return fmi.AdmissionBinding(**base)


def double_work(**over):
    base = dict(schema=fmi.WORK_ACCOUNT_SCHEMA, prediction_calls=1, native_calls_allocated=1, native_calls_executed=1,
                charged_native_policy_units_sha256=h("charged"), actual_primitive_work_sha256=h("actual"),
                evaluator_calls=0, controller_wall_ns=10, verification_wall_ns=5)
    base.update(over)
    return fmi.WorkAccount(**base)


def double_cas_output(prediction, seq, **over):
    """A TEST DOUBLE of a CAS-path output. The real CAS path is unimplemented; this stands in for its record shape."""
    base = dict(schema=fmi.SYSTEM_OUTPUT_RECORD_SCHEMA, repair_path="CAS_CLOSED_LOOP",
                prediction_sha256=prediction.raw_output_sha256, item=prediction.item,
                native_receipt_sha256=h("receipt-%d" % seq), verified_output_sha256=h("verified-%d" % seq),
                checked_effect=None, work=double_work(), produced_utc=UTC, output_sequence=seq, provenance=TEST_DOUBLE)
    base.update(over)
    return fmi.SystemOutputRecord(**base)


def refused(code):
    return pytest.raises(fmi.InterfaceRefused, match="^" + code)


# --- constants and typed identity -----------------------------------------------------------------------

def test_constants_bind_the_codex_stated_parent_and_sources():
    assert fmi.PARENT_CHECKPOINT_SHA256 == "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"
    assert fmi.PARENT_CHECKPOINT_BYTES == 4025999 and fmi.PARENT_CURSOR == 2940
    assert fmi.SCIENTIFIC_SOURCE == "c45f775f225dd06cc20cdf313f0a0398486e0d61"
    assert fmi.CAS_SOURCE == "7bbf1e0f7bae635126c05b3203cca706ea8654dc"
    assert fmi.JOINT_SOURCE == "d7808d59c13ea94c6ff35d2327a4acb8535daabc"


def test_identity_validation_accepts_a_double_and_returns_its_digest():
    identity = double_identity()
    digest = fmi.validate_frozen_model_identity(identity)
    assert digest == fmi.identity_digest(identity) and len(digest) == 64
    assert digest != fmi.identity_digest(double_identity(cursor=2941))


def test_identity_on_cpu_is_gpu_required_not_a_fallback():
    with refused("GPU_REQUIRED"):
        fmi.validate_frozen_model_identity(double_identity(device_class="cpu"))


@pytest.mark.parametrize("override,code", [
    ({"model_state_identity": "abc"}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"checkpoint_bytes": 0}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"cursor": True}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"scientific_source": "0" * 40}, "IDENTITY_FIELD_INVALID"),
])
def test_identity_field_defects_are_refused_by_name(override, code):
    with refused(code):
        fmi.validate_frozen_model_identity(double_identity(**override))


def test_identity_of_the_wrong_type_is_refused():
    with refused("RECORD_TYPE_INVALID"):
        fmi.validate_frozen_model_identity({"checkpoint_sha256": h("checkpoint")})


# --- admission binding: a hash alone does not authorize ------------------------------------------------

def test_admission_with_a_self_issued_authority_is_not_authorization():
    identity = double_identity()
    with refused("AUTHORIZATION_NOT_PROVEN"):
        fmi.validate_admission_binding(identity, double_admission(identity, admitted_by="SELF"))


def test_admission_naming_another_digest_is_not_authorization():
    identity = double_identity()
    with refused("AUTHORIZATION_NOT_PROVEN"):
        fmi.validate_admission_binding(identity, double_admission(double_identity(cursor=1)))


def test_admission_binding_is_structural_and_says_so():
    identity = double_identity()
    result = fmi.validate_admission_binding(identity, double_admission(identity))
    assert result["identity_digest"] == fmi.identity_digest(identity)
    assert result["structural_check_only"] is True and result["signature_verified"] is False


# --- budget and work account -------------------------------------------------------------------------------

def test_budget_validation_and_exhaustion_refuse_before_the_call():
    fmi.validate_budget(double_budget())
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_budget(double_budget(prediction_calls_max=0))
    ledger = fmi.BudgetLedger(double_budget(prediction_calls_max=2))
    assert ledger.charge_prediction() == 1 and ledger.charge_prediction() == 2
    with refused("PREDICTION_BUDGET_EXHAUSTED"):
        ledger.charge_prediction()
    assert ledger.snapshot()["spent"]["prediction"] == 2


@pytest.mark.parametrize("override,code", [
    ({"native_calls_executed": 2}, "WORK_ACCOUNT_INCOMPLETE"),
    ({"controller_wall_ns": -1}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"charged_native_policy_units_sha256": "not-a-digest"}, "PUBLIC_FIELD_FORMAT_INVALID"),
])
def test_work_account_defects_are_refused(override, code):
    with refused(code):
        fmi.validate_work_account(double_work(**override))


def test_work_account_is_checked_against_the_budget():
    fmi.validate_work_account(double_work(), budget=double_budget())
    with refused("NATIVE_BUDGET_EXHAUSTED"):
        fmi.validate_work_account(double_work(native_calls_allocated=2, native_calls_executed=1), budget=double_budget())
    with refused("EVALUATOR_BUDGET_EXHAUSTED"):
        fmi.validate_work_account(double_work(evaluator_calls=4), budget=double_budget())


# --- public-record validation: explicit permitted fields, formats, provenance ----------------------------

def test_prediction_record_double_is_public_safe():
    assert fmi.validate_record_is_public_safe(double_prediction(1, 1)) == "PredictionRecord"


def test_a_body_field_is_refused_by_name_before_anything_else():
    as_dict = fmi.asdict(double_prediction(1, 1))
    as_dict["raw_output"] = "the answer is 42"
    with refused("PREDICTION_BODY_IN_PUBLIC_RECORD"):
        fmi.validate_record_is_public_safe(as_dict)


def test_unlisted_or_missing_fields_are_refused():
    extra = fmi.asdict(double_prediction(1, 1))
    extra["note"] = "ok"
    with refused("PUBLIC_FIELD_NOT_PERMITTED"):
        fmi.validate_record_is_public_safe(extra)
    missing = fmi.asdict(double_prediction(1, 1))
    del missing["device_name"]
    with refused("PUBLIC_FIELD_NOT_PERMITTED"):
        fmi.validate_record_is_public_safe(missing)


@pytest.mark.parametrize("override,code", [
    ({"device_name": "a b"}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"private_body_ref": "short"}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"produced_utc": "yesterday"}, "PUBLIC_FIELD_FORMAT_INVALID"),
    ({"provenance": "MY_RUN"}, "PROVENANCE_INVALID"),
])
def test_a_short_string_is_not_automatically_safe(override, code):
    record = fmi.asdict(double_prediction(1, 1))
    record.update(override)
    with refused(code):
        fmi.validate_record_is_public_safe(record)


def test_nested_records_are_checked_the_same_way():
    record = fmi.asdict(double_prediction(1, 1))
    record["item"]["item_id"] = "has space"
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_record_is_public_safe(record)


def test_public_check_opens_no_file(monkeypatch):
    import builtins

    def no_open(*args, **kwargs):
        raise AssertionError("validation must never open a file")

    monkeypatch.setattr(builtins, "open", no_open)
    fmi.validate_record_is_public_safe(double_prediction(1, 1))
    fmi.validate_admission_binding(double_identity(), double_admission(double_identity()))


def test_dict_record_without_a_known_schema_is_refused():
    with refused("RECORD_SCHEMA_INVALID"):
        fmi.validate_record_is_public_safe({"item_id": "x"})


# --- ledger ordering: original prediction before repair ----------------------------------------------------

def test_ledger_assigns_and_enforces_sequence():
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    with refused("LEDGER_SEQUENCE_MISMATCH"):
        ledger.append(double_prediction(2, 1))
    assert ledger.append(double_prediction(1, 1)) == 1 and ledger.next_sequence() == 2


def test_ledger_provenance_must_match_every_row():
    ledger = fmi.RecordLedger("HELM_ADMITTED_RUN")
    with refused("PROVENANCE_INVALID"):
        ledger.append(double_prediction(1, 1))
    with refused("PROVENANCE_INVALID"):
        fmi.RecordLedger("SOMEONE_ELSE")


def test_repair_none_is_refused_until_the_prediction_is_recorded():
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    prediction = double_prediction(1, 1)
    with refused("PREDICTION_NOT_RECORDED_BEFORE_REPAIR"):
        fmi.repair_none(prediction, evaluator=double_evaluator(), budget=double_budget(), ledger=ledger)
    assert ledger.rows == ()


def test_repair_none_preserves_the_original_prediction():
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget())
    prediction = double_prediction(1, 1)
    before = fmi.asdict(prediction)
    fmi.record_prediction(ledger, budget, prediction)
    output = fmi.repair_none(prediction, evaluator=double_evaluator(), budget=budget.budget, ledger=ledger)
    assert output.repair_path == "NONE" and output.verified_output_sha256 == prediction.raw_output_sha256
    assert output.prediction_sha256 == prediction.raw_output_sha256 and output.item == prediction.item
    assert output.native_receipt_sha256 is None and output.checked_effect is None
    assert output.work.native_calls_allocated == 0 and output.work.native_calls_executed == 0
    assert output.work.prediction_calls == 1 and output.work.evaluator_calls == 0
    assert output.work.charged_native_policy_units_sha256 == fmi.EMPTY_WORK_DIGEST
    assert fmi.asdict(prediction) == before, "the prediction record was changed by the repair path"
    assert ledger.rows == (prediction, output) and output.output_sequence == 2
    fmi.validate_record_is_public_safe(output)
    assert len(ledger.digest()) == 64 and ledger.to_public()["rows"][0] == before


def test_record_prediction_charges_the_budget_before_appending():
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget(prediction_calls_max=3))
    for seq in (1, 2, 3):
        fmi.record_prediction(ledger, budget, double_prediction(seq, seq))
    with refused("PREDICTION_BUDGET_EXHAUSTED"):
        fmi.record_prediction(ledger, budget, double_prediction(4, 4))
    assert len(ledger.rows) == 3


def test_an_output_without_its_prediction_row_cannot_be_appended():
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    orphan = double_cas_output(double_prediction(1, 1), 1)
    with refused("PREDICTION_NOT_RECORDED_BEFORE_REPAIR"):
        ledger.append(orphan)


def test_none_path_output_that_changed_the_digest_is_refused():
    prediction = double_prediction(1, 1)
    changed = double_cas_output(prediction, 2, repair_path="NONE", native_receipt_sha256=None,
                                work=double_work(native_calls_allocated=0, native_calls_executed=0))
    with refused("PREDICTION_NOT_PRESERVED"):
        fmi.validate_system_output_record(changed)


# --- parity: same items, order, evaluator, budget, frozen model, raw predictions ------------------------------

def _paths(n=2, cas_raw_label=None, cas_item_order=None):
    """Builds a NONE path through the real ledger and a CAS path from labeled doubles."""
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget(prediction_calls_max=n))
    path_none = []
    for i in range(1, n + 1):
        prediction = double_prediction(ledger.next_sequence(), i)
        fmi.record_prediction(ledger, budget, prediction)
        path_none.append((prediction, fmi.repair_none(prediction, evaluator=double_evaluator(),
                                                      budget=budget.budget, ledger=ledger)))
    path_cas = []
    order = cas_item_order or list(range(1, n + 1))
    for seq, i in enumerate(order, start=1):
        prediction = double_prediction(seq, i, raw_label=(cas_raw_label if (cas_raw_label and i == 1) else None))
        path_cas.append((prediction, double_cas_output(prediction, seq)))
    return path_none, path_cas


def test_parity_returns_work_totals_and_no_verdict():
    path_none, path_cas = _paths()
    totals = fmi.episode_parity_check(path_none, path_cas, budget_none=double_budget(), budget_cas=double_budget(),
                                      evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())
    assert totals["items"] == 2
    assert totals["NONE"]["native_calls_executed"] == 0 and totals["CAS_CLOSED_LOOP"]["native_calls_executed"] == 2
    assert totals["NONE"]["prediction_calls"] == 2 and totals["CAS_CLOSED_LOOP"]["prediction_calls"] == 2
    assert not any(key in totals for key in ("verdict", "score", "winner", "threshold", "accepted"))


def test_parity_refuses_item_order_mismatch():
    path_none, path_cas = _paths(cas_item_order=[2, 1])
    with refused("ITEM_ORDER_MISMATCH"):
        fmi.episode_parity_check(path_none, path_cas, budget_none=double_budget(), budget_cas=double_budget(),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())


def test_parity_refuses_budget_and_evaluator_mismatch():
    path_none, path_cas = _paths()
    with refused("BUDGET_MISMATCH"):
        fmi.episode_parity_check(path_none, path_cas, budget_none=double_budget(), budget_cas=double_budget(wall_seconds_max=61),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())
    with refused("EVALUATOR_MISMATCH"):
        fmi.episode_parity_check(path_none, path_cas, budget_none=double_budget(), budget_cas=double_budget(),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator(panel="course"))


def test_parity_refuses_a_changed_raw_prediction():
    path_none, path_cas = _paths(cas_raw_label="different-raw")
    with refused("PREDICTION_NOT_PRESERVED"):
        fmi.episode_parity_check(path_none, path_cas, budget_none=double_budget(), budget_cas=double_budget(),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())


def test_parity_refuses_wrong_path_labels_and_missing_receipts():
    path_none, path_cas = _paths()
    with refused("REPAIR_PATH_MISMATCH"):
        fmi.episode_parity_check(path_cas, path_cas, budget_none=double_budget(), budget_cas=double_budget(),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())
    prediction, output = path_cas[0]
    no_receipt = [(prediction, double_cas_output(prediction, 1, native_receipt_sha256=None))] + path_cas[1:]
    with refused("NATIVE_RECEIPT_MISSING"):
        fmi.episode_parity_check(path_none, no_receipt, budget_none=double_budget(), budget_cas=double_budget(),
                                 evaluator_none=double_evaluator(), evaluator_cas=double_evaluator())


# --- unimplemented paths say so, exactly -----------------------------------------------------------------

@pytest.mark.parametrize("name,call", [
    ("admit_frozen_model", lambda: fmi.admit_frozen_model(double_identity(), path="/nonexistent", host=None)),
    ("predict_raw", lambda: fmi.predict_raw(None, double_item(1), budget=double_budget(), ledger=fmi.RecordLedger(TEST_DOUBLE))),
    ("repair_cas_closed_loop", lambda: fmi.repair_cas_closed_loop(double_prediction(1, 1), None, calls=1, allow_acquisition=True,
                                                                  actuator_enabled=True, evaluator=double_evaluator(),
                                                                  budget=double_budget(), ledger=fmi.RecordLedger(TEST_DOUBLE))),
    ("evaluate", lambda: fmi.evaluate(None, evaluator=double_evaluator(), ledger=fmi.RecordLedger(TEST_DOUBLE))),
])
def test_unimplemented_paths_raise_their_exact_reason(name, call):
    with pytest.raises(NotImplementedError, match="^" + fmi.NOT_IMPLEMENTED_REASONS[name] + "$"):
        call()


def test_refusal_codes_are_a_closed_set():
    with pytest.raises(ValueError, match="UNKNOWN_REFUSAL_CODE:BOGUS"):
        fmi.InterfaceRefused("BOGUS")
    assert fmi.InterfaceRefused("GPU_REQUIRED", "why").code == "GPU_REQUIRED"
