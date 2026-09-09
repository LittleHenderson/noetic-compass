"""Deterministic panel-separation evidence for the confirmation experiment.

NO neural work, NO GPU, NO training: this tool only builds the pure-Python
lesson datasets and compares record identities. It answers one narrow
question with exact numbers:

  Does the confirmation design's newly generated sealed panel exclude the
  panel that was previously examined (the attempt-010 / competence-run-005
  panel, dataset seed 20260909)?

Reported per predeclared seed:
  * sealed panel ids (validation + test, whole-part ops) and their counts,
  * overlap with the previously examined panel ids (must be 0),
  * overlap of the familiar (train + practice) ids with the previously
    examined panel ids (must be 0 — no training on previously examined
    sealed examples).

The previous panel ids are read from the preserved run-005 result when it is
available (authoritative record of what was examined); otherwise they are
rebuilt from dataset seed 20260909 and the rebuilt/rebuilt comparison is
reported explicitly so the source of the identity list is never ambiguous.
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

from cas_meta2.graph_teaching import competence, lessons, trainer  # noqa: E402

PREVIOUS_DATASET_SEED = 20260909
RECEIPT_GLOB = ("records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/"
                "receipt_cas-meta2-competence-*/competence_result.json")


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False) + "\n"


def sealed_ids(seed):
    dataset = lessons.build_dataset(seed=seed)
    ids = []
    for split in trainer.SEALED_SPLITS:
        for record in dataset[split]:
            if record["family"] == "whole_part" and record["op"] in trainer.WHOLE_PART_OPS:
                ids.append(record["record_id"])
    return ids


def familiar_ids(seed):
    return [record["record_id"] for record in trainer.training_records(seed)]


def per_op(ids, seed):
    dataset = lessons.build_dataset(seed=seed)
    counts = {}
    for split in trainer.SEALED_SPLITS:
        for record in dataset[split]:
            if record["family"] == "whole_part" and record["op"] in trainer.WHOLE_PART_OPS:
                counts[record["op"]] = counts.get(record["op"], 0) + 1
    return counts


def previous_panel():
    """(ids, source) for the previously examined sealed panel.

    The ids come from the preserved run-005 result (the authoritative record
    of what was actually examined). If no preserved result carries sealed
    predictions, the panel is rebuilt from dataset seed 20260909 and the
    report says so explicitly.
    """
    for path in reversed(sorted(ROOT.glob(RECEIPT_GLOB))):
        try:
            document = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        runs = document.get("runs") if isinstance(document, dict) else None
        for run in (runs if runs else [document]):
            stage3 = (run or {}).get("stage3") or {}
            predictions = (stage3.get("sealed") or {}).get("sealed_predictions")
            if predictions:
                return ([row["record_id"] for row in predictions],
                        "preserved_result:" + str(path.relative_to(ROOT)))
    return (sealed_ids(PREVIOUS_DATASET_SEED),
            "rebuilt_from_dataset_seed_%d" % PREVIOUS_DATASET_SEED)


def build_report():
    previous, previous_source = previous_panel()
    previous_set = set(previous)
    rows = []
    for seed in competence.CONFIRM_SEEDS:
        sealed = sealed_ids(seed)
        familiar = familiar_ids(seed)
        rows.append({
            "seed": seed,
            "sealed_ids": sealed,
            "sealed_count": len(sealed),
            "sealed_per_op": per_op(sealed, seed),
            "familiar_count": len(familiar),
            "sealed_overlap_with_examined_panel": sorted(set(sealed) & previous_set),
            "familiar_overlap_with_examined_panel": sorted(set(familiar) & previous_set),
        })
    return {
        "schema": "cas-graph-training-confirmation-panel-check/1",
        "neural_work": False,
        "gpu_used": False,
        "examined_panel_source": previous_source,
        "examined_panel_count": len(previous),
        "examined_panel_ids": sorted(previous),
        "predeclared_seeds": list(competence.CONFIRM_SEEDS),
        "transfer_threshold": competence.TRANSFER_THRESHOLD,
        "fit_margin": competence.FIT_MARGIN,
        "per_seed": rows,
        "all_sealed_panels_disjoint_from_examined_panel":
            all(not row["sealed_overlap_with_examined_panel"] for row in rows),
        "no_familiar_overlap_with_examined_panel":
            all(not row["familiar_overlap_with_examined_panel"] for row in rows),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    raw = canonical(build_report()).encode("utf-8")
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
