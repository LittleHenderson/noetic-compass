"""Tests for the seed-18 frozen-model interface (slice 1 executed locally at commit 2022be45 from its former path
claude_lead_20260927/seed18_interfaces/test_frozen_model_interface_slice1.py; slice 2 written, NOT run).

EVERY object built here is a TEST DOUBLE. No HELM model, checkpoint, run, answer key or private body exists
behind any value; every digest is the SHA-256 of a labeled string or of test-double bytes; every record carries the
provenance ``CLAUDE_TEST_DOUBLE_NOT_A_HELM_RUN``. Nothing here is a HELM run or a HELM result. GPU-dependent
operations (the real restore and predict) are never exercised; doubles stand in for their record shapes only.
"""
import contextlib
import hashlib
import inspect
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
NAMESPACE = HERE / "claude_lead_20260927" / "seed18_interfaces"
if str(NAMESPACE) not in sys.path:
    sys.path.insert(0, str(NAMESPACE))
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
                run_identity_digest=h("run_identity"), learnable_names=("double.bias", "double.weight"))
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


# ===================================================== slice 1 (executed locally at 2022be45: 43 passed) ======

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


@pytest.mark.parametrize("name,call", [
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


# ===================================================== slice 2 (written for packet B1-SEED18-IMPLEMENT-02; NOT run) ==

@pytest.mark.parametrize("override", [
    {"device_name": "42"}, {"device_name": "yes"}, {"torch_version": "no"}, {"torch_version": "the answer is 7"},
])
def test_short_prediction_bodies_cannot_hide_in_a_free_field(override):
    record = fmi.asdict(double_prediction(1, 1))
    record.update(override)
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_record_is_public_safe(record)


def test_short_bodies_in_item_id_and_admission_ref_are_refused():
    record = fmi.asdict(double_prediction(1, 1))
    record["item"]["item_id"] = "yes"
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_record_is_public_safe(record)
    identity = double_identity()
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_admission_binding(identity, double_admission(identity, admission_ref="the answer is 7"))
    fmi.validate_admission_binding(identity, double_admission(identity, admission_ref="admission://codex-runner/comment-5856489964"))


def test_real_structured_forms_are_accepted_without_free_text():
    record = fmi.asdict(double_prediction(1, 1))
    record["device_name"] = "cuda:0"
    record["torch_version"] = "2.11.0+cu128"
    record["item"]["item_id"] = "development:" + h("item")[:16]
    assert fmi.validate_record_is_public_safe(record) == "PredictionRecord"


def _checkpoint_file(tmp_path, identity, *, size=None, bytes_override=None):
    """Writes TEST-DOUBLE bytes (not a model) whose size and digest match ``identity`` unless overridden."""
    body = bytes_override if bytes_override is not None else (b"\x00" * (size if size is not None else identity.checkpoint_bytes))
    path = tmp_path / "double_checkpoint.pt"
    path.write_bytes(body)
    return path


def _matching_identity(body):
    return double_identity(checkpoint_sha256=hashlib.sha256(body).hexdigest(), checkpoint_bytes=len(body))


class DoubleLearner:
    """TEST DOUBLE of a restored learner clone: records calls, never computes anything."""

    def __init__(self, cursor=2940, result=b"double-prediction-bytes", model_revision=None):
        self.cursor = cursor
        self.model_revision = cursor if model_revision is None else model_revision
        self.result = result
        self.predict_calls = []
        self.stage_batch_calls = 0

    def predict(self, packet, depth):
        self.predict_calls.append((packet, depth))
        return self.result

    def stage_batch(self, *args, **kwargs):
        self.stage_batch_calls += 1


class DoubleStore:
    """TEST DOUBLE of the venue's private store: hashes what it is given and returns a receipt; keeps no body."""

    def __init__(self, bad_ref=False):
        self.puts = 0
        self.bad_ref = bad_ref

    def put(self, raw):
        self.puts += 1
        digest = hashlib.sha256(raw).hexdigest()
        ref = "private://test-double-store/" + (h("wrong") if self.bad_ref else digest)
        return fmi.PrivateBodyReceipt(ref=ref, sha256=digest, nbytes=len(raw))


def _rng_guard_double(log):
    @contextlib.contextmanager
    def guard():
        log.append("enter")
        yield
        log.append("exit")
    return guard


def test_admit_refuses_a_missing_or_symlinked_checkpoint_path(tmp_path):
    identity = double_identity()
    admission = double_admission(identity)
    with refused("CHECKPOINT_PATH_INVALID"):
        fmi.admit_frozen_model(identity, admission, path=tmp_path / "missing.pt", device="cuda:0")
    real = _checkpoint_file(tmp_path, identity)
    link = tmp_path / "link.pt"
    link.symlink_to(real)
    with refused("CHECKPOINT_PATH_INVALID"):
        fmi.admit_frozen_model(identity, admission, path=link, device="cuda:0")


def test_admit_refuses_size_mismatch_before_reading_bytes(tmp_path, monkeypatch):
    identity = double_identity()
    path = _checkpoint_file(tmp_path, identity, size=10)
    import builtins
    real_open = builtins.open

    def counting_open(*args, **kwargs):
        raise AssertionError("bytes must not be read when the size already differs")

    monkeypatch.setattr(builtins, "open", counting_open)
    with refused("FROZEN_MODEL_BYTES_MISMATCH"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0")
    monkeypatch.setattr(builtins, "open", real_open)


def test_admit_refuses_sha_mismatch_before_any_load(tmp_path):
    identity = double_identity()
    path = _checkpoint_file(tmp_path, identity)  # right size, wrong bytes for the double's digest
    calls = []
    with refused("FROZEN_MODEL_SHA_MISMATCH"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0",
                               restore=lambda *a, **k: calls.append(1), framework_factory=lambda: None,
                               encoder=object(), torch=object(), rng_guard=_rng_guard_double([]))
    assert calls == []


def test_admit_on_cpu_is_gpu_required_before_any_load(tmp_path):
    body = b"\x01" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    calls = []
    with refused("GPU_REQUIRED"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cpu",
                               restore=lambda *a, **k: calls.append(1), framework_factory=lambda: None,
                               encoder=object(), torch=object(), rng_guard=_rng_guard_double([]))
    assert calls == []


def test_admit_without_restore_dependencies_stops_at_the_cpu_dry_boundary(tmp_path):
    body = b"\x02" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    with refused("RESTORE_DEPENDENCIES_NOT_SUPPLIED"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0")


def test_admit_with_a_double_restore_returns_a_predict_only_handle(tmp_path):
    body = b"\x03" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    learner = DoubleLearner()
    seen = {}
    frameworks = []

    def restore(torch, framework, encoder, *, path, expected_sha256, expected_run_identity_digest, device,
                expected_learnable_names=None):
        seen.update(torch=torch, framework=framework, encoder=encoder, path=path, sha=expected_sha256,
                    rid=expected_run_identity_digest, device=device, names=expected_learnable_names)
        log.append("restore")
        return learner

    def framework_factory():
        frameworks.append(object())
        return frameworks[-1]

    log = []
    encoder, torch = object(), object()
    handle = fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0", restore=restore,
                                    framework_factory=framework_factory, encoder=encoder, torch=torch,
                                    rng_guard=_rng_guard_double(log))
    assert seen == dict(torch=torch, framework=frameworks[0], encoder=encoder, path=str(path),
                        sha=identity.checkpoint_sha256, rid=identity.run_identity_digest, device="cuda:0",
                        names=["double.bias", "double.weight"])
    assert len(frameworks) == 1, "one fresh framework per admission"
    assert log == ["enter", "restore", "exit"], "the restore itself runs inside the RNG guard"
    assert handle.predict("double-packet") == b"double-prediction-bytes"
    assert learner.predict_calls == [("double-packet", 8)] and log == ["enter", "restore", "exit", "enter", "exit"]
    assert handle.predict_calls == 1
    for name in ("stage_batch", "train_sealed_batch", "export_checkpoint"):
        with refused("TRAINING_ENTRY_POINT_FORBIDDEN"):
            getattr(handle, name)
    assert learner.stage_batch_calls == 0
    with pytest.raises(AttributeError):
        handle.something_else


def test_admit_refuses_cursor_mismatch_after_a_double_restore(tmp_path):
    body = b"\x04" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    with refused("FROZEN_MODEL_CURSOR_MISMATCH"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0",
                               restore=lambda *a, **k: DoubleLearner(cursor=2941), framework_factory=lambda: None,
                               encoder=object(), torch=object(), rng_guard=_rng_guard_double([]))


@pytest.mark.parametrize("names", [("has space",), ("b.w", "a.w"), ("a.w", "a.w"), (), "a.w"])
def test_learnable_names_must_be_sorted_unique_structured_parameter_names(names):
    with refused("PUBLIC_FIELD_FORMAT_INVALID"):
        fmi.validate_frozen_model_identity(double_identity(learnable_names=names))


def test_admit_refuses_model_revision_mismatch_after_a_double_restore(tmp_path):
    body = b"\x06" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    with refused("FROZEN_MODEL_CURSOR_MISMATCH"):
        fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0",
                               restore=lambda *a, **k: DoubleLearner(cursor=2940, model_revision=2939),
                               framework_factory=lambda: None, encoder=object(), torch=object(),
                               rng_guard=_rng_guard_double([]))


def test_binding_constants_name_the_exact_public_slice():
    assert fmi.LEARNER_SOURCE_FILE_SHA256 == "0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8"
    assert fmi.LEARNER_SOURCE_BLOB == "d07012d48d8543c342bffaa7a8ec67c6e69ccc9c"
    assert fmi.LEARNER_SOURCE_LINES["restore_checkpoint"] == 2144 and fmi.LEARNER_SOURCE_LINES["predict"] == 1954
    assert set(fmi.FORBIDDEN_HANDLE_ATTRIBUTES) <= set(fmi.LEARNER_SOURCE_LINES)


def test_admit_takes_no_host_and_names_the_separate_si_contract():
    assert "host" not in inspect.signature(fmi.admit_frozen_model).parameters
    assert fmi.SI_HOST_NEURAL_PARENT_CONTRACT.startswith("SEPARATE")
    assert fmi.UNACCEPTED_GPU_OPERATIONS == ("restore_checkpoint", "predict")


def _admitted_handle(tmp_path, learner, log):
    body = b"\x05" * 4096
    identity = _matching_identity(body)
    path = _checkpoint_file(tmp_path, identity, bytes_override=body)
    return fmi.admit_frozen_model(identity, double_admission(identity), path=path, device="cuda:0",
                                  restore=lambda *a, **k: learner, framework_factory=lambda: None,
                                  encoder=object(), torch=object(), rng_guard=_rng_guard_double(log))


def test_predict_raw_charges_then_stores_then_records_in_that_order(tmp_path):
    learner, log = DoubleLearner(), []
    handle = _admitted_handle(tmp_path, learner, log)
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget(prediction_calls_max=1))
    store = DoubleStore()
    record = fmi.predict_raw(handle, double_item(1), "double-packet", budget_ledger=budget, ledger=ledger,
                             private_store=store, device_name="test-double-no-device", torch_version="test-double-no-torch")
    assert store.puts == 1 and ledger.rows == (record,) and record.prediction_sequence == 1
    assert record.raw_output_sha256 == hashlib.sha256(b"double-prediction-bytes").hexdigest()
    assert record.raw_output_bytes == len(b"double-prediction-bytes")
    assert record.private_body_ref.endswith("/" + record.raw_output_sha256)
    assert "double-prediction-bytes" not in fmi.canonical_bytes(fmi.asdict(record)).decode()
    assert fmi.validate_record_is_public_safe(record) == "PredictionRecord"
    assert budget.snapshot()["spent"]["prediction"] == 1 and log == ["enter", "exit"]
    with refused("PREDICTION_BUDGET_EXHAUSTED"):
        fmi.predict_raw(handle, double_item(2), "double-packet", budget_ledger=budget, ledger=ledger,
                        private_store=store, device_name="test-double-no-device", torch_version="test-double-no-torch")
    assert len(learner.predict_calls) == 1 and store.puts == 1 and len(ledger.rows) == 1


def test_predict_raw_refuses_an_inconsistent_store_receipt(tmp_path):
    learner, log = DoubleLearner(), []
    handle = _admitted_handle(tmp_path, learner, log)
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget())
    with refused("PRIVATE_STORE_RECEIPT_INVALID"):
        fmi.predict_raw(handle, double_item(1), "double-packet", budget_ledger=budget, ledger=ledger,
                        private_store=DoubleStore(bad_ref=True), device_name="test-double-no-device",
                        torch_version="test-double-no-torch")
    assert ledger.rows == ()


def test_predict_raw_refuses_a_none_result(tmp_path):
    learner, log = DoubleLearner(result=None), []
    handle = _admitted_handle(tmp_path, learner, log)
    ledger = fmi.RecordLedger(TEST_DOUBLE)
    budget = fmi.BudgetLedger(double_budget())
    store = DoubleStore()
    with refused("PREDICTION_OUTPUT_INVALID"):
        fmi.predict_raw(handle, double_item(1), "double-packet", budget_ledger=budget, ledger=ledger,
                        private_store=store, device_name="test-double-no-device", torch_version="test-double-no-torch")
    assert store.puts == 0 and ledger.rows == ()
