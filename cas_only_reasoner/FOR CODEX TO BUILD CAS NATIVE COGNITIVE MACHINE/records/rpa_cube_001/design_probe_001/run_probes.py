"""Retain exact pure design probes; refuse to overwrite any evidence."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
IDENTITY = HERE / "source_identity.json"
inputs = json.loads(IDENTITY.read_text(encoding="utf-8"))
composition = pathlib.Path(inputs["composition_root"])
cncm = pathlib.Path(inputs["cncm_root"])


def seal(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def check_sources():
    for row in inputs["sources"]:
        root = cncm if row["root"] == "CNCM" else composition
        assert seal(root / row["path"]) == {k: row[k] for k in ("bytes", "sha256")}, row["path"]
    row = inputs["attachment"]
    assert seal(pathlib.Path(row["path"])) == {k: row[k] for k in ("bytes", "sha256")}


# Freeze all project Python bytes before importing the pure compiler so the
# actual transitive import inventory can later be matched to pre-run bytes.
before = {}
for relative in ("cas_meta2",):
    for path in (composition / relative).rglob("*.py"):
        before[str(path.resolve())] = seal(path)

check_sources()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
rows = []
for name in ("target_free", "graph_derived"):
    script = HERE / ("probe_" + name + ".py")
    inventory = HERE / (name + "_module_inventory.json")
    stdout = HERE / (name + "_stdout.txt")
    stderr = HERE / (name + "_stderr.txt")
    for target in (inventory, stdout, stderr, HERE / "receipt.json"):
        if target.exists():
            raise FileExistsError(str(target))
    # Python -c keeps the declared composition cwd on sys.path as in the
    # original stdin probes. The exact launcher and argv are retained.
    launcher = """import hashlib,json,pathlib,sys
source=pathlib.Path(sys.argv[1])
inventory=pathlib.Path(sys.argv[2])
try:
 exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),{'__name__':'__main__'})
finally:
 rows=[]
 for name,module in sorted(sys.modules.items()):
  file=getattr(module,'__file__',None)
  if name.startswith('cas_meta2') and file and str(file).endswith('.py'):
   p=pathlib.Path(file).resolve(); raw=p.read_bytes()
   rows.append({'module':name,'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 prohibited=sorted({'torch','numpy','boto3','botocore','requests','cas_cjt'} & set(sys.modules))
 with inventory.open('xb') as f:
  f.write((json.dumps({'project_modules':rows,'prohibited_imports_present':prohibited},sort_keys=True,indent=2)+'\\n').encode('utf-8'))
"""
    argv = [sys.executable, "-c", launcher, str(script), str(inventory)]
    result = subprocess.run(argv, cwd=str(composition), capture_output=True, timeout=60, check=False)
    write_new(stdout, result.stdout)
    write_new(stderr, result.stderr)
    modules = json.loads(inventory.read_text(encoding="utf-8"))
    assert not modules["prohibited_imports_present"]
    for module in modules["project_modules"]:
        expected = {k: module[k] for k in ("bytes", "sha256")}
        assert before[module["path"]] == expected
        assert seal(pathlib.Path(module["path"])) == expected
    check_sources()
    if name == "target_free":
        assert result.returncode != 0
        assert b"KeyError: 'correct'" in result.stderr
        assert b"answer_refs" in result.stderr
        outcome = "EXPECTED_LEGACY_TARGET_FREE_FAILURE_REPRODUCED"
    else:
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        report = json.loads(result.stdout)
        assert report["bundle_digest"] == inputs["bundle_digest"]
        assert not report["prohibited_imports_present"]
        assert report["neural_calls"] == report["optimizer_updates"] == 0
        for item in report["counts"].values():
            assert item == {"questions": 51, "matching_compilations": 102, "refusals": []}
        assert set(report["counts"]) == {"view_formal", "view_context", "view_analogy"}
        outcome = "306_GRAPH_DERIVED_PUBLIC_COMPILATIONS_MATCH"
    rows.append({
        "name": name, "argv": argv, "cwd": str(composition),
        "script": script.name, "script_identity": seal(script),
        "exit_code": result.returncode, "outcome": outcome,
        "stdout": stdout.name, "stderr": stderr.name,
        "module_inventory": inventory.name,
    })

check_sources()
receipt = {
    "schema_version": "cncm.rpa-cube-design-probe/0.1",
    "status": "DESIGN_ONLY",
    "started_utc": started,
    "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": {"executable": sys.executable, "version": sys.version},
    "source_commit_context": "9597840c3a0344ea730c689bfc9ffc22401fe707",
    "results": rows,
    "source_inputs_match_before_and_after": True,
    "actual_transitive_project_imports_match_before_and_after": True,
    "neural_calls": 0,
    "learner_invocations": 0,
    "optimizer_updates": 0,
    "delivered_neural_lessons": 0,
    "provider_calls": 0,
    "learning_claim": False,
    "cube_rpa_bridge_implemented": False,
    "artifacts": {},
}
for path in sorted(HERE.iterdir()):
    if path.is_file():
        receipt["artifacts"][path.name] = seal(path)
write_new(HERE / "receipt.json", json_bytes(receipt))
print(json.dumps({"receipt": str(HERE / "receipt.json"), **seal(HERE / "receipt.json"),
                  "results": [row["outcome"] for row in rows]}, sort_keys=True))

