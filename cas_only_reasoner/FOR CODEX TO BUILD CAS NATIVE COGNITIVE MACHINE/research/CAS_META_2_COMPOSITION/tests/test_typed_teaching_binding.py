"""Pure complete-token binding checks; no numerical runtime or private teacher."""
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import struct
import sys

import pytest

from cas_meta2.typed_teaching import answers, binding, course, encoder, input_frames, slots, source, tokenization

DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def pure_only(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.endswith(".checker") or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_OR_COURSE_CONSTRUCTION")
    monkeypatch.setattr(builtins, "__import__", guarded)
    for name in ("compile_course", "prepare_course", "derive_targets_from_seal", "_worked_target"):
        monkeypatch.setattr(course, name, forbidden)
    monkeypatch.setattr(course.focal, "derive_roles", forbidden)
    monkeypatch.setattr(course.focal, "render_excerpt", forbidden)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


def packet_for(public):
    query = answers.compile_query(public, kind="context")
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
            "source_world_id": public["focus_world_id"], "query": query, "cue": "CUBE_FACE_2",
            "instruction": course.REQUESTS["context"], "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": []}
    for world in [w for w in public["worlds"] if w["world_id"] != public["focus_world_id"]][:3]:
        sq = answers.compile_query(public, kind="parts", arguments={"whole": world["declared_whole"]},
                                   focus_world_id=world["world_id"])
        # Wrong but syntactically valid support: the encoder must transport it,
        # never invoke a checker to filter or repair supplied teaching content.
        body["supports"].append({"query": sq, "cue": "CUBE_FACE_5", "instruction": course.REQUESTS["parts"],
            "worked_answer": answers.make_answer(public, sq, {"nodes": []}),
            "selection_rule": course.SEMANTIC_POLICY["support_example_selection"]})
    return {"source": deepcopy(public), "record": {"record_id": "typed-input-" + source.digest(body), **body}}


def reseal_packet(packet):
    row = packet["record"]
    row["record_id"] = "typed-input-" + source.digest({k: v for k, v in row.items() if k != "record_id"})
    return packet


def reseal_plan(plan):
    plan["plan_digest"] = binding._digest({k: v for k, v in plan.items() if k != "plan_digest"})
    return plan


@pytest.fixture(scope="module")
def prepared():
    families = source.training_families(expected_source_profile_digest=source.source_profile()["profile_digest"])
    bank = source.freeze_bank(families[:4])
    public = source.compile_source(families[0], bank=bank)["public"]
    packet = packet_for(public)
    course.validate_model_packet(packet)
    frame = input_frames.compile_packet(packet)
    tokenizer = tokenization.fit_train([frame], max_tokens=16384)
    return packet, frame, tokenizer, binding.compile_packet(packet, tokenizer, seed=101)


def test_complete_sequence_scopes_lf_and_markers(prepared):
    packet, frame, tokenizer, plan = prepared
    assert [t for row in plan["rows"] for t in row["token_ids"]] == tokenizer.encode_frame(frame)["ids"]
    assert plan["rows"][0]["token_ids"] == [0] and plan["rows"][-1]["token_ids"] == [1]
    assert [r["scope"] for r in plan["rows"] if r["scope"][0] == "WORLD"] == [["WORLD", "W%d" % i] for i in range(4)]
    assert [r["scope"] for r in plan["rows"] if r["scope"][0] == "SUPPORT"] == [["SUPPORT", "S%d" % i] for i in range(3)]
    assert {r["scope"][0] for r in plan["rows"]} == {"START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE", "WORLD", "RECORD", "QUERY", "SUPPORT", "END"}
    fragments = [line + ("\n" if at < len(frame["text"].split("\n")) - 1 else "")
                 for at, line in enumerate(frame["text"].split("\n"))]
    assert [tokenizer.decode_text(r["token_ids"]) for r in plan["rows"][1:-1]] == fragments
    cursor = 0
    for ordinal, row in enumerate(plan["rows"]):
        assert row["ordinal"] == ordinal and row["start"] == cursor and row["count"] == len(row["token_ids"])
        cursor += row["count"]
    assert input_frames.restore_packet(frame) == packet
    assert plan["packet_digest"] == source.digest(packet)
    assert plan["frame_digest"] == source.digest(frame)


def test_exact_serialization_and_reconstruction(prepared):
    packet, _, tokenizer, plan = prepared
    wire = json.loads(json.dumps(plan))
    assert binding.validate_plan(packet, tokenizer, wire) == plan
    wire["profile"]["numeric_acceptance"] = True
    assert plan["profile"]["numeric_acceptance"] is False
    with pytest.raises(ValueError, match="RECONSTRUCTION"):
        binding.validate_plan(packet, tokenizer, reseal_plan(wire))


def test_accepted_full_bank_frame_has_no_legacy_truncation():
    folder = Path(__file__).resolve().parents[3] / "records/typed_interface_001/checks_002"
    raw = (folder / "public_frames.jsonl").read_bytes()
    assert sha256(raw).hexdigest() == "c13fe9f64ae6e815ed1ac215e57057cd68bde7a207f450b5672dda778fb928e8"
    item = json.loads(raw.split(b"\n", 1)[0])
    tokenizer_raw = (folder / "training_tokenizer.json").read_bytes()
    assert sha256(tokenizer_raw).hexdigest() == "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c"
    tokenizer = tokenization.FrameTokenizer.from_dict(json.loads(tokenizer_raw))
    packet = input_frames.restore_packet(item["frame"])
    plan = binding.compile_packet(packet, tokenizer, seed=101)
    ids = [t for row in plan["rows"] for t in row["token_ids"]]
    assert len(ids) == 27576 and len(plan["rows"]) == 76
    assert ids == tokenizer.encode_frame(item["frame"])["ids"]
    assert len([r for r in plan["rows"] if r["scope"][0] == "WORLD"]) == 64
    assert len([r for r in plan["rows"] if r["scope"][0] == "SUPPORT"]) == 3
    assert max(r["count"] for r in plan["rows"]) == 6852
    assert all(r["count"] * 64 <= encoder.MAX_ROLE_ELEMENTS for r in plan["rows"])


@pytest.mark.parametrize("change", ("scope", "ordinal", "start", "count", "token", "drop", "duplicate", "float", "extra"))
def test_resealed_incomplete_or_wrong_binding_is_refused(prepared, change):
    packet, _, tokenizer, original = prepared
    plan = deepcopy(original); row = plan["rows"][2]
    if change == "scope": row["scope"] = ["QUERY"]
    elif change == "ordinal": row["ordinal"] += 1
    elif change == "start": row["start"] += 1
    elif change == "count": row["count"] -= 1
    elif change == "token": row["token_ids"][0] += 1
    elif change == "drop": del plan["rows"][2]
    elif change == "duplicate": plan["rows"].insert(2, deepcopy(row))
    elif change == "float": row["token_ids"][0] = float(row["token_ids"][0])
    else: plan["extra"] = None
    with pytest.raises(ValueError):
        binding.validate_plan(packet, tokenizer, reseal_plan(plan))


def test_support_swap_is_valid_content_and_changes_bound_sequence(prepared):
    packet, _, tokenizer, original = prepared
    swapped = deepcopy(packet)
    swapped["record"]["supports"][0], swapped["record"]["supports"][1] = swapped["record"]["supports"][1], swapped["record"]["supports"][0]
    reseal_packet(swapped); course.validate_model_packet(swapped)
    plan = binding.compile_packet(swapped, tokenizer, seed=101)
    assert plan["packet_digest"] != original["packet_digest"]
    assert plan["sequence_digest"] != original["sequence_digest"]
    before = [r for r in original["rows"] if r["scope"][0] == "SUPPORT"]
    after = [r for r in plan["rows"] if r["scope"][0] == "SUPPORT"]
    assert before[0]["scope"] == after[0]["scope"] == ["SUPPORT", "S0"]
    assert before[0]["token_ids"] != after[0]["token_ids"]
    assert all(s["worked_answer"]["value"] == {"nodes": []} for s in swapped["record"]["supports"])


@pytest.mark.parametrize("field,value", [("seed", True), ("seed", 1.0), ("seed", -1), ("seed", 2**63),
    ("d_model", True), ("d_model", 64.0), ("d_model", 63), ("ordinal", True), ("ordinal", 142),
    ("position", 0.0), ("position", 262144), ("scope", ["WORLD", "W65"]), ("scope", ["SUPPORT", "S3"])])
def test_exact_coordinate_types_and_bounds(field, value):
    args = dict(seed=101, scope=["WORLD", "W0"], ordinal=7, position=0, d_model=64)
    args[field] = value
    with pytest.raises(ValueError): binding.signed_permutation(**args)


def test_permutations_are_bijections_and_all_coordinates_affect_exact_maps():
    base = dict(seed=101, scope=["WORLD", "W0"], ordinal=7, position=0)
    order, signs = binding.signed_permutation(**base)
    assert sorted(order) == list(range(64)) and set(signs) == {-1, 1}
    assert binding.signed_permutation(**base) == (order, signs)
    variants = [dict(base, seed=202), dict(base, scope=["WORLD", "W1"]), dict(base, ordinal=8), dict(base, position=1)]
    assert all(binding.signed_permutation(**v) != (order, signs) for v in variants)
    row = {"ordinal": 7, "scope": ["WORLD", "W0"], "start": 0, "count": 2, "token_ids": [10, 11]}
    maps = binding.linear_terms(row, seed=101)
    expected = []
    perms = [binding.signed_permutation(**dict(base, position=p)) for p in range(2)]
    for dest in range(64):
        expected.append(tuple(sorted((t, perms[p][0][dest], perms[p][1][dest]) for p, t in enumerate((10, 11)))))
    assert maps == tuple(expected)
    assert binding.linear_terms(dict(row, scope=["WORLD", "W1"]), seed=101) != maps
    assert binding.linear_terms(dict(row, token_ids=[11, 10]), seed=101) != maps
    assert binding.profile()["collision_free_claim"] is False  # Exact maps are not numeric acceptance.


def test_exact_linear_map_inspection_is_bounded_before_allocation():
    row = {"ordinal": 1, "scope": ["QUERY"], "start": 0, "count": 129, "token_ids": [10] * 129}
    with pytest.raises(ValueError, match="INSPECTION_BOUND"): binding.linear_terms(row, seed=0)
    with pytest.raises(ValueError, match="DIMENSION"): binding.linear_terms(row, seed=0, d_model=10**20)
    row.update(count=1, token_ids=[True])
    with pytest.raises(ValueError, match="TOKEN_IDS"): binding.linear_terms(row, seed=0)


def test_frozen_expected_rows_are_exact_unit_float32_and_domain_separated(prepared):
    tokenizer = prepared[2]
    raw = binding.projection_bytes(tokenizer, seed=101)
    rows = [raw[i:i + 256] for i in range(0, len(raw), 256)]
    assert len(rows) == len(set(rows)) == len(tokenizer.vocabulary)
    for row in rows:
        values = struct.unpack("<64f", row)
        assert set(values) <= {-.125, .125} and sum(v*v for v in values) == 1.0
    out = binding.readout_bytes(seed=101)
    assert len(out) == 90 * 256 and len({out[i:i+256] for i in range(0, len(out), 256)}) == 90
    assert binding.row_bytes(["token", "PRESENT"], seed=101) != binding.row_bytes(["readout", "PRESENT"], seed=101)
    assert binding.readout_bytes(seed=202) != out


def test_slot_query_is_scoped_and_membership_checked(prepared):
    packet, _, _, _ = prepared
    plan = slots.compile_slots(packet)
    node_slots = [s for s in plan["slots"] if s["coordinates"]]
    assert len(node_slots) >= 2
    left, right = node_slots[:2]
    spec = binding.slot_query_spec(packet, plan, left)
    assert spec["scope"] == left["scope_alias"]
    assert all(c.startswith(spec["scope"] + "/N") for c in spec["coordinates"])
    assert binding.query_bytes(packet, plan, left, seed=101) != binding.query_bytes(packet, plan, right, seed=101)
    bad = deepcopy(left); bad["scope_alias"] = "W64"
    with pytest.raises(ValueError, match="MEMBERSHIP"): binding.slot_query_spec(packet, plan, bad)
    badplan = deepcopy(plan); badplan["slots"][0]["symbols"].reverse()
    with pytest.raises(ValueError): binding.slot_query_spec(packet, badplan, left)


def test_expected_identity_binds_full_profiles_and_actual_byte_receipts(prepared):
    tokenizer = prepared[2]
    identity = encoder.expected_identity(tokenizer, seed=101)
    assert encoder.validate_identity(tokenizer, json.loads(json.dumps(identity))) == identity
    assert identity["projection"]["sha256"] == sha256(binding.projection_bytes(tokenizer, seed=101)).hexdigest()
    assert identity["readout"]["shape"] == [90, 64] and identity["profile"]["numeric_acceptance"] is False
    for mutate in (lambda v: v.update(seed=101.0), lambda v: v["projection"].update(bytes=float(v["projection"]["bytes"])),
                   lambda v: v["readout"].update(sha256="0"*64), lambda v: v["profile"].update(numeric_acceptance=True)):
        bad = deepcopy(identity); mutate(bad)
        bad["identity_digest"] = binding._digest({k: v for k, v in bad.items() if k != "identity_digest"})
        with pytest.raises(ValueError): encoder.validate_identity(tokenizer, bad)


def test_fresh_module_initialization_is_guarded():
    for module in (binding, encoder):
        name = "cas_meta2.typed_teaching._guarded_" + Path(module.__file__).stem
        spec = importlib.util.spec_from_file_location(name, module.__file__)
        fresh = importlib.util.module_from_spec(spec)
        try:
            sys.modules[name] = fresh
            spec.loader.exec_module(fresh)
            assert fresh.profile()["numeric_acceptance"] is False
        finally:
            sys.modules.pop(name, None)


def test_bad_factory_and_restore_admission_do_not_touch_numeric_runtime(prepared):
    class NoRuntime:
        def __getattr__(self, name): raise AssertionError("NUMERIC_RUNTIME_TOUCHED:" + name)
    forbidden = NoRuntime(); tokenizer = prepared[2]
    for device in ("cpu", "mps", "cuda:bad"):
        with pytest.raises(ValueError, match="CUDA_ONLY"):
            encoder.build_frozen_typed_encoder(forbidden, tokenizer, seed=101, device=device)
    with pytest.raises(ValueError, match="SEED"):
        encoder.build_frozen_typed_encoder(forbidden, tokenizer, seed=True, device="cuda")
    with pytest.raises(ValueError, match="TOKENIZER_TYPE"):
        encoder.build_frozen_typed_encoder(forbidden, {}, seed=101, device="cuda")
    with pytest.raises(ValueError, match="STATE_FIELDS"):
        encoder.restore_frozen_typed_encoder(forbidden, {}, expected_identity={}, device="cuda")
    identity = encoder.expected_identity(tokenizer, seed=101)
    payload = {"schema": encoder.STATE_SCHEMA, "identity": identity, "tokenizer": tokenizer.to_dict(), "projection": None, "readout": None}
    wrong = deepcopy(identity); wrong["readout"]["sha256"] = "0"*64
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        encoder.restore_frozen_typed_encoder(forbidden, payload, expected_identity=wrong, device="cuda")
    with pytest.raises(ValueError, match="CUDA_ONLY"):
        encoder.restore_frozen_typed_encoder(forbidden, payload, expected_identity=identity, device="cpu")
