"""Bounded recheck of the exact historical 18-question population, not a full registry rescore.

Identity-check every saved prediction file first. Recheck all presentations of every
historical gate question with the preserved private checker; reuse only byte-identical
checker inputs. Use the corrected active tool's rule and agreement functions.
The expensive population-selection/zero-learning-floor calculation is not rerun:
the exact original question IDs must agree between both original readings and anchors.
"""
import collections
import hashlib
import json
import pathlib
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=ROOT/"records/typed_pointer_001"
OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import trusted_rescore as T

def run(source):
    started=time.monotonic()
    originals=[]
    cases=[("helm1","study_helm1_certified.json","trust_anchor_helm1_certified.json","admission_helm1_certified/gate_reading.json","receipt_helm1_certified_"),
           ("helm2","admission_001/study.json","trust_anchor_helm2_experimental_20208c92.json","admission_001/gate_reading.json","receipt_")]
    jobs=[]
    # All identity checks precede any private-checker import.
    for name,study,anchor,gate,prefix in cases:
        overrides={str(seed):str(source/(prefix+str(seed))) for seed in (20260917,20260918,20260919)}
        check=T._Run()
        a,s,p=T._safe_checks(check,HERE/study,HERE/anchor,overrides)
        assert not check.reasons,check.reasons
        g=json.loads((HERE/gate).read_text(encoding="utf-8"))
        for seed in p:
            assert g["seeds"][seed]["G_LEARN_population"]["keys"]==a["population"]["question_ids"]
        jobs.append((name,a,p,g,check))
        originals.extend(T.file_pin(HERE/x)|{"path":str(HERE/x)} for x in (study,anchor,gate))
    before=T.code_closure_pins()
    sys.path.insert(0,str(T.CODE_ROOT))
    from cas_meta2.typed_teaching import worker_contract as baseline, checker, course
    frozen,_,_=baseline.load_material(ROOT)  # pinned public course/tokenizer; no development expansion
    by_id={r["record_id"]:r for r in frozen["registry"]}
    packet_cache,answer_cache={},{}
    report={"schema":"helm.historical-population-recheck/1",
            "scope":"all presentations of original 18 gate questions, every seed/phase; not the 564-record full registry",
            "population_source":"original frozen gate keys matched against unchanged external anchors; population selection and zero-learning floor NOT recalculated",
            "source_files":originals,"tool":T.file_pin(T.__file__),"checks":[],"studies":{}}
    for name,a,predictions,g,safety in jobs:
        assert checker.checker_profile()["profile_digest"]==a["checker"]["profile_digest"]
        assert frozen["course_digest"]==a["course_digest"]
        population=a["population"]["question_ids"]
        chosen={rid:r for rid,r in by_id.items() if r["query"]["query_id"] in population}
        kind_of={r["query"]["query_id"]:r["query"]["kind"] for r in chosen.values()}
        world_of={r["query"]["query_id"]:r["source_world_id"] for r in chosen.values()}
        assert all(a["population"]["kind_of"][q]==kind_of[q] and a["population"]["world_of"][q]==world_of[q] for q in population)
        results={}
        for seed,info in predictions.items():
            phase_correct={}
            for phase,slot in info["phases"].items():
                rows=collections.defaultdict(list)
                selected=[r for r in slot["predictions"] if r["record_id"] in chosen]
                assert {r["record_id"] for r in selected}==set(chosen)
                for prediction in selected:
                    assert time.monotonic()-started<900,"CPU_LIMIT"
                    rid=prediction["record_id"]
                    if rid not in packet_cache:
                        packet_cache[rid]=course.model_packet(frozen,rid)
                    packet=packet_cache[rid]
                    key=hashlib.sha256(T._canon([packet["source"],packet["record"]["query"],prediction["answer"]])).hexdigest()
                    reused=key in answer_cache
                    if not reused:
                        answer_cache[key]=checker.check_answer(packet["source"],packet["record"]["query"],prediction["answer"])
                    checked=answer_cache[key]
                    rows[checked["query_id"]].append(checked["correct"])
                    report["checks"].append({"study":name,"seed":seed,"phase":phase,"record_id":rid,
                        "prediction_id":prediction["prediction_id"],"original_answer":prediction["answer"],
                        "correct":checked["correct"],"check_digest":checked["check_digest"],
                        "identical_input_reused":reused,"checker_input_sha256":key})
                assert set(rows)==set(population)
                phase_correct[phase]={q:all(v) for q,v in rows.items()}
            initial,final=phase_correct["course_p00"],phase_correct["course_p10"]
            gains=[q for q in population if not initial[q] and final[q]]
            losses=[q for q in population if initial[q] and not final[q]]
            result={"gained":len(gains),"broken":len(losses),"initial_correct":sum(initial.values()),"final_correct":sum(final.values()),
                    **T.historical_seed_result(len(gains),len(losses),[kind_of[q] for q in gains],[world_of[q] for q in gains])}
            comparison=T.compare_seed_result(g["seeds"][seed]["G_LEARN_population"],result)
            assert comparison["agree"],comparison
            results[seed]=result|{"agreement":comparison}
            print(name,seed,result["passed"],result["p_one_sided"],flush=True)
        label="LEARNS_NEW_WORLDS" if all(r["passed"] for r in results.values()) else "NO_TRANSFER_TO_NEW_WORLDS"
        assert label==g["label"]
        report["studies"][name]={"per_seed":results,"label":label,"population_questions":len(population),"presentations_per_phase":len(chosen)}
    assert before==T.code_closure_pins(),"SOURCE_CHANGED"
    report.update(status="HISTORICAL_POPULATION_REPRODUCED",unique_private_checker_calls=len(answer_cache),
                  presentation_checks=len(report["checks"]),elapsed_seconds=time.monotonic()-started,
                  frozen_grader=T.file_pin(T.GRADER),historical_rule=T.HISTORICAL_RULE)
    destination=OUT/"historical_population_recheck.json"
    with destination.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2)
        stream.write("\n")

if __name__=="__main__":
    run(pathlib.Path(sys.argv[1]).resolve())
