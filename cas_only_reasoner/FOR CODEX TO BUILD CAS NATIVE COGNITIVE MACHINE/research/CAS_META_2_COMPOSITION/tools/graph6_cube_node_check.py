"""Deterministic evidence for the Cube Node Schema v0.1 draft (no neural work).

Reports, from the pinned illustrative bundle only:
  * the §12 validation result and the bundle digest;
  * the three worked answers of the schema document, recomputed by the
    unchanged deterministic reference checker;
  * the contrast set: consistent renaming, harmless reordering, rewiring, the
    analogy presentation, and the two stale-content rejections;
  * the §9 leakage boundary: the learner's masked paths per lesson, and the
    proof that changing the private target leaves the learner's input unchanged;
  * the stage table: which of the seven stages the current three-choice
    interface can already express;
  * one complete seven-stage cycle with its counts kept separate.

This is a reading of data. It trains nothing, reserves nothing and launches
nothing, and it leaves the contrast probe, the accepted models, the retained
checkpoints and every paid-run decision exactly as they were.
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import cube_node  # noqa: E402

OWNER_DELIVERED_COPY = Path(r"C:\Users\wakil\Downloads\Cube_Node_Example_v0.1.json")
OWNER_SCHEMA_COPY = Path(r"C:\Users\wakil\Downloads\Cube_Node_Schema_v0.1.md")


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False) + "\n"


def file_identity(path):
    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "present": False}
    raw = path.read_bytes()
    return {"path": str(path), "present": True, "bytes": len(raw),
            "sha256": sha256(raw).hexdigest()}


def source_identity():
    """The pinned input, and whether it still matches the delivered copy."""
    pinned = cube_node.pinned_bundle_path()
    schema = cube_node.CUBE_RECORD_DIR / "Cube_Node_Schema_v0.1.md"
    pinned_identity = file_identity(pinned)
    delivered = file_identity(OWNER_DELIVERED_COPY)
    return {
        "pinned_bundle": pinned_identity,
        "pinned_schema_document": file_identity(schema),
        "delivered_copy": delivered,
        "pinned_matches_delivered": (
            delivered.get("present") is True
            and delivered.get("sha256") == pinned_identity.get("sha256")),
        "delivered_schema_copy": file_identity(OWNER_SCHEMA_COPY),
        "status": cube_node.CUBE_STATUS,
        "provenance_note": ("the illustrative bundle is authored data, not "
                            "experimental evidence: it is the handoff example of "
                            "Cube Node Schema v0.1, copied into this homebase with "
                            "its source identity recorded"),
    }


def build_report(bundle_path=None, view_id="view_context"):
    bundle = cube_node.load_bundle(bundle_path)
    report = cube_node.check(bundle, bundle_path=bundle_path, view_id=view_id)
    report["sources"] = source_identity()
    report["worked_example"] = {
        op: {"question": case["question"], "answer": case["correct"],
             "derivation": case["derivation"]}
        for op, case in cube_node.select_cases(bundle, view_id).items()}
    report["boundary"] = {
        "training": "none",
        "reservation": "none",
        "launch": "none",
        "neural_calls": 0,
        "checkpoints_touched": "none",
        "registered_records_changed": "none",
        "unchanged": cube_node.interface_report()["unchanged_by_this_draft"],
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=None,
                        help="cube bundle to read (default: the pinned example)")
    parser.add_argument("--view", default="view_context",
                        help="presentation view used for the lessons")
    parser.add_argument("--output", default=None,
                        help="write the report here (must not already exist)")
    arguments = parser.parse_args(argv)
    raw = canonical(build_report(arguments.bundle, arguments.view)).encode("utf-8")
    if arguments.output:
        path = Path(arguments.output).absolute()
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
    sys.stdout.write(raw.decode("utf-8"))
    sys.stdout.write("sha256: %s\n" % sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
