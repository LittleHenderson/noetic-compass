"""Frozen material and complete-course admission, without any neural imports."""
import builtins
from copy import deepcopy
import json
from pathlib import Path

import pytest

from cas_meta2.typed_teaching import worker_contract as contract

HOME = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def material():
    return contract.load_material(HOME)


def test_frozen_complete_material(material):
    frozen, tokenizer, report = material
    assert report["registry_packets"] == 564 and report["main_presentations"] == 1152
    assert report["groups"] == 160 and report["planned_compute_only"] is True
    assert tokenizer.digest == contract.TOKENIZER_DIGEST
    assert len(frozen["bank"]["worlds"]) == 64


@pytest.mark.parametrize("change,reason", [
    (lambda c: c["batches"].pop(), "COURSE_COUNTS"),
    (lambda c: c["registry"].pop(), "COURSE_COUNTS"),
    (lambda c: c["batches"][0].update(depth=True), "BATCH_DEPTH"),
    (lambda c: c["batches"][0].update(depth=3), "BATCH_DEPTH"),
    (lambda c: c["batches"][0].update(cursor=True), "BATCH_CURSOR"),
    (lambda c: c["batches"][0]["record_ids"].__setitem__(0, "missing"), "BATCH_UNKNOWN_RECORD"),
    (lambda c: c["batches"][0]["record_ids"].reverse(), "PRESENTATION_JOIN"),
    (lambda c: c.update(source_seed=True), "COURSE_IDENTITY"),
    (lambda c: c["presentations"].reverse(), "PRESENTATION_JOIN"),
    (lambda c: c["batches"][0]["presentation_ids"].reverse(), "PRESENTATION_ORDER"),
])
def test_incomplete_or_reordered_course_refused(material, change, reason):
    frozen = deepcopy(material[0]); change(frozen)
    with pytest.raises(ValueError, match=reason):
        contract.validate_schedule(frozen)


def test_public_packet_path_never_invokes_teacher(material, monkeypatch):
    original = builtins.__import__
    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "cas_cjt", "casformer"} or "checker" in name or "checker" in (fromlist or ()):
            raise AssertionError("PUBLIC_FORBIDDEN_IMPORT:" + name)
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", guarded)
    seen = set()
    for record_id, packet in contract.public_packets(material[0]):
        assert set(packet) == {"source", "record"}
        assert record_id == packet["record"]["record_id"]
        assert not {"intent", "lineage", "plan", "batches", "correct_answer", "targets"} & set(packet["record"])
        seen.add(packet["record"]["query"]["kind"])
        if len(seen) == 8:
            break
    assert len(seen) == 8


def test_input_inventory_is_bounded_and_excludes_private_targets():
    rows = contract.input_inventory(HOME)
    assert len(rows) <= 2000 and max(r["bytes"] for r in rows) <= 4 * 1024 ** 2
    assert sum(r["bytes"] for r in rows) <= 96 * 1024 ** 2
    assert not any("private_targets" in r["path"] or "public_frames" in r["path"] for r in rows)
    assert set(contract.MATERIAL) <= {r["path"] for r in rows}


def test_config_freezes_material_source_and_full_course():
    config = contract.make_config(HOME, source_sha="a" * 40,
        job="cas-meta2-typedcourse-20260916120000-aaaaaaaa", bucket="typed-engineering-test")
    assert contract.validate_config(config, HOME) == config
    config["design"]["main_optimizer_updates"] = 159
    with pytest.raises(ValueError, match="CONFIG_IDENTITY"):
        contract.validate_config(config, HOME)


def test_changed_material_byte_is_rejected(tmp_path):
    path = tmp_path / "sample.json"; path.write_bytes(b"{}")
    with pytest.raises(ValueError, match="MATERIAL_BYTES"):
        contract.read_pinned(tmp_path, path.name, {"bytes": 2, "sha256": "0" * 64})


def test_public_import_is_stdlib_and_pure_by_ast():
    import ast
    tree = ast.parse(Path(contract.__file__).read_bytes())
    names = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not names.intersection({"torch", "numpy", "checker", "boto3"})
