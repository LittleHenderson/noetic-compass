"""Verify this additive reconciliation bundle without rerunning historical tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
CN = HERE.parents[1]
ROOT = CN.parents[1]
MANIFEST = HERE / "BUNDLE_MANIFEST.json"
BASE = "eb9985566bd11a89f485d627186ef0efa7177f02"
APP = "noetic-compass-scaffold/noetic-compass"
PROTECTED = [
    APP+"/api/notation/compiler.py", APP+"/api/notation/cas_ohm.py",
    "dist/cas-offline/api/notation/compiler.py", "dist/cas-offline/api/notation/cas_ohm.py",
    "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/rpa_ohm_atlas.py",
    "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/rpa_coordinates.py",
    "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/cncm/rpa_recorded_helm.py",
    "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/tools/render_rpa_view.py",
]


def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    inputs=[]
    for folder in ("cas_reconciliation_20260922", "ohm_numeric_repair_20260922", "audit_reconciliation_20260922"):
        directory=CN/"records"/folder
        if not directory.is_dir():
            raise RuntimeError("Missing bundle directory: "+str(directory))
        inputs += [p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != MANIFEST]
    inputs += [CN/"docs/CAS_OHM_SHARED_CORE_PROPOSAL_20260922.md",
               CN/"docs/CAS_SHARED_MODULE_INVENTORY_20260922.json",
               CN/"tools/inventory_cas_shared_modules.py",
               CN/"tools/prepare_q4_reconciliation.py"]
    files=[{"path":p.relative_to(ROOT).as_posix(), "bytes":p.stat().st_size,
            "sha256_raw":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(inputs)]
    preserved=[]
    for path in PROTECTED:
        historical=git("show",BASE+":"+path)
        current=(ROOT/path).read_bytes()
        if current.replace(b"\r\n",b"\n") != historical.replace(b"\r\n",b"\n"):
            raise RuntimeError("Protected source changed: "+path)
        preserved.append({"path":path,"base_commit":BASE,
                          "git_blob":git("rev-parse",BASE+":"+path).decode().strip(),
                          "sha256_git_bytes":hashlib.sha256(historical).hexdigest(),
                          "sha256_working_bytes":hashlib.sha256(current).hexdigest()})
    if args.write:
        value={"schema":"cas.reconciliation-bundle/0.1",
               "scope":"Artifact integrity and preserved source identity, not scientific acceptance or model execution.",
               "source_commit":git("rev-parse","HEAD").decode().strip(),
               "manifest_excludes_itself":True,"files":files,"preserved_sources":preserved}
        MANIFEST.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8",newline="\n")
    expected=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if files != expected["files"] or preserved != expected["preserved_sources"]:
        raise RuntimeError("Bundle bytes changed; inspect differences before updating the manifest.")
    print(json.dumps({"integrity":"PASS","artifacts":len(files),"preserved_sources":len(preserved)}))


if __name__ == "__main__":
    main()
