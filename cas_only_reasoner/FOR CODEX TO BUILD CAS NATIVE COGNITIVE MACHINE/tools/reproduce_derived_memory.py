"""Actual-source reproduction for proof-backed derived-result memory0.6.

Run only after the new model, verifier, kernel and recovery contract are present.
Public engineering fixtures are not protected held-out learning evidence.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
ROOT=next(parent for parent in Path(__file__).resolve().parents
          if (parent/'cncm/derived_model.py').is_file() and (parent/'cas_reasoner.txt').is_file())
HELPER_BOOT_RAW=Path(__file__).read_bytes()
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import derived_acceptance_support as support_module
from derived_acceptance_support import (write_new, read, identity, verify_preservation,
    no_models_or_providers, allocation_conservation,
    observe_work, require, interpreter_identity, declared_inputs, verify_declared, verify_imported_subset,
    checked_manifest, policy_guard, require_stale_refusal, FORBIDDEN_IMPORTS, SUPPORT_BOOT_IDENTITY)

COUNTER_BOUNDARY='Observed calls at individually named aliases; not total computation, independent verifier services, or policy allocation units. Direct and receipt-recheck math entries are recorded separately.'

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

def restore(journal,genesis,ingress,extensions=(),*,expected_journal_digest):
    from cncm.derived_recovery import recover_derived_journal
    return recover_derived_journal(journal,trusted_genesis=genesis,trusted_ingress=ingress,
        trusted_ingress_extensions=extensions,expected_journal_digest=expected_journal_digest)

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

def run_new(machine,problem,*,allow_generation=True,allow_acquisition=True,additions=(),output=None,name=None,stale_source=None):
    guard=policy_guard(allow_generation=allow_generation,allow_acquisition=allow_acquisition)
    with guard as attempts, observe_work() as work:
        result=machine.run(problem,allow_generation=allow_generation,allow_acquisition=allow_acquisition,
                           additional_trusted_ingress=additions)
    assert not attempts
    if not allow_generation:
        assert work["cncm.derived_kernel.generate_candidate"]==0
    if result.output is not None:
        assert work["cncm.compound_kernel.check_program_call"]==1
        assert result.terminal_status.value=='CONCLUDED' and machine.state.commitment_state.decision_status=='COMMITTED'
    if stale_source is not None:
        require_stale_refusal(result,machine,stale_source,work)
    if output is not None:
        write_new(output/(name+"_result.json"),{
            "output":result.output,"terminal_status":result.terminal_status.value,
            "state":machine.state.to_dict(),"forbidden_entry_attempts":attempts,
            "policy":{"allow_generation":allow_generation,"allow_acquisition":allow_acquisition},
            "stale_refusal_asserted":stale_source is not None,
            "observed_new_work":work,"counter_boundary":COUNTER_BOUNDARY})
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
    retained=machine.journal()
    machine=restore(retained,genesis,ingress,expected_journal_digest=retained['journal_digest'])
    assert run_new(machine,task("reuse-checked-y","41"),allow_generation=False,allow_acquisition=False,
                   output=output,name="reuse").output=="4"
    correction=source("17",first.statement_digest)
    assert run_new(machine,task("stale-checked-y",updates=(correction,)),allow_generation=False,allow_acquisition=False,
                   additions=(correction.statement_digest,),output=output,name="stale",stale_source=correction).output is None
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
    retained=machine.journal()
    machine=restore(retained,genesis,ingress,expected_journal_digest=retained['journal_digest'])
    task=create_problem(consumer_inputs,variable="y",store_result=consumer,problem_id="stored-consumer")
    assert run_new(machine,task,allow_generation=False,allow_acquisition=False,
                   output=output,name="consumer").output=="7/2"
    correction=source("8",first.statement_digest,key="offset")
    stale=create_problem(dict(a=consumer,b="1",c="0",d="0",e="7"),variable="z",
                         updates=(correction,),problem_id="transitive-stale-consumer")
    assert run_new(machine,stale,allow_generation=False,allow_acquisition=False,
                   additions=(correction.statement_digest,),output=output,name="transitive_stale",stale_source=correction).output is None
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

def replay_child(output,expected_manifest_sha256):
    manifest=checked_manifest(output/'child_input_manifest.json',expected_manifest_sha256)
    child_interpreter=interpreter_identity()
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
        restored=restore(complete,genesis,ingress,extensions,expected_journal_digest=custody['expected_journal_digest'])
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
                # This prefix was reconstructed from parent-hash-bound inputs.
                # It is checked under caller custody, not principal authentication.
                # Denial guards apply only to NEW continuation, after historical replay.
                resumed=restore(prefix,genesis,ingress,extensions[:episode_index],
                                expected_journal_digest=prefix['journal_digest'])
                assert resumed.journal()==prefix
                guard=policy_guard(allow_generation=allow_generation,allow_acquisition=allow_acquisition)
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
            print(json.dumps({'phase':'episode_replay_complete','pid':os.getpid(),'case':name,
                              'episode':episode_index,'cuts':len(episode['trace'])+1,
                              'total_cuts_so_far':len(all_cuts)}),flush=True)
    assert any(row["committed"] and not row["derived_stored"] and row["case"]=="stored_results" for row in all_cuts)
    assert any("DerivedFrame" in row["frames"] for row in all_cuts)
    checked_manifest(output/'child_input_manifest.json',expected_manifest_sha256)
    child_imports=verify_imported_subset(manifest['declared_inputs'])
    write_new(output/'child_actual_imports.json',child_imports)
    write_new(output/"all_cut_replay.json",{"pid":os.getpid(),"cuts":all_cuts,"all_exact":True,
        'child_input_manifest_sha256':expected_manifest_sha256,'interpreter':child_interpreter,
        'process_boundary':'Every prefix reconstructed and continued inside one fresh child process; not a new OS process for each cut.',
        'trust_boundary':'Parent-held manifest SHA binds locally generated custody inputs; no principal authentication or outside-world truth.',
        'source_inventory':'child_actual_imports.json'})
    print(json.dumps({"pid":os.getpid(),"cuts":len(all_cuts),"all_exact":True}),flush=True)

def main():
    interpreter=interpreter_identity()
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--replay-child",action="store_true")
    parser.add_argument('--expected-input-manifest-sha256')
    parser.add_argument('--test-evidence',type=Path,action='append',default=[])
    options=parser.parse_args()
    output=options.output.resolve()
    parent=(ROOT/'records/derived_memory_001').resolve()
    require(output.parent==parent,'direct derived-memory record child required')
    if options.replay_child:
        require(output.is_dir() and options.expected_input_manifest_sha256,'child requires existing output and parent-held manifest hash')
        with no_models_or_providers() as import_attempts:
            replay_child(output,options.expected_input_manifest_sha256)
            require(not import_attempts,'forbidden imports attempted in child')
            write_new(output/'child_execution_guard.json',{'forbidden_imports':sorted(FORBIDDEN_IMPORTS),
                'observed_import_attempts':import_attempts,'boundary':'Named Python import gate; not provider/account telemetry.'})
        return
    require(options.test_evidence,'--test-evidence must name retained passing JUnit report(s)')
    assert output.parent==parent and not output.exists(),"new direct record child required"
    output.mkdir()
    try:
        with no_models_or_providers() as import_attempts:
            require(sha256(Path(__file__).read_bytes()).hexdigest()==sha256(HELPER_BOOT_RAW).hexdigest(), 'helper changed since module entry')
            require(identity(support_module.__file__)==SUPPORT_BOOT_IDENTITY,'support changed since module entry')
            declared=declared_inputs(Path(__file__),Path(support_module.__file__),options.test_evidence)
            verify_declared(declared)
            write_new(output/'declared_inputs_before.json',declared)
            preserved=verify_preservation()
            from cncm.derived_profile import load_derived_profile
            runtime_profile=load_derived_profile()
            write_new(output/"runtime_source_profile.json",runtime_profile.to_dict())
            require([r['path'] for r in runtime_profile.to_dict()['source_files']]==declared['runtime_source_names'],
                    'static and loaded runtime profile inventories differ')
            verify_declared(declared)
            cases=[acquire_case(output),stored_case(output)]
            child_manifest={'schema_version':'cncm.derived-child-input-manifest/0.1',
                'parent_pid':os.getpid(),'declared_inputs':declared,
                'artifacts':[identity(path) for path in sorted(output.iterdir()) if path.is_file()],
                'trust_boundary':'Generated by this parent; explicit SHA delivered to child outside artifact contents.'}
            manifest_identity=write_new(output/'child_input_manifest.json',child_manifest)
            expected_manifest_sha256=manifest_identity['sha256']
            with (output/'replay_stdout.txt').open('x',encoding='utf-8',newline='\n') as stdout_file, \
                 (output/'replay_stderr.txt').open('x',encoding='utf-8',newline='\n') as stderr_file:
                child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--output',str(output),
                    '--replay-child','--expected-input-manifest-sha256',expected_manifest_sha256],
                    stdout=subprocess.PIPE,stderr=stderr_file,text=True,encoding='utf-8')
                try:
                    for line in child.stdout:
                        stdout_file.write(line); stdout_file.flush()
                        print(line,end='',flush=True)
                    child_exit=child.wait()
                except BaseException:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill(); child.wait(timeout=10)
                    raise
                finally:
                    child.stdout.close()
            require(child_exit==0,'fresh-child replay failed; retained replay_stderr.txt contains details')
            checked_manifest(output/'child_input_manifest.json',expected_manifest_sha256)
            verify_declared(declared)
            assert load_derived_profile().to_dict()==runtime_profile.to_dict(),"runtime profile changed during acceptance"
            preserved_after=verify_preservation()
            assert preserved_after==preserved
            actual_imports=verify_imported_subset(declared)
            write_new(output/"parent_actual_imports.json",actual_imports)
            write_new(output/'declared_inputs_after.json',declared)
            write_new(output/'parent_execution_guard.json',{'forbidden_imports':sorted(FORBIDDEN_IMPORTS),
                'observed_import_attempts':import_attempts,'boundary':'Named Python import gate; not provider/account telemetry.'})
            artifacts=[identity(path) for path in sorted(output.iterdir()) if path.is_file()]
            replay=read(output/"all_cut_replay.json")
            require(replay['pid']==child.pid and replay['pid']!=os.getpid(),'fresh child process identity mismatch')
            require(replay['child_input_manifest_sha256']==expected_manifest_sha256,'child used different input manifest')
            for key in ('executable','executable_sha256','version','implementation','optimize'):
                require(replay['interpreter'][key]==interpreter[key],'child interpreter mismatch: '+key)
            require(not import_attempts,'forbidden imports attempted in parent')
            receipt={"schema_version":"cncm.derived-memory-acceptance/0.6",
                "status":"PASS","pid":os.getpid(),"child_pid":replay["pid"],
                "runtime_profile_digest":runtime_profile.profile_digest,
                "cases":cases,"exact_cuts":len(replay["cuts"]),"preservation":preserved,
                "helper":identity(Path(__file__).resolve()),"support":identity(support_module.__file__),
                'interpreter':interpreter,'child_input_manifest_sha256':expected_manifest_sha256,
                'declared_input_count':len(declared['files']),'parent_imported_sources':len(actual_imports),
                'child_imported_sources':len(read(output/'child_actual_imports.json')),
                'test_evidence':declared['junit_reports'],'counter_boundary':COUNTER_BOUNDARY,
                "artifacts":artifacts,'observed_forbidden_import_attempts':0,
                'artifact_manifest_boundary':'All completed output files except this receipt; receipt self-hash belongs to the enclosing publication/review record.',
                'execution_boundary':'No model/provider operations in this pure local recipe; named import denial is recorded, not provider or account telemetry.',
                'replay_boundary':replay['process_boundary'],"full_vision_complete":False,
                "boundary":"Bounded conditional formal-result retention/reuse; public engineering cases, no neural-learning gain."}
            write_new(output/"receipt.json",receipt)
            print(json.dumps({"receipt":str(output/"receipt.json"),"cuts":len(replay["cuts"])}),flush=True)
    except BaseException as error:
        write_new(output/"failure.json",{"type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc()})
        raise

if __name__=="__main__":
    main()
