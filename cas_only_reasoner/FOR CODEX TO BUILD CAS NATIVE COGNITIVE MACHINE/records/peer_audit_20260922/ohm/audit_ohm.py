"""Read-only source audit. Writes evidence only under this script's directory.
Uses exact Git object names; never imports a model, invokes a GPU or changes source.
"""
from __future__ import annotations
import ast
import dataclasses
import decimal
import enum
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "noetic-compass-scaffold").is_dir())
HOME = next(p for p in ROOT.parents if (p / "cas_reasoner.txt").is_file())
RELPATH = "noetic-compass-scaffold/noetic-compass/api/cas_ohm"
PINS = {
    "pre": "078d00edc85fe97570b6aa3c4ea47b0ad2dad248",
    "first_fix": "86ba3d75431c56147f229f24794805a3d8504f76",
    "second_fix": "a4b2e0d7c6726968903b99c714b7b5a6b15d401f",
    "frozen": "626cc84b574e60217a103b72d2f09388d7aa5e34",
}
sys.dont_write_bytecode = True
def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])
def blob(pin, name):
    return git("show", f"{pin}:{RELPATH}/{name}")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def clean(value):
    if isinstance(value, enum.Enum):
        return value.value
    if dataclasses.is_dataclass(value):
        return {"type": type(value).__name__, **{f.name: clean(getattr(value,f.name)) for f in dataclasses.fields(value)}}
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, decimal.Decimal):
        return {"decimal": str(value)}
    if isinstance(value, dict):
        return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [clean(v) for v in value]
    return value
def call(module, expr):
    try:
        result = eval(expr, {"m": module, "nan": float("nan"), "inf": float("inf"), "Decimal": decimal.Decimal})
        return {"status": "RETURNED", "result": clean(result)}
    except Exception as exc:
        return {"status": "RAISED", "type":type(exc).__name__, "message": str(exc)}
def load(raw, target, name):
    target.write_bytes(raw)
    spec=importlib.util.spec_from_file_location(name,target)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

old_cases = [
    "m.i_pred(nan, 4.0)", "m.i_pred(8.0, nan)", "m.i_pred(8.0, inf)",
    "m.i_pred(inf, 4.0)", "m.r_total(1e308,1e308,1.0,1.0)",
    "m.i_pred(8.0,4.0)", "m.y_hat(8.0,4.0)", "m.r_total(1,2,3,4)",
    "m.r_hidden(v=8.0,i_obs=2.0,r_known=2.0)",
    "m.i_pred(8.0,0.0)", "m.i_pred(8.0,-2.0)",
    "m.r_hidden(v=nan,i_obs=2.0,r_known=2.0)",
    "m.r_hidden(v=inf,i_obs=2.0,r_known=2.0)",
    "m.asom(0.0,m.Outcome.INTENDED)",
    "m.delta_current(2.0,2.0)", "m.delta_current(2.0,0.0)",
    "m.delta_current(2.0,nan)", "m.delta_current(2.0,inf)",
]
adversarial = [
    ("FINITE_PREDICTION_OVERFLOW", "m.i_pred(1e308,1e-308)"),
    ("FINITE_PREDICTION_OVERFLOW_ALIAS", "m.y_hat(1e308,1e-308)"),
    ("PREDICTION_OVERFLOW_CONSUMER", "m.delta_current(2.0,m.i_pred(1e308,1e-308))"),
    ("FINITE_HIDDEN_RATIO_OVERFLOW", "m.r_hidden(v=1e308,i_obs=0.1,r_known=2.0)"),
    ("FINITE_HIDDEN_DIFFERENCE_OVERFLOW", "m.r_hidden(v=-1e308,i_obs=1.0,r_known=1e308)"),
    ("FINITE_DELTA_OVERFLOW", "m.delta_current(1e308,-1e308)"),
    ("NAN_OBSERVATION_FALSE_ALIGNMENT", "m.delta_current(nan,2.0)"),
    ("NAN_PREDICTION_FALSE_ALIGNMENT", "m.delta_current(2.0,nan)"),
    ("INF_MINUS_INF_FALSE_ALIGNMENT", "m.delta_current(inf,inf)"),
    ("NAN_TOLERANCE_FALSE_ALIGNMENT", "m.delta_current(100.0,0.0,tolerance=nan)"),
    ("INF_TOLERANCE_FALSE_ALIGNMENT", "m.delta_current(100.0,0.0,tolerance=inf)"),
    ("NEGATIVE_TOLERANCE_NORMALIZED", "m.delta_current(1.0,0.0,tolerance=-2.0)"),
    ("NAN_EPS_ZERO_DIVISION", "m.r_hidden(v=8,i_obs=0,r_known=2,zero_compat_eps=nan)"),
    ("INF_EPS_CENSORS_VALID_POINT", "m.r_hidden(v=8,i_obs=2,r_known=2,zero_compat_eps=inf)"),
    ("INTERVAL_ZERO_POINT_DIVISION", "m.r_hidden(v=8,i_obs=0,r_known=2,i_obs_interval=(1,2))"),
    ("REVERSED_INTERVAL_ACCEPTED", "m.r_hidden(v=8,i_obs=2,r_known=2,i_obs_interval=(3,1))"),
    ("INTERVAL_EXCLUDES_POINT_ACCEPTED", "m.r_hidden(v=8,i_obs=-2,r_known=2,i_obs_interval=(1,3))"),
    ("INTERVAL_EXTRA_ELEMENTS_ACCEPTED", "m.r_hidden(v=8,i_obs=2,r_known=2,i_obs_interval=(1,3,99))"),
    ("INTERVAL_VALID_TINY_POINT", "m.r_hidden(v=1,i_obs=1e-12,r_known=2,i_obs_interval=(0.5e-12,1.5e-12))"),
    ("POINT_ZERO_CENSORED", "m.r_hidden(v=8,i_obs=0,r_known=2)"),
    ("POINT_NAN_CENSORED", "m.r_hidden(v=8,i_obs=nan,r_known=2)"),
    ("CENSORED_IS_NOT_NUMERIC", "m.delta_current(2,m.r_hidden(v=8,i_obs=0,r_known=2))"),
    ("RCAP_INFINITY_BOUND", "m.r_cap(10,r_min=1,r_max=inf)"),
    ("RCAP_BOTH_INFINITY", "m.r_cap(5,r_min=inf,r_max=inf)"),
    ("RCAP_NAN_SCORE", "m.r_cap(nan,r_min=1,r_max=5)"),
    ("RCAP_FINITE_EXTREMES", "m.r_cap(10,r_min=1e-308,r_max=1e308)"),
    ("MATURITY_INFINITY", "m.maturity_q4(inf)"),
    ("MATURITY_NEGATIVE_INFINITY", "m.maturity_q4(-inf)"),
    ("MATURITY_NEGATIVE", "m.maturity_q4(-1)"),
    ("MATURITY_NAN", "m.maturity_q4(nan)"),
    ("MATURITY_TOLERANCE_INFINITY", "m.maturity_q4(8,prev_i_q=2,minimum_effect=inf)"),
    ("MATURITY_TOLERANCE_NAN", "m.maturity_q4(8,prev_i_q=2,minimum_effect=nan)"),
    ("MATURITY_EXACT_CUT_BELOW", "m.maturity_q4(Decimal('2.49999999999999999999999999999999999999999999999999999'))"),
    ("MATURITY_EXACT_CUT_AT", "m.maturity_q4(Decimal('2.5'))"),
    ("TREND_NAN_POINT_NO_TREND", "m.admissible_trend(nan,8,axis='I_Q/test/profile',earlier_interval=(1,2),later_interval=(7,9),minimum_effect=0.1)"),
    ("TREND_NAN_INTERVAL_NO_TREND", "m.admissible_trend(1.5,8,axis='I_Q/test/profile',earlier_interval=(nan,nan),later_interval=(7,9),minimum_effect=0.1)"),
    ("TREND_NAN_THRESHOLD_NO_TREND", "m.admissible_trend(1.5,8,axis='I_Q/test/profile',earlier_interval=(1,2),later_interval=(7,9),minimum_effect=nan)"),
    ("TREND_REVERSED_INTERVAL_ACCEPTED", "m.admissible_trend(2,8,axis='I_Q/test/profile',earlier_interval=(3,1),later_interval=(9,7),minimum_effect=0.1)"),
    ("TREND_UNSUPPORTED_RULE_ACCEPTED", "m.admissible_trend(1.5,8,axis='I_Q/test/profile',earlier_interval=(1,2),later_interval=(7,9),minimum_effect=0.1,uncertainty_rule='made-up-rule')"),
    ("TREND_EMPTY_AXIS_ACCEPTED", "m.admissible_trend(1.5,8,axis='',earlier_interval=(1,2),later_interval=(7,9),minimum_effect=0.1)"),
    ("TREND_FLOAT_LOSS", "m.admissible_trend(Decimal('1.00000000000000000001'),Decimal('1.00000000000000000004'),axis='I_Q/test/profile',earlier_interval=(Decimal('1.00000000000000000000'),Decimal('1.00000000000000000002')),later_interval=(Decimal('1.00000000000000000003'),Decimal('1.00000000000000000005')),minimum_effect=Decimal('0.000000000000000000001'))"),
    ("ELIGIBILITY_MISSING_STALENESS", "m.check_eligibility(m.Region.ACTIVE,True,True,None)"),
    ("ELIGIBILITY_MISSING_OUTCOME", "m.check_eligibility(m.Region.ACTIVE,True,True,False,outcome=None)"),
    ("ELIGIBILITY_STRING_FLAGS", "m.check_eligibility(m.Region.ACTIVE,'false','false',False)"),
    ("PREDICTION_NO_PROVENANCE_FIELD", "m.i_pred(12,4)"),
    ("TRACE_MISSING_PROVENANCE", "m.CjtQRecord(i_pred=3.0,region=m.Region.ACTIVE,outcome=m.Outcome.INTENDED)"),
    ("TRACE_UNPROVEN_ALIGNED_LABEL", "m.CjtQRecord(i_pred=3.0,region=m.Region.ACTIVE,outcome=m.Outcome.INTENDED).asom_label"),
    ("MATURITY_DECIMAL_SENTINEL_NAN", "m.maturity_q4(Decimal('NaN'))"),
    ("RESISTANCE_POSITIVE_SUBNORMAL", "m.i_pred(1.0,5e-324)"),
    ("DEFAULT_REGION_ASSUMPTION", "m.delta_current(2.0,2.0).region"),
]
report={"schema":"cas.peer-audit.ohm/1.0","source_snapshot":PINS["frozen"],"source_scope":RELPATH,"environment":{"python":sys.version,"executable":sys.executable,"platform":platform.platform()},"pins":PINS,"files":{},"suites":[],"historical_cases":{},"adversarial":[],"no_neural_execution":True}
env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"}
scratch_parent=HOME / "_test_runs"
scratch_parent.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="peer_ohm_",dir=scratch_parent) as tmp:
    scratch=Path(tmp)
    modules={}
    for label,pin in PINS.items():
        folder=scratch/label/"api"/"cas_ohm"
        folder.mkdir(parents=True)
        report["files"][label]={}
        for name in ("quantifiers.py","__init__.py","test_quantifiers.py"):
            raw=blob(pin,name)
            (folder/name).write_bytes(raw)
            report["files"][label][name]={"sha256":digest(raw),"lf_sha256":digest(raw.replace(b"\r\n",b"\n")),"bytes":len(raw)}
        module=load(blob(pin,"quantifiers.py"),scratch/f"module_{label}.py",f"audited_ohm_{label}")
        modules[label]=module
        report["historical_cases"][label]=[{"call":c,**call(module,c)} for c in old_cases]
        process=subprocess.run([sys.executable,"-B",str(folder/"test_quantifiers.py")],cwd=folder.parents[1],env=env,capture_output=True,text=True,encoding="utf-8")
        report["suites"].append({"name":label,"implementation_commit":pin,"tests_commit":pin,"command":[sys.executable,"-B","api/cas_ohm/test_quantifiers.py"],"exit_code":process.returncode,"stdout":process.stdout,"stderr":process.stderr})
    for tests_label in ("first_fix","frozen"):
        folder=scratch/("falsification_"+tests_label)/"api"/"cas_ohm"
        folder.mkdir(parents=True)
        for name in ("quantifiers.py","__init__.py"):
            (folder/name).write_bytes(blob(PINS["pre"],name))
        (folder/"test_quantifiers.py").write_bytes(blob(PINS[tests_label],"test_quantifiers.py"))
        process=subprocess.run([sys.executable,"-B",str(folder/"test_quantifiers.py")],cwd=folder.parents[1],env=env,capture_output=True,text=True,encoding="utf-8")
        report["suites"].append({"name":"pre_implementation_with_"+tests_label+"_tests","implementation_commit":PINS["pre"],"tests_commit":PINS[tests_label],"command":[sys.executable,"-B","api/cas_ohm/test_quantifiers.py"],"exit_code":process.returncode,"stdout":process.stdout,"stderr":process.stderr})
    m=modules["frozen"]
    report["adversarial"]=[{"id":name,"call":expr,**call(m,expr)} for name,expr in adversarial]
    report["attribution"]={
        "original_module_commit":"3ea9dbe67a09a4e71c38b8d2a7330229a3a0aff9",
        "original_module_committed_date":"2026-08-18T20:50:18-07:00",
        "original_and_pre_fix_blob_id":git("rev-parse",f"3ea9dbe67a09a4e71c38b8d2a7330229a3a0aff9:{RELPATH}/quantifiers.py").decode().strip(),
        "original_equals_pre_fix":blob("3ea9dbe67a09a4e71c38b8d2a7330229a3a0aff9","quantifiers.py")==blob(PINS["pre"],"quantifiers.py"),
        "probes":[]
    }
    for current, (name, expr) in zip(report["adversarial"],adversarial):
        before=call(modules["pre"],expr)
        now={k:v for k,v in current.items() if k not in ("id","call")}
        report["attribution"]["probes"].append({"id":name,"pre_fix_observation":before,"same_at_frozen":before==now})
    tree=ast.parse(blob(PINS["frozen"],"quantifiers.py"))
    report["public_function_lines"]={n.name:n.lineno for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    report["declarations"]={"exported_symbols":m.__all__,"module_honesty_rule":m.__doc__,"delta_current_default_region":m.delta_current.__defaults__[-1].value}
    pre_tree=ast.parse(blob(PINS["pre"],"quantifiers.py"))
    report["pre_guard_source"]=ast.get_source_segment(blob(PINS["pre"],"quantifiers.py").decode(),next(n for n in pre_tree.body if isinstance(n,ast.FunctionDef) and n.name=="_as_resistance"))
    pre_test=blob(PINS["pre"],"test_quantifiers.py").decode()
    pre_test_tree=ast.parse(pre_test)
    report["pre_nonfinite_test"]=ast.get_source_segment(pre_test,next(n for n in pre_test_tree.body if isinstance(n,ast.FunctionDef) and n.name=="test_r_hidden_censors_non_finite"))
    comp_path="noetic-compass-scaffold/noetic-compass/api/notation/compiler.py"
    compiler=git("show",f"{PINS['frozen']}:{comp_path}").decode()
    report["peer_compiler_ohm_references"]=[{"line":i,"text":line} for i,line in enumerate(compiler.splitlines(),1) if any(s in line for s in ("cas_ohm","delta_current","r_hidden","maturity_q4","i_pred"))]
report["script_sha256"]=digest(Path(__file__).read_bytes())
(HERE/"results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
verdicts=[
    ("OHM-1","REPRODUCES","Pre-fix returns nan, nan, 0.0, inf, inf.","historical_cases.pre[0:5]"),
    ("OHM-2","REPRODUCES","Five ValueError refusals each containing finite at first_fix and frozen.","historical_cases.first_fix[0:5]; historical_cases.frozen[0:5]"),
    ("OHM-3","REPRODUCES","Listed good examples and zero/negative refusals reproduce before/after. This is bounded to those examples, not a universal unchanged-behavior proof.","historical_cases.pre[5:11]; historical_cases.first_fix[5:11]"),
    ("OHM-4","FALSE","Historical matched39/39 and48/48 reproduce, as does42/48 using exact86ba tests against oldcode. Frozen HEADtests instead give51/51 or44/51 against oldcode: floatingHEAD instruction stale.","suites"),
    ("OHM-5","REPRODUCES","Pre-change resistance guard only tests rf<=0 and does not call the existing finite helper.","pre_guard_source"),
    ("OHM-6","REPRODUCES","asom(0.0,INTENDED)->None; delta prediction2,0,nan,inf gives WITHIN_TOLERANCE,OVERSHOOT,WITHIN_TOLERANCE,UNDERSHOOT. Known NaN defect remains live.","historical_cases.frozen[13:18]"),
    ("OHM-7","REPRODUCES","Frozen peer compiler lacks quantifier imports/calls. Scoped only to626cc84b and this cas_ohm package; does not negate separate Codex compiler helper at eb998556.","peer_compiler_ohm_references"),
    ("OHM-8","REPRODUCES","No V=IxR function exported; apparent R=V/I is within r_hidden and tagged APPARENT_SAME_SAMPLE.","declarations.exported_symbols; historical_cases.frozen[8]"),
    ("OHM-9","REPRODUCES","NaN/infinite drives return nonfinite RHidden at86ba; ValueError containing finite at a4b2/frozen.48/48 then51/51.","historical_cases.first_fix[11:13]; historical_cases.frozen[11:13]; suites"),
    ("OHM-10","REPRODUCES","Original test already covers nan/inf as i_obs; correction accurately limits missing coverage to i_pred/r_total.","pre_nonfinite_test"),
]
claim_pin_path="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/audit_package_20260922/01_CLAIMS_TO_CHECK.json"
original_claims=json.loads(git("show",f"{PINS['frozen']}:{claim_pin_path}"))
claim_lookup={c["id"]:c for c in original_claims["claims"]}
claim_report={"schema":"cas.peer-audit.ohm-claims/1.0","source_snapshot":PINS["frozen"],"command":"C:/Python314/python.exe -B audit_ohm.py","claims":[{"id":name,"original_claim":claim_lookup[name]["claim"],"auditor_verdict":verdict,"auditor_observed":observed,"literal_evidence_in_results_json":ref} for name,verdict,observed,ref in verdicts]}
(HERE/"CLAIM_VERDICTS.json").write_text(json.dumps(claim_report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
for suite in report["suites"]:
    print(suite["name"],"exit="+str(suite["exit_code"]),suite["stdout"].strip())
print("ADVERSARIAL CASES",len(report["adversarial"]))
print("WROTE",HERE/"results.json")
