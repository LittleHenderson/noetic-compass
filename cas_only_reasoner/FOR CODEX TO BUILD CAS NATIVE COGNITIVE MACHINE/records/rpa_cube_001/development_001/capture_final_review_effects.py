"""Capture consequences of the final-review findings without model calls."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from test_rpa_cube_adversarial import bridge, BASE, document, lesson
from cncm.canonical import digest

source = Path(bridge.__file__)
before = sha256(source.read_bytes()).hexdigest()
doc = document(BASE)
wire = doc.to_dict()
wire["catalog"]["bundle"]["cube_nodes"][0]["revision"] = True
accepted = bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)
page = bridge.catalog_page(accepted)
row = next(row for row in page["rows"] if row["cube"]["node_id"] == BASE["cube_nodes"][0]["node_id"])
revision_effect = {
    "loader_accepted_changed_json_type": True,
    "source_revision_type": type(BASE["cube_nodes"][0]["revision"]).__name__,
    "returned_revision_type": type(row["cube"]["revision"]).__name__,
    "returned_record_digest_matches_returned_cube": row["record_digest"] == digest(row["cube"]),
}
wire = doc.to_dict()
index = next(iter(wire["catalog"]["cube_index"].values()))
index["source_path"][1] = float(index["source_path"][1])
accepted = bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)
try:
    bridge.catalog_page(accepted)
except Exception as exc:
    paging_effect = {"loader_accepted_float_index": True, "paging_exception": type(exc).__name__, "message": str(exc)}
else:
    paging_effect = {"loader_accepted_float_index": True, "paging_exception": None}
forged = lesson(BASE)
forged["teacher_sidecar"]["expected_answer"] = ["not a source answer"]
forged["binding"]["teacher_sidecar_digest"] = digest(forged["teacher_sidecar"])
agreement = bridge.check_teacher_target(forged, ["not a source answer"])
print(json.dumps({
    "reviewed_adapter_sha256": before, "adapter_unchanged": before == sha256(source.read_bytes()).hexdigest(),
    "wire_scalar_integrity_bug": revision_effect, "wire_index_integrity_bug": paging_effect,
    "teacher_agreement_external_source_not_checked": agreement,
    "counts": {"neural_calls": 0, "provider_calls": 0},
}, indent=2))

