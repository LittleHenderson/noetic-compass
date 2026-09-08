"""Generate inspectable, untrained teaching material using only Python data work."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle.controller import Allocation
from cas_meta2.teaching_cycle.data import build_dataset, fit_tokenizer, make_cycle, make_public


def prepare(destination):
    output = Path(destination).absolute()
    allowed = ROOT / "records/teaching_cycle_001"
    if (not output.is_relative_to(allowed) or output.exists()
            or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))):
        raise ValueError("FRESH_TEACHING_RECORD_DIRECTORY_REQUIRED")
    dataset = build_dataset()
    tokenizer = fit_tokenizer(dataset)
    max_length = 0
    for cases in dataset["splits"].values():
        for case in cases:
            public = make_public(case)
            tokenizer.check_round_trip(public)
            max_length = max(max_length, len(tokenizer.encode_public(public)["ids"]))
    source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.strip()
    source_files = ("data.py", "controller.py", "gpu_adapter.py", "__init__.py")
    identities = {"cas_meta2/teaching_cycle/" + name:
        sha256((ROOT / "cas_meta2/teaching_cycle" / name).read_bytes()).hexdigest() for name in source_files}
    identities["tools/prepare_teaching_cycle.py"] = sha256(Path(__file__).read_bytes()).hexdigest()
    for name in ("cas_meta2/policy.py", "cas_meta2/features_v2.py", "cas_meta2/codec.py",
                 "records/teaching_cycle_001/PROTOCOL.md"):
        identities[name] = sha256((ROOT / name).read_bytes()).hexdigest()
    artifacts = {}
    output.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with target.open("xb") as stream:
            stream.write(payload)
        artifacts[name] = {"sha256": sha256(payload).hexdigest(), "bytes": len(payload)}
    for split in ("train", "development"):
        write(f"teaching/{split}.json", dataset["splits"][split])
    for split in ("test_fresh", "test_context", "test_names"):
        cases = dataset["splits"][split]
        write(f"evaluation_public/{split}.json", [make_public(case) for case in cases])
        write(f"evaluator_private/{split}.json", [{"family_id": c["family_id"],
            "binding": c["target_binding"], "selected_values": next(
                r["values"] for r in c["observations"] if r["slot"] == c["target_binding"])} for c in cases])
    write("teaching/tokenizer.json", tokenizer.to_dict())
    write("sample_aligned_cycle.json", make_cycle(dataset["splits"]["train"][0]))
    report = {"schema": "cas-teaching-preparation/1", "status": "PREPARED_NOT_TRAINED",
        "parent_commit": source, "source_files_sha256": identities,
        "dataset_sha256": canonical_sha256(dataset), "counts": dataset["counts"],
        "evaluation_targets": dataset["evaluation_targets"],
        "binding_distribution": {split: dict(Counter(c["target_binding"] for c in cases))
                                  for split, cases in dataset["splits"].items()},
        "planned_minimum_complete_cycles_per_aligned_arm": Allocation().minimum_full_cycles,
        "planned_maximum_blocks_per_arm": Allocation().maximum_cycles,
        "planned_minimum_stage_presentations_per_arm": 7 * Allocation().minimum_full_cycles,
        "delivered_neural_cycles": 0, "optimizer_steps": 0,
        "new_paid_reservations": 0, "maximum_unassisted_input_tokens": max_length,
        "tokenizer_training_rows_are_not_delivered_lessons": tokenizer.fitted_examples,
        "artifacts": artifacts,
        "boundary": "Preparation only. Private targets must be excluded from the future training worker; directory separation is not access enforcement."}
    write("preparation_receipt.json", report)
    print(json.dumps({"status": report["status"], "counts": report["counts"],
                      "delivered_neural_cycles": 0, "receipt": str(output / "preparation_receipt.json")}))


if __name__ == "__main__":
    prepare(sys.argv[1])
