"""Non-neural local checks only. Never start AWS or construct/execute a model."""
import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cas_meta1.baseline import verify_baseline, verify_installed_wheels
from cas_meta1.curriculum import validate_dataset


def hashes():
    names = []
    for folder in ("cas_meta1","tests","tools","aws","programs","data"):
        names.extend(path for path in (ROOT/folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts
                     and path.suffix in (".py",".json",".md"))
    names.extend(ROOT/name for name in ("README.md","PREREGISTRATION.json",
                                        "BASELINE_MANIFEST.json","requirements-gpu.txt","pytest.ini"))
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/"records") or output.exists():
        raise ValueError("NEW_OUTPUT_INSIDE_PILOT_RECORDS_REQUIRED")
    output.mkdir(parents=True)
    initial_head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    initial = hashes()
    parsed = 0
    for name in initial:
        if name.endswith(".py"):
            ast.parse((ROOT/name).read_text(encoding="utf-8")); parsed += 1
    dataset = {split:json.loads((ROOT/"data"/name).read_text(encoding="utf-8"))
               for split,name in (("train","train.json"),("validation","validation.json"),("test","test_private.json"))}
    dataset_check = validate_dataset(dataset)
    baseline = verify_baseline()
    wheels = verify_installed_wheels()
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1",CAS_META1_RUN_GPU_TESTS="0")
    (ROOT/"runs").mkdir(exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="local-checks-",dir=ROOT/"runs")
    argv = [sys.executable,"-B","-m","pytest","tests","-q","-p","no:cacheprovider",
            "-m","not gpu","--basetemp",scratch,
            "--junitxml",str(output/"tests.xml")]
    (ROOT/"runs").mkdir(exist_ok=True)
    run = subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True)
    (output/"tests.stdout.txt").write_text(run.stdout,encoding="utf-8")
    (output/"tests.stderr.txt").write_text(run.stderr,encoding="utf-8")
    (output/"command.json").write_text(json.dumps({"argv":argv,"returncode":run.returncode,
                                                  "environment_overrides":{k:env[k] for k in ("PYTHONDONTWRITEBYTECODE","OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","CAS_META1_RUN_GPU_TESTS")}},indent=2)+"\n",encoding="utf-8")
    if run.returncode:
        raise RuntimeError("LOCAL_CONTRACT_TESTS_FAILED")
    xml = ET.parse(output/"tests.xml").getroot()
    counts = {key:sum(int(s.attrib.get(key,0)) for s in xml) for key in ("tests","failures","errors","skipped")}
    if any(counts[k] for k in ("failures","errors","skipped")) or counts["tests"] == 0:
        raise RuntimeError("LOCAL_COUNTS_NOT_COMPLETE")
    final = hashes()
    if initial != final:
        raise RuntimeError("SOURCE_CHANGED_DURING_CHECK")
    if baseline != verify_baseline():
        raise RuntimeError("BASELINE_CHANGED_DURING_CHECK")
    if wheels != verify_installed_wheels():
        raise RuntimeError("INSTALLED_WHEEL_BYTES_CHANGED_DURING_CHECK")
    head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    if head != initial_head:
        raise RuntimeError("GIT_HEAD_CHANGED_DURING_CHECK")
    receipt = {"status":"CAS_META_1_LOCAL_CONTRACT_CHECKS_PASSED_GPU_PENDING",
               "git_head_at_check":head,"counts":counts,"python_files_parsed":parsed,
               "dataset_check":dataset_check,"baseline":baseline,"installed_frozen_wheels":wheels,
               "neural_forward_backward_training_evaluation_local":False,
               "gpu_tests_run":False,"aws_launch_performed":False,
               "measured_learning_result":None,"trained_checkpoint":None,
               "required_next_gate":"AWS GPU integration/training/evaluation under the recorded $100 owner cap.",
               "source_sha256":final}
    (output/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k!="source_sha256"},indent=2))


if __name__ == "__main__":
    main()
