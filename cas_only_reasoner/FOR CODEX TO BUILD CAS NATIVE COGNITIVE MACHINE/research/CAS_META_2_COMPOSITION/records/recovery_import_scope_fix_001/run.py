"""Test-only fresh-import correction; no package, model or provider execution."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from uuid import uuid4
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES=("tests/test_contrast_recovery_v6_core.py","tests/test_recovery_v6_profile.py")
SELECTED=[FILES[0]+"::RecoveryCoreTests::test_module_imports_remain_pure",
          FILES[1]+"::test_no_neural_import"]
INTEGRATION=["tests/test_launch.py::LaunchTests::test_cleanup_deletes_owned_role_when_policy_already_absent",
 "tests/test_launch.py::LaunchTests::test_cleanup_will_not_delete_untagged_security_group",
 "tests/test_validate_local_v3.py::test_real_sdk_exception_import_works_without_live_client_modules"]
def sha(path): return sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open("xb") as stream:
        stream.write(json.dumps(value,sort_keys=True,indent=2).encode()+b"\n")
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--child",action="store_true")
    parser.add_argument("--stage",choices=("focused","integration"))
    parser.add_argument("--scratch",type=Path)
    args=parser.parse_args()
    if args.child:
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location("canonical_pure_validator",ROOT/"tools/validate_local_v3.py")
        validator=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        sys.meta_path.insert(0,validator.NoNeuralOrProviderImports())
        if args.stage=="integration":
            # Simulate the unrelated native-module name without importing native code.
            sys.modules["cas_meta2.native"]=ModuleType("cas_meta2.native")
            from botocore.exceptions import ClientError
            print(json.dumps({"parent_native_module":"explicit inert test stub",
                              "parent_botocore":"canonical permitted pure exception closure"}),flush=True)
        import pytest
        selected=SELECTED+(INTEGRATION if args.stage=="integration" else [])
        return pytest.main([*selected,"-q","-s","-p","no:cacheprovider",
            "--basetemp="+str(args.scratch/"pytest"),"--junitxml="+str(HERE/args.stage/"tests.xml")])
    assert not (HERE/"receipt.json").exists()
    before={name:sha(ROOT/name) for name in FILES}
    outer=[p for p in ROOT.parents if p.name=="FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"][-1]
    processes=[]
    for phase in ("focused","integration"):
        output=HERE/phase
        output.mkdir(exist_ok=False)
        scratch=outer/"_tmp"/("recovery-import-"+uuid4().hex[:12])
        assert scratch.parent.resolve()==(outer/"_tmp").resolve() and not scratch.exists()
        assert not any(p.is_symlink() or getattr(p,"is_junction",lambda:False)() for p in (scratch,*scratch.parents))
        (scratch/"temp").mkdir(parents=True)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTEST_ADDOPTS="",PYTEST_PLUGINS="",CUDA_VISIBLE_DEVICES="",
            CAS_META1_RUN_GPU_TESTS="0",CAS_META2_RUN_GPU_TESTS="0",
            TEMP=str(scratch/"temp"),TMP=str(scratch/"temp"),TMPDIR=str(scratch/"temp"))
        env.pop("PYTHONPATH",None)
        command=[sys.executable,"-B",str(Path(__file__).resolve()),"--child","--stage",phase,"--scratch",str(scratch)]
        started=datetime.now(timezone.utc).isoformat()
        try:
            run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=120)
            timed_out=False
        except subprocess.TimeoutExpired as error:
            run=subprocess.CompletedProcess(command,124,error.stdout or b"",error.stderr or b"")
            timed_out=True
        (output/"stdout.txt").write_bytes(run.stdout)
        (output/"stderr.txt").write_bytes(run.stderr)
        suites=ET.parse(output/"tests.xml").getroot().findall("testsuite") if (output/"tests.xml").exists() else []
        row={"stage":phase,"command":command,"cwd":str(ROOT),"returncode":run.returncode,
            "timed_out":timed_out,"started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
            "scratch":str(scratch),"counts":{key:sum(int(s.get(key,"0")) for s in suites)
                for key in ("tests","failures","errors","skipped")} if suites else None,
            "stdout_sha256":sha(output/"stdout.txt"),"stderr_sha256":sha(output/"stderr.txt")}
        save(output/"receipt.json",row)
        processes.append(row)
        print(run.stdout.decode(errors="replace"),flush=True)
        if run.returncode: print(run.stderr.decode(errors="replace"),flush=True)
    after={name:sha(ROOT/name) for name in FILES}
    success=all(row["returncode"]==0 for row in processes) and before==after
    receipt={"completed":success,"processes":processes,"source_before":before,"source_after":after,
        "source_unchanged":before==after,"python":sys.version,"executable":sys.executable,
        "canonical_guard_unchanged":True,"production_sources_changed":False,
        "neural_or_provider_execution":False,"packet_or_current_task_reads":False,
        "boundary":"Two corrected tests plus explicit mixed-import integration only; not full-suite or GPU proof."}
    save(HERE/"receipt.json",receipt)
    print(json.dumps(receipt,indent=2),flush=True)
    return 0 if success else 1
if __name__=="__main__":
    raise SystemExit(main())

