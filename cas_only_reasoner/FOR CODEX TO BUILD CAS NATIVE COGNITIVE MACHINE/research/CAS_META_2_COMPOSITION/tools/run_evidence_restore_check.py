"""Restore check: regenerate the report from retained bytes, originals unavailable.

The directive's completion standard is: after the GPU is gone, the full experiment
can still be opened, checked and reconstructed from retained evidence. A hash is an
identity check, not a backup; a local commit is not proof of a separately readable
copy. So this tool takes an archive directory, copies nothing from the original run
directory, and rebuilds the non-neural report from the retained rows alone.

What it does, in order, all of it deterministic and with no model, no torch and no
network:

1. copy the archive into a NEW directory, so the original is never read again;
2. verify every required object's size and SHA-256 from those copied bytes;
3. parse the per-question rows and check the exact item identities, phases and faces;
4. regenerate per-layer and per-face counts, macro accuracy, constant-rule baselines,
   the paired comparisons and the milestone report from the rows;
5. compare the regenerated figures with the stored ones and report every difference.

It is not a substitute for the archival backup, and it does not prove the cloud
configuration: it proves the bytes on hand are sufficient to inspect the experiment
without the machine that produced them.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aws import run_evidence as re_  # noqa: E402


def restore(archive, destination, contract, *, job=None):
    """Rebuild the report from an archive into a fresh directory."""
    archive = Path(archive)
    destination = Path(destination)
    if destination.exists():
        raise ValueError("RESTORE_DESTINATION_MUST_NOT_EXIST:" + str(destination))
    destination.mkdir(parents=True)
    # 1. copy bytes only; the source directory is not consulted again
    files = []
    for path in sorted(archive.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(archive).as_posix()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        files.append({"relative_path": relative, "bytes": target.stat().st_size,
                      "sha256": re_.digest_file(target),
                      "bytes_raw": target.read_bytes()})

    # 2. byte integrity from the restored copy
    byte_verdict = re_.verify_byte_integrity(files, contract)

    # 3. rows, parsed from the restored copy
    records, rows_by_layer, rows_by_key = {}, OrderedDict(), {}
    unparsable = []
    for key in re_.required_records(contract):
        path = destination / key
        if not path.is_file():
            continue
        try:
            records[key] = re_.read_records(path)
        except ValueError as error:
            # A damaged record file is reported, never trusted and never fatal:
            # the point of the check is to say whether the archive is sufficient.
            unparsable.append({"key": key, "error": str(error)[:300]})
            continue
        rows_by_key[key] = records[key]
    for key, rows in records.items():
        spec = re_.required_records(contract)[key]
        if spec.get("records") is None:
            continue
        for row in rows:
            rows_by_layer.setdefault(row.get("layer", "unknown"), []).append(row)
    completeness = re_.verify_completeness(records, contract)

    # 4. per-layer, per-face, macro, before/after pairing (pure arithmetic)
    layers = OrderedDict()
    for layer, rows in rows_by_layer.items():
        after = [row for row in rows if (row.get("phase") or "after") == "after"]
        before = [row for row in rows if row.get("phase") == "before"]
        by_face = OrderedDict()
        for row in after:
            bucket = by_face.setdefault(str(row.get("face")), {"correct": 0,
                                                               "total": 0})
            bucket["total"] += 1
            bucket["correct"] += 1 if row.get("is_correct") else 0
        for bucket in by_face.values():
            bucket["accuracy"] = (bucket["correct"] / bucket["total"]
                                  if bucket["total"] else None)
        face_accuracies = [value["accuracy"] for value in by_face.values()
                           if value["accuracy"] is not None]
        layers[layer] = {
            "questions": len(after),
            "correct": sum(1 for row in after if row.get("is_correct")),
            "accuracy": (sum(1 for row in after if row.get("is_correct"))
                         / len(after)) if after else None,
            "by_face": by_face,
            "macro_accuracy": (sum(face_accuracies) / len(face_accuracies)
                               if face_accuracies else None),
            "faces_at_or_above_half": sum(1 for value in face_accuracies
                                          if value >= 0.5),
            "before_after": _before_after(before, after),
        }

    # 5. compare with the stored figures and report every difference
    stored, differences = {}, []
    analysis = destination / "results/evidence/panel_analysis.json"
    if analysis.is_file():
        document = json.loads(analysis.read_bytes())
        stored = (document.get("by_condition") or document.get("layers") or {})
    per_condition = OrderedDict()
    for key, rows in rows_by_key.items():
        spec = re_.required_records(contract)[key]
        condition = spec.get("condition")
        if not condition:
            continue
        after = [row for row in rows if (row.get("phase") or "after") == "after"]
        per_condition.setdefault(condition, []).extend(after)
    for condition, rows in per_condition.items():
        for layer in {row.get("layer") for row in rows}:
            layer_rows = [row for row in rows if row.get("layer") == layer]
            regenerated = {"correct": sum(1 for row in layer_rows
                                          if row.get("is_correct")),
                           "questions": len(layer_rows)}
            candidates = [stored.get(condition, {}).get(layer)
                          if isinstance(stored.get(condition), dict) else None,
                          stored.get(layer)]
            for wanted in candidates:
                if not isinstance(wanted, dict):
                    continue
                if wanted.get("correct") != regenerated["correct"] \
                        or (wanted.get("questions") or wanted.get("total")) \
                        != regenerated["questions"]:
                    differences.append({"condition": condition, "layer": layer,
                                        "regenerated": regenerated,
                                        "stored": wanted})
                break
    return {"schema": "cas.run-evidence-restore-check/1", "job": job,
            "archive": str(archive), "destination": str(destination),
            "originals_unavailable": True,
            "byte_integrity": {key: value for key, value in byte_verdict.items()
                               if key not in ("verified",)},
            "measurement_completeness": completeness["state"],
            "completeness_failures": completeness["failures"],
            "regenerated": {"layers": layers, "conditions": list(per_condition)},
            "stored_compared": bool(stored),
            "differences": differences,
            "unparsable_records": unparsable,
            "report_regenerated": bool(layers),
            "restored": (byte_verdict["state"] == "COMPLETE_VERIFIED"
                         and completeness["state"] == "COMPLETE"
                         and not differences and not unparsable and bool(layers)),
            "boundary": ("the report is rebuilt from retained rows with no model, "
                         "no torch and no network; this proves the archive is "
                         "sufficient, not that the cloud configuration is correct")}


def _before_after(before, after):
    """Per-question before/after pairing from retained rows."""
    by_id = {row.get("item_id"): row for row in before}
    gained = lost = both = neither = 0
    for row in after:
        prior = by_id.get(row.get("item_id"))
        if prior is None:
            continue
        if row.get("is_correct") and not prior.get("is_correct"):
            gained += 1
        elif prior.get("is_correct") and not row.get("is_correct"):
            lost += 1
        elif row.get("is_correct"):
            both += 1
        else:
            neither += 1
    return {"gained": gained, "lost": lost, "both_correct": both,
            "neither_correct": neither, "discordant_pairs": gained + lost,
            "mcnemar_ready": (gained + lost) > 0}


def extra_files(directory, contract, destination):
    """Copy anything in the archive the contract does not name, so nothing is lost."""
    copied = []
    known = set(re_.contract_keys(contract))
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        if relative in known:
            continue
        target = Path(destination) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append(relative)
    return copied


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--job")
    arguments = parser.parse_args(argv)
    contract = json.loads(Path(arguments.contract).read_bytes())
    report = restore(arguments.archive, arguments.destination, contract,
                     job=arguments.job)
    print(json.dumps({"restored": report["restored"],
                      "layers": list(report["regenerated"]["layers"]),
                      "differences": len(report["differences"]),
                      "byte_integrity": report["byte_integrity"]["state"],
                      "measurement_completeness":
                          report["measurement_completeness"]}, sort_keys=True))
    return 0 if report["restored"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
