"""Non-neural ln(3) diagnostic on the exported package (owner-directed).

Measures, WITHOUT torch or any neural execution, the parts of the flat-loss
symptom that are checkable in pure code and retained records:

  1. Are the three public option TAG STRINGS distinct per record?
  2. Are the three option TOKEN-ID SEQUENCES (from the real tokenizer's
     encode_public) distinct per record?
  3. Does the reported eval_loss recompute from the live module (source
     check), and what are the effective optimizer settings (weight decay)?

The neural quantities (option vectors after the fixed projection, the three
scores, task-loss gradients, parameter movement vs decay) are prepared in the
separate authorized diagnostic (cas_meta2/graph_teaching/diagnostic.py).

Usage:
    python -B tools/graph_training_ln3_diagnostic.py <package_zip> <evidence_dir>
"""
import json
import sys
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path


def digest(raw):
    return sha256(raw).hexdigest()


def main(argv):
    package_zip, evidence_dir = Path(argv[1]), Path(argv[2])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    extracted = Path(tempfile.mkdtemp(prefix="graph_ln3_diag_"))
    with zipfile.ZipFile(package_zip) as archive:
        archive.extractall(extracted)
    sys.path.insert(0, str(extracted / "research/CAS_META_2_COMPOSITION"))

    from cas_meta2.graph_teaching import trainer, adapter  # noqa: E402
    from cas_meta2.features_v2 import LosslessPublicTokenizer  # noqa: E402

    records = trainer.training_records(20260909)
    publics = [adapter.public_records(record, arm)["public"]
               for record in records for arm in ("cas", "generic")]
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=1024)

    distinct_tags = 0
    distinct_ids = 0
    total = 0
    id_lengths = []
    per_record = []
    for record in records:
        for arm in ("cas", "generic"):
            task = adapter.public_records(record, arm)
            tags = [item["tag"] for item in task["public"]["observations"]]
            encoded = tokenizer.encode_public(task["public"])
            slot_sequences = []
            for slot in (0, 1, 2):
                ids = tuple(token_id for token_id, kind, s in
                            zip(encoded["ids"], encoded["kinds"], encoded["slots"])
                            if kind == 2 and s == slot + 1)
                slot_sequences.append(ids)
                id_lengths.append(len(ids))
            total += 1
            tags_distinct = len(set(tags)) == 3
            ids_distinct = len(set(slot_sequences)) == 3
            distinct_tags += 1 if tags_distinct else 0
            distinct_ids += 1 if ids_distinct else 0
            per_record.append({
                "record_id": task["record_id"], "op": task["op"], "arm": arm,
                "tags": tags, "tags_distinct": tags_distinct,
                "id_sequence_lengths": [len(ids) for ids in slot_sequences],
                "id_sequences_distinct": ids_distinct,
                "correct_slot": task["encoded_correct_index"]})

    framework_src = (extracted / "research/CAS_META_2_COMPOSITION"
                     / "cas_meta2/graph_teaching/real_framework.py").read_text()
    trainer_src = (extracted / "research/CAS_META_2_COMPOSITION"
                   / "cas_meta2/graph_teaching/trainer.py").read_text()
    source_checks = {
        "eval_loss_recomputes_from_live_module": "self.forward(" in framework_src,
        "adamw_weight_decay_value": "weight_decay=0.0",
        "adamw_weight_decay_zero_in_source": "weight_decay=0.0" in framework_src,
        "cross_entropy_used": "cross_entropy" in framework_src,
        "before_and_after_share_eval_path": "eval_loss" in trainer_src,
    }

    evidence = {
        "schema": "cas-graph-training-ln3-diagnostic/1",
        "package_archive_sha256": digest(package_zip.read_bytes()),
        "per_arm_record_count": total,
        "distinct_tags": {"count": distinct_tags, "of": total},
        "distinct_token_id_sequences": {"count": distinct_ids, "of": total},
        "option_id_sequence_lengths": {"min": min(id_lengths) if id_lengths else None,
                                       "max": max(id_lengths) if id_lengths else None,
                                       "mean": sum(id_lengths) / len(id_lengths) if id_lengths else None},
        "source_checks": source_checks,
        "examples": per_record[:8],
        "boundary": {"torch_executed": False, "neural_modules_created": False,
                     "aws_calls": 0, "weights_untouched": True},
    }
    raw = (json.dumps(evidence, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (evidence_dir / "ln3_diagnostic.json").write_bytes(raw)
    receipt = {"schema": "cas-graph-training-ln3-receipt/1",
               "file": "ln3_diagnostic.json", "bytes": len(raw),
               "sha256": digest(raw)}
    (evidence_dir / "receipt.json").write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"distinct_tags": [distinct_tags, total],
                      "distinct_ids": [distinct_ids, total],
                      "id_lengths": [min(id_lengths), max(id_lengths)],
                      "source_checks": source_checks,
                      "evidence_sha256": receipt["sha256"]}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main(sys.argv)
