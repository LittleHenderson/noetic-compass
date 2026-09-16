"""Pin focused compatibility tests; deny neural/provider imports in child."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).parent
HOME = ROOT.parents[3]
sys.path.insert(0, str(ROOT))
TESTS = [
 "tests/test_rpa_learning_smoke.py", "tests/test_rpa_learning_worker.py",
 "research/CAS_META_2_COMPOSITION/tests/test_ingestion_smoke_launch.py",
 "tests/test_rpa_learning_cycle.py", "tests/test_rpa_learning_adapter.py",
]
CHILD = r'''
import importlib.abc,json,os,sys
from pathlib import Path
DENIED={"torch","numpy","tensorflow","jax","boto3","botocore","requests","httpx","openai","anthropic","cas_cjt","casformer"}
attempts=[]
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split(".")[0] in DENIED:
   attempts.append(fullname)
   raise AssertionError("PROHIBITED_TEST_IMPORT:"+fullname)
if DENIED.intersection(sys.modules):raise RuntimeError("PRELOADED_PROHIBITED_MODULE")
sys.meta_path.insert(0,Deny())
import pytest
code=pytest.main(sys.argv[1:])
loaded=sorted(DENIED.intersection(sys.modules))
raw=json.dumps({"forbidden_import_attempts":attempts,"forbidden_modules_loaded":loaded,"exit_code":int(code)},sort_keys=True)+"\n"
with Path(os.environ["CAS_INGESTION_GUARD_RECEIPT"]).open("x",encoding="utf-8",newline="\n") as stream:stream.write(raw)
raise SystemExit(1 if loaded else int(code))
'''

def pin(name):
    raw = (ROOT / name).read_bytes()
    return {"path":name,"bytes":len(raw),"sha256":sha256(raw).hexdigest()}

def main():
    leaf = sys.argv[1] if len(sys.argv) > 1 else "focused_001"
    if not leaf.replace("_","").isalnum(): raise ValueError("OUTPUT_NAME_INVALID")
    output = BASE / leaf
    output.mkdir(exist_ok=False)
    temporary = HOME / "_tmp" / ("learning_smoke_" + leaf)
    temporary.parent.mkdir(exist_ok=True)
    if temporary.exists(): raise ValueError("TEMPORARY_PATH_ALREADY_EXISTS")
    def put(name,value):
        with (output/name).open("x",encoding="utf-8",newline="\n") as stream:
            json.dump(value,stream,sort_keys=True,separators=(",",":"));stream.write("\n")
    baseline = json.loads((BASE/"source_baseline.json").read_bytes())
    names = {row["path"] for row in baseline["accepted_sources"] + baseline["prior_evidence"]}
    names.update(TESTS + [
        "cncm/rpa_learning_adapter.py", "cncm/rpa_learning_cycle.py",
        "cncm/rpa_learning_smoke.py", "cncm/rpa_learning_worker.py",
        "research/CAS_META_2_COMPOSITION/aws/ingestion_smoke_launch.py",
        "tools/reproduce_learning_ingestion.py",
        "records/learning_smoke_001/run_focused.py",
        "records/learning_smoke_001/source_baseline.json",
        "research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Example_v0.1.json"])
    from cncm.rpa_learning_worker import input_inventory
    names.update(row["path"] for row in input_inventory(ROOT))
    names.update(path.relative_to(ROOT).as_posix() for path in BASE.glob("*.py")
                 if path.name != "rehearse_package.py")
    names.update("research/CAS_META_2_COMPOSITION/aws/" + name + ".py" for name in (
        "graph6_contrast_launch", "recurrent_cjt_launch", "graph_training_candidate_launch",
        "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))
    before = [pin(name) for name in sorted(names)]
    put("inputs_before.json",before)
    arguments=["-q",*TESTS,"--basetemp="+str(temporary),"--junitxml="+str(output/"tests.xml")]
    command=[sys.executable,"-B","-c",CHILD,*arguments]
    environment=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="",PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/"research/CAS_META_2_COMPOSITION"),
        CAS_INGESTION_GUARD_RECEIPT=str(output/"guard.json"),TEMP=str(temporary.parent),TMP=str(temporary.parent))
    put("launch.json",{"argv":command,"cwd":str(ROOT),"python":sys.version,"temporary":str(temporary),
        "disabled_plugin_autoload":True,"prohibited_execution_import_guard":True})
    with (output/"stdout.txt").open("xb") as stdout,(output/"stderr.txt").open("xb") as stderr:
        result=subprocess.run(command,cwd=ROOT,env=environment,stdout=stdout,stderr=stderr)
    after=[pin(name) for name in sorted(names)]
    put("inputs_after.json",after)
    suites=list(ET.parse(output/"tests.xml").getroot().iter("testsuite"))
    counts={key:sum(int(row.get(key,"0")) for row in suites) for key in ("tests","failures","errors","skipped")}
    guard=json.loads((output/"guard.json").read_bytes())
    ok=(result.returncode==0 and before==after and counts["tests"]>0
        and not any(counts[key] for key in ("failures","errors","skipped"))
        and not guard["forbidden_modules_loaded"] and not guard["forbidden_import_attempts"])
    put("receipt.json",{"status":"PASS" if ok else "FAIL","counts":counts,"exit_code":result.returncode,
        "inputs_unchanged":before==after,"guard":guard,
        "artifacts":[{"path":path.name,"bytes":len(raw),"sha256":sha256(raw).hexdigest()}
                     for path in sorted(output.iterdir()) if path.is_file() for raw in [path.read_bytes()]]})
    print(json.dumps({"status":"PASS" if ok else "FAIL","counts":counts,"inputs_unchanged":before==after}),flush=True)
    raise SystemExit(0 if ok else 1)

if __name__=="__main__":main()
