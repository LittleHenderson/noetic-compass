"""Independent offline review of one externally pinned evaluation-only recovery."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def run(*,packet_path,packet_sha256,extracted,source_archive,source_archive_sha256,job,
        old_packet,old_extracted,create_extraction=False):
    here=Path(__file__).resolve().parent
    c=module('_recovery_review_common',here/'common.py')
    own={p.name:c.file_hash(p) for p in here.glob('*.py')}
    manifest,admission=c.source_preflight(source_archive,source_archive_sha256)
    packet=c.Packet(packet_path,packet_sha256,extracted,create=create_extraction)
    prior=c.Packet(old_packet,c.OLD_PACKET,old_extracted)
    c.require(len(prior.inventory)==879 and c.regular(old_packet).stat().st_size==74958249
        and {x['path']:x for x in admission['inventory']}==prior.inventory,'REVIEW_ORIGINAL_INVENTORY')
    with c.pure_guard():
        # All 557 local helper bytes were checked against the external source ZIP
        # AND the frozen Git commit above, before importing any of them.
        helper=c.load('_recovery_collection_primitives',c.ROOT/'tools/inspect_cloud_packet.py')
        profiles=c.load('_recovery_source_profile',c.ROOT/'tools/experiment_profiles_recovery_v6.py')
        c.require(profiles.validate_manifest(manifest)==manifest['experiment'],'REVIEW_EXPERIMENT_PROFILE')
        from cas_meta2.contrast_recovery_v6 import binding
        context=binding.load_inputs(admission_path=c.ROOT.parents[1]/manifest['recovery']['admission_path'],
            admission_sha256=c.ADMISSION,recovery_manifest_path=c.ROOT.parents[1]/manifest['recovery']['source_manifest_path'],
            recovery_manifest_sha256=c.RUNTIME,inputs=prior.root,packet=old_packet)
        c.require(context['admission']==admission,'REVIEW_ADMISSION_COPY')
        extraction=packet.json(c.BASE+'input_extraction.json')
        c.require(extraction['schema']=='cas-meta2-contrast-recovery-extraction/6'
            and extraction['packet_sha256']==c.OLD_PACKET and extraction['packet_bytes']==74958249
            and extraction['files_verified']==879 and extraction['all_member_bytes_verified_after_write'] is True
            and extraction['output']=='/opt/cas-meta2/recovery_input'
            and len(extraction['inventory'])==879
            and {x['path']:x for x in extraction['inventory']}==prior.inventory,'REVIEW_REMOTE_INPUT_EXTRACTION')
        # Separate opaque byte checks for every initial, selected and final file.
        checkpoints=admission['training_gate']['checkpoints']
        training=prior.json('cloud_job/campaign/training/training_receipt.json')
        c.require(training['checkpoints']==checkpoints,'REVIEW_CHECKPOINT_RECEIPT_COPY')
        for family in ('cas','generic'):
            c.require(set(checkpoints[family])=={'initial','selected','final'},'REVIEW_CHECKPOINT_ROLES')
            for role,row in checkpoints[family].items():
                name='cloud_job/campaign/training/'+c.safe_name(row['path'])
                prior.same_hash(name,row['sha256'])
                c.require(prior.inventory[name]['bytes']==row['bytes'] and row['family']==family,
                          'REVIEW_CHECKPOINT_BYTES_OR_FAMILY')
        engine=c.load('_recovery_semantic_primitives',c.ROOT/'tools/audit_stored_packet_v3.py')
        from jsonschema import Draft202012Validator
        from cas_meta2.campaign_v3 import admission_error
        from cas_meta2.curriculum import check_native_topology,graph_signature,parse_problem
        from cas_meta2.stored import verify_stored_composition
        engine.Draft202012Validator=Draft202012Validator
        engine.admission_error=admission_error;engine.check_native_topology=check_native_topology
        engine.graph_signature=graph_signature;engine.parse_problem=parse_problem
        engine.verify_stored_composition=verify_stored_composition;engine.safe_name=c.safe_name
        validator,schema=engine.protected_schema()
        anchor_path='cloud_job/campaign/native/evaluation/case_0000/'
        anchor_task=context['tasks'][0]
        anchor_result=prior.json(anchor_path+'reference_result.json')
        anchor=engine._native(prior,anchor_result,anchor_path+'reference',anchor_task['public'],anchor_task['target'],reference=True)
        engine.compare_verdict(prior.json(anchor_path+'reference_verdict.json'),engine.reference_verdict(anchor_task,anchor))
        context['runtime_identity']=anchor_result['runtime_identity']
        evidence=c.load('_recovery_receipt_auditor',here/'evidence.py')
        outcomes=c.load('_recovery_outcome_auditor',here/'outcomes.py')
        partial=c.load('_recovery_prefix_auditor',here/'partial.py')
        receipt,worker_check,checked=evidence.receipts(packet,context,manifest,job,source_archive_sha256,helper,c)
        audited=outcomes.audit(packet,context,engine,validator,partial,worker_check,c)
        outcomes.compare_aggregate(receipt['results'],audited['results'],c)
        traces=engine.validate_all_traces(packet,validator)
        exports=outcomes.exports(packet,validator,c)
        # This old literal diagnostic is extra local code, not a runtime source
        # dependency. Pin it independently to the frozen recovery Git tree.
        path=c.ROOT/'records/first_transition_review_v5_001/run.py'
        repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=c.ROOT,text=True).strip())
        raw=subprocess.check_output(['git','cat-file','blob',c.SOURCE+':'+path.relative_to(repo).as_posix()],cwd=repo)
        c.require(c.file_hash(path)==sha256(raw).hexdigest(),'REVIEW_DIAGNOSTIC_SOURCE_CHANGED')
        differences=c.load('_recovery_frozen_first_difference',path)
        c.require(differences.self_checks()==11,'REVIEW_DIAGNOSTIC_SELF_CHECK')
        report=c.load('_recovery_metrics_report',here/'report.py')
        diagnostics=report.build_report(context['tasks'],context['predictions'],audited['cases'],differences,c)
        c.require(not any(name in sys.modules for name in c.FORBIDDEN),'REVIEW_NEURAL_PROVIDER_IMPORTED')
        c.check_source_again(manifest);prior.verify_all();packet.verify_all()
        c.pin(source_archive,source_archive_sha256)
        c.require(own=={p.name:c.file_hash(p) for p in here.glob('*.py')},'REVIEW_OWN_CODE_CHANGED')
    checked['worker_pids']=sorted(checked['worker_pids'])
    return {'schema':'cas-meta2-contrast-recovery-stored-review/6',
        'status':'RECOVERY_STORED_REVIEW_PASSED','completed':True,'errors':[],
        'job':job,'source_sha':c.SOURCE,'source_archive_sha256':source_archive_sha256,
        'packet_sha256':packet_sha256,'source_manifest':manifest,'source_manifest_sha256':c.digest(manifest),
        'original_packet_sha256':c.OLD_PACKET,'original_job':c.OLD_JOB,'admission_sha256':c.ADMISSION,
        'runtime_manifest_sha256':c.RUNTIME,'reviewer_files_sha256':own,
        'frozen_first_difference_sha256':sha256(raw).hexdigest(),'protected_schema':schema,
        'inventory':list(packet.inventory.values()),'member_files':len(packet.inventory),
        'extraction':{'path':str(packet.root),'files_verified':len(packet.inventory),
            'all_member_bytes_verified_after_write':True},
        'original_inputs_sha256':context['input_sha256'],'sealed_predictions_unchanged':True,
        'runtime_identity_anchor':{'packet_sha256':c.OLD_PACKET,'member':anchor_path+'reference_result.json',
            'sha256':prior.inventory[anchor_path+'reference_result.json']['sha256'],
            'independent_stored_reference_checked':True},
        'checkpoints_checked_as_opaque_bytes':checkpoints,'checkpoint_tensors_loaded':False,
        'process_evidence':checked,'outcomes':audited,'trace_schema_counts':traces,'trace_exports':exports,
        'diagnostics':diagnostics,'sources_and_extractions_rechecked_at_end':True,
        'original_campaign_completed':False,'fresh_test':False,'training_performed':False,
        'neural_execution_during_audit':False,'provider_calls_during_audit':False,'automatic_promotion':False,
        'environment':{'python':sys.version,'platform':platform.platform()},
        'finished_utc':datetime.now(timezone.utc).isoformat(),
        'boundary':'Independent documentary and stored-program replay audit of all 72 reused cases and 360 saved choices. '
            'The original training job remains failed. Completed arms use the unchanged stored verifier. '
            'Post-start failures retain unknown failed-tick compute and do not acquire complete traces or final answers. '
            'Literal first divergence is not proof of the earliest causal neural token. No new neural execution, '
            'fresh-test claim, learning acceptance, CAS-specific advantage or automatic promotion follows.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    for name in ('packet','extracted','source-archive','old-packet','old-extracted','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('packet-sha256','source-archive-sha256','job'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--create-extraction',action='store_true')
    args=parser.parse_args(argv)
    here=Path(__file__).resolve().parent
    c=module('_recovery_main_common',here/'common.py')
    output=args.output.absolute()
    c.require(not output.exists() and output.resolve().is_relative_to(here.resolve())
        and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (output,*output.parents)),
        'REVIEW_NEW_LOCAL_OUTPUT_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    try:
        result=run(packet_path=args.packet,packet_sha256=args.packet_sha256,extracted=args.extracted,
            source_archive=args.source_archive,source_archive_sha256=args.source_archive_sha256,job=args.job,
            old_packet=args.old_packet,old_extracted=args.old_extracted,create_extraction=args.create_extraction)
    except BaseException as error:
        failure={'schema':'cas-meta2-contrast-recovery-stored-review/6','status':'RECOVERY_STORED_REVIEW_FAILED',
            'completed':False,'errors':[{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}],
            'packet_sha256':args.packet_sha256,'source_archive_sha256':args.source_archive_sha256,'job':args.job,
            'finished_utc':datetime.now(timezone.utc).isoformat(),'no_partial_success_claim':True}
        with (output/'review_failure.json').open('xb') as stream:stream.write(c.canonical(failure)+b'\n')
        raise
    with (output/'recovery_stored_review.json').open('xb') as stream:stream.write(c.canonical(result)+b'\n')
    print(json.dumps({'status':result['status'],'receipt':str(output/'recovery_stored_review.json'),
        'sha256':c.file_hash(output/'recovery_stored_review.json'),'cases':72,'arm_verdicts':360},sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
