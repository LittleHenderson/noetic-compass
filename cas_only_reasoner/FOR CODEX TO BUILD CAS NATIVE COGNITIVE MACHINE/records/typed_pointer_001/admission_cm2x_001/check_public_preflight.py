"""Public, CPU-only scientific identity checks; never executes a model or provider."""
from pathlib import Path
import ast
from hashlib import sha256
import json
import math
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "research/CAS_META_2_COMPOSITION")]
from aws import typed_pointer_launch as launch
from cas_meta2.typed_teaching import pointer_contract as contract

R18 = "3df31d965bb2eabb168ae7efbf03300a1a1144d7"
PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
SCIENCE = [
 "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + name
 for name in ("pointer_learner.py", "loss_plan.py", "worker_contract.py", "practice_contract.py",
              "matched_contract.py", "encoder.py", "pointer_inputs.py", "checker.py", "course.py", "development.py")
]
# Only existing design declarations which express duration, output or resources.
ALLOWED = {
 "passes", "pass_checkpoints", "full_course_checkpoints", "schedule",
 "schedule_stratified_batches_digest", "max_wall_seconds",
 "worker_deadline_seconds", "instance_seconds_max", "reservation_usd",
}

ANNOTATIONS = {
 "best_checkpoint_selection": False, "evaluated_at_both_durations": True,
 "experiment_version": "cncm.typed-pointer-critical-mass-2x/1",
 "learning_rate_schedule": "CONSTANT_AS_HELM_1_0", "planned_main_updates": None,
 "pass_multiplier_over_r18": 2, "run_model_seed": 20260918,
 "training_duration_change_only": "SAME_MODEL_DATA_BATCH_ORDER_OPTIMIZER_HOLDOUT_DEV_PANEL_SCORING_AND_SOURCE_LOGIC_AS_R18_ONLY_THE_TRAINING_DURATION_AND_THE_OUTPUT_ENVELOPE_MOVE",
}

def canonical(v):
 return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def git_blob(name):
 return subprocess.check_output(["git", "-c", "core.longpaths=true", "show", R18 + ":" + PREFIX + name], cwd=ROOT)

def check(output):
 bindings = []
 for name in SCIENCE:
  before, after = git_blob(name), (ROOT/name).read_bytes()
  if before != after:
   raise ValueError("SCIENTIFIC_SOURCE_CHANGED:" + name)
  bindings.append({"path":name, "r18_sha256":sha256(before).hexdigest(), "candidate_sha256":sha256(after).hexdigest(), "equal":True})
 frozen, _, _ = contract.load_material(ROOT)
 ten, old_stats = contract.pointer_schedule(frozen, passes=10)
 twenty, new_stats = contract.pointer_schedule(frozen, passes=20)
 assert len(ten)==1470 and len(twenty)==2940 and twenty[:1470]==ten
 assert old_stats["batches_digest"] == contract.STRATIFIED_BATCHES_DIGEST_AT_10_PASSES
 learner = ast.parse((ROOT/SCIENCE[0]).read_text())
 cls = next(n for n in learner.body if isinstance(n,ast.ClassDef) and any(isinstance(f,ast.FunctionDef) and f.name=="_learning_rate" for f in n.body))
 fn = next(f for f in cls.body if isinstance(f,ast.FunctionDef) and f.name=="_learning_rate")
 env={"math":math}
 exec(compile(ast.Module(body=[fn],type_ignores=[]), "<exact-source-learning-rate>", "exec"),env)
 prior = json.loads((ROOT/"records/typed_pointer_001/admission_analogy_on_001/seeds/20260918/authority.json").read_bytes())
 old_design = prior["worker_config"]["design"]
 head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
 new_design = launch.worker_config("cas-meta2-tpntr-20260925150000-" + head[:8] + "-m-20260918", source_sha=head)["design"]
 diff=[]
 for name in sorted(set(old_design)|set(new_design)):
  a,b=old_design.get(name),new_design.get(name)
  if canonical(a)!=canonical(b) or (name in old_design)!=(name in new_design):
   annotation = name in ANNOTATIONS and name not in old_design and canonical(b)==canonical(ANNOTATIONS[name])
   diff.append({"field":name,"r18":a,"candidate":b,"r18_present":name in old_design,
                "candidate_present":name in new_design,"allowed":name in ALLOWED or annotation,
                "classification":"explicit existing-law/version annotation" if annotation else "duration/output/resource"})
 if any(not x["allowed"] for x in diff):
  raise ValueError("UNDECLARED_DESIGN_CHANGE:" + ",".join(x["field"] for x in diff if not x["allowed"]))
 assert old_design["optimizer_config"] == new_design["optimizer_config"]
 assert new_design["optimizer_config"]["learning_rate"]==0.003
 steps=[]
 for index,(a,b) in enumerate(zip(ten,twenty),1):
  old_self=SimpleNamespace(optimizer_config=old_design["optimizer_config"], planned_main_updates=None,cursor=index-1)
  new_self=SimpleNamespace(optimizer_config=new_design["optimizer_config"], planned_main_updates=None,cursor=index-1)
  lr_before,lr_after=env["_learning_rate"](old_self),env["_learning_rate"](new_self)
  assert lr_before==lr_after==0.003 and len(a["record_ids"])==len(b["record_ids"])==8
  steps.append({"step":index,"cursor_before":index-1,"r18_batch_sha256":sha256(canonical(a)).hexdigest(),
                "candidate_batch_sha256":sha256(canonical(b)).hexdigest(),"learning_rate":lr_after,
                "betas":[0.9,0.999],"epsilon":1e-8,"weight_decay":0.01,"batch_size":8,
                "loss_scale":1.0,"amp_grad_scaler":False,"gradient_clip_norm":1.0,
                "update_order":"task_mean,backward,clip,set_constant_rate,AdamW.step",
                "equal":True})
 worker_old=ast.parse(git_blob("cncm/typed_pointer_worker.py"))
 worker_new=ast.parse((ROOT/"cncm/typed_pointer_worker.py").read_text())
 old_fn=next(n for n in worker_old.body if isinstance(n,ast.FunctionDef) and n.name=="_main_training")
 new_fn=next(n for n in worker_new.body if isinstance(n,ast.FunctionDef) and n.name=="_main_training")
 assert ast.dump(old_fn,include_attributes=False)==ast.dump(new_fn,include_attributes=False)
 report={"schema":"helm.cm2x.public-preflight/1","r18_source":R18,"candidate_source":head,"checker_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
         "H1":{"status":"PASS_SOURCE_AND_ALL_1470_SCHEDULE_STEPS","main_training_ast_equal":True,"source_bindings":bindings,"steps":steps},
         "H2":{"route":"FRESH_20_PASS_NOT_R18_CHECKPOINT_RESUME",
               "reason":"Existing exact R18 original-profile continuation helper is not integrated in this versioned fresh worker.",
               "required_pass10_state":["results/evidence/main_checkpoint_1470.pt","results/evidence/main_checkpoint_1470.json"],
               "runtime_cuda_state_identity":"NOT_TESTABLE_BEFORE_JOB"},
         "H3":{"status":"PASS_DECLARED_DESIGN_DIFFERENCES_ONLY","field_count":len(set(old_design)|set(new_design)),
               "fields":[{"field":k,"r18":old_design.get(k),"candidate":new_design.get(k),"r18_present":k in old_design,"candidate_present":k in new_design,"equal":k in old_design and k in new_design and canonical(old_design.get(k))==canonical(new_design.get(k))} for k in sorted(set(old_design)|set(new_design))],
               "changed":diff,"runtime_initial_weights_and_cuda":"NOT_TESTABLE_BEFORE_JOB"},
         "limits":"Source/schedule proof, not measured CUDA trajectory or a result. Historical receipts unchanged."}
 Path(output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"H1":report["H1"]["status"],"H2":report["H2"]["route"],"H3":report["H3"]["status"],"steps":1470,"changed_fields":[x["field"] for x in diff],"report_sha256":sha256(Path(output).read_bytes()).hexdigest()}))

if __name__=="__main__":
 check(sys.argv[1])
