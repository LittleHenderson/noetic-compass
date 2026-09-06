"""Create exactly one new detached recovery audit checkout."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

SOURCE = "bd3341b0da893d0a68cfc05fb454848d2f027cd7"
RECORD = Path(__file__).resolve().parent
OUTER = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
REPO = OUTER / "_worktrees/meta1"
TARGET = OUTER / "_worktrees/recovery-v6-audit-bd3341b0"

def main():
    assert not TARGET.exists()
    assert TARGET.parent.resolve() == (OUTER/"_worktrees").resolve()
    assert not (RECORD/"worktree_creation.json").exists()
    for path in (TARGET,*TARGET.parents):
        assert not path.is_symlink() and not getattr(path,"is_junction",lambda:False)()
    command = ["git","-C",str(REPO),"-c","core.autocrlf=false","worktree","add","--detach",str(TARGET),SOURCE]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command,capture_output=True,timeout=300)
    (RECORD/"worktree_creation.stdout.txt").write_bytes(result.stdout)
    (RECORD/"worktree_creation.stderr.txt").write_bytes(result.stderr)
    status = subprocess.run(["git","-C",str(TARGET),"status","--porcelain","--untracked-files=all"],
                            capture_output=True,timeout=60) if result.returncode == 0 else None
    head = subprocess.run(["git","-C",str(TARGET),"rev-parse","HEAD"],
                          capture_output=True,timeout=60) if result.returncode == 0 else None
    receipt = {"source_sha":SOURCE,"command":command,"returncode":result.returncode,
        "started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
        "target_absent_before":True,"target":str(TARGET),"core_autocrlf":False,
        "initial_status":status.stdout.decode() if status else None,
        "head":head.stdout.decode().strip() if head else None,
        "stdout_sha256":sha256(result.stdout).hexdigest(),"stderr_sha256":sha256(result.stderr).hexdigest(),
        "neural_or_provider_work":False}
    with (RECORD/"worktree_creation.json").open("x",encoding="utf-8") as stream:
        stream.write(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,indent=2),flush=True)
    assert result.returncode == 0 and status.returncode == 0 and not status.stdout.strip()
    assert head.returncode == 0 and receipt["head"] == SOURCE

if __name__ == "__main__":
    main()

