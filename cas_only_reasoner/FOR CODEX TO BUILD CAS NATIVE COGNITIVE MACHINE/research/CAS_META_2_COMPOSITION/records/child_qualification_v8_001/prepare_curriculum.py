"""Create a fresh, source-bound pure curriculum artifact. No neural execution."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FORBIDDEN = frozenset(("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "tensorflow",
                       "jax", "cupy", "boto3", "botocore"))
SOURCES = ("cas_meta2/child_curriculum_v8.py", "cas_meta2/child_scaffold_v8.py",
    "cas_meta2/codec.py", "cas_meta2/curriculum.py", "cas_meta2/ir.py", "cas_meta2/native.py",
    "cas_meta2/executor.py", "records/child_qualification_v8_001/prepare_curriculum.py")


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("CURRICULUM_NEURAL_PROVIDER_IMPORT_REFUSED:" + fullname)


def install_guard():
    if FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules):
        raise RuntimeError("CURRICULUM_IMPORT_BEFORE_GUARD")
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event == "sqlite3.connect" or event in {"socket.connect", "socket.connect_ex",
                "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("CURRICULUM_DATABASE_NETWORK_REFUSED:" + event)
    sys.addaudithook(audit)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def stamp(path):
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def main():
    if len(sys.argv) != 2 or re.fullmatch(r"dataset_[0-9]{3,}", sys.argv[1]) is None:
        raise SystemExit("usage: prepare_curriculum.py dataset_001 (choose a fresh name)")
    destination = HERE / sys.argv[1]
    if destination.exists() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                  for p in (destination, *destination.parents)):
        raise SystemExit("A new, unlinked output directory is required.")
    install_guard()
    sys.path.insert(0, str(ROOT))
    from cas_meta2 import child_curriculum_v8 as curriculum
    started = datetime.now(timezone.utc).isoformat()
    before = {name: stamp(ROOT / name) for name in SOURCES}
    budget = ROOT / "records/budget/campaign_ledger.json"
    budget_before = stamp(budget)
    dataset = curriculum.generate_dataset()
    parts = curriculum.export_parts(dataset)
    parts["qualification_development.json"] = curriculum.qualification_tasks()
    if {name: stamp(ROOT / name) for name in SOURCES} != before or stamp(budget) != budget_before:
        raise RuntimeError("CURRICULUM_SOURCE_OR_BUDGET_CHANGED")
    destination.mkdir(exist_ok=False)
    for name, value in parts.items():
        with (destination / name).open("xb") as stream:
            stream.write(encode(value))
    after = {name: stamp(ROOT / name) for name in SOURCES}
    if after != before or stamp(budget) != budget_before:
        raise RuntimeError("CURRICULUM_SOURCE_OR_BUDGET_CHANGED")
    receipt = {"schema": "cas-meta2-child-curriculum-artifact/8", "status": "PURE_CURRICULUM_ASSEMBLED",
        "seed": dataset["seed"], "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv], "python": sys.version, "cwd": str(Path.cwd()),
        "observed_git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_before": before, "source_after": after, "source_unchanged": True,
        "canonical_budget_before": budget_before, "canonical_budget_after": stamp(budget),
        "split_report": dataset["manifest"]["splits"],
        "files": {name: stamp(destination / name) for name in parts},
        "forbidden_imports": sorted(FORBIDDEN), "database_network_operations_blocked": True,
        "neural_execution": False, "provider_calls": False, "training": False,
        "native_outcomes_checked": False,
        "boundary": "312 declared tasks in 112 independent contexts. Pure meaning/structure checks only. "
                    "The separate four-task development qualification is not held-out evaluation. "
                    "No native acceptance, learning or generalization follows from this artifact."}
    with (destination / "receipt.json").open("xb") as stream:
        stream.write(encode(receipt))
    print(json.dumps({"status": receipt["status"], "receipt_sha256": stamp(destination / "receipt.json")["sha256"],
                      "splits": {k: v["count"] for k, v in receipt["split_report"].items()}}))


if __name__ == "__main__":
    main()
