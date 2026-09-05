"""Pure inventory test fixtures, deliberately not native-reuse evidence."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools import audit_native_demo as audit


def write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def example(tmp_path):
    demo, native = tmp_path / "demo", tmp_path / "native"
    demo.mkdir()
    native.mkdir()
    entries = []
    for kind, folder in (("demo", demo), ("native", native)):
        path = folder / "mock.json"
        checksum = write(path, {"synthetic_inventory_only": True, "kind": kind})
        entries.append({"root": kind, "path": path.name, "bytes": path.stat().st_size, "sha256": checksum})
    index = {"schema": "cas-meta3-file-index/0.1", "roots": {"demo": "/old/demo", "native": "/old/native"},
             "entries": entries}
    reseal(demo, index)
    return demo, native, index


def reseal(demo, index):
    checksum = write(demo / "file_index.json", index)
    write(demo / "memory_demo_receipt.json", {"file_index_sha256": checksum,
          "note": "NOT_A_NATIVE_EXECUTION_RECEIPT"})


def test_inventory_has_no_native_success_claim(tmp_path):
    demo, native, _ = example(tmp_path)
    inventory = audit.IndexedEvidence(demo, native)
    assert len(inventory.inventory) == 2
    assert inventory.json("native/mock.json")["synthetic_inventory_only"] is True
    assert not hasattr(inventory, "completed")
    inventory.verify_all()


@pytest.mark.parametrize("mutation", ["changed", "added", "removed", "receipt", "index"])
def test_bytes_cannot_change_after_inventory_check(tmp_path, mutation):
    demo, native, _ = example(tmp_path)
    inventory = audit.IndexedEvidence(demo, native)
    if mutation == "changed":
        (native / "mock.json").write_bytes(b"changed")
    elif mutation == "added":
        (demo / "new.txt").write_text("added")
    elif mutation == "removed":
        (native / "mock.json").unlink()
    else:
        (demo / ("file_index.json" if mutation == "index" else "memory_demo_receipt.json")).write_bytes(b"{}")
    with pytest.raises(audit.AuditError):
        inventory.verify_all()


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a//b", "a/./b", "a\\b", "a:b",
                                 "CON", "nul.txt", "a.", "a ", "a/../b", "a\u0000b"])
def test_nonportable_or_escaping_paths_rejected(tmp_path, path):
    demo, native, index = example(tmp_path)
    index["entries"][0]["path"] = path
    reseal(demo, index)
    with pytest.raises(audit.AuditError, match="UNSAFE_EVIDENCE_PATH"):
        audit.IndexedEvidence(demo, native)


@pytest.mark.parametrize("mutation", ["alias", "root", "size", "hash", "sidecar", "one_root"])
def test_invalid_index_fields_are_rejected(tmp_path, mutation):
    demo, native, index = example(tmp_path)
    if mutation == "alias":
        item = deepcopy(index["entries"][0])
        item["path"] = item["path"].upper()
        index["entries"].append(item)
    elif mutation == "root":
        index["entries"][0]["root"] = "outside"
    elif mutation == "size":
        index["entries"][0]["bytes"] = True
    elif mutation == "hash":
        index["entries"][0]["sha256"] = "a"
    elif mutation == "sidecar":
        index["entries"][0]["path"] = "memory_demo_receipt.json"
    else:
        index["entries"].pop()
    reseal(demo, index)
    with pytest.raises(audit.AuditError):
        audit.IndexedEvidence(demo, native)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1e999}', b'{broken'])
def test_invalid_json_rejected(raw):
    with pytest.raises(audit.AuditError):
        audit.json_bytes(raw)


def test_original_paths_never_grant_read_authority(tmp_path):
    demo, native, index = example(tmp_path)
    index["roots"] = {"demo": "C:/unrelated/data", "native": "/unrelated/database"}
    reseal(demo, index)
    assert audit.IndexedEvidence(demo, native).json("demo/mock.json")["kind"] == "demo"


def test_roots_cannot_overlap(tmp_path):
    demo, _, _ = example(tmp_path)
    with pytest.raises(audit.AuditError, match="DISJOINT"):
        audit.IndexedEvidence(demo, demo)


def source_paths_fixture():
    from types import SimpleNamespace
    names = ("CAS_META_3_PROCEDURAL_MEMORY", "CAS_META_2_COMPOSITION",
             "CAS_META_1_LEARNED_SELECTION", "CASFORMER_v0_3_META_LOGIC_WIP")
    paths = ["/synthetic/research/" + name for name in names]
    values = {stage: {"python_source_paths": list(paths)} for stage in ("writer", "reader")}
    packet = SimpleNamespace(index={"roots": {
        "demo": paths[0] + "/runs/cloud_job/demo", "native": paths[1] + "/records/meta3_fixture"}},
        receipt={"job": "fixture"}, json=lambda name: values[name.split("/")[1].split("_")[0]])
    return packet, values, paths


def test_only_explicit_four_child_source_roots_are_accepted():
    packet, _, paths = source_paths_fixture()
    assert audit.check_process_source_paths(packet) == paths


@pytest.mark.parametrize("change", ["outside_demo", "wrong_native_job", "relative_native", "missing_root", "extra_root", "reordered"])
def test_child_source_paths_cannot_expand_or_change(change):
    packet, values, _ = source_paths_fixture()
    if change == "outside_demo":
        packet.index["roots"]["demo"] = "/unrelated/demo"
    elif change == "wrong_native_job":
        packet.index["roots"]["native"] += "other"
    elif change == "relative_native":
        packet.index["roots"]["native"] = "relative"
    elif change == "missing_root":
        values["reader"]["python_source_paths"].pop()
    elif change == "extra_root":
        values["reader"]["python_source_paths"].append("/unrelated/import")
    else:
        values["reader"]["python_source_paths"].reverse()
    with pytest.raises(audit.AuditError):
        audit.check_process_source_paths(packet)
