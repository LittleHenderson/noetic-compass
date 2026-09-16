"""Actual-source reproduction for proof-backed derived-result memory0.6.

Run only after the new model, verifier, kernel and recovery contract are present.
Public engineering fixtures are not protected held-out learning evidence.
"""
from __future__ import annotations
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tools"))
from derived_acceptance_support import (write_new, read, identity, verify_preservation,
    imported_source_inventory, no_models_or_providers, deny_new_generation, allocation_conservation,
    observe_work)

def source(value="11",previous=None,key="rhs",scope="acceptance",source_id="fixture"):
    from cncm.semantic_model import SourceStatement
    return SourceStatement(scope,key,source_id,value,"TEST_FIXTURE","ASSERT",previous,
                           "engineering-fixture:derived-memory-001")

def ref(key,scope="acceptance"):
    from cncm.derived_model import DerivedResultRef
    return DerivedResultRef(scope,key)

def definition(target,parameters,variable="x",revision=1,supersedes=None):
    from cncm.derived_model import DerivedDefinition
    return DerivedDefinition(target.scope,target.key,revision,supersedes,variable,tuple(sorted(parameters.items())))

def restore(journal,genesis,ingress,extensions=()):
    from cncm.derived_recovery import recover_derived_journal
    return recover_derived_journal(journal,trusted_genesis=genesis,trusted_ingress=ingress,
        trusted_ingress_extensions=extensions,expected_journal_digest=journal["journal_digest"])

def targets():
    import cncm.compound_kernel as compound
    import cncm.derived_kernel as derived
    # The exact candidate alias is checked explicitly after implementation.
    names=("construct_program","qualify_program","select_finite_candidate","qualify_procedure")
    result=[(compound,name) for name in names]
    result.append((derived,"generate_candidate"))
    return tuple(result)

def save_case(output,name,machine,genesis,ingress,extensions,policies,expected):
    journal=machine.journal()
    assert len(journal["episodes"])==len(policies)==len(expected)
    write_new(output/(name+"_journal.json"),journal)
    write_new(output/(name+"_custody.json"),{
        "genesis":genesis.to_dict(),"initial_ingress":list(ingress),
        "extensions":[list(row) for row in extensions],
        "expected_journal_digest":journal["journal_digest"],"policies":policies,
        "expected_outputs":expected})
    return {"name":name,"journal_digest":journal["journal_digest"],
            "episodes":len(policies),"allocation":allocation_conservation(machine)}

def run_new(machine,problem,*,allow_generation=True,allow_acquisition=True,additions=(),output=None,name=None):
    guard=deny_new_generation(targets()) if not allow_generation and not allow_acquisition else nullcontext([])
    with guard as attempts, observe_work() as work:
        result=machine.run(problem,allow_generation=allow_generation,allow_acquisition=allow_acquisition,
                           additional_trusted_ingress=additions)
    assert not attempts
    if not allow_generation:
        assert work["cncm.derived_kernel.generate_candidate"]==0
    if result.output is not None:
        assert work["cncm.compound_kernel.check_program_call"]==1
    if output is not None:
        write_new(output/(name+"_result.json"),{
            "output":result.output,"terminal_status":result.terminal_status.value,
            "state":machine.state.to_dict(),"new_generation_attempts":attempts,
            "observed_new_work":work})
    return result

def acquire_case(output):
    from cncm.derived_engine import DerivedMachine
    from cncm.derived_model import create_problem
    from cncm.semantic_model import MemoryRef
    first=source()
    remembered=ref("y")
    declared=definition(remembered,dict(a="1",b="2",c="1",d="0",e=MemoryRef("acceptance","rhs")),variable="y")
    ingress=(first.statement_digest,declared.definition_digest)
    def task(name,target="35",updates=(),definitions=()):
        return create_problem(dict(a="2",b="3",c=remembered,d="7",e=target),
                              updates=updates,definitions=definitions,problem_id=name)
    genesis=task("missing-checked-y",updates=(first,),definitions=(declared,))
    machine=DerivedMachine(trusted_ingress=ingress)
    assert run_new(machine,genesis,output=output,name="acquire").output=="3"
    machine=restore(machine.journal(),genesis,ingress)
    assert run_new(machine,task("reuse-checked-y","41"),allow_generation=False,allow_acquisition=False,
                   output=output,name="reuse").output=="4"
    correction=source("17",first.statement_digest)
    assert run_new(machine,task("stale-checked-y",updates=(correction,)),allow_generation=False,allow_acquisition=False,
                   additions=(correction.statement_digest,),output=output,name="stale").output is None
    assert run_new(machine,task("refresh-checked-y"),allow_acquisition=False,
                   output=output,name="refresh").output=="2"
    assert run_new(machine,task("reuse-refreshed-y","41"),allow_generation=False,allow_acquisition=False,
                   output=output,name="refreshed_reuse").output=="3"
    return save_case(output,"acquisition",machine,genesis,ingress,
        ((),(correction.statement_digest,),(),()),
        [(True,True),(False,False),(False,False),(True,False),(False,False)],
        ["3","4",None,"2","3"])

def stored_case(output):
    from cncm.derived_engine import DerivedMachine
    from cncm.derived_model import create_problem
    from cncm.semantic_model import MemoryRef
    first=source("5",key="offset")
    producer,consumer=ref("producer-x"),ref("consumer-y")
    inputs=dict(a="2",b="3",c=MemoryRef("acceptance","offset"),d="7",e="35")
    producer_definition=definition(producer,inputs)
    consumer_inputs=dict(a=producer,b="2",c="1",d="4",e="28")
    consumer_definition=definition(consumer,consumer_inputs,variable="y")
    ingress=(first.statement_digest,producer_definition.definition_digest,consumer_definition.definition_digest)
    genesis=create_problem(inputs,updates=(first,),definitions=(producer_definition,consumer_definition),
                           store_result=producer,problem_id="stored-producer")
    machine=DerivedMachine(trusted_ingress=ingress)
    assert run_new(machine,genesis,output=output,name="producer").output=="3"
    machine=restore(machine.journal(),genesis,ingress)
    task=create_problem(consumer_inputs,variable="y",store_result=consumer,problem_id="stored-consumer")
    assert run_new(machine,task,allow_generation=False,allow_acquisition=False,
                   output=output,name="consumer").output=="7/2"
    correction=source("8",first.statement_digest,key="offset")
    stale=create_problem(dict(a=consumer,b="1",c="0",d="0",e="7"),variable="z",
                         updates=(correction,),problem_id="transitive-stale-consumer")
    assert run_new(machine,stale,allow_generation=False,allow_acquisition=False,
                   additions=(correction.statement_digest,),output=output,name="transitive_stale").output is None
    renewed=create_problem(inputs,store_result=producer,problem_id="renew-producer")
    assert run_new(machine,renewed,allow_generation=False,allow_acquisition=False,
                   output=output,name="renewed_producer").output=="2"
    task=create_problem(consumer_inputs,variable="y",store_result=consumer,problem_id="renew-consumer")
    assert run_new(machine,task,allow_generation=False,allow_acquisition=False,
                   output=output,name="renewed_consumer").output=="11/2"
    return save_case(output,"stored_results",machine,genesis,ingress,
        ((),(correction.statement_digest,),(),()),
        [(True,True),(False,False),(False,False),(False,False),(False,False)],
        ["3","7/2",None,"2","11/2"])

def replay_child(output):
    from cncm.canonical import canonical_json,digest
    from cncm.derived_engine import DerivedMachine
    from cncm.derived_model import DerivedProblem
    from cncm.derived_recovery import _decode_proposal_batch
    from cncm.model import TerminalStatus
    all_cuts=[]
    for name in ("acquisition","stored_results"):
        custody=read(output/(name+"_custody.json"))
        complete=read(output/(name+"_journal.json"))
        assert complete["journal_digest"]==custody["expected_journal_digest"]
        genesis=DerivedProblem.from_dict(custody["genesis"])
        ingress=tuple(custody["initial_ingress"])
        extensions=tuple(tuple(row) for row in custody["extensions"])
        restored=restore(complete,genesis,ingress,extensions)
        assert restored.journal()==complete
        replay=DerivedMachine(trusted_ingress=ingress)
        for episode_index,episode in enumerate(complete["episodes"]):
            addition=() if episode_index==0 else extensions[episode_index-1]
            replay.start(DerivedProblem.from_dict(episode["problem"]),additional_trusted_ingress=addition)
            expected_body={key:value for key,value in complete.items() if key not in {"episodes","journal_digest"}}
            expected_body["episodes"]=complete["episodes"][:episode_index+1]
            expected_body["ingress_digest"]=episode["ingress_digest"]
            expected={**expected_body,"journal_digest":digest(expected_body)}
            allow_generation,allow_acquisition=custody["policies"][episode_index]
            for cut in range(len(episode["trace"])+1):
                if cut:
                    event=episode["trace"][cut-1]
                    step=replay.coordinator.execute(
                        enabled_components=event["enabled_components"],
                        scheduled_components=event["scheduled_components"],
                        intents=_decode_proposal_batch(episode["proposal_batches"][cut-1]))
                    assert canonical_json(step.trace_event.to_dict())==canonical_json(event)
                prefix=replay.journal()
                # Historical replay is authenticated first. Disabling generation
                # applies only to NEW continuation after that reconstructed cut.
                resumed=restore(prefix,genesis,ingress,extensions[:episode_index])
                assert resumed.journal()==prefix
                guard=deny_new_generation(targets()) if not allow_generation and not allow_acquisition else nullcontext([])
                with guard as attempts:
                    result=resumed.run(allow_generation=allow_generation,allow_acquisition=allow_acquisition)
                assert not attempts
                assert result.output==custody["expected_outputs"][episode_index]
                assert canonical_json(resumed.journal())==canonical_json(expected)
                all_cuts.append({"case":name,"episode":episode_index,"cut":cut,
                    "prefix_digest":prefix["journal_digest"],"complete_digest":expected["journal_digest"],
                    "state_hash":replay.state.state_hash,"depth":len(replay.state.rpm_stack),
                    "frames":[type(frame).__name__ for frame in replay.state.rpm_stack],
                    "committed":replay.state.commitment_state.decision_status=="COMMITTED",
                    "derived_stored":replay.state.derived_stored,
                    "remaining":replay.state.native_budget.to_dict()})
    assert any(row["committed"] and not row["derived_stored"] and row["case"]=="stored_results" for row in all_cuts)
    assert any("DerivedFrame" in row["frames"] for row in all_cuts)
    write_new(output/"all_cut_replay.json",{"pid":os.getpid(),"cuts":all_cuts,"all_exact":True})
    print(json.dumps({"pid":os.getpid(),"cuts":len(all_cuts),"all_exact":True}),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--replay-child",action="store_true")
    options=parser.parse_args()
    output=options.output.resolve()
    if options.replay_child:
        with no_models_or_providers():
            replay_child(output)
        return
    parent=(ROOT/"records/derived_memory_001").resolve()
    assert output.parent==parent and not output.exists(),"new direct record child required"
    output.mkdir()
    try:
        with no_models_or_providers():
            preserved=verify_preservation()
            from cncm.derived_profile import load_derived_profile
            runtime_profile=load_derived_profile()
            write_new(output/"runtime_source_profile.json",runtime_profile.to_dict())
            before={str(path.relative_to(ROOT)):identity(path)
                    for path in sorted((ROOT/"cncm").glob("*.py"))}
            write_new(output/"sources_before.json",before)
            cases=[acquire_case(output),stored_case(output)]
            completed=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                "--output",str(output),"--replay-child"],capture_output=True,text=True)
            write_new(output/"replay_stdout.txt",completed.stdout.encode())
            write_new(output/"replay_stderr.txt",completed.stderr.encode())
            assert completed.returncode==0,completed.stderr
            for name,row in before.items():
                assert identity(ROOT/name)==row,("source changed during acceptance",name)
            assert load_derived_profile().to_dict()==runtime_profile.to_dict(),"runtime profile changed during acceptance"
            preserved_after=verify_preservation()
            assert preserved_after==preserved
            write_new(output/"actual_imports.json",imported_source_inventory())
            artifacts=[identity(path) for path in sorted(output.iterdir()) if path.is_file()]
            replay=read(output/"all_cut_replay.json")
            receipt={"schema_version":"cncm.derived-memory-acceptance/0.6",
                "status":"PASS","pid":os.getpid(),"child_pid":replay["pid"],
                "runtime_profile_digest":runtime_profile.profile_digest,
                "cases":cases,"exact_cuts":len(replay["cuts"]),"preservation":preserved,
                "helper":identity(Path(__file__).resolve()),"support":identity(ROOT/"tools/derived_acceptance_support.py"),
                "artifacts":artifacts,"models_or_providers":0,"full_vision_complete":False,
                "boundary":"Bounded conditional formal-result retention/reuse; public engineering cases, no neural-learning gain."}
            write_new(output/"receipt.json",receipt)
            print(json.dumps({"receipt":str(output/"receipt.json"),"cuts":len(replay["cuts"])}),flush=True)
    except BaseException as error:
        write_new(output/"failure.json",{"type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc()})
        raise

if __name__=="__main__":
    main()
