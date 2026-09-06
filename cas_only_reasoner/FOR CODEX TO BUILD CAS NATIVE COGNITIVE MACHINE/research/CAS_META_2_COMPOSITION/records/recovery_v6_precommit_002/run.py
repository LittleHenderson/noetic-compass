"""Record scoped, pure precommit checks. Never contact AWS or load a model."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def digest(raw): return sha256(raw).hexdigest()
def write(path,value):
    with path.open("xb") as f:
        f.write((json.dumps(value,sort_keys=True,indent=2)+"\n").encode())
def snapshot():
    sp=importlib.util.spec_from_file_location("recovery_profile_precommit",ROOT/"tools/experiment_profiles_recovery_v6.py")
    p=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(p)
    admission=(ROOT.parents[1]/p.ADMISSION_PATH).read_bytes()
    names=p.allowlist(admission)
    members={name:(ROOT.parents[1]/name).read_bytes() for name in names}
    p.make_record(members)
    return {name:digest(raw) for name,raw in sorted(members.items())}
def main():
    if (HERE/"receipt.json").exists(): raise ValueError("NEW_CHECK_DIRECTORY_REQUIRED")
    before=snapshot()
    scratch=Path(tempfile.mkdtemp(prefix="cas-recovery-pure-"))
    selected=[
        "tests/test_contrast_recovery_v6_core.py","tests/test_contrast_recovery_v6_binding.py",
        "tests/test_contrast_recovery_v6_gpu.py","tests/test_launch_recovery_v6.py",
        "tests/test_recovery_remote_v6.py","tests/test_recovery_v6_profile.py",
        "tests/test_contrast_v7_bridge.py",
        "tests/test_launch.py::LaunchTests::test_cleanup_deletes_owned_role_when_policy_already_absent",
        "tests/test_launch.py::LaunchTests::test_cleanup_will_not_delete_untagged_security_group",
        "tests/test_validate_local_v3.py::test_real_sdk_exception_import_works_without_live_client_modules"]
    child=("import sys;from tools.validate_local_v3 import NoNeuralOrProviderImports;"
           "sys.meta_path.insert(0,NoNeuralOrProviderImports());import pytest;"
           "raise SystemExit(pytest.main(sys.argv[1:]))")
    command=[sys.executable,"-B","-c",child,"-q","-p","no:cacheprovider",
             "--junitxml",str(HERE/"tests.xml"),"--basetemp",str(scratch/"pytest"),*selected]
    env={k:v for k,v in os.environ.items() if not k.startswith(("CAS_META1_RUN_","CAS_META2_RUN_"))}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env["PYTHONPATH"]=str(ROOT)
    write(HERE/"command.json",command)
    write(HERE/"source_before.json",before)
    started=time.monotonic()
    result={"started_utc":datetime.now(timezone.utc).isoformat(),"completed":False,"command":command,
            "neural_execution":False,"provider_execution":False,"full_suite":False,
            "source_files_verified":len(before),"scratch_retained":str(scratch),
            "python":sys.version,"executable":sys.executable,"platform":platform.platform(),
            "head_before_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()}
    try:
        with (HERE/"stdout.txt").open("xb") as out,(HERE/"stderr.txt").open("xb") as err:
            childproc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=err)
            result["pid"]=childproc.pid
            try: childproc.wait(timeout=300)
            except subprocess.TimeoutExpired:
                childproc.kill();childproc.wait()
                result["timed_out"]=True
                raise
            result["returncode"]=childproc.returncode
        after=snapshot()
        write(HERE/"source_after.json",after)
        result["source_bytes_unchanged"]=before==after
        xml=ET.parse(HERE/"tests.xml").getroot()
        suites=list(xml.iter("testsuite"))
        result["counts"]={k:sum(int(x.get(k,"0")) for x in suites) for k in ("tests","failures","errors","skipped")}
        text=(HERE/"stdout.txt").read_text()
        found=re.findall(r"(?<!subtests )(\d+) passed",text)
        subs=re.findall(r"(\d+) subtests passed",text)
        result["passed_functions"]=int(found[-1]) if found else None
        result["passed_subtests"]=int(subs[-1]) if subs else 0
        result["completed"]=(childproc.returncode==0 and before==after
            and result["counts"]["failures"]==result["counts"]["errors"]==0 and result["counts"]["skipped"]==2)
    except BaseException as exc:
        result["failure"]={"type":type(exc).__name__,"message":str(exc)}
    finally:
        result["wall_seconds"]=time.monotonic()-started
        result["finished_utc"]=datetime.now(timezone.utc).isoformat()
        result["raw_sha256"]={name:digest((HERE/name).read_bytes()) for name in
                             ("stdout.txt","stderr.txt","tests.xml","command.json") if (HERE/name).is_file()}
        result["script_sha256"]=digest(Path(__file__).read_bytes())
        write(HERE/"receipt.json",result)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["completed"] else 1
if __name__=="__main__": raise SystemExit(main())
