"""Retain actual-source nested planning, fresh-process resume, reuse and rollback."""
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
from cncm.model import ContractError,TerminalStatus
from cncm.native_profile import load_native_profile
from cncm.nested_engine import NestedMachine
from cncm.nested_model import Equation,NestedProblem,create_problem
from cncm.nested_profile import load_nested_profile
from cncm.nested_recovery import recover_nested_journal,_decode_proposal_batch

def write(path,value):
    raw=value if type(value) is bytes else (canonical_json(value)+"\n").encode()
    with path.open("xb") as stream:stream.write(raw)

def graph(constant="26",name="nested-acquisition"):
    return create_problem((
        Equation("side","1","0","0",(("leaf","1"),)),
        Equation("unused","0","0","1",(("unused","1"),)),
        Equation("root","2","1","0",(("mid","1"),("side","1"))),
        Equation("leaf","3","5",constant),
        Equation("mid","1","0","1",(("leaf","2"),)),
    ),"root",problem_id=name)

def restore(journal,genesis,anchor):
    return recover_nested_journal(journal,trusted_genesis=genesis,expected_journal_digest=anchor)

def child(output):
    class DenyModelsAndProviders:
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split(".")[0] in {"torch","transformers","boto3","botocore","requests","httpx","openai"}:
                raise AssertionError("forbidden model/provider import: "+fullname)
    sys.meta_path.insert(0,DenyModelsAndProviders())
    genesis=NestedProblem.from_dict(json.loads((output/"genesis.json").read_bytes()))
    complete=json.loads((output/"acquisition_journal.json").read_bytes())
    anchor=json.loads((output/"acquisition_anchor.json").read_bytes())["journal_digest"]
    original=restore(complete,genesis,anchor)
    replay=NestedMachine(original.profile);replay.start(genesis)
    episode=complete["episodes"][0]
    cuts=[]
    for index in range(len(episode["trace"])+1):
        if index:
            event=episode["trace"][index-1]
            outcome=replay.coordinator.execute(enabled_components=event["enabled_components"],
                scheduled_components=event["scheduled_components"],
                intents=_decode_proposal_batch(episode["proposal_batches"][index-1]))
            assert outcome.trace_event.to_dict()==event
        prefix=replay.journal()
        restored=restore(prefix,genesis,prefix["journal_digest"])
        assert restored.journal()==prefix
        before=restored.state
        result=restored.run()
        assert restored.journal()==complete
        cuts.append({"cut":index,"prefix_journal_digest":prefix["journal_digest"],
            "restored_state_hash":before.state_hash,"restored_active_goal":before.active_goal_id,
            "restored_depth":len(before.rpm_stack),
            "restored_calls":[[call.call_id,call.variable,call.status] for call in before.native_calls],
            "completed_journal_digest":restored.journal()["journal_digest"],"output":result.output})
    import cncm.nested_kernel as kernel
    def forbidden(*args,**kwargs):
        raise AssertionError("new episode attempted selection or qualification")
    kernel.select_finite_candidate=forbidden
    kernel.qualify_procedure=forbidden
    reuse=original.run(graph("29","fresh-reuse"),allow_acquisition=False)
    assert reuse.output=="12" and reuse.terminal_status is TerminalStatus.CONCLUDED
    assert reuse.evidence["authorized_nested_transitions"]["SELECT_PROCEDURE"]==0
    assert reuse.evidence["conservative_policy_work_reserved"]=={"instructions":120,"checker_calls":8}
    write(output/"reuse_result.json",reuse.to_dict())
    retained=original.state.procedural_artifacts
    original.start(graph("26","rollback-refusal"))
    original.rollback()
    refusal=original.run(allow_acquisition=False)
    assert refusal.terminal_status is TerminalStatus.NEEDS_CAPABILITY and refusal.output is None
    assert not original.state.rpm_stack and not original.state.procedure_heads
    assert original.state.procedural_artifacts==retained
    write(output/"rollback_refusal_result.json",refusal.to_dict())
    final=original.journal()
    write(output/"final_journal.json",final)
    write(output/"final_anchor.json",{"journal_digest":final["journal_digest"],
        "source_profile_digest":original.profile.profile_digest})
    receipt={"pid":os.getpid(),"source_profile_digest":original.profile.profile_digest,
        "cuts":cuts,"all_cuts_exact":True,"maximum_restored_depth":max(row["restored_depth"] for row in cuts),
        "reuse_output":reuse.output,"new_call_selector_and_qualifier_disabled":True,
        "rollback_terminal_status":refusal.terminal_status.value,
        "final_journal_digest":final["journal_digest"],"model_or_provider_work":False}
    write(output/"fresh_process_receipt.json",receipt)
    print(canonical_json({"pid":os.getpid(),"cuts":len(cuts),"reuse_output":reuse.output,
        "final_journal_digest":final["journal_digest"]}))

def reproduce(output):
    output.mkdir(parents=True,exist_ok=False)
    profile=load_nested_profile()
    assert load_native_profile().profile_digest=="c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607"
    problem=graph()
    write(output/"genesis.json",problem.to_dict())
    write(output/"source_profile.json",profile.to_dict())
    machine=NestedMachine(profile);machine.start(problem)
    suspended=False
    while machine.state.halt_status is TerminalStatus.RUNNING:
        machine.advance()
        if not suspended and len(machine.state.rpm_stack)==3:
            snapshot=machine.journal()
            write(output/"nested_suspension_journal.json",snapshot)
            write(output/"nested_suspension_anchor.json",{"journal_digest":snapshot["journal_digest"],
                "state_hash":machine.state.state_hash,"depth":3})
            suspended=True
    result=machine.result()
    assert suspended and result.output=="21/2" and result.terminal_status is TerminalStatus.CONCLUDED
    assert result.evidence["authorized_nested_transitions"]["INSTALL_PROCEDURE"]==1
    assert result.evidence["authorized_nested_transitions"]["APPLY_EQUATION"]==4
    assert result.evidence["conservative_policy_work_reserved"]=={"instructions":324,"checker_calls":42}
    assert {call.variable for call in machine.state.native_calls}=={"root","mid","leaf","side"}
    journal=machine.journal()
    write(output/"acquisition_result.json",result.to_dict())
    write(output/"acquisition_journal.json",journal)
    write(output/"acquisition_anchor.json",{"journal_digest":journal["journal_digest"],
        "source_profile_digest":profile.profile_digest})
    worker=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),"--child",str(output)],
        cwd=ROOT,capture_output=True,text=True,timeout=180)
    write(output/"subprocess_exit.json",{"exit_code":worker.returncode,"stdout":worker.stdout,"stderr":worker.stderr})
    if worker.returncode:
        raise RuntimeError("separate-process nested acceptance failed; see subprocess_exit.json")
    receipt=json.loads((output/"fresh_process_receipt.json").read_bytes())
    assert receipt["pid"]!=os.getpid()
    final_anchor=json.loads((output/"final_anchor.json").read_bytes())
    recovered=restore((output/"final_journal.json").read_bytes(),problem,final_anchor["journal_digest"])
    assert recovered.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
    assert load_nested_profile().profile_digest==profile.profile_digest,"source changed during acceptance"
    failures={}
    from cncm.native_model import NativeBudget
    limit=2**127-1
    cases={
        "missing":create_problem((Equation("x","1","0","0",(("absent","1"),)),),"x"),
        "cycle":create_problem((Equation("x","1","0","0",(("y","1"),)),Equation("y","1","0","0",(("x","1"),))),"x"),
        "zero_slope":create_problem((Equation("x","0","1","2"),),"x"),
        "budget":create_problem((Equation("x","1","0","7"),),"x",budget=NativeBudget(20,2)),
        "depth":create_problem((Equation("x","1","0","0",(("y","1"),)),Equation("y","1","0","7")),"x",rpm_depth_limit=1),
        "input_bound":create_problem((Equation("x","1/"+str(limit),"0",str(limit-1)),
            Equation("y","1","0","0",(("x","1"),))),"y"),
    }
    for name,packet in cases.items():
        failed=NestedMachine(profile);failure=failed.run(packet)
        assert failure.output is None and failure.terminal_status is not TerminalStatus.CONCLUDED
        saved=failed.journal()
        assert restore(saved,packet,saved["journal_digest"]).journal()==saved
        write(output/(name+"_journal.json"),saved)
        failures[name]={"status":failure.terminal_status.value,"journal_digest":saved["journal_digest"],
            "remaining_budget":failed.state.native_budget.to_dict(),"unresolved_frames":len(failed.state.rpm_stack)}
    files=[{"path":path.name,"bytes":path.stat().st_size,"sha256":sha256(path.read_bytes()).hexdigest()}
        for path in sorted(output.iterdir()) if path.is_file()]
    write(output/"receipt.json",{"schema_version":"cncm.nested-acceptance/0.3",
        "status":"BOUNDED_NATIVE_NESTED_EPISODE_PASSED","source_profile_digest":profile.profile_digest,
        "producer_pid":os.getpid(),"fresh_process_pid":receipt["pid"],
        "acquisition_output":"21/2","reuse_output":"12","calls_executed":4,"procedure_installations":1,
        "suspension_depth":3,"fresh_process_cuts":len(receipt["cuts"]),
        "acquisition_policy_cost":{"instructions":324,"checker_calls":42},
        "failure_examples":failures,"acquisition_journal_digest":journal["journal_digest"],
        "final_journal_digest":final_anchor["journal_digest"],"files":files,
        "reproducer_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope":"Native bounded dependency planning with reused finite arithmetic skill; not learned program topology, neural synthesis, externally held-out learning or complete CNCM.",
        "model_or_provider_work":False,"full_goal_complete":False})
    print(canonical_json({"status":"BOUNDED_NATIVE_NESTED_EPISODE_PASSED",
        "output":str(output),"cuts":len(receipt["cuts"]),"source_profile_digest":profile.profile_digest}))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--output",type=Path)
    modes.add_argument("--child",type=Path)
    args=parser.parse_args()
    target=(args.output or args.child).resolve()
    if not target.is_relative_to(ROOT/"records"):
        raise SystemExit("nested acceptance output must stay in this homebase records directory")
    if args.child:child(target)
    else:reproduce(target)
