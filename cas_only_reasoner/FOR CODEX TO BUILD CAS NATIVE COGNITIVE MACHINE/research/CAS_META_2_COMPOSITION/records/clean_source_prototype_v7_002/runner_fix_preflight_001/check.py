import ast, hashlib, importlib.abc, importlib.util, io, json, subprocess, sys
from pathlib import Path
SOURCE = "246f490d7d0dad2c18cc14a125b07e296ed74a3c"
root = Path.cwd()
repo = Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],text=True).strip())
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split(".")[0] in {"torch","casformer","cas_cjt","tensorflow","jax","cupy","boto3","botocore"}:
   raise RuntimeError("NO_NEURAL_PROVIDER:"+fullname)
sys.meta_path.insert(0,Guard())
def raw_git(path):
 return subprocess.check_output(["git","cat-file","blob",SOURCE+":"+path.relative_to(repo).as_posix()])
def checked_module(relative,name):
 path=root/relative
 assert path.read_bytes()==raw_git(path),relative
 s=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 return m
p=checked_module("tools/experiment_profiles_prototype_v7.py","preflight_profile")
v=checked_module("tools/validate_local_v3.py","preflight_validator")
admission=(root.parents[1]/p.ADMISSION_PATH).read_bytes()
pins_raw=(root.parents[1]/p.SOURCE_PINS_PATH).read_bytes()
closed=p.launch_allowlist(admission,pins_raw)
expected={}
def add(path,pin=None):
 assert path.is_file(),str(path)
 assert not any(x.is_symlink() or getattr(x,"is_junction",lambda:False)() for x in (path,*path.parents))
 name=path.relative_to(repo).as_posix()
 expected[name]=pin or hashlib.sha256(path.read_bytes()).hexdigest()
for name in closed:add(root.parents[1]/name)
for name,pin in v.source_snapshot().items():add(root/name,pin)
protected=v.protected_snapshot()
for name,pin in protected["files_sha256"].items():add(root.parent/name,pin)
add(root.parent/"CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json",protected["manifest_sha256"])
integration="records/prototype_training_integration_v7_001"
extra=[
 "records/contrast_v7_bridge_checks_001/run.py",
 "records/contrast_v7_bridge_checks_001/source_pins.json",
 "records/contrast_v7_exclusions_001/build.py",
 "records/contrast_v7_exclusions_001/test_build.py",
 "records/contrast_v6_exclusions_001/inventory.json",
 integration+"/adapter.py",integration+"/public_data.py",integration+"/test_public_data.py",
 integration+"/test_adapter.py",integration+"/run_checks.py"]
for name in extra:add(root/name)
for directory in (integration+"/checks_002/positive_merge/bundle","records/contrast_v6_bundle_probe_001/dataset"):
 manifest=json.loads((root/directory/"manifest.json").read_bytes())
 add(root/directory/"manifest.json")
 for name,pin in manifest["sha256"].items():add(root/directory/name,pin)
for name,pin in json.loads(pins_raw)["frozen_files_sha256"].items():add(root/name,pin)
for name in ("manifest.json","train.json","validation.json","test_public.json","tokenizer.json","training_imports.json","base_manifest.json","base_train.json"):
 add(root/"records/contrast_v7_bridge_checks_001/roundtrip/trainer_input"/name)
for name in ("probe.py","sitecustomize.py"):add(root/"records/contrast_v7_cold_child_review_001"/name)
add(root/"records/clean_source_prototype_v7_002/README.md")
names=sorted(expected)
r=subprocess.run(["git","cat-file","--batch"],input="".join(SOURCE+":"+name+"\n" for name in names).encode(),capture_output=True,check=True)
stream=io.BytesIO(r.stdout)
for name in names:
 h=stream.readline().decode().split()
 assert len(h)==3 and h[1]=="blob",(name,h)
 raw=stream.read(int(h[2]));assert stream.read(1)==b"\n"
 assert raw==(repo/name).read_bytes(),name
 assert hashlib.sha256(raw).hexdigest()==expected[name],name
assert stream.read()==b""
runner=root/"records/clean_source_prototype_v7_002/run.py"
ast.parse(runner.read_bytes())
assert "records/contrast_v7_exclusions_001/inventory.json" not in runner.read_text()
assert set(extra).issubset(set(x.value for x in ast.walk(ast.parse(runner.read_bytes())) if isinstance(x,ast.Constant) and isinstance(x.value,str)) | {integration+"/"+n for n in ("adapter.py","public_data.py","test_public_data.py","test_adapter.py","run_checks.py")})
print(json.dumps({"status":"ALL_REAL_RETAINED_INPUTS_GIT_RAW_MATCH","source_sha":SOURCE,
 "closed_inputs":len(closed),"protected_files":protected["files_verified"],"all_verified_distinct_files":len(names),
 "missing_or_mismatched":[],"explicit_portable_helpers":extra,
 "source_profile_sha256":hashlib.sha256((root/"tools/experiment_profiles_prototype_v7.py").read_bytes()).hexdigest(),
 "corrected_runner_sha256":hashlib.sha256(runner.read_bytes()).hexdigest(),
 "runner_excluded_from_old_source_equality":"Only the authorized one-line correction is uncommitted.",
 "runner_imported_or_executed":False,"worktree_created":False,"neural_provider_imports":False},indent=2))
