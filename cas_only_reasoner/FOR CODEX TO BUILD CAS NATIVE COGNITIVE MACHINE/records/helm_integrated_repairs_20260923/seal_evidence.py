"""Seal current repair evidence and verify the branch's protected-file boundary."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

CN=Path(__file__).resolve().parents[2]
REPO=CN.parents[1]
OUT=Path(__file__).resolve().parent
REL=CN.relative_to(REPO).as_posix()
def pin(p):
 raw=p.read_bytes()
 return {"path":str(p.resolve()),"relative_path":p.relative_to(CN).as_posix(),"bytes":len(raw),
         "sha256_raw":hashlib.sha256(raw).hexdigest(),"sha256_lf":hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()}
code=[
 "records/typed_pointer_001/trusted_rescore.py","records/typed_pointer_001/test_trusted_rescore.py",
 "records/typed_pointer_001/test_historical_rescore_rule.py",
 "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py",
 "tests/test_helm_analogy_focus_comparison.py",
 "research/helm_cas_expression_lab/q4_panel_evaluation.py",
 "research/helm_cas_expression_lab/test_q4_panel_evaluation.py"]
protected=["records/typed_pointer_001/evaluate_gates.py",
           "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/slots.py",
           "records/typed_pointer_001/admission_001/gate_reading.json",
           "records/typed_pointer_001/admission_helm1_certified/gate_reading.json",
           "records/typed_pointer_001/trust_anchor_helm1_certified.json",
           "records/typed_pointer_001/trust_anchor_helm2_experimental_20208c92.json"]
rows=[]
for name in protected:
 p=CN/name
 baseline=subprocess.check_output(["git","-C",str(REPO),"show","a6e6f95b:"+REL+"/"+name])
 current=p.read_bytes()
 assert current.replace(b"\r\n",b"\n")==baseline.replace(b"\r\n",b"\n"),name
 rows.append(pin(p)|{"unchanged_from_baseline_lf":True})
allowed=set(code+["AGENTS.md","AUDIT_PACK.md","BRAIN_LINEAGE.md"])
prefixes=("records/helm_integrated_repairs_20260923/","records/helm_why_review_20260922/","_handoffs/HELM_NEXT_PHASE_20260923/")
changed=subprocess.check_output(["git","-C",str(REPO),"diff","--name-only","a6e6f95b","HEAD"],text=True).splitlines()
for name in changed:
 assert name.startswith(REL+"/"),name
 short=name[len(REL)+1:]
 assert short in allowed or short.startswith(prefixes),short
manifest={"schema":"helm.integrated-repair-output-manifest/1",
          "observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "source_commit":subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip(),
          "branch":subprocess.check_output(["git","-C",str(REPO),"branch","--show-current"],text=True).strip(),
          "code":[pin(CN/p) for p in code],"protected_files":rows,"committed_change_scope_checked":changed,
          "files":[pin(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name!="OUTPUT_MANIFEST.json"],
          "custody":"Agent-authored evidence; no independent review or owner signature fabricated.",
          "historical_helper_manifest":"q4/OUTPUT_MANIFEST.json describes helper source at03b9632f; later integration fixes are sealed here. Verify that old source on its original branch."}
# Include the preserved nested manifest itself, excluding only this self-referential file.
nested=OUT/"q4/OUTPUT_MANIFEST.json"
manifest["files"].append(pin(nested))
(OUT/"OUTPUT_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print({"output_files":len(manifest["files"]),"code_files":len(manifest["code"]),"protected_files":len(rows),"scope":"PASS"})
