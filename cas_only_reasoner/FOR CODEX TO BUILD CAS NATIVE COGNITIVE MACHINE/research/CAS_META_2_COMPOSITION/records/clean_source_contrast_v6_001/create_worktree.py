"""Create one new detached source audit checkout; no GPU or provider work."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

SOURCE = "acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0"
RECORD = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo.resolve()
    target = args.worktree.absolute()
    homebase = next(p for p in root.parents if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
    assert target.parent.resolve() == (homebase / "_worktrees").resolve()
    assert target.name == "contrast-v6-audit-acbb266f"
    assert not target.exists()
    for path in (target, *target.parents):
        assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
    assert not (RECORD / "worktree_creation.json").exists()
    command = ["git", "-C", str(root), "-c", "core.autocrlf=false", "worktree", "add",
               "--detach", str(target), SOURCE]
    started = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(command, capture_output=True, timeout=300)
    (RECORD / "worktree_creation.stdout.txt").write_bytes(run.stdout)
    (RECORD / "worktree_creation.stderr.txt").write_bytes(run.stderr)
    receipt = {"source_sha": SOURCE, "command": command, "returncode": run.returncode,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "target_absent_before": True, "worktree": str(target),
               "stdout_sha256": sha256(run.stdout).hexdigest(),
               "stderr_sha256": sha256(run.stderr).hexdigest(),
               "neural_work": False, "provider_calls": False,
               "scope": "Detached checkout creation only; not validation or installation."}
    with (RECORD / "worktree_creation.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))
    return run.returncode

if __name__ == "__main__":
    raise SystemExit(main())

