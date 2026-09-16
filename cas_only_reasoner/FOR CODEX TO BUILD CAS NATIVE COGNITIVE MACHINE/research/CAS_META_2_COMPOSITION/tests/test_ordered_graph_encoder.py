"""Pure contract regressions: no torch import, model, or numerical execution."""
from collections import Counter
from copy import deepcopy
import builtins
import importlib
import inspect

import pytest

from cas_meta2.codec import PolicyContractError
from cas_meta2.features_v2 import BYTE_START, WORD_START, LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder as ordered


def public(edge="A --contains--> B", query="REACHED_VIA(part=A, idea=B)"):
    return {"problem": "Graph\nnode A value=alpha\nnode B value=beta\n"
            "node C value=gamma\nrel " + edge + "\nRequest " + query,
            "observations": [{"slot": index, "tag": text, "values": [0.0] * 8}
                             for index, text in enumerate(("direct", "absent", "via:C"))]}


@pytest.fixture
def tokenizer():
    return LosslessPublicTokenizer.fit_train([public()], max_length=1024)


def terms(frame):
    return ordered.linear_binding_terms(frame, d_model=64, seed=20260916)


def changed_frame(left, right, tokenizer, kind):
    a = [frame for frame in ordered.compile_frames(left, tokenizer) if frame.kind == kind]
    b = [frame for frame in ordered.compile_frames(right, tokenizer) if frame.kind == kind]
    pairs = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(pairs) == 1
    return pairs[0]


def test_directed_edge_swap_no_longer_has_forced_multiset_symmetry(tokenizer):
    a, b = changed_frame(public(), public(edge="B --contains--> A"), tokenizer, "rel")
    assert Counter(a.token_ids) == Counter(b.token_ids)
    assert terms(a) != terms(b)


def test_query_role_swap_no_longer_has_forced_multiset_symmetry(tokenizer):
    a, b = changed_frame(public(), public(query="REACHED_VIA(part=B, idea=A)"),
                         tokenizer, "framing")
    assert Counter(a.token_ids) == Counter(b.token_ids)
    assert terms(a) != terms(b)


def test_unseen_anagrams_retain_byte_position(tokenizer):
    a, b = changed_frame(public(query="unseen_zqx"), public(query="unseen_xqz"),
                         tokenizer, "framing")
    assert Counter(a.token_ids) == Counter(b.token_ids)
    assert any(BYTE_START <= value < WORD_START for value in a.token_ids)
    assert terms(a) != terms(b)


def test_structural_order_has_same_frames_and_aggregation_order(tokenizer):
    a = public()
    lines = a["problem"].split("\n")
    b = deepcopy(a)
    b["problem"] = "\n".join([lines[0], *reversed(lines[1:-1]), lines[-1]])
    assert ordered.compile_frames(a, tokenizer) == ordered.compile_frames(b, tokenizer)


def test_framing_line_order_is_bound(tokenizer):
    a = public()
    a["problem"] += "\nContext alpha\nContext beta"
    b = deepcopy(a)
    b["problem"] = b["problem"].replace("Context alpha\nContext beta",
                                        "Context beta\nContext alpha")
    frames_a = ordered.compile_frames(a, tokenizer)
    frames_b = ordered.compile_frames(b, tokenizer)
    assert frames_a != frames_b
    assert tuple(terms(f) for f in frames_a) != tuple(terms(f) for f in frames_b)


def test_structural_duplicates_are_not_discarded(tokenizer):
    a = public()
    a["problem"] += "\nrel A --contains--> B"
    assert len([f for f in ordered.compile_frames(a, tokenizer) if f.kind == "rel"]) == 2


def test_permutations_are_bijective_signed_and_not_periodic_rolls():
    permutations = []
    for position in (0, 1, 63, 64, 65, 1023):
        order, signs = ordered.signed_permutation(seed=20260916, kind="rel", ordinal=0,
                                                 position=position, d_model=64)
        assert sorted(order) == list(range(64))
        assert set(signs) == {-1, 1}
        assert len({(source - target) % 64 for target, source in enumerate(order)}) > 1
        permutations.append((order, signs))
    assert len(set(permutations)) == len(permutations)


@pytest.mark.parametrize("change", ["target", "expected", "record_id", "graph", "answer"])
def test_private_input_fields_fail_closed(tokenizer, change):
    task = public()
    task[change] = "never admissible"
    with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):
        ordered.compile_frames(task, tokenizer)


def test_observation_targets_fail_closed(tokenizer):
    task = public()
    task["observations"][0]["correct"] = True
    with pytest.raises(PolicyContractError, match="PUBLIC_OBSERVATION_FIELDS_INVALID"):
        ordered.compile_frames(task, tokenizer)


def test_options_are_validated_but_not_used_for_problem_binding(tokenizer):
    a = public()
    b = deepcopy(a)
    b["observations"][0]["tag"] = "different public option"
    b["observations"][1]["values"] = [13.0] * 8
    assert ordered.compile_frames(a, tokenizer) == ordered.compile_frames(b, tokenizer)


@pytest.mark.parametrize("problem", ["", "only a request", "node A\n" + "X" * 8192])
def test_malformed_or_oversize_input_fails(tokenizer, problem):
    task = public()
    task["problem"] = problem
    with pytest.raises(PolicyContractError):
        ordered.compile_frames(task, tokenizer)


def test_tokenizer_overflow_is_not_silently_truncated(tokenizer):
    task = public()
    task["problem"] += "\n" + "zzqx " * 500
    with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_TOO_LONG"):
        ordered.compile_frames(task, tokenizer)


def test_new_identity_rejects_legacy_and_different_encoder_checkpoints(tokenizer):
    profile = ordered.profile_identity(tokenizer, d_model=64, seed=20260916,
                                       projection_sha256="a" * 64)
    assert profile["legacy_checkpoint_compatible"] is False
    assert ordered.validate_checkpoint_identity({"encoder_identity": profile}, profile)
    for old in ({}, {"encoder_identity": {"profile_id": "legacy"}},
                {"encoder_identity": {**profile, "permutation_seed": 0}}):
        with pytest.raises(PolicyContractError, match="CHECKPOINT_IDENTITY_MISMATCH"):
            ordered.validate_checkpoint_identity(old, profile)
    other = ordered.profile_identity(tokenizer, d_model=64, seed=20260916,
                                     projection_sha256="b" * 64)
    assert other["identity_sha256"] != profile["identity_sha256"]
    with pytest.raises(PolicyContractError, match="CHECKPOINT_IDENTITY_MISMATCH"):
        ordered.validate_checkpoint_identity({"encoder_identity": profile}, other)


def test_tampered_expected_identity_is_rejected(tokenizer):
    profile = ordered.profile_identity(tokenizer, d_model=64, seed=20260916,
                                       projection_sha256="a" * 64)
    profile["permutation_seed"] = 0
    with pytest.raises(PolicyContractError, match="EXPECTED_PROFILE_DIGEST_INVALID"):
        ordered.validate_checkpoint_identity({"encoder_identity": profile}, profile)


def test_incomplete_expected_profile_is_not_a_checkpoint_contract():
    profile = {"profile_id": ordered.PROFILE_ID}
    with pytest.raises(PolicyContractError, match="EXPECTED_PROFILE_INVALID"):
        ordered.validate_checkpoint_identity({"encoder_identity": profile}, profile)


def test_cpu_adapter_rejects_before_touching_torch():
    class ForbiddenTorch:
        def __getattr__(self, name):
            raise AssertionError("Torch must not be touched for CPU device")
    with pytest.raises(PolicyContractError, match="REQUIRES_CUDA"):
        ordered.build_ordered_encoder(ForbiddenTorch(), {}, device="cpu")


def test_unavailable_cuda_rejects_before_tensor_operations():
    class UnavailableCuda:
        @staticmethod
        def is_available():
            return False
    class NoTensorTorch:
        cuda = UnavailableCuda()
        def __getattr__(self, name):
            raise AssertionError("No tensor operations are permitted")
    with pytest.raises(PolicyContractError, match="CUDA_UNAVAILABLE"):
        ordered.build_ordered_encoder(NoTensorTorch(), {}, device="cuda")


def test_import_and_pure_framing_need_no_tensor_or_answer_module(monkeypatch, tokenizer):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "casformer", "cas_cjt"} or "reference" in name:
            raise AssertionError("Forbidden import: " + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    importlib.reload(ordered)
    assert ordered.compile_frames(public(), tokenizer)
    assert "public" in inspect.signature(ordered.compile_frames).parameters
