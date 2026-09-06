"""Read-only regression against the already-admitted original failed case 9."""
from pathlib import Path
from copy import deepcopy
import importlib.util
import json
import shutil
import sqlite3
import tempfile


def run():
    here=Path(__file__).resolve().parent
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    c=load('_prefix_common',here/'common.py')
    partial=load('_prefix_auditor',here/'partial.py')
    admission_path=c.ROOT/'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
    c.pin(admission_path,c.ADMISSION)
    admission=c.decode(admission_path.read_bytes())
    c.check_source_again(admission['source_manifest'])
    with c.pure_guard():
        engine=c.load('_prefix_engine',c.ROOT/'tools/audit_stored_packet_v3.py')
        from jsonschema import Draft202012Validator
        from cas_meta2.curriculum import check_native_topology
        engine.Draft202012Validator=Draft202012Validator
        engine.check_native_topology=check_native_topology
        validator,schema=engine.protected_schema()
        packet=c.Packet(c.ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip',c.OLD_PACKET,
                        c.ROOT/'records/aws_contrast_v6_001_failure_extracted')
        base='cloud_job/campaign/'
        task=packet.json(base+'dataset/test_private.json')[9]
        action=c.decode(packet.raw(base+'native/predictions.jsonl').splitlines()[9])['actions']['cas_trained']
        identity=packet.json(base+'native/evaluation/case_0009/reference_result.json')['runtime_identity']
        result=partial.audit_prefix(packet,base+'native/evaluation/case_0009/cas_trained/native',
            task['public'],action,identity,engine,validator,c)
        c.require(result['committed_native_runs']==7 and result['committed_reserved_policy_units']==504
                  and result['failed_tick_compute'] is None,'ORIGINAL_CASE9_RECOUNT_CHANGED')
        # Deliberately reseal copied fixture bytes here so these negatives reach
        # the semantic prefix checks, instead of stopping at outer ZIP hashes.
        # The original externally pinned packet and extraction are never edited.
        original=packet.path(base+'native/evaluation/case_0009/cas_trained/native/native.db').parent
        negatives=[]
        for mutation in ('error_message','trace_payload_hash','schema_resealed','missing_commit',
                         'head_count','state_payload_hash','binding','output_artifact'):
            with tempfile.TemporaryDirectory(prefix='prefix_negative_',dir=here) as scratch:
                root=Path(scratch);folder=root/'fixture';folder.mkdir()
                for name in ('native.db','failure.json'):shutil.copyfile(original/name,folder/name)
                changed_action=deepcopy(action)
                db=sqlite3.connect(folder/'native.db')
                try:
                    # The actual store prevents writes with immutable triggers.
                    # Remove them only in this disposable negative-test copy so
                    # the independently rehashed corruption reaches the auditor.
                    triggers=db.execute('SELECT name FROM sqlite_master WHERE type=?',('trigger',)).fetchall()
                    for (trigger,) in triggers:
                        db.execute('DROP TRIGGER "'+trigger.replace('"','""')+'"')
                    if mutation=='error_message':
                        (folder/'failure.json').write_bytes(c.canonical({'status':'INFRASTRUCTURE_FAILURE',
                            'type':'RuntimeContractError','message':'different error'}))
                    elif mutation=='trace_payload_hash':db.execute('UPDATE trace_events SET payload_sha256=? WHERE sequence=1',('0'*64,))
                    elif mutation=='schema_resealed':
                        value=c.decode(db.execute('SELECT payload_json FROM trace_events WHERE sequence=1').fetchone()[0])
                        value['tick']='not-an-integer';raw=c.canonical(value).decode()
                        db.execute('UPDATE trace_events SET payload_json=?,payload_sha256=? WHERE sequence=1',
                                   (raw,c.sha256(raw.encode()).hexdigest()))
                    elif mutation=='missing_commit':db.execute('DELETE FROM commit_receipts WHERE rowid=(SELECT MIN(rowid) FROM commit_receipts)')
                    elif mutation=='head_count':db.execute('UPDATE active_head SET state_version=99')
                    elif mutation=='state_payload_hash':db.execute('UPDATE state_versions SET payload_sha256=?',('0'*64,))
                    elif mutation=='binding':changed_action['binding']=999
                    elif mutation=='output_artifact':db.execute(
                        'UPDATE artifacts SET sha256=? WHERE artifact_id=(SELECT artifact_id FROM model_versions LIMIT 1)',('0'*64,))
                    db.commit()
                finally:db.close()
                class CopyPacket:
                    def __init__(self):
                        self.inventory={'fixture/'+n:{'path':'fixture/'+n,'bytes':(folder/n).stat().st_size,
                            'sha256':c.file_hash(folder/n)} for n in ('native.db','failure.json')}
                    def path(self,name):return root/name
                    def json(self,name):return c.decode(self.path(name).read_bytes())
                try:
                    partial.audit_prefix(CopyPacket(),'fixture',task['public'],changed_action,identity,engine,validator,c)
                except Exception as error:
                    negatives.append({'mutation':mutation,'rejected':True,'type':type(error).__name__,'message':str(error)[:400]})
                else:raise AssertionError('PREFIX_NEGATIVE_NOT_REJECTED:'+mutation)
        packet.verify_all();c.check_source_again(admission['source_manifest'])
    return {'schema':'cas-meta2-recovery-review-prefix-regression/6','completed':True,
            'packet_sha256':c.OLD_PACKET,'admission_sha256':c.ADMISSION,'schema_identity':schema,
            'result':result,'negative_tests':negatives,'new_recovery_packet_checked':False,'neural_execution':False}


if __name__=='__main__':
    print(json.dumps(run(),sort_keys=True,indent=2))
