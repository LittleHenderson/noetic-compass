"""Pure full-course admission checks; no model, provider or final panel data."""
from copy import deepcopy
from collections import Counter
import importlib.abc
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer",
          "boto3", "botocore", "requests", "httpx", "openai", "anthropic"}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED:" + fullname)


guard = Deny()
sys.meta_path.insert(0, guard)
research = str(ROOT / "research/CAS_META_2_COMPOSITION")
sys.path.insert(0, research)
try:
    from cncm import rpa_course_adapter as adapter
    from cncm.canonical import canonical_json, digest
finally:
    sys.path.remove(research)
    sys.meta_path.remove(guard)


@pytest.fixture(autouse=True)
def deny_numeric_provider():
    guard = Deny()
    sys.meta_path.insert(0, guard)
    try:
        yield
        assert not DENIED.intersection(n.split(".")[0] for n in sys.modules)
    finally:
        sys.meta_path.remove(guard)


@pytest.fixture(scope="module")
def profile():
    return adapter.source_profile()


@pytest.fixture(scope="module")
def prepared(profile):
    return adapter.prepare_course(seed=101, condition="ALT_COMPONENT_WHOLE",
        expected_source_profile_digest=profile["profile_digest"])


@pytest.fixture(scope="module")
def identity(prepared):
    tokenizer = adapter.fit_training_tokenizer(prepared)
    ordered = adapter._scoped_encoder().profile_identity(tokenizer, d_model=64,
        seed=101, projection_sha256="b" * 64)
    return {"tokenizer": tokenizer, "ordered_profile": ordered,
            "model_context": {"model_id": "pure-course-test", "checkpoint_sha256": "a" * 64}}


@pytest.fixture(scope="module")
def bound(prepared, identity):
    return adapter.bind_course(prepared, **identity)


def test_source_profile_has_code_pins_and_no_final_data(profile):
    body = {key: value for key, value in profile.items() if key != "profile_digest"}
    assert profile["profile_digest"] == digest(body)
    assert profile["data_files"] == []
    assert profile["final_target_files_read"] is False
    assert all(row["path"].endswith(".py") and "/records/" not in row["path"]
               for row in profile["files"])


def test_full_1152_presentation_schedule_and_all_four_operation_families(prepared):
    assert len(prepared["presentations"]) == 1152
    assert len(prepared["batches"]) == 160
    assert len({b["round"] for b in prepared["batches"]}) == 16
    assert Counter(row["operation"] for row in prepared["presentations"]) == {
        "FACE_APPLY": 800, "ROLE_FROM_CONTENT": 96, "LIST_PARTS": 128, "REACHED_VIA": 128}
    assert Counter(row["source_selector"]["teaching_role"] for row in prepared["presentations"]) == {
        "CFC_FOUNDATION": 768, "MAINTENANCE": 128, "COMPONENT": 128, "WHOLE": 128}
    ids = [row["presentation_id"] for row in prepared["presentations"]]
    assert len(set(ids)) == 1152
    assert [i for batch in prepared["batches"] for i in batch["presentation_ids"]] == ids


def test_all_source_lines_and_choices_survive_losslessly(prepared):
    built = [f for f in adapter.face_corpus.families() if f["split"] == adapter.face_corpus.TRAINING]
    source = adapter.course.compile_complementary_course(101, "ALT_COMPONENT_WHOLE", built=built)
    tasks = [t for b in source["batches"] for t in b["tasks"]]
    for old, row in zip(tasks, prepared["presentations"]):
        operation, restored = adapter._parse_public(row["public"], row["encoded_options"])
        assert operation == old["op"]
        assert restored == old["public"]["problem"]
        assert row["encoded_options"] == old["encoded_options"]
        assert row["public"]["observations"] == old["public"]["observations"]
        assert row["public"]["problem"].splitlines().count(adapter.INVENTORY_DECLARATION) == 1
        assert row["teacher_sidecar"]["expected_answer"] == old["correct"]


def test_registry_deduplicates_only_cache_not_presentations(bound, prepared, identity):
    assert prepared["readiness"]["scope_binding_status"] == "SCOPED_PROFILE_REQUIRED_NOT_BOUND"
    assert bound["readiness"]["scope_binding_status"] == "SCOPED_FRAME_MAPS_PURE_CHECKED_CUDA_PENDING"
    assert len(bound["registry"]) == 624
    assert len(bound["presentations"]) == 1152
    assert bound["batches"] == prepared["batches"]
    assert set(bound["teacher_registry"]) == {p["record_id"] for p in bound["registry"]}
    assert all(set(p) == {"record_id", "public", "encoded_options"} for p in bound["registry"])
    assert identity["tokenizer"].fitted_examples == len(adapter._training_publics(prepared))
    assert bound["binding"]["max_encoded_tokens"] <= 1024
    assert bound["readiness"]["status"] == "NOT_YET_EXECUTION_ADMITTED"
    for field in ("support_query_scope_binding_verified", "course_aware_predictor_verified",
                  "fresh_origin_worker_factory_verified", "world_truth_established"):
        assert bound["readiness"][field] is False
    assert all(bound["readiness"][key] == 0 for key in
               ("numeric_encoder_calls", "neural_calls", "optimizer_updates"))


def test_mixed_order_preserves_all_items_and_exact_training_tokenizer(profile, prepared, identity):
    other = adapter.prepare_course(seed=101, condition="MIXED_SAME_ITEMS",
        expected_source_profile_digest=profile["profile_digest"])
    assert Counter(p["prepared_id"] for p in other["presentations"]) == (
        Counter(p["prepared_id"] for p in prepared["presentations"]))
    assert [p["prepared_id"] for p in other["presentations"]] != [
        p["prepared_id"] for p in prepared["presentations"]]
    assert adapter.fit_training_tokenizer(other).to_dict() == identity["tokenizer"].to_dict()


def test_whole_control_retains_full_course_and_doubles_whole_supplement(profile):
    other = adapter.prepare_course(seed=101, condition="WHOLE_SUPPLEMENT",
        expected_source_profile_digest=profile["profile_digest"])
    assert len(other["presentations"]) == 1152
    assert Counter(p["operation"] for p in other["presentations"]) == {
        "FACE_APPLY": 800, "ROLE_FROM_CONTENT": 96, "LIST_PARTS": 256}


@pytest.mark.parametrize("seed,condition", [(True, "ALT_COMPONENT_WHOLE"),
    (101.0, "ALT_COMPONENT_WHOLE"), (999, "ALT_COMPONENT_WHOLE"), (101, "SUBSTITUTE_THREE_OPS")])
def test_undeclared_course_refused(profile, seed, condition):
    with pytest.raises(ValueError):
        adapter.prepare_course(seed=seed, condition=condition,
            expected_source_profile_digest=profile["profile_digest"])


def test_changed_source_pin_refused(profile):
    with pytest.raises(ValueError, match="PROFILE_CHANGED"):
        adapter.prepare_course(seed=101, condition="ALT_COMPONENT_WHOLE",
            expected_source_profile_digest="0" * 64)


@pytest.mark.parametrize("field", ["teacher", "public", "selector", "missing_presentation", "extra"])
def test_modified_prepared_source_is_refused_even_when_digest_resealed(prepared, identity, field):
    changed = deepcopy(prepared)
    row = changed["presentations"][0]
    if field == "teacher":
        row["teacher_sidecar"]["encoded_correct_index"] = (row["teacher_sidecar"]["encoded_correct_index"] + 1) % 3
    elif field == "public":
        row["public"]["problem"] += 'text "injected"\n'
    elif field == "selector":
        row["source_selector"]["family_id"] = "foreign"
    elif field == "missing_presentation":
        changed["presentations"].pop()
    else:
        changed["expected_answer"] = "private"
    changed["prepared_course_digest"] = digest({
        k: v for k, v in changed.items() if k != "prepared_course_digest"})
    with pytest.raises(ValueError):
        adapter.bind_course(changed, **identity)


@pytest.mark.parametrize("field", ["correct", "encoded_correct_index", "teacher_sidecar",
                                   "source_selector", "op", "family_id"])
def test_public_packet_refuses_private_or_host_extras(bound, identity, field):
    packet = deepcopy(bound["registry"][0])
    packet[field] = "injected"
    with pytest.raises(ValueError, match="PUBLIC_FIELDS"):
        adapter.validate_prediction_packet(packet, **identity)


def test_public_validation_never_reconstructs_source_or_teacher(bound, identity, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SOURCE_OR_TEACHER_FROM_INFERENCE")
    for owner, name in ((adapter, "prepare_course"), (adapter, "check_course_targets"),
                        (adapter.course, "compile_complementary_course"),
                        (adapter, "_reprepare"), (adapter, "source_profile")):
        monkeypatch.setattr(owner, name, forbidden)
    packet = bound["registry"][0]
    assert adapter.validate_prediction_packet(packet, **identity) == packet


@pytest.mark.parametrize("change", ["public", "options", "checkpoint"])
def test_cache_identity_rejects_changed_actual_input(bound, identity, change):
    packet = deepcopy(bound["registry"][0])
    supplied = dict(identity)
    if change == "public":
        packet["public"]["problem"] += 'text "new public framing"\n'
    elif change == "options":
        packet["encoded_options"].reverse()
        for i, row in enumerate(packet["public"]["observations"]):
            row["tag"] = str(packet["encoded_options"][i])
    else:
        supplied["model_context"] = {"model_id": "pure-course-test", "checkpoint_sha256": "c" * 64}
    with pytest.raises(ValueError):
        adapter.validate_prediction_packet(packet, **supplied)


def test_teacher_sidecar_does_not_change_public_identity(bound, identity):
    changed = deepcopy(bound)
    key = changed["registry"][0]["record_id"]
    target = changed["teacher_registry"][key]
    target["encoded_correct_index"] = (target["encoded_correct_index"] + 1) % 3
    assert adapter.validate_prediction_packet(changed["registry"][0], **identity) == bound["registry"][0]


def test_source_target_join_rejects_resealed_private_changes(bound, prepared, identity):
    changed = deepcopy(bound)
    target = next(iter(changed["teacher_registry"].values()))
    target["encoded_correct_index"] = (target["encoded_correct_index"] + 1) % 3
    changed["bound_course_digest"] = digest({k: v for k, v in changed.items() if k != "bound_course_digest"})
    with pytest.raises(ValueError, match="BOUND_SOURCE_MISMATCH"):
        adapter.check_course_targets(changed, prepared=prepared, **identity)


def test_fit_on_non_course_publics_cannot_be_admitted(prepared, identity):
    public = deepcopy(prepared["presentations"][0]["public"])
    tokenizer = adapter.base.LosslessPublicTokenizer.fit_train([public], max_length=1024)
    profile = adapter._scoped_encoder().profile_identity(tokenizer, d_model=64,
        seed=101, projection_sha256="b" * 64)
    with pytest.raises(ValueError, match="EXACT_TRAINING_ONLY"):
        adapter.bind_course(prepared, tokenizer=tokenizer, ordered_profile=profile,
                            model_context=identity["model_context"])


def test_scope_sorting_collision_is_retained_as_an_open_execution_gate(prepared, identity):
    public = deepcopy(next(row["public"] for row in prepared["presentations"]
                           if row["operation"] == "FACE_APPLY"))
    lines = public["problem"].splitlines()
    runs = []
    start = None
    for i, line in enumerate(lines + ["end"]):
        if adapter._structural(line):
            start = i if start is None else start
        elif start is not None:
            runs.append((start, i))
            start = None
    assert len(runs) >= 2
    (a, b), (c, d) = runs[0], runs[-1]
    changed = deepcopy(public)
    changed["problem"] = "\n".join(lines[:a] + lines[c:d] + lines[b:c] + lines[a:b] + lines[d:]) + "\n"
    assert changed["problem"] != public["problem"]
    tokenizer = identity["tokenizer"]
    assert adapter.ordered_encoder.compile_frames(changed, tokenizer) == (
        adapter.ordered_encoder.compile_frames(public, tokenizer))
    assert adapter._scoped_encoder().compile_frames(changed, tokenizer) != (
        adapter._scoped_encoder().compile_frames(public, tokenizer))
    assert prepared["readiness"]["support_query_scope_binding_verified"] is False
    assert prepared["readiness"]["status"] == "NOT_YET_EXECUTION_ADMITTED"


def test_legacy_unscoped_profile_cannot_bind_full_course(prepared, identity):
    legacy = adapter.ordered_encoder.profile_identity(identity["tokenizer"], d_model=64,
        seed=101, projection_sha256="b" * 64)
    with pytest.raises(ValueError, match="SCOPED_PROFILE_REQUIRED"):
        adapter.bind_course(prepared, **{**identity, "ordered_profile": legacy})
