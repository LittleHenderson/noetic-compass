"""Lossless public input transport; never execute a teacher or learner."""
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import sys

import pytest

from cas_meta2.typed_teaching import answers, input_frames as frames, source

DENIED = {"torch", "numpy", "tensorflow", "jax", "casformer", "cas_cjt", "boto3", "botocore",
          "openai", "anthropic", "requests", "httpx", "transformers"}


@pytest.fixture(autouse=True)
def guarded(monkeypatch):
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching") or name in {
                "cas_meta2.typed_teaching.course", "cas_meta2.typed_teaching.focal", "cas_meta2.typed_teaching.checker"}:
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guard)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def families():
    return source.training_families(expected_source_profile_digest=source.source_profile()["profile_digest"])


@pytest.fixture(scope="module")
def bank(families):
    return source.freeze_bank(families)


@pytest.fixture(scope="module")
def public(families, bank):
    return source.compile_source(families[0], bank=bank)["public"]


def make_packet(public, *, kind="definition", arguments=None, supports=False):
    query = answers.compile_query(public, kind=kind, arguments=arguments)
    body = {"schema": "cas.typed-teaching-model-packet/0.1", "source_digest": source.public_digest(public),
            "source_world_id": public["focus_world_id"], "query": query,
            "cue": None if kind == "role_set" else "CUBE_FACE_%d" % frames._KIND_FACE[kind],
            "instruction": "An exact public instruction; this synthetic packet is not an admitted course.",
            "role_catalog": {str(i): "Public role %d" % i for i in range(1, 7)}, "supports": []}
    if supports:
        other = [w for w in public["worlds"] if w["world_id"] != public["focus_world_id"]][:3]
        for world in other:
            sq = answers.compile_query(public, kind="parts", arguments={"whole": world["declared_whole"]},
                                       focus_world_id=world["world_id"])
            # Deliberately do not derive/check semantic truth; empty is a valid
            # syntax payload even when this declared whole has direct parts.
            body["supports"].append({"query": sq, "cue": "CUBE_FACE_5", "instruction": "Supplied example text",
                "worked_answer": answers.make_answer(public, sq, {"nodes": []}),
                "selection_rule": "SYNTHETIC_SYNTAX_FIXTURE_NOT_CERTIFIED_TEACHING"})
    return {"source": deepcopy(public), "record": {"record_id": "typed-input-" + source.digest(body), **body}}


def reseal_record(packet):
    row = packet["record"]
    row["record_id"] = "typed-input-" + source.digest({k: v for k, v in row.items() if k != "record_id"})
    return packet


def reseal_frame(frame):
    frame["frame_digest"] = frames._digest({k: v for k, v in frame.items() if k != "frame_digest"})
    return frame


def rows(frame):
    return [json.loads(line) for line in frame["text"].split("\n")]


def changed_text(frame, values):
    result = deepcopy(frame)
    result["text"] = "\n".join(frames._canonical(row) for row in values)
    return reseal_frame(result)


def test_full_bank_supports_and_every_field_roundtrip(public):
    packet = make_packet(public, supports=True)
    before = source.canonical(packet)
    frame = frames.compile_packet(packet)
    assert source.canonical(frames.restore_packet(frame)) == before
    assert frames.validate_frame(frame) == frame
    assert frames._restore_text(frame["text"]) == packet  # All information is in text.
    assert source.canonical(packet) == before
    assert len(frame["aliases"]) == 64
    assert len([r for r in rows(frame) if r[0] == "WORLD"]) == 64
    assert [r[1] for r in rows(frame) if r[0] == "SUPPORT"] == ["S0", "S1", "S2"]
    assert len([r for r in rows(frame) if r[0] == "POLICY"]) == 1
    assert len(frame["text"].encode()) < len(before.encode())
    for field, value in (("source", packet["source"]), ("record", packet["record"]), ("packet", packet)):
        raw = source.canonical(value).encode()
        assert frame["bindings"][field] == {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    for world in frames.restore_packet(frame)["source"]["worlds"]:
        assert world["contains_inventory_complete"] is True
        assert world["branch_order"]["process_order"] is None
        assert world["branch_order"]["source_order"]
        assert world["source_status"]["world_truth_established"] is False


def test_aliases_equal_sorted_public_worlds_and_scoped_node_refs(public):
    frame = frames.compile_packet(make_packet(public))
    for i, (alias, world) in enumerate(zip(frame["aliases"], public["worlds"])):
        assert alias["alias"] == "W%d" % i
        assert alias["world_id"] == world["world_id"]
        assert [a for a, _ in alias["nodes"]] == ["N%d" % j for j in range(len(world["nodes"]))]
        assert [world["world_id"] + suffix for _, suffix in alias["nodes"]] == sorted(n["ref"] for n in world["nodes"])
    assert len({a["world_id"] + suffix for a in frame["aliases"] for _, suffix in a["nodes"]}) == sum(
        len(a["nodes"]) for a in frame["aliases"])


def test_focus_outside_full_bank_keeps_world_union_65(families, bank):
    family = deepcopy(families[0]); family["function"] += " with an additional declared function"
    public = source.compile_source(family, bank=bank)["public"]
    frame = frames.compile_packet(make_packet(public))
    assert len(frame["aliases"]) == 65 and frame["aliases"][-1]["alias"] == "W64"
    restored = frames.restore_packet(frame)
    assert len(restored["source"]["bank"]["world_ids"]) == 64
    assert restored["source"]["focus_world_id"] not in restored["source"]["bank"]["world_ids"]


def test_literal_alias_like_text_unicode_and_embedded_real_refs_roundtrip(public):
    wid = public["focus_world_id"]
    literal = "Literal @{W0/N0}, @@ and @; Unicode café; actual " + wid + "/n0 and " + wid + "."
    packet = make_packet(public, kind="role_set", arguments={"focal_excerpt": literal})
    packet["record"]["instruction"] = literal
    packet["record"]["role_catalog"]["6"] = "@{W64} is literal public wording"
    reseal_record(packet)
    frame = frames.compile_packet(packet)
    assert frames.restore_packet(frame) == packet
    assert "@@{W0/N0}" in frame["text"]
    assert "caf\\u00e9" in frame["text"]
    assert frames.restore_packet(frame)["record"]["query"]["arguments"]["focal_excerpt"] == literal


@pytest.mark.parametrize("field", ["instruction", "role_catalog", "supports"])
def test_meaningful_public_changes_produce_different_exact_frames(public, field):
    first = make_packet(public, supports=True)
    second = deepcopy(first)
    if field == "instruction": second["record"][field] += " changed"
    elif field == "role_catalog": second["record"][field]["5"] += " changed"
    else: second["record"][field].reverse()
    reseal_record(second)
    a, b = frames.compile_packet(first), frames.compile_packet(second)
    assert a["text"] != b["text"] and a["frame_digest"] != b["frame_digest"]
    assert frames.restore_packet(a) == first and frames.restore_packet(b) == second


def test_wrong_but_syntactically_valid_support_answer_is_preserved(public):
    packet = make_packet(public, supports=True)
    frame = frames.compile_packet(packet)
    restored = frames.restore_packet(frame)
    assert all(s["worked_answer"]["value"] == {"nodes": []} for s in restored["record"]["supports"])
    assert "checker" not in frames.__dict__ and "focal" not in frames.__dict__


@pytest.mark.parametrize("mutation", ["world_scope", "world_body", "support_scope", "support_body", "alias_scope",
                                      "binding", "policy", "drop_world", "query_focus"])
def test_resealed_scope_changes_and_omissions_are_rejected(public, mutation):
    frame = frames.compile_packet(make_packet(public, supports=True))
    values = rows(frame)
    wi = [i for i, row in enumerate(values) if row[0] == "WORLD"]
    si = [i for i, row in enumerate(values) if row[0] == "SUPPORT"]
    if mutation == "world_scope": values[wi[0]][1], values[wi[1]][1] = values[wi[1]][1], values[wi[0]][1]
    elif mutation == "world_body": values[wi[0]][2], values[wi[1]][2] = values[wi[1]][2], values[wi[0]][2]
    elif mutation == "support_scope": values[si[0]][1], values[si[1]][1] = values[si[1]][1], values[si[0]][1]
    elif mutation == "support_body": values[si[0]][2], values[si[1]][2] = values[si[1]][2], values[si[0]][2]
    elif mutation == "alias_scope": values[2][1][0]["world_id"], values[2][1][1]["world_id"] = values[2][1][1]["world_id"], values[2][1][0]["world_id"]
    elif mutation == "binding": values[1][1]["source"]["bytes"] += 1
    elif mutation == "policy": next(row for row in values if row[0] == "POLICY")[2]["process_order"] = []
    elif mutation == "drop_world": values.pop(wi[-1])
    else: next(row for row in values if row[0] == "QUERY")[1]["focus_world_id"] = "@{W64}"
    with pytest.raises(ValueError): frames.restore_packet(changed_text(frame, values))


@pytest.mark.parametrize("mutation", ["teacher_field", "lineage", "unknown_support", "wrong_cue", "wrong_record_id", "source_float"])
def test_closed_packet_and_exact_scalar_identity_refusals(public, mutation):
    packet = make_packet(public, supports=True)
    if mutation == "teacher_field": packet["record"]["teacher_target"] = "private"
    elif mutation == "lineage": packet["record"]["plan"] = {}
    elif mutation == "unknown_support": packet["record"]["supports"][0]["hidden_face"] = 5
    elif mutation == "wrong_cue": packet["record"]["cue"] = "CUBE_FACE_6"
    elif mutation == "wrong_record_id": packet["record"]["record_id"] = "typed-input-" + "0" * 64
    else: packet["source"]["worlds"][0]["contains_inventory_complete"] = 1.0
    if mutation != "wrong_record_id": reseal_record(packet)
    with pytest.raises(ValueError): frames.compile_packet(packet)


def test_frame_closed_fields_identity_and_canonical_text(public):
    frame = frames.compile_packet(make_packet(public))
    for change in (lambda f: f.update(hidden_teacher={}),
                   lambda f: f.update(profile_digest="0" * 64),
                   lambda f: f.update(text=f["text"] + "\n"),
                   lambda f: f["aliases"][0].update(alias="W1")):
        changed = deepcopy(frame); change(changed); reseal_frame(changed)
        with pytest.raises(ValueError): frames.validate_frame(changed)
    changed = deepcopy(frame); changed["bindings"]["packet"]["bytes"] += 1
    with pytest.raises(ValueError, match="IDENTITY"): frames.validate_frame(changed)
    changed = deepcopy(frame); changed["text"] = changed["text"].replace('["FORMAT",', '["FORMAT", ', 1)
    reseal_frame(changed)
    with pytest.raises(ValueError): frames.validate_frame(changed)


def test_caller_mutation_does_not_change_frame_or_future_reconstruction(public):
    packet = make_packet(public)
    frame = frames.compile_packet(packet)
    raw = source.canonical(frame)
    restored = frames.restore_packet(frame)
    restored["record"]["instruction"] = "changed"
    assert source.canonical(frame) == raw
    assert frames.restore_packet(frame) == packet
    assert frames.compile_packet(dict(reversed(list(packet.items())))) == frame


def test_fresh_module_initialization_uses_only_pure_syntax_modules():
    alias = "cas_meta2.typed_teaching._input_frames_guarded_test"
    assert alias not in sys.modules
    spec = importlib.util.spec_from_file_location(alias, frames.__file__)
    fresh = importlib.util.module_from_spec(spec)
    sys.modules[alias] = fresh
    try:
        spec.loader.exec_module(fresh)
        assert fresh.compile_packet.__module__ == alias
        assert fresh.profile() == frames.profile()
        assert not {"checker", "focal", "course"}.intersection(vars(fresh))
    finally:
        if sys.modules.get(alias) is fresh: del sys.modules[alias]
