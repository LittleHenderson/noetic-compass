"""Create a new manifest of actual stored artifacts; never overwrite it."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
CN = ROOT.parents[1]
LAB = CN / "research/helm_cas_expression_lab"
REPO = CN.parents[1]


def fingerprint(path):
    raw = path.read_bytes()
    row = {"path": path.relative_to(CN).as_posix(), "bytes": len(raw),
           "sha256_raw": hashlib.sha256(raw).hexdigest()}
    if not path.is_relative_to(ROOT):
        row["sha256_lf"] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        row["verification"] = "LF_NORMALIZED_SOURCE_WITH_RAW_FINGERPRINT_RETAINED"
    else:
        row["verification"] = "EXACT_RAW_RECEIPT"
    return row


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def seal():
    preparation = json.loads((ROOT / "preparation.json").read_text())
    plan = json.loads((ROOT / "plan.json").read_text())
    source_commit = preparation["source_commit"]
    components = []
    for name, pinned in plan["source_pins"].items():
        source = LAB / name
        old = subprocess.check_output(["git", "show", source_commit + ":" + source.relative_to(REPO).as_posix()], cwd=REPO)
        if hashlib.sha256(old.replace(b"\r\n", b"\n")).hexdigest() != pinned:
            raise ValueError("Source commit differs from run source: " + name)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        components.append({**fingerprint(source), "sha256_lf": pinned,
                           "entry_points": [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]})
    inventory_path = CN / "docs/CAS_SHARED_MODULE_INVENTORY_Q4_20260922.json"
    write_new(inventory_path, {"schema": "cas.shared-module-inventory-addendum/0.1",
        "base_inventory": "docs/CAS_SHARED_MODULE_INVENTORY_20260922.json",
        "source_commit": source_commit, "editing_worktree": str(REPO),
        "scope": "Q4 runtime closure only; previous repository-wide inventory remains preserved",
        "shared_core_implementation": "NOT_SELECTED", "components": components})
    files = [path for path in ROOT.rglob("*") if path.is_file()
             and not any(part in {".pytest_cache", "__pycache__"} for part in path.parts)
             and path.name != "ACCEPTANCE_MANIFEST.json"]
    files += [LAB / name for name in plan["source_pins"]]
    files += [LAB / name for name in ("test_q4_authorized_supervisor.py", "test_q4_device_capacity.py",
                                       "test_q4_conversation_authorization.py", "test_q4_followup.py",
                                       "test_q4_preparation.py", "test_learner_q4.py")]
    files += [inventory_path, CN / "docs/OWNER_RUN_AUTHORIZATION_20260922.md"]
    write_new(ROOT / "ACCEPTANCE_MANIFEST.json", {
        "schema": "helm-cas-expression-lab.q4-run-evidence/0.1",
        "sealed_utc": datetime.now(timezone.utc).isoformat(), "runtime_source_commit": source_commit,
        "plan_canonical_sha256": preparation["new_plan_canonical_sha256"],
        "scope": "Actual bounded development smoke; measured, not certified; not complete Helm 3.0",
        "artifacts": [fingerprint(path) for path in sorted(set(files))]})
    print("Saved exact source inventory and artifact manifest")


if __name__ == "__main__":
    seal()
