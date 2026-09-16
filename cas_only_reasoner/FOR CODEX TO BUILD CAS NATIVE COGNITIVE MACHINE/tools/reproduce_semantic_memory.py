"""Source-bound engineering correction episode with independent process replay."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json,digest
from cncm.model import TerminalStatus
from cncm.native_model import NativeBudget
from cncm.nested_profile import load_nested_profile
from cncm.semantic_engine import SemanticMachine
from cncm.semantic_model import SourceStatement,MemoryRef,SemanticEquation,SemanticProblem,create_problem
from cncm.semantic_profile import load_semantic_profile
from cncm.semantic_recovery import recover_semantic_journal,_decode_proposal_batch


def write(path,value):
    raw=value if type(value) is bytes else (canonical_json(value)+"\n").encode()
    with path.open("xb") as stream:stream.write(raw)


def source(value="5",*,previous=None,scope="project",source_id="fixture-a",action="ASSERT"):
    return SourceStatement(scope,"fee",source_id,value,"TEST_FIXTURE",action,previous,
                           "engineering-fixture:semantic-memory-001")


def task(constant="26",*,updates=(),name="memory-baseline",scope="project",requirement="ATTESTED",budget=None):
    return create_problem((SemanticEquation("x","3",MemoryRef(scope,"fee",requirement),constant),),
        "x",updates=updates,problem_id=name,budget=NativeBudget() if budget is None else budget)


def restore(journal,genesis,ingress,anchor,extensions=()):
    return recover_semantic_journal(journal,trusted_genesis=genesis,trusted_ingress=ingress,
                                   expected_journal_digest=anchor,trusted_ingress_extensions=extensions)


def child(output):
    class DenyModelsAndProviders:
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split(".")[0] in {"torch","transformers","boto3","botocore","requests","httpx","openai"}:
                raise AssertionError("forbidden model/provider import: "+fullname)
    sys.meta_path.insert(0,DenyModelsAndProviders())
    genesis=SemanticProblem.from_dict(json.loads((output/"genesis.json").read_bytes()))
    custody=json.loads((output/"external_ingress.json").read_bytes())
    ingress=tuple(custody["statement_digests"])
    extensions=tuple(tuple(row) for row in custody["extensions"])
    complete=json.loads((output/"correction_journal.json").read_bytes())
    anchor=json.loads((output/"correction_anchor.json").read_bytes())["journal_digest"]
    original=restore(complete,genesis,ingress,anchor,extensions)
    replay=SemanticMachine(original.profile,trusted_ingress=ingress)
    cuts=[]
    for episode_index,episode in enumerate(complete["episodes"]):
        problem=SemanticProblem.from_dict(episode["problem"])
        replay.start(problem,additional_trusted_ingress=() if episode_index==0 else extensions[episode_index-1])
        expected_body={k:v for k,v in complete.items() if k not in {"episodes","journal_digest"}}
        expected_body["episodes"]=complete["episodes"][:episode_index+1]
        expected_body["ingress_digest"]=episode["final_state"]["ingress_digest"]
        expected={**expected_body,"journal_digest":digest(expected_body)}
        for index in range(len(episode["trace"])+1):
            if index:
                event=episode["trace"][index-1]
                outcome=replay.coordinator.execute(enabled_components=event["enabled_components"],
                    scheduled_components=event["scheduled_components"],
                    intents=_decode_proposal_batch(episode["proposal_batches"][index-1]))
                assert outcome.trace_event.to_dict()==event
            prefix=replay.journal()
            restored=restore(prefix,genesis,ingress,prefix["journal_digest"],extensions[:episode_index])
            assert restored.journal()==prefix
            result=restored.run()
            assert restored.journal()==expected
            cuts.append({"episode":episode_index,"cut":index,"prefix_digest":prefix["journal_digest"],
                "completed_digest":expected["journal_digest"],"output":result.output,
                "stored_claims":len(replay.state.memory_statements),
                "resolved":replay.state.memory_resolution_digest is not None,
                "depth":len(replay.state.rpm_stack)})
    import cncm.nested_kernel as kernel
    def forbidden(*args,**kwargs):
        raise AssertionError("new episode selected or qualified procedure")
    kernel.select_finite_candidate=forbidden
    kernel.qualify_procedure=forbidden
    later=task("35",name="fresh-later-task")
    assert later.updates==() and type(later.equations[0].b) is MemoryRef
    result=original.run(later,allow_acquisition=False)
    assert result.output=="9" and result.terminal_status is TerminalStatus.CONCLUDED
    assert original.state.native_budget==NativeBudget(454,124)
    write(output/"later_task.json",later.to_dict())
    write(output/"later_result.json",result.to_dict())
    structural=create_problem((SemanticEquation("root","2","1","0",(("x","3"),)),
        SemanticEquation("x","-4",MemoryRef("project","fee"),"20"),
        SemanticEquation("unused","0",MemoryRef("absent","secret"),"1")),"root",problem_id="fresh-structural-task")
    variant=original.run(structural,allow_acquisition=False)
    assert variant.output=="-5" and variant.terminal_status is TerminalStatus.CONCLUDED
    assert {c.variable for c in original.state.native_calls}=={"root","x"}
    write(output/"structural_result.json",variant.to_dict())
    neighbor=original.run(task("35",name="neighbor-retention",scope="neighbor"),allow_acquisition=False)
    assert neighbor.output=="8" and neighbor.terminal_status is TerminalStatus.CONCLUDED
    write(output/"neighbor_result.json",neighbor.to_dict())
    retained=original.state.memory_statements
    original.start(task("35",name="procedure-rollback"))
    while original.state.memory_resolution_digest is None:original.advance()
    original.rollback()
    refusal=original.run(allow_acquisition=False)
    assert refusal.output is None and refusal.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert original.state.memory_statements==retained and not original.state.procedure_heads
    final=original.journal()
    write(output/"final_journal.json",final)
    write(output/"final_anchor.json",{"journal_digest":final["journal_digest"]})
    write(output/"fresh_process_receipt.json",{"pid":os.getpid(),"source_profile_digest":original.profile.profile_digest,
        "cuts":cuts,"all_cuts_exact":True,"later_output":"9","structural_output":"-5",
        "neighbor_output":"8","selector_and_qualifier_disabled_for_new_tasks":True,
        "rollback_preserves_semantic_memory":True,"rollback_terminal_status":refusal.terminal_status.value,
        "final_journal_digest":final["journal_digest"],"model_or_provider_work":False,
        "factual_status":"NOT_INDEPENDENTLY_VERIFIED","source_status":"TEST_FIXTURE"})
    print(canonical_json({"pid":os.getpid(),"cuts":len(cuts),"later_output":"9"}))


def reproduce(output):
    output.mkdir(parents=True,exist_ok=False)
    profile=load_semantic_profile()
    assert load_nested_profile().profile_digest=="49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38"
    old=source();correction=source("8",previous=old.statement_digest);neighbor=source("11",scope="neighbor")
    ingress=tuple(sorted(s.statement_digest for s in (old,neighbor)))
    extensions=((correction.statement_digest,),)
    genesis=task(updates=(old,neighbor))
    write(output/"genesis.json",genesis.to_dict())
    write(output/"external_ingress.json",{"statement_digests":list(ingress),"extensions":[list(row) for row in extensions],
        "custody":"engineering fixture anchors supplied outside replay journal; not real user authorization"})
    write(output/"source_profile.json",profile.to_dict())
    m=SemanticMachine(profile,trusted_ingress=ingress)
    baseline=m.run(genesis)
    assert baseline.output=="7" and baseline.terminal_status is TerminalStatus.CONCLUDED
    write(output/"baseline_result.json",baseline.to_dict())
    assert correction.statement_digest not in m.trusted_ingress
    corrected=m.run(task(updates=(correction,),name="anchored-correction"),allow_acquisition=False,
                    additional_trusted_ingress=extensions[0])
    assert corrected.output=="6" and corrected.terminal_status is TerminalStatus.CONCLUDED
    journal=m.journal()
    write(output/"correction_result.json",corrected.to_dict())
    write(output/"correction_journal.json",journal)
    write(output/"correction_anchor.json",{"journal_digest":journal["journal_digest"]})
    control=SemanticMachine(profile,trusted_ingress=ingress)
    control_result=control.run(task("35",updates=(old,),name="uncorrected-control"))
    assert control_result.output=="10" and control_result.terminal_status is TerminalStatus.CONCLUDED
    write(output/"uncorrected_control_result.json",control_result.to_dict())
    worker=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),"--child",str(output)],
        cwd=ROOT,capture_output=True,text=True,timeout=240)
    write(output/"subprocess_exit.json",{"exit_code":worker.returncode,"stdout":worker.stdout,"stderr":worker.stderr})
    if worker.returncode:raise RuntimeError("separate-process semantic acceptance failed; see subprocess_exit.json")
    receipt=json.loads((output/"fresh_process_receipt.json").read_bytes())
    assert receipt["pid"]!=os.getpid()
    final_anchor=json.loads((output/"final_anchor.json").read_bytes())["journal_digest"]
    recovered=restore((output/"final_journal.json").read_bytes(),genesis,ingress,final_anchor,extensions)
    assert recovered.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
    stale=source("8",previous="a"*64)
    revoked=source(None,action="RETRACT",previous=old.statement_digest)
    rival=source("9",source_id="fixture-b")
    failures={}
    cases={"missing":(task(),()),"untrusted":(task(updates=(old,)),()),
        "stale":(task(updates=(old,stale)),(old.statement_digest,stale.statement_digest)),
        "revoked":(task(updates=(old,revoked)),(old.statement_digest,revoked.statement_digest)),
        "conflict":(task(updates=(old,rival)),(old.statement_digest,rival.statement_digest)),
        "insufficient_evidence":(task(updates=(old,),requirement="INDEPENDENTLY_VERIFIED"),(old.statement_digest,)),
        "budget":(task(updates=(old,),budget=NativeBudget(11,128)),(old.statement_digest,))}
    for name,(packet,anchors) in cases.items():
        bad=SemanticMachine(profile,trusted_ingress=anchors);result=bad.run(packet)
        assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
        saved=bad.journal();assert restore(saved,packet,anchors,saved["journal_digest"]).journal()==saved
        write(output/(name+"_journal.json"),saved)
        failures[name]={"status":result.terminal_status.value,"reason":bad.state.memory_failure,
            "journal_digest":saved["journal_digest"],"remaining_budget":bad.state.native_budget.to_dict()}
    assert load_semantic_profile().profile_digest==profile.profile_digest,"source changed during acceptance"
    files=[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha256(p.read_bytes()).hexdigest()}
           for p in sorted(output.iterdir()) if p.is_file()]
    result={"schema_version":"cncm.semantic-acceptance/0.4","status":"BOUNDED_SOURCED_CORRECTION_EPISODE_PASSED",
        "source_profile_digest":profile.profile_digest,"producer_pid":os.getpid(),"fresh_process_pid":receipt["pid"],
        "fresh_process_cuts":len(receipt["cuts"]),"uncorrected_control_output":"10","corrected_later_output":"9",
        "structural_output":"-5","neighbor_retained_output":"8","later_input_omits_value":True,
        "correction_authorized_after_initial_episode":True,
        "later_policy_work":{"instructions":58,"checker_calls":4},"failure_examples":failures,
        "correction_journal_digest":journal["journal_digest"],"final_journal_digest":final_anchor,
        "reproducer_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),"files":files,
        "scope":"Exact provenance-bound fixture correction and reuse; not independently verified facts, general learning or complete CNCM.",
        "model_or_provider_work":False,"full_goal_complete":False}
    write(output/"receipt.json",result)
    print(canonical_json({k:result[k] for k in ("status","source_profile_digest","fresh_process_cuts")}))


if __name__=="__main__":
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--output",type=Path);modes.add_argument("--child",type=Path);args=parser.parse_args()
    target=(args.output or args.child).resolve()
    if not target.is_relative_to(ROOT/"records"):raise SystemExit("acceptance output must remain under this homebase records")
    if args.child:child(target)
    else:reproduce(target)
