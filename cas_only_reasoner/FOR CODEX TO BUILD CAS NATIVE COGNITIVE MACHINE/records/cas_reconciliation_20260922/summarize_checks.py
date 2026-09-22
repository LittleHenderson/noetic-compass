"""Summarize new selected checks and match every initial setup error to its retry."""
from collections import Counter
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
CN=HERE.parents[1]
ROOT=CN.parents[1]


def main():
    initial=json.loads((HERE/"integration_checks.json").read_text(encoding="utf-8"))
    final=json.loads((HERE/"final/integration_checks.json").read_text(encoding="utf-8"))
    cases={}
    functions=set()
    selected=set()
    groups=[]
    for run in final["runs"]:
        assert run["exit_code"]==0
        for source in run["selected_test_files"]:
            selected.add(Path(source["path"]).relative_to(ROOT).as_posix())
        for case in run["cases"]:
            identity=(run["group"],case["classname"],case["name"])
            assert identity not in cases
            assert case["outcome"]=="PASS"
            cases[identity]=case
            functions.add((run["group"],case["classname"],case["name"].split("[")[0]))
        groups.append({key:run[key] for key in ("group","case_count","function_count","exit_code")})
    resolved=[]
    for run in initial["runs"]:
        for case in run["cases"]:
            if case["outcome"]!="PASS":
                identity=(run["group"],case["classname"],case["name"])
                assert cases[identity]["outcome"]=="PASS"
                resolved.append({"group":run["group"],"classname":case["classname"],"case":case["name"],
                                 "initial":case["outcome"],"final":"PASS"})
    names=subprocess.check_output(["git","ls-tree","-r","--name-only","HEAD"],cwd=ROOT,text=True).splitlines()
    candidates={name for name in names if Path(name).name.startswith("test_") and name.endswith(".py")}
    assert selected <= candidates
    assert len(cases)==836 and len(functions)==256 and len(resolved)==58
    authored=[case for identity,case in cases.items() if "test_numeric_boundaries" in identity[1]]
    authored_functions={(case["classname"],case["name"].split("[")[0]) for case in authored}
    assert len(authored)==152 and len(authored_functions)==19
    summary={
        "schema":"cas.integration-check-summary/0.1","groups":groups,
        "final":{"cases":len(cases),"functions":len(functions),"passed":len(cases),
                 "failures":0,"errors":0,"skips":0},
        "newly_authored":{"cases":152,"functions":19},
        "existing_including_imported_peer":{"cases":684,"functions":237},
        "imported_peer_existing_subset":{"cases":12,"functions":12},
        "relative_to_integration_base_eb998556":{"existing_cases":672,"existing_functions":225,
                                              "added_cases":164,"added_functions":31},
        "initial_setup":{"passed":778,"failures":0,"errors":58,
                         "reason":"Runner omitted parent temporary directory; corrected runner, no product-source correction."},
        "initial_error_reconciliation":resolved,
        "selected_test_files":sorted(selected),
        "selected_files_unloaded_or_collection_failed":[],
        "tracked_test_filename_candidates_not_selected":sorted(candidates-selected),
        "not_selected_count":len(candidates-selected),
        "historical_twenty_unloaded_modules":"Peer-reported aggregate only; exact original per-file list unavailable. This new filename census does not reconstruct it.",
        "scope":"Selected deterministic tests, not full-repository collection, code coverage, independent requirements count or neural evidence.",
        "warnings":["One unknown asyncio_mode configuration warning in numeric_interfaces with unrelated plugins disabled."],
        "repeats":"The diagnostic repair's separate203-case run overlaps numeric_interfaces and is not added to836."
    }
    (HERE/"TEST_SCOPE.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"final":summary["final"],"new":summary["newly_authored"],
                      "existing":summary["existing_including_imported_peer"],
                      "initial_errors_resolved":len(resolved),"unselected_filename_candidates":len(candidates-selected)}))


if __name__=="__main__":
    main()
