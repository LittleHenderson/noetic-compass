"""Clean recovery source audit; no packet, neural, provider or paid execution."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SOURCE = "bd3341b0da893d0a68cfc05fb454848d2f027cd7"
HERE = Path(__file__).resolve().parent
REPO = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/recovery-v6-audit-bd3341b0")
ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/recovery-v6-audit-bd3341b0/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION")
BRIDGE = ROOT/"records/clean_recovery_portable_v7_001"
FULL = ROOT/"records/clean_source_recovery_v6_001/full_validation"

def digest(raw): return sha256(raw).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json.dumps(value,sort_keys=True,indent=2,allow_nan=False).encode()+b"\n")
def git(*args):
    return subprocess.run(["git","-C",str(REPO),*args],capture_output=True,check=True,timeout=60).stdout

def load_checked(path,name):
    key=path.relative_to(REPO).as_posix()
    assert git("show",SOURCE+":"+key)==path.read_bytes(), key
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def snapshot(base,validator,old_profile,recovery):
    result=base.snapshot(validator,old_profile)
    admission_path=ROOT.parent.parent/recovery.ADMISSION_PATH
    admission=admission_path.read_bytes()
    assert digest(admission)==recovery.ADMISSION_SHA256
    old=recovery.frozen_inputs(admission)
    names=recovery.allowlist(admission)
    assert len(names)==557 and len(old)==538
    members={name:(ROOT.parent.parent/name).read_bytes() for name in sorted(names)}
    experiment=recovery.make_record(members)
    identities=dict(result["files"])
    expected={}
    for name,raw in members.items():
        relative=(ROOT.parent.parent/name).relative_to(REPO).as_posix()
        expected[relative]=old.get(name,digest(raw))
    exposure=ROOT/"records/contrast_v7_exclusions_from_failed_v6_001"
    for path in sorted(exposure.iterdir()):
        if path.is_file():
            relative=path.relative_to(REPO).as_posix()
            expected[relative]=digest(path.read_bytes())
    blobs=base.committed(sorted(expected))
    for name,pin in expected.items():
        raw=(REPO/name).read_bytes()
        assert digest(raw)==pin==digest(blobs[name]),name
        identities[name]={"expected_sha256":pin,"git_sha256":digest(blobs[name]),
                          "checkout_sha256":digest(raw),"bytes":len(raw)}
    inventory_raw=(exposure/"inventory.json").read_bytes()
    receipt_raw=(exposure/"receipt.json").read_bytes()
    assert digest(inventory_raw)=="9f579ea2d593671dfddf16db39aa22563d6b98f7388758d2a2b99539e66ed623"
    assert digest(receipt_raw)=="a965297027e5ba1c1a2340bb9f9c40d52297debd91af5c4e4fab57065a5d6267"
    inventory=json.loads(inventory_raw)
    receipt=json.loads(receipt_raw)
    prior_path=ROOT/"records/contrast_v6_exclusions_001/inventory.json"
    prior_raw=prior_path.read_bytes()
    assert digest(prior_raw)==inventory["previous_inventory_sha256"]==receipt["prior_inventory_sha256"]
    prior=json.loads(prior_raw)
    signatures=inventory["graph_signatures"]
    assert signatures==sorted(set(signatures)) and len(signatures)==inventory["count"]==8837
    assert prior["count"]==8053 and set(prior["graph_signatures"])<=set(signatures)
    assert all(inventory["origins"][name]==record for name,record in prior["origins"].items())
    union=set()
    for origin in inventory["origins"].values():
        assert origin["count"]==len(set(origin["graph_signatures"]))
        union.update(origin["graph_signatures"])
    assert union==set(signatures)
    assert inventory["native_success_claim"] is False and inventory["neural_execution"] is False
    assert receipt["inventory_sha256"]==digest(inventory_raw)
    result.update(files=dict(sorted(identities.items())),all_checked_files=len(identities),
        recovery_source_files=557,original_recovery_dependency_files=538,
        recovery_experiment=experiment,
        recovery_source_manifest_sha256=digest(members[recovery.SOURCE_MANIFEST_PATH]),
        exposure_inventory={"count":8837,"previous_count":8053,"added_unique":784,
            "sha256":digest(inventory_raw),"receipt_sha256":digest(receipt_raw),
            "prior_origins_preserved":True,"union_recounted":True,
            "underlying_packet_or_task_files_reopened":False})
    return result

def stage(name,command,env,timeout):
    started=datetime.now(timezone.utc).isoformat()
    print(json.dumps({"stage":name,"started_utc":started}),flush=True)
    clock=time.monotonic()
    try:
        run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=timeout)
        timed_out=False
    except subprocess.TimeoutExpired as error:
        run=subprocess.CompletedProcess(command,124,error.stdout or b"",error.stderr or b"")
        timed_out=True
    (HERE/(name+".stdout.txt")).write_bytes(run.stdout)
    (HERE/(name+".stderr.txt")).write_bytes(run.stderr)
    result={"name":name,"command":command,"cwd":str(ROOT),"returncode":run.returncode,
        "timed_out":timed_out,"timeout_seconds":timeout,"started_utc":started,
        "finished_utc":datetime.now(timezone.utc).isoformat(),"wall_seconds":time.monotonic()-clock,
        "stdout_sha256":digest(run.stdout),"stderr_sha256":digest(run.stderr)}
    save(HERE/(name+".process.json"),result)
    print(json.dumps(result),flush=True)
    return result

def copy_records(source,target):
    target.mkdir(exist_ok=False)
    for path in sorted(source.iterdir()):
        if path.is_file():
            assert not path.is_symlink()
            shutil.copyfile(path,target/path.name)

def main():
    assert not (HERE/"source_before.json").exists()
    initial=git("status","--porcelain","--untracked-files=all").decode()
    assert not initial.strip()
    # Reuse only the committed audit helper's read/check functions, never its main.
    base=load_checked(ROOT/"records/clean_source_prototype_v7_001/run.py","frozen_clean_source_audit_helpers")
    base.SOURCE,base.REPO,base.ROOT=SOURCE,REPO,ROOT
    base.INTEGRATION=ROOT/"records/prototype_training_integration_v7_001"
    validator=load_checked(ROOT/"tools/validate_local_v3.py","recovery_clean_canonical_validator")
    sys.meta_path.insert(0,validator.NoNeuralOrProviderImports())
    old_profile=load_checked(ROOT/"tools/experiment_profiles_contrast_v6.py","recovery_clean_old_profile")
    recovery=load_checked(ROOT/"tools/experiment_profiles_recovery_v6.py","recovery_clean_profile")
    before=snapshot(base,validator,old_profile,recovery)
    save(HERE/"source_before.json",before)
    assert not BRIDGE.exists() and not FULL.exists()
    BRIDGE.mkdir()
    original=ROOT/"records/contrast_v7_bridge_checks_001/run.py"
    shutil.copyfile(original,BRIDGE/"run.py")
    assert original.read_bytes()==(BRIDGE/"run.py").read_bytes()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="",PYTEST_PLUGINS="",CUDA_VISIBLE_DEVICES="",
        CAS_META1_RUN_GPU_TESTS="0",CAS_META2_RUN_GPU_TESTS="0")
    env.pop("PYTHONPATH",None)
    start=time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        full=pool.submit(stage,"full_validator",[sys.executable,"-B",str(ROOT/"tools/validate_local_v3.py"),
            "--output",str(FULL)],env,660)
        bridge=pool.submit(stage,"portable_bridge",[sys.executable,"-B",str(BRIDGE/"run.py")],env,780)
        stages=[full.result(),bridge.result()]
    after=snapshot(base,validator,old_profile,recovery)
    save(HERE/"source_after.json",after)
    for source,name in ((FULL,"full_validator_artifacts"),(BRIDGE,"portable_bridge_artifacts")):
        if source.exists(): copy_records(source,HERE/name)
    full=json.loads((FULL/"receipt.json").read_bytes()) if (FULL/"receipt.json").exists() else {}
    bridge=json.loads((BRIDGE/"receipt.json").read_bytes()) if (BRIDGE/"receipt.json").exists() else {}
    passed=all(row["returncode"]==0 for row in stages) and before==after and full.get("completed") and bridge.get("completed")
    versions={}
    for package in ("pytest","jsonschema","torch","boto3","botocore"):
        try: versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: versions[package]=None
    result={"schema":"cas-meta2-clean-recovery-source-audit/6","completed":bool(passed),
        "status":"CLEAN_RECOVERY_SOURCE_CHECKS_PASSED" if passed else "CLEAN_RECOVERY_SOURCE_CHECKS_FAILED",
        "source_sha":SOURCE,"source_worktree":str(REPO),"source_package":str(ROOT),
        "initial_git_status":initial,"final_git_status":git("status","--porcelain","--untracked-files=all").decode(),
        "source_unchanged":before==after,"all_checked_files":before["all_checked_files"],
        "source_files":before["source_files"],"protected_files":before["protected_files"],
        "recovery_source_files":557,"original_recovery_dependency_files":538,
        "git_blob_or_checkout_mismatches":[],"processes":stages,"wall_seconds":time.monotonic()-start,
        "full_validator":{key:full.get(key) for key in ("completed","counts","passed_test_functions",
            "passed_subtests","sources_unchanged","protected_unchanged","errors")},
        "portable_bridge":{key:bridge.get(key) for key in ("completed","source_unchanged",
            "original_manifest_sha256","source_pins_sha256","loader_sha256")},
        "exposure_inventory":before["exposure_inventory"],
        "existing_environment":{"python":sys.version,"executable":sys.executable,
                                "distribution_metadata_only":versions},
        "fresh_environment_or_install":False,"core_autocrlf_on_checkout":False,
        "neural_or_provider_work":False,"packet_opened":False,"registered_dataset_generated":False,
        "inherited_pythonpath_removed":True,"no_double_counting_of_overlapping_tests":True,
        "boundary":"Clean source/control and saved diagnostic proof only; no GPU, provider, paid launch, training or held-out recovery execution."}
    save(HERE/"receipt.json",result)
    print(json.dumps({key:result[key] for key in ("status","completed","full_validator",
        "portable_bridge","source_unchanged","all_checked_files","wall_seconds")},indent=2),flush=True)
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())

