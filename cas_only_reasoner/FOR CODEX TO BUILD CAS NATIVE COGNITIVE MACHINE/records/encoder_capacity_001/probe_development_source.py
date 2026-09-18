"""Can the development panel's targets be derived? Probe, read-only.

Pure standard library. No torch, no device, no model, no run.

The development panel is 59 questions with ZERO overlap with the exposed course, and the machine
scores 0 of 59 on it at every cursor. It has never been scoreable by this record, because
`course.model_packet` raises TYPED_COURSE_RECORD_UNKNOWN for its record_ids and its targets therefore
cannot be derived.

`collected/results/artifacts/protocol_material.json` carries a `development` object and a `schedule`.
This prints its actual shape, and then tries to derive a target for one development record.
"""

from __future__ import annotations

import json
import pathlib
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

ARTIFACTS = HOME / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"


def shape(value, depth=0, width=110):
    pad = "  " * depth
    if isinstance(value, dict):
        print(f"{pad}dict[{len(value)}]")
        for key in list(value)[:12]:
            print(f"{pad}  {key!r}:")
            shape(value[key], depth + 2, width)
    elif isinstance(value, list):
        print(f"{pad}list[{len(value)}]")
        if value:
            shape(value[0], depth + 1, width)
    else:
        text = repr(value)
        print(f"{pad}{type(value).__name__} {text[:width]}")


def main() -> int:
    material = json.loads((ARTIFACTS / "protocol_material.json").read_text(encoding="utf-8"))
    print("=" * 100)
    print("protocol_material['development']")
    print("=" * 100)
    shape(material["development"])
    print()
    print("=" * 100)
    print("protocol_material['schedule']")
    print("=" * 100)
    shape(material["schedule"])
    print()

    dev = json.loads((ARTIFACTS / "development_000_predictions.json").read_text(encoding="utf-8"))
    record_id = dev["predictions"][0]["record_id"]
    print(f"a development record_id: {record_id}")
    print()

    from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    print(f"frozen course registry size: {len(frozen_course['registry'])}")
    print(f"development record in the registry? "
          f"{any(row['record_id'] == record_id for row in frozen_course['registry'])}")
    print()

    for name in ("development", "development_course", "held_out", "probe"):
        if name in frozen_course:
            value = frozen_course[name]
            size = len(value) if hasattr(value, "__len__") else ""
            print(f"frozen_course[{name!r}] present, {type(value).__name__} {size}")

    print()
    print("top-level keys of `frozen_course`:")
    for key in frozen_course:
        value = frozen_course[key]
        size = len(value) if hasattr(value, "__len__") else ""
        print(f"   {key!r}: {type(value).__name__} {size}")

    print()
    print("--- attempting a development packet ---")
    try:
        packet = course.model_packet(frozen_course, record_id)
        print("model_packet SUCCEEDED")
        target = checker.derive_target(packet["source"], packet["record"]["query"])
        print(f"target admissible answers: {len(target['admissible_answers'])}")
    except Exception as error:                                        # noqa: BLE001
        print(f"model_packet FAILED: {type(error).__name__}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
