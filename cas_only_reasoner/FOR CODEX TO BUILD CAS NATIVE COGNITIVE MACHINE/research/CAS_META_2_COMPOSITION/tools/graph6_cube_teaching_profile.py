"""Deterministic evidence for CUBE_TEACHING_PROFILE_001 (no neural work).

Reports, from the pinned illustrative bundle only:
  * one complete seven-stage machine-facing lesson, guided and unassisted, with
    the learner input, prediction, corrective signal, update flag, and
    assistance state at every stage;
  * the declared visibility profiles by task and assistance level, and what the
    unassisted mask withholds;
  * target independence over the whole compile -> visibility -> encode path,
    including the refusal of any target the graph does not derive, and the
    read-only reading of the legacy slot-order dependency;
  * every askable question audited through the declared profile.

This is a reading of data and code. It trains nothing, reserves nothing, and
launches nothing. The contrast probe, the retained checkpoints, the measured
negatives, and every paid-run decision are unchanged.
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

from cas_meta2.graph_teaching import cube_node, cube_profile  # noqa: E402

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


def source_identity(bundle):
    pinned = cube_node.pinned_bundle_path()
    pinned_identity = file_identity(pinned)
    delivered = file_identity(OWNER_DELIVERED_COPY)
    return {
        "pinned_bundle": pinned_identity,
        "pinned_schema_document": file_identity(
            cube_node.CUBE_RECORD_DIR / "Cube_Node_Schema_v0.1.md"),
        "delivered_copy": delivered,
        "pinned_matches_delivered": (
            delivered.get("present") is True
            and delivered.get("sha256") == pinned_identity.get("sha256")),
        "delivered_schema_copy": file_identity(OWNER_SCHEMA_COPY),
        "canonical_bundle_digest": cube_node.bundle_digest(bundle),
        "status": cube_node.CUBE_STATUS,
    }


def build_report(view_id="view_context", bundle_path=None):
    bundle = cube_node.load_bundle(bundle_path)
    report = cube_profile.build_report(bundle, view_id)
    report["sources"] = source_identity(bundle)
    report["replaces"] = {
        "previous_record": "CUBE_NODE_SCHEMA_001 (data-only handoff, unchanged)",
        "lesson_schema_versions": {
            "cube_node": cube_node.LESSON_SCHEMA,
            "cube_profile": cube_profile.LESSON_V2_SCHEMA,
        },
        "reason": ("visibility is now declared by task and assistance level "
                   "instead of chosen from the answer, and task identity and "
                   "slot order are derived from the public exercise only"),
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--view", default="view_context")
    parser.add_argument("--output", default=None,
                        help="write the report here (must not already exist)")
    arguments = parser.parse_args(argv)
    raw = canonical(build_report(arguments.view, arguments.bundle)).encode("utf-8")
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
