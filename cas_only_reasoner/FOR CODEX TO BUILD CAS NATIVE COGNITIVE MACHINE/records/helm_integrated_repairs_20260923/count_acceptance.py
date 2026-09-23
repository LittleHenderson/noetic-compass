"""Count selected pytest cases/functions without adding superseded runs."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT.parents[1]
OUT=Path(__file__).resolve().parent
selected={
 "tests/test_helm_analogy_focus_comparison.py":"new",
 "records/typed_pointer_001/test_historical_rescore_rule.py":"new",
 "records/typed_pointer_001/test_trusted_rescore.py":"existing",
 "research/helm_cas_expression_lab/test_q4_panel_evaluation.py":"new",
}
runs=[]
for filename in ("builder_acceptance.xml","q4_integration_tests_final.xml"):
 path=OUT/filename
 cases=[]
 for case in ET.parse(path).getroot().iter("testcase"):
  status="failed" if case.find("failure") is not None else "error" if case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
  cases.append({"class":case.get("classname"),"name":case.get("name"),"status":status})
 runs.append({"path":str(path.resolve()),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"cases":cases,
              "counts":{status:sum(c["status"]==status for c in cases) for status in ("passed","failed","error","skipped")},
              "collected_functions":len({(c["class"],c["name"].split("[")[0]) for c in cases})})
files=[]
for path,kind in selected.items():
 nodes=ast.walk(ast.parse((ROOT/path).read_text(encoding="utf-8")))
 functions=[n.name for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_")]
 cases=[c for r in runs for c in r["cases"] if c["class"].endswith(path[:-3].replace("/", ".")) or c["class"].endswith(Path(path).stem)]
 files.append({"path":str((ROOT/path).resolve()),"category":kind,"functions":functions,"function_count":len(functions),
               "case_count":len(cases),"passed":sum(c["status"]=="passed" for c in cases),"skipped":sum(c["status"]=="skipped" for c in cases)})
tracked=subprocess.check_output(["git","-C",str(REPO),"ls-files","-z"],text=True).split("\0")
census=[p for p in tracked if Path(p).name.startswith("test_") and p.endswith(".py")]
chosen={str((ROOT/p).relative_to(REPO)).replace("\\","/") for p in selected}
attempted=ROOT/"research/CAS_META_2_COMPOSITION/tests/test_typed_teaching_slots.py"
unloaded=sorted(set(census)-chosen-{attempted.relative_to(REPO).as_posix()})
report={"schema":"helm.repair-test-accounting/1","files":files,"runs":runs,
        "totals":{key:sum(f[key] for f in files) for key in ("function_count","case_count","passed","skipped")},
        "by_category":{kind:{key:sum(f[key] for f in files if f["category"]==kind) for key in ("function_count","case_count","passed","skipped")} for kind in ("new","existing")},
        "loaded_test_files_in_completed_runs":len(files),"additional_attempted_test_files":[str(attempted.resolve())],
        "all_loaded_test_files":len(files)+1,"unloaded_test_filenames":unloaded,"unloaded_file_count":len(unloaded),
        "unloaded_scope":"Tracked repository filename census, not a whole-repository collectability claim.",
        "other_checks":{"historical_population_recheck":"660 presentation checks; 88 unique exact checker inputs, 572 memoized identical inputs; 6 original run outcomes",
                        "evidence":"429/429 manifested research outputs; Q4 handoff verified 29/29 LF-normalized, 21/29 raw before integration fixes; new active files and acceptance use the parent OUTPUT_MANIFEST",
                        "not_completed":["Full-registry rescore: 900-second timeout","Selected older decoder regression: stopped after 900-second wall bound during large shared fixture; no completed-case claim"],
                        "earlier_failures":"Initial rescorer:2fail/791pass/9skip; initial analogy:1fail/9pass; Q4 initial:1fail/31pass. Superseded by selected final runs, not deleted."}}
(OUT/"TEST_ACCOUNTING.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(report["totals"]);print(report["by_category"]);print({"unloaded":len(unloaded)})
