"""Pure scope-binding regressions; no tensor, provider or model execution."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import builtins
import inspect
from pathlib import Path
import subprocess
import sys

import pytest

from cas_meta2.codec import PolicyContractError
from cas_meta2.features_v2 import CLS_ID, LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder as old
from cas_meta2.graph_teaching import scoped_ordered_encoder as scoped

DENIED = {"torch", "numpy", "tensorflow", "jax", "jaxlib", "cas_cjt", "casformer",
          "boto3", "botocore", "transformers", "openai", "anthropic", "requests", "httpx"}


@pytest.fixture(autouse=True)
def no_numerical_or_provider_imports(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED:
            raise AssertionError("FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


def public(problem):
    return {"problem": problem, "observations": [
        {"slot": i, "tag": tag, "values": [0.0] * 8}
        for i, tag in enumerate(("direct", "absent", "via:C"))]}


def pair():
    nodes = "node A value=alpha\nnode B value=beta\nnode C value=gamma\n"
    prefix = "Support context:\n" + nodes
    middle = "\nCurrent task context:\n" + nodes
    query = "\nUse the current graph.\nRequest REACHED_VIA(part=A, idea=B)"
    return (public(prefix + "rel A --contains--> B" + middle + "rel A --contains--> C" + query),
            public(prefix + "rel A --contains--> C" + middle + "rel A --contains--> B" + query))


@pytest.fixture
def tokenizer():
    return LosslessPublicTokenizer.fit_train([pair()[0]], max_length=1024)


def aggregate_map(module, frames):
    # Exact integer aggregate before scaling/normalization; no projection rows.
    result = Counter()
    for frame in frames:
        for destination, row in enumerate(module.linear_binding_terms(frame, d_model=32, seed=20260916)):
            for token, source, count in row:
                result[destination, token, source] += count
    return {key: value for key, value in result.items() if value}


def test_old_baseline_bytes_are_untouched():
    assert sha256(Path(old.__file__).read_bytes()).hexdigest() == (
        "670fb5acc42a9aa13fd7b1ff3d91bdd1ded38399833095293bec572313bc1bc4")


def test_cross_scope_swap_has_different_frames_and_exact_linear_maps(tokenizer):
    left, right = pair()
    old_left, old_right = [old.compile_frames(x, tokenizer) for x in (left, right)]
    assert old_left == old_right
    assert len(old_left) == 13
    assert sum(f.kind != "framing" for f in old_left) == 8
    assert aggregate_map(old, old_left) == aggregate_map(old, old_right)
    a, b = [scoped.compile_frames(x, tokenizer) for x in (left, right)]
    assert a != b
    # Same bag, same nonstructural text; only the assignment to scopes changed.
    assert Counter((f.kind, f.token_ids) for f in a) == Counter((f.kind, f.token_ids) for f in b)
    assert [f for f in a if f.kind == "framing"] == [f for f in b if f.kind == "framing"]
    assert aggregate_map(scoped, a) != aggregate_map(scoped, b)
    for anchor in (1, 2):
        ar = next(f for f in a if f.kind == "rel" and f.scope_anchor == anchor)
        br = next(f for f in b if f.kind == "rel" and f.scope_anchor == anchor)
        assert scoped.linear_binding_terms(ar, d_model=32, seed=7) != (
            scoped.linear_binding_terms(br, d_model=32, seed=7))
    # These integer-map facts do not assert all projected numeric outputs differ.


def test_same_scope_reorder_is_exactly_invariant(tokenizer):
    left = pair()[0]
    lines = left["problem"].split("\n")
    right = deepcopy(left)
    right["problem"] = "\n".join([lines[0], *reversed(lines[1:5]), lines[5],
                                     *reversed(lines[6:10]), *lines[10:]])
    a, b = [scoped.compile_frames(x, tokenizer) for x in (left, right)]
    assert a == b
    assert aggregate_map(scoped, a) == aggregate_map(scoped, b)
    structural = [f for f in a if f.kind != "framing"]
    assert structural == sorted(structural, key=lambda f: (f.scope_anchor, f.kind, f.token_ids))


def test_initial_scope_empty_lines_whitespace_and_duplicate_headers(tokenizer):
    task = public("node A\n\nrel A --contains--> B\nContext:\nnode B\n \nnode C\nContext:\nnode D\nnode D")
    frames = scoped.compile_frames(task, tokenizer)
    structural = [f for f in frames if f.kind != "framing"]
    assert [f.scope_anchor for f in structural] == [0, 0, 1, 2, 3, 3]
    framing = [f for f in frames if f.kind == "framing"]
    assert framing[0] == scoped.TokenFrame("framing", 0, (CLS_ID,), 0)
    assert [f.ordinal for f in framing] == [0, 1, 2, 3]
    assert [f.scope_anchor for f in framing] == [0, 1, 2, 3]
    assert [tokenizer.decode_text(f.token_ids) for f in framing[1:]] == ["Context:", " ", "Context:"]
    assert structural[-1] == structural[-2]  # Duplicates retained, not collapsed.


def test_nonstructural_order_and_exact_text_are_preserved(tokenizer):
    left = public("Context alpha\nContext beta\nnode A\nRequest R(x=A)")
    right = public("Context beta\nContext alpha\nnode A\nRequest R(x=A)")
    a, b = [scoped.compile_frames(x, tokenizer) for x in (left, right)]
    assert a != b and aggregate_map(scoped, a) != aggregate_map(scoped, b)
    weird = public("  node A\nNODE B\nrelax C\n\tContext é\nnode Z")
    frames = scoped.compile_frames(weird, tokenizer)
    assert [(f.kind, f.scope_anchor) for f in frames[:2]] == [("node", 0), ("node", 3)]
    assert [tokenizer.decode_text(f.token_ids) for f in frames[3:]] == ["NODE B", "relax C", "\tContext é"]


def test_scope_enters_each_permutation_hash_domain(monkeypatch):
    calls = []
    digest = scoped._digest
    def observe(value):
        calls.append(value)
        return digest(value)
    scoped._signed_permutation.cache_clear()
    monkeypatch.setattr(scoped, "_digest", observe)
    first = scoped.signed_permutation(seed=17, kind="rel", scope_anchor=2, ordinal=0, position=9, d_model=32)
    assert len(calls) == 64
    assert all(x[:7] == [scoped.ALGORITHM, 17, "rel", 2, 0, 9, 32] for x in calls)
    second = scoped.signed_permutation(seed=17, kind="rel", scope_anchor=3, ordinal=0, position=9, d_model=32)
    assert first != second
    assert sorted(first[0]) == list(range(32)) and set(first[1]) == {-1, 1}


@pytest.mark.parametrize("field,value", [("seed", True), ("seed", -1), ("seed", 2**63),
    ("scope_anchor", True), ("scope_anchor", 1.0), ("scope_anchor", -1), ("scope_anchor", 65537),
    ("ordinal", True), ("ordinal", 1), ("position", -1), ("position", 65536),
    ("d_model", True), ("d_model", 2.0), ("d_model", 1), ("d_model", 4097), ("kind", "unknown")])
def test_coordinate_bounds_and_cached_scalar_aliases_fail(field, value):
    args = dict(seed=1, kind="rel", scope_anchor=1, ordinal=0, position=0, d_model=2)
    scoped.signed_permutation(**args)  # Populate cache before alias attempts.
    args[field] = value
    with pytest.raises(PolicyContractError):
        scoped.signed_permutation(**args)


@pytest.mark.parametrize("changes", [{"token_ids": []}, {"token_ids": ()}, {"token_ids": (True,)},
    {"token_ids": (1.0,)}, {"token_ids": (-1,)}, {"scope_anchor": 2}, {"ordinal": 2}])
def test_frame_constructor_is_closed_and_typed(changes):
    values = dict(kind="framing", ordinal=1, token_ids=(1,), scope_anchor=1)
    values.update(changes)
    with pytest.raises(PolicyContractError):
        scoped.TokenFrame(**values)


def test_options_unchanged_and_private_nonfinite_inputs_refused(tokenizer):
    task = pair()[0]
    changed = deepcopy(task)
    changed["observations"][0] = {"slot": 0, "tag": "new choice", "values": [13.0] * 8}
    assert scoped.compile_frames(task, tokenizer) == scoped.compile_frames(changed, tokenizer)
    for field in ("target", "expected", "record_id", "answer", "graph"):
        with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):
            scoped.compile_frames({**task, field: "private"}, tokenizer)
    for value in (float("nan"), float("inf"), -float("inf"), True):
        changed["observations"][0]["values"][0] = value
        with pytest.raises(PolicyContractError, match="PUBLIC_VALUES_INVALID"):
            scoped.compile_frames(changed, tokenizer)


def test_input_and_linewise_token_caps_and_missing_structure(tokenizer):
    for problem in ("", "only framing", "node A\n" + "x" * 8192):
        with pytest.raises(PolicyContractError):
            scoped.compile_frames(public(problem), tokenizer)
    with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_TOO_LONG"):
        scoped.compile_frames(public("node A\n" + "zqx " * 500), tokenizer)
    compressed = public("node A" + "\n " * 40 + "\nnode B")
    small = LosslessPublicTokenizer.fit_train([compressed], max_length=32)
    assert len(small.encode_public(compressed)["ids"]) <= 32
    with pytest.raises(PolicyContractError, match="ORDERED_FRAMED_INPUT_TOO_LONG"):
        scoped.compile_frames(compressed, small)


def profile(tokenizer):
    return scoped.profile_identity(tokenizer, d_model=32, seed=7, projection_sha256="a" * 64)


def test_profile_separate_from_old_and_exact_checkpoint_match(tokenizer):
    value = profile(tokenizer)
    assert set(value) == scoped._IDENTITY_FIELDS
    assert value["profile_id"] != old.PROFILE_ID and value["algorithm"] != old.ALGORITHM
    assert value["legacy_checkpoint_compatible"] is False
    assert value["option_path"] == "inherited unchanged"
    assert scoped.validate_checkpoint_identity({"encoder_identity": value}, value)
    legacy = old.profile_identity(tokenizer, d_model=32, seed=7, projection_sha256="a" * 64)
    for actual in ({}, legacy, {**value, "d_model": 32.0}, {**value, "permutation_seed": 7.0},
                   {**value, "legacy_checkpoint_compatible": 0}, {**value, "extra": "value"}):
        with pytest.raises(PolicyContractError, match="CHECKPOINT_IDENTITY_MISMATCH"):
            scoped.validate_checkpoint_identity({"encoder_identity": actual}, value)
    with pytest.raises(PolicyContractError):
        scoped.validate_checkpoint_identity({"encoder_identity": legacy}, legacy)
    other = scoped.profile_identity(tokenizer, d_model=32, seed=7, projection_sha256="b" * 64)
    with pytest.raises(PolicyContractError, match="CHECKPOINT_IDENTITY_MISMATCH"):
        scoped.validate_checkpoint_identity({"encoder_identity": value}, other)


@pytest.mark.parametrize("field,value", [("scope_binding", "ignore scope"),
    ("structural_order", "sort(kind, token_ids); duplicates retained"), ("option_path", "new options"),
    ("max_length", 15), ("max_length", 65537), ("max_length", 1024.0), ("permutation_seed", True),
    ("projection_sha256", "not a hash"), ("tokenizer_sha256", "A" * 64),
    ("legacy_checkpoint_compatible", 0), ("d_model", float("nan"))])
def test_resealed_invalid_profile_is_not_a_contract(tokenizer, field, value):
    changed = profile(tokenizer)
    changed[field] = value
    if not isinstance(value, float) or value == value:
        changed["identity_sha256"] = scoped._digest({k: v for k, v in changed.items() if k != "identity_sha256"})
    with pytest.raises(PolicyContractError):
        scoped.validate_checkpoint_identity({"encoder_identity": changed}, changed)


def test_missing_and_tampered_profile_refused(tokenizer):
    value = profile(tokenizer)
    del value["scope_binding"]
    with pytest.raises(PolicyContractError):
        scoped.validate_checkpoint_identity({"encoder_identity": value}, value)
    value = profile(tokenizer)
    value["permutation_seed"] = 0
    with pytest.raises(PolicyContractError, match="EXPECTED_PROFILE_DIGEST_INVALID"):
        scoped.validate_checkpoint_identity({"encoder_identity": value}, value)


def test_factory_refuses_cpu_or_unavailable_cuda_without_tensor_work():
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError("NO_TENSOR_OPERATION:" + name)
    for device in ("cpu", "mps", "cuda:-1", "cuda:0:1"):
        with pytest.raises(PolicyContractError, match="REQUIRES_CUDA"):
            scoped.build_scoped_ordered_encoder(Forbidden(), {}, device=device)
    class Unavailable(Forbidden):
        class cuda:
            @staticmethod
            def is_available():
                return False
    with pytest.raises(PolicyContractError, match="CUDA_UNAVAILABLE"):
        scoped.build_scoped_ordered_encoder(Unavailable(), {}, device="cuda")


@pytest.mark.parametrize("field,value", [("projection_frozen", False),
    ("projection_frozen", 1), ("embed", None), ("encode", None), ("tokenizer", None),
    ("d_model", True), ("ordered_profile", {})])
def test_factory_frozen_inheritance_refuses_before_embedding(tokenizer, field, value):
    def forbidden(*args, **kwargs):
        raise AssertionError("NO_EMBEDDING_OR_TENSOR_EXECUTION")
    class MetadataOnlyTorch:
        class cuda:
            @staticmethod
            def is_available():
                return True  # Synthetic capability flag; never calls real CUDA.
        @staticmethod
        def device(name):
            return name
        def __getattr__(self, name):
            return forbidden(name)
    inherited = dict(tokenizer=tokenizer, d_model=32, projection_frozen=True,
                     embed=forbidden, encode=forbidden)
    inherited[field] = value
    with pytest.raises(PolicyContractError):
        scoped.build_scoped_ordered_encoder(MetadataOnlyTorch(), inherited, device="cuda:0")


def test_coordinate_upper_bounds_are_explicit_without_allocating_projection():
    scoped._validate_coordinates(2**63 - 1, "rel", 65536, 0, 65535, 4096)
    scoped._validate_coordinates(0, "framing", 65536, 65536, 0, 2)
    with pytest.raises(PolicyContractError, match="SCOPE_ANCHOR_INVALID"):
        scoped._validate_coordinates(0, "framing", 0, 1, 0, 2)


def test_import_in_fresh_process_needs_no_numeric_provider_or_answer_module():
    research = Path(__file__).resolve().parents[1]
    script = """
import builtins, sys
deny = %r
original = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split('.')[0] in deny or 'reference' in name:
        raise AssertionError('FORBIDDEN_IMPORT:' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guard
from cas_meta2.graph_teaching import scoped_ordered_encoder as scoped
assert not deny.intersection(name.split('.')[0] for name in sys.modules)
print(scoped.PROFILE_ID)
""" % DENIED
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=research,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == scoped.PROFILE_ID
    source = inspect.getsource(scoped.build_scoped_ordered_encoder)
    assert '"encode":' not in source  # Option callable is inherited by dict expansion.
    assert 'scope_anchor=frame.scope_anchor' in source
