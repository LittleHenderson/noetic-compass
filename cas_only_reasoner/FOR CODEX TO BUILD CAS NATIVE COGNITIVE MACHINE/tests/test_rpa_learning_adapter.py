"""Source-bound learner preparation; every test is pure Python."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(RESEARCH))
try:
    from cncm import rpa_learning_adapter as adapter
    from cncm import rpa_cube_adapter as cube
    from cncm.canonical import canonical_json, digest
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching import ordered_encoder
finally:
    sys.path.remove(str(RESEARCH))

DENIED = {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt", "casformer"}
BUNDLE_DIGEST = "b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16"
CONTEXT = {"model_id": "candidate-pure-fixture", "checkpoint_sha256": "a" * 64}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED_IMPORT:" + fullname)


@pytest.fixture(autouse=True)
def deny_imports():
    finder = Deny()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)


def document_for(bundle, view="view_context", namespace="actual_source_fixture", raw=None):
    raw = canonical_json(bundle).encode() if raw is None else raw
    return cube.cube_atlas_from_bytes(raw, expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=cube.cube_node.bundle_digest(bundle), source_namespace=namespace,
        observation_id="supplied_fixture_read", observation_time="fixture-not-a-clock-claim",
        record_version=1, view_id=view)


@pytest.fixture(scope="module")
def bundle():
    raw = cube.cube_node.pinned_bundle_path().read_bytes()
    value = json.loads(raw)
    assert cube.cube_node.bundle_digest(value) == BUNDLE_DIGEST
    return value


@pytest.fixture(scope="module")
def document(bundle):
    return document_for(bundle, raw=cube.cube_node.pinned_bundle_path().read_bytes())


def prepare(document, case=None, assistance="unassisted"):
    case = case or {"op": "LIST_PARTS", "question": {"idea": "Bicycle"}}
    return adapter.prepare_public_lesson(document, operation=case["op"],
        question=case["question"], assistance=assistance)


@pytest.fixture(scope="module")
def prepared(document):
    return prepare(document)


def identities(publics):
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=1024)
    profile = ordered_encoder.profile_identity(tokenizer, d_model=64, seed=20260916,
                                                projection_sha256="b" * 64)
    return {"tokenizer": tokenizer, "ordered_profile": profile, "model_context": deepcopy(CONTEXT)}


@pytest.fixture(scope="module")
def identity(prepared):
    return identities([prepared["public"]])


@pytest.fixture(scope="module")
def lesson(document, prepared, identity):
    return adapter.bind_prepared_lesson(prepared, document=document, **identity)


def test_prepare_uses_actual_graph_and_preserves_ordered_choices(bundle, document, prepared):
    legacy = cube.compile_atlas_lesson(document, bundle=bundle,
        expected_bundle_digest=BUNDLE_DIGEST, operation="LIST_PARTS",
        question={"idea": "Bicycle"}, assistance="unassisted")
    assert prepared["public"]["problem"].startswith(
        cube.cube_node.containment_graph(bundle).render())
    assert prepared["public"]["observations"] == legacy["learner_input"]["public"]["observations"]
    assert prepared["encoded_options"] == legacy["learner_input"]["encoded_options"]
    assert prepared["source_binding"]["source_file_sha256"] == sha256(
        cube.cube_node.pinned_bundle_path().read_bytes()).hexdigest()
    assert "record_id" not in prepared
    assert "ordered_profile" not in prepared


def test_bound_public_private_and_supplied_identity_boundaries(lesson, identity, document):
    packet = adapter.prediction_packet(lesson, **identity)
    assert set(packet) == {"record_id", "public", "encoded_options"}
    teacher = adapter.check_source_target(lesson, document=document, **identity)
    assert packet["encoded_options"][teacher["encoded_correct_index"]] == teacher["expected_answer"]
    binding = lesson["binding"]
    for name in ("worker_observed", "projection_bytes_verified", "checkpoint_bytes_verified",
                 "cached_vectors_verified"):
        assert binding[name] is False
    for name in ("numeric_encoder_calls", "neural_calls", "optimizer_updates"):
        assert binding[name] == 0
    assert binding["checkpoint_context_scope"] == adapter.CHECKPOINT_SCOPE
    assert binding["tokenization"]["text_round_trip"] is True
    assert binding["tokenization"]["structural_frame_count"] == 11
    assert binding["identity_evidence"] == adapter.IDENTITY_EVIDENCE


def test_all_306_actual_source_combinations(bundle):
    rows = []
    for view in ("view_context", "view_formal", "view_analogy"):
        doc = document_for(bundle, view)
        before = doc.to_dict()
        cases = cube.cube_node.answer_cases(bundle, view)["cases"]
        assert len(cases) == 51
        for case in cases:
            for assistance in ("guided", "unassisted"):
                p = prepare(doc, case, assistance)
                legacy = cube.compile_atlas_lesson(doc, bundle=bundle,
                    expected_bundle_digest=BUNDLE_DIGEST, operation=case["op"],
                    question=case["question"], assistance=assistance)
                assert p["encoded_options"] == legacy["learner_input"]["encoded_options"]
                assert p["public"]["observations"] == legacy["learner_input"]["public"]["observations"]
                assert p["teacher_sidecar"]["expected_answer"] == case["correct"]
                rows.append((doc, p, case))
        assert doc.to_dict() == before
    # All rows are explicitly public engineering training fixtures, not a
    # held-out panel; fitting here makes no contamination/transfer claim.
    context = identities([p["public"] for _, p, _ in rows])
    for doc, p, case in rows:
        bound = adapter.bind_prepared_lesson(p, document=doc, **context)
        packet = adapter.validate_prediction_packet(bound["learner_input"], **context)
        target = adapter.check_source_target(bound, document=doc, **context)
        assert target["expected_answer"] == case["correct"]
        assert packet["encoded_options"][target["encoded_correct_index"]] == case["correct"]
    assert len(rows) == 306


def test_training_projection_matches_exact_registry(lesson, document, identity):
    record = adapter.training_record(lesson, document=document, **identity)
    teacher = adapter.check_source_target(lesson, document=document, **identity)
    packet = adapter.prediction_packet(lesson, **identity)
    assert record["record_id"] == packet["record_id"]
    assert record["options"] == packet["encoded_options"]
    assert record["correct"] == teacher["expected_answer"]
    assert record["framings"] == {"cas": packet["public"]["problem"],
                                   "generic": packet["public"]["problem"]}
    assert record["question"] == {"op": "LIST_PARTS", "idea": "Bicycle"}


def test_public_validation_never_calls_teacher_or_source(lesson, identity, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("TEACHER_OR_SOURCE_CALLED_FROM_PUBLIC_PATH")
    for obj, name in ((cube, "compile_atlas_lesson"), (cube, "_revalidate_document"),
                      (cube.cube_profile, "derived_answer"),
                      (adapter, "prepare_public_lesson"), (adapter, "check_source_target")):
        monkeypatch.setattr(obj, name, forbidden)
    assert adapter.prediction_packet(lesson, **identity) == lesson["learner_input"]
    assert adapter.validate_prediction_packet(lesson["learner_input"], **identity) == lesson["learner_input"]


@pytest.mark.parametrize("mode", ["change", "remove", "opaque"])
def test_private_teacher_cannot_change_inference(lesson, identity, document, mode):
    changed = deepcopy(lesson)
    if mode == "change":
        changed["teacher_sidecar"]["expected_answer"] = ["invented"]
    elif mode == "remove":
        changed["teacher_sidecar"].pop("expected_answer")
    else:
        changed["teacher_sidecar"] = {"private_untrusted": "ignored for inference"}
    assert adapter.prediction_packet(changed, **identity) == lesson["learner_input"]
    with pytest.raises(ValueError):
        adapter.check_source_target(changed, document=document, **identity)


@pytest.mark.parametrize("area", ["public", "options", "teacher", "provenance", "extra"])
def test_prepared_tampering_refused(prepared, identity, document, area):
    bad = deepcopy(prepared)
    if area == "public":
        bad["public"]["problem"] += "answer Bicycle\n"
    elif area == "options":
        bad["encoded_options"][0] = bad["encoded_options"][1]
    elif area == "teacher":
        bad["teacher_sidecar"]["expected_answer"] = ["invented"]
    elif area == "provenance":
        bad["source_binding"]["source_namespace"] = "other_source"
    else:
        bad["expected_answer"] = "private extra"
    with pytest.raises(ValueError):
        adapter.bind_prepared_lesson(bad, document=document, **identity)


@pytest.mark.parametrize("name", ["correct", "encoded_correct_index", "reference", "op", "expected_answer"])
def test_prediction_packet_has_closed_allowlist(lesson, identity, name):
    bad = deepcopy(lesson["learner_input"])
    bad[name] = 0
    with pytest.raises(ValueError):
        adapter.validate_prediction_packet(bad, **identity)


@pytest.mark.parametrize("mode", ["question", "choice_order", "slot_alias", "integer_zero", "tag",
                                   "nested_answer", "extra_line", "duplicate_node"])
def test_public_tampering_rejected(lesson, identity, mode):
    bad = deepcopy(lesson["learner_input"])
    if mode == "question":
        bad["public"]["problem"] = bad["public"]["problem"].replace("LIST_PARTS(Bicycle)", "LIST_PARTS(Cart)")
    elif mode == "choice_order":
        bad["encoded_options"].reverse()
        for i, row in enumerate(bad["public"]["observations"]):
            row["tag"] = str(bad["encoded_options"][i])
    elif mode == "slot_alias":
        bad["public"]["observations"][0]["slot"] = False
    elif mode == "integer_zero":
        bad["public"]["observations"][0]["values"][0] = 0
    elif mode == "tag":
        bad["public"]["observations"][0]["tag"] = "wrong"
    elif mode == "nested_answer":
        bad["public"]["observations"][0]["correct"] = True
    elif mode == "extra_line":
        bad["public"]["problem"] += "rel Bicycle --contains--> Cart\n"
    else:
        bad["public"]["problem"] = "node Bicycle kind=idea\n" + bad["public"]["problem"]
    with pytest.raises(ValueError):
        adapter.validate_prediction_packet(bad, **identity)


@pytest.mark.parametrize("key,value", [("d_model", True), ("d_model", 64.0),
    ("max_length", 1024.0), ("legacy_checkpoint_compatible", 0),
    ("projection_sha256", "bad"), ("tokenizer_sha256", "0" * 64),
    ("identity_sha256", "0" * 64), ("algorithm", "unregistered")])
def test_profile_strict_reconstruction(lesson, identity, key, value):
    changed = deepcopy(identity)
    changed["ordered_profile"][key] = value
    with pytest.raises(ValueError):
        adapter.validate_prediction_packet(lesson["learner_input"], **changed)


@pytest.mark.parametrize("kind", ["model", "checkpoint", "dimension", "seed"])
def test_valid_changed_context_cannot_reuse_old_input_id(lesson, identity, kind):
    changed = deepcopy(identity)
    if kind == "model":
        changed["model_context"]["model_id"] = "other"
    elif kind == "checkpoint":
        changed["model_context"]["checkpoint_sha256"] = "c" * 64
    else:
        profile = identity["ordered_profile"]
        changed["ordered_profile"] = ordered_encoder.profile_identity(identity["tokenizer"],
            d_model=32 if kind == "dimension" else profile["d_model"],
            seed=77 if kind == "seed" else profile["permutation_seed"],
            projection_sha256=profile["projection_sha256"])
    with pytest.raises(ValueError, match="stale"):
        adapter.validate_prediction_packet(lesson["learner_input"], **changed)


def test_tokenizer_subclass_and_bad_wire_refused(lesson, identity):
    class Untrusted(LosslessPublicTokenizer):
        def check_round_trip(self, public):
            return True
    t = identity["tokenizer"]
    unsafe = Untrusted(t.vocabulary, t.fitted_public_sha256, t.fitted_examples, t.max_length)
    with pytest.raises(ValueError, match="exact immutable"):
        adapter.validate_prediction_packet(lesson["learner_input"], **{**identity, "tokenizer": unsafe})
    unsafe = deepcopy(t)
    object.__setattr__(unsafe, "fitted_examples", True)
    with pytest.raises(ValueError):
        adapter.validate_prediction_packet(lesson["learner_input"], **{**identity, "tokenizer": unsafe})


def test_changed_profile_produces_fresh_identity(prepared, lesson, document, identity):
    context = {**identity, "model_context": {"model_id": "next_run", "checkpoint_sha256": "d" * 64}}
    changed = adapter.bind_prepared_lesson(prepared, document=document, **context)
    assert changed["learner_input"]["record_id"] != lesson["learner_input"]["record_id"]
    assert changed["learner_input"]["public"] == lesson["learner_input"]["public"]


def test_copy_isolation(prepared, lesson, document, identity):
    before = deepcopy(lesson)
    packet = adapter.prediction_packet(lesson, **identity)
    packet["public"]["observations"][0]["tag"] = "changed"
    target = adapter.check_source_target(lesson, document=document, **identity)
    target["expected_answer"] = ["changed"]
    record = adapter.training_record(lesson, document=document, **identity)
    record["graph"]["nodes"].clear()
    assert lesson == before
    bound = adapter.bind_prepared_lesson(prepared, document=document, **identity)
    bound["binding"]["ordered_profile"]["d_model"] = 2
    assert identity["ordered_profile"]["d_model"] == 64


def test_focus_and_hypothesis_do_not_change_preparation(document, prepared, bundle, identity):
    focused = document.focus(document.atlas.nodes[-1].node_id)
    assert prepare(focused) == prepared
    hypothesis = document_for(bundle, namespace="explicit_hypothesis")
    extended = document.with_hypothesis(hypothesis)
    assert prepare(extended) == prepared
    assert adapter.bind_prepared_lesson(prepared, document=extended, **identity)["learner_input"] == (
        adapter.bind_prepared_lesson(prepared, document=document, **identity)["learner_input"])


@pytest.mark.parametrize("injection", ["newline", "field", "reserved", "too_long"])
def test_ambiguous_source_labels_refused(bundle, injection):
    replacement = {"newline": "Bicycle\nnode Forged kind=idea", "field": "Bicycle kind=other",
                   "reserved": "none", "too_long": "B" * 129}[injection]
    def rewrite(value):
        if type(value) is str:
            return replacement if value == "Bicycle" else value
        if type(value) is list:
            return [rewrite(x) for x in value]
        if type(value) is dict:
            return {key: rewrite(x) for key, x in value.items()}
        return value
    changed = rewrite(bundle)
    doc = document_for(changed)
    with pytest.raises(ValueError):
        adapter.prepare_public_lesson(doc, operation="LIST_PARTS", question={"idea": replacement})


def test_faulty_graph_render_refused(document, monkeypatch):
    graph_type = type(cube.cube_node.containment_graph(document.catalog["bundle"]))
    original = graph_type.render
    def omit_edge(graph):
        lines = original(graph).splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith("rel "))
        return "\n".join(lines[:index] + lines[index + 1:]) + "\n"
    monkeypatch.setattr(graph_type, "render", omit_edge)
    with pytest.raises(ValueError, match="rendering"):
        prepare(document)


@pytest.mark.parametrize("mode", ["answer", "index_alias", "foreign_request", "foreign_source"])
def test_compiler_teacher_receiver_is_checked(document, monkeypatch, mode):
    original = cube.compile_atlas_lesson
    def corrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        teacher = result["teacher_sidecar"]
        if mode == "answer":
            index = (teacher["encoded_correct_index"] + 1) % 3
            teacher["encoded_correct_index"] = index
            teacher["expected_answer"] = deepcopy(result["learner_input"]["encoded_options"][index])
        elif mode == "index_alias":
            teacher["encoded_correct_index"] = float(teacher["encoded_correct_index"])
        elif mode == "foreign_request":
            teacher["question"] = {"idea": "Cart"}
        else:
            teacher["source_bundle_digest"] = "0" * 64
        return result
    monkeypatch.setattr(cube, "compile_atlas_lesson", corrupt)
    with pytest.raises(ValueError, match="teacher receipt"):
        prepare(document)


def test_1024_token_limit_fails_without_truncation(lesson, identity):
    public = deepcopy(lesson["learner_input"]["public"])
    # Allowed, single-line graph names can still exceed actual byte-token bounds.
    labels = ["N" + ("a" * 110) + str(i) for i in range(50)]
    public["problem"] = "\n".join("node %s kind=idea" % name for name in labels)
    public["problem"] += "\n%s\nLIST_PARTS(%s): what does it directly contain?\n%s\n" % (
        adapter.INVENTORY_DECLARATION, labels[0], "Choose one of the three supplied options.")
    options = [[], [labels[0]], [labels[1]]]
    public["observations"] = [{"slot": i, "tag": str(value), "values": [0.0] * 8}
                              for i, value in enumerate(options)]
    packet = {"record_id": adapter._public_id(public, options,
        identity["ordered_profile"], identity["model_context"]), "public": public,
        "encoded_options": options}
    assert len(public["problem"]) < 8192
    with pytest.raises(ValueError, match="PUBLIC_INPUT_TOO_LONG"):
        adapter.validate_prediction_packet(packet, **identity)


def test_fresh_process_import_denies_neural_provider():
    code = """import importlib.abc, sys
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','numpy','cas_cjt','casformer','boto3','botocore','requests'}:
            raise AssertionError('FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Deny())
sys.path.insert(0,sys.argv[1])
from cncm import rpa_learning_adapter
assert not any(name.split('.')[0] in {'torch','numpy','cas_cjt','casformer','boto3','requests'} for name in sys.modules)
print('PURE_IMPORT_PASS')
"""
    result = subprocess.run([sys.executable, "-B", "-c", code, str(RESEARCH)],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "PURE_IMPORT_PASS"
