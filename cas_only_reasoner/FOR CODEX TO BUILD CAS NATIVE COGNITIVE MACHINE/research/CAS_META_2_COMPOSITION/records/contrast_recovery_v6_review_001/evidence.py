"""Recovery process and receipt binding without models, providers or execution."""
from datetime import datetime
import math
import re
import xml.etree.ElementTree as ET


def timestamp(value,c):
    stamp=datetime.fromisoformat(value)
    c.require(stamp.tzinfo is not None,'EVIDENCE_TIME_ZONE_REQUIRED')
    return stamp


def process(packet,name,command,c):
    row=packet.json(name)
    c.require(row['schema']=='cas-meta2-campaign-subprocess/3' and row['command']==command
        and row['completed'] is True and type(row['returncode']) is int and row['returncode']==0
        and row['timed_out'] is False and row['automatic_retry'] is False and row['new_process_group'] is True
        and type(row['pid']) is int and row['pid']>0,'EVIDENCE_PROCESS_FAILED_OR_CHANGED')
    c.require(timestamp(row['finished_utc'],c)>timestamp(row['started_utc'],c)
        and type(row['wall_seconds']) in (int,float) and math.isfinite(row['wall_seconds'])
        and row['wall_seconds']>0 and row['cwd']=='/opt/cas-meta2/package/'+c.PILOT,'EVIDENCE_PROCESS_TIME_OR_CWD')
    for stream in ('stdout','stderr'):
        actual=c.remote_member(row[stream])
        c.require(actual==name.removesuffix('process_receipt.json')+stream+'.txt','EVIDENCE_PROCESS_LOG_ATTRIBUTION')
        packet.same_hash(actual,row[stream+'_sha256'])
    return row


def gpu_gate(packet,job,c):
    gate=packet.json(c.BASE+'gpu_gate.json')
    base='/opt/cas-meta2/package/'+c.PILOT+'/runs/'+c.BASE.rstrip('/')
    command=packet.json(c.BASE+'gpu_command.json')
    c.require(type(command) is list and len(command)>0 and type(command[0]) is str
        and command[0].startswith('/opt/cas-meta2/venv/bin/python'),'EVIDENCE_GPU_PYTHON')
    expected=[command[0],'-B','-m','pytest','-m','gpu','tests/test_contrast_recovery_v6_gpu.py','-q',
        '--junitxml',base+'/gpu_tests.xml','--basetemp',base+'/gpu_scratch',
        '-p','no:cacheprovider','-p','cas_meta2.pytest_no_aliases_v4']
    c.require(command==expected and gate['schema']=='cas-meta2-contrast-recovery-gpu-gate/6'
        and gate['job']==job and gate['completed'] is True and gate['expected_command']==command
        and gate['recovery_manifest_sha256']==c.RUNTIME,'EVIDENCE_GPU_GATE_IDENTITY')
    for key,path in (('process_receipt','gpu_process/process_receipt.json'),('tests_xml','gpu_tests.xml')):
        c.require(gate[key]['path']==path,'EVIDENCE_GPU_GATE_PATH')
        packet.same_hash(c.BASE+path,gate[key]['sha256'])
    proc=process(packet,c.BASE+'gpu_process/process_receipt.json',command,c)
    raw=packet.raw(c.BASE+'gpu_tests.xml',2*1024**2)
    c.require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(),'EVIDENCE_XML_DECLARATION')
    xml=ET.fromstring(raw);cases=list(xml.iter('testcase'));suites=list(xml.iter('testsuite'))
    expected_names={'test_saved_case_zero_uses_frozen_reference_and_verifier',
                    'test_saved_case_nine_contains_only_known_post_start_failure'}
    c.require(len(cases)==2 and {x.attrib['name'] for x in cases}==expected_names
        and all(x.attrib.get('classname','').endswith('test_contrast_recovery_v6_gpu') for x in cases)
        and not any(list(xml.iter(tag)) for tag in ('failure','error','skipped')),
        'EVIDENCE_GPU_CASES_OR_FAILURE')
    c.require(suites and sum(int(x.attrib.get('tests','-1')) for x in suites)==2
        and all(int(x.attrib.get(k,'-1'))==0 for x in suites for k in ('failures','errors','skipped')),
        'EVIDENCE_GPU_XML_COUNTS')
    return {'gate_sha256':packet.inventory[c.BASE+'gpu_gate.json']['sha256'],'job':job,
        'recovery_manifest_sha256':c.RUNTIME,'tests':2,'process_pid':proc['pid'],'finished_utc':proc['finished_utc']},proc


def _baseline(value):
    return {'source':value['source'],'installed_wheels':{name:{k:v for k,v in row.items() if k!='path'}
            for name,row in value['installed_wheels'].items()}}


def baseline(value,expected,c):
    c.require(_baseline(value)==_baseline(expected)
        and value['source']=={'baseline_sha':c.BASELINE,'files_verified':316},'EVIDENCE_BASELINE_CHANGED')


def identity_pair(before,after,job,c,*,parent=None,pid=None,earliest=None,latest=None):
    c.require(type(before) is dict and type(after) is dict
        and all(before[k]==after[k] for k in ('pid','ppid','executable','python','platform','argv','job','cwd'))
        and type(before['pid']) is int and before['pid']>0 and type(before['ppid']) is int and before['ppid']>0
        and before['job']==job and before['platform']=='linux'
        and before['cwd']=='/opt/cas-meta2/package/'+c.PILOT,'EVIDENCE_PROCESS_IDENTITY_CHANGED')
    if parent is not None:c.require(before['ppid']==parent,'EVIDENCE_WORKER_PARENT')
    if pid is not None:c.require(before['pid']==pid,'EVIDENCE_NATIVE_PROCESS_PID')
    start,end=timestamp(before['utc'],c),timestamp(after['utc'],c)
    c.require(end>=start and (earliest is None or start>=earliest)
        and (latest is None or end<=latest),'EVIDENCE_PROCESS_IDENTITY_TIME')
    return before['pid']


def environment(value,runtime,c):
    c.require(runtime['cuda_matmul_passed'] is True and runtime['torch']=='2.11.0+cu128' and runtime['cuda']=='12.8'
        and type(runtime['gpu']) is str and runtime['gpu'] and 'T4' not in runtime['gpu'].upper()
        and value['torch']==runtime['torch'] and value['cuda_runtime']==runtime['cuda']
        and value['cuda_device_name']==runtime['gpu'] and value['deterministic_algorithms'] is True
        and value['tf32_matmul'] is False and value['tf32_cudnn'] is False and value['torch_cpu_threads']==1,
        'EVIDENCE_CUDA_ENVIRONMENT')


def receipts(packet,context,manifest,job,source_archive_hash,helper,c):
    c.require(type(job) is str and re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}',job)
        and job!=c.OLD_JOB,'EVIDENCE_RECOVERY_JOB')
    collection,index=helper._collection(packet,job,c.SOURCE,source_archive_hash)
    c.require(index and collection['returncode']==0 and collection['partial_evidence'] is False
        and collection['smoke_only'] is False and collection.get('experiment')==manifest['experiment'],
        'EVIDENCE_COMPLETE_COLLECTION_REQUIRED')
    job_record=packet.json('cloud_job/job.json')
    c.require(job_record['job']==job and job_record['source_sha']==c.SOURCE
        and job_record['archive_sha256']==source_archive_hash and job_record['baseline_sha']==c.BASELINE
        and type(job_record['returncode']) is int and job_record['returncode']==0
        and job_record['smoke_only'] is False and job_record['experiment']==manifest['experiment'],
        'EVIDENCE_JOB_COMPLETION')
    gpu,pgpu=gpu_gate(packet,job,c)
    gate4=helper._gpu_gate(packet,'contract')
    command=packet.json(c.BASE+'native_command.json')
    prefix='/opt/cas-meta2/package/'
    out=prefix+c.PILOT+'/runs/'+c.NATIVE.rstrip('/')
    expected=[pgpu['command'][0],'-B','-m','cas_meta2.contrast_recovery_v6',
        '--admission',prefix+manifest['recovery']['admission_path'],'--admission-sha256',c.ADMISSION,
        '--recovery-manifest',prefix+manifest['recovery']['source_manifest_path'],'--recovery-manifest-sha256',c.RUNTIME,
        '--inputs','/opt/cas-meta2/recovery_input','--packet','/opt/cas-meta2/prior_packet.zip',
        '--output',out,'--job',job,'--max-seconds','2400','--enable-native-evaluation',
        '--gpu-gate',prefix+c.PILOT+'/runs/'+c.BASE+'gpu_gate.json','--gpu-gate-sha256',gpu['gate_sha256']]
    c.require(command==expected,'EVIDENCE_NATIVE_COMMAND')
    outer=packet.json('cloud_job/command.json')
    c.require(type(outer) is list and len(outer)>=3 and outer[-1]=='--enable-native-evaluation'
        and outer[-3]=='--max-seconds' and outer[-2].isdigit() and 2800<=int(outer[-2])<=3000,
        'EVIDENCE_COORDINATOR_COMMAND_BOUND')
    expected_outer=[pgpu['command'][0],'-B',prefix+c.PILOT+'/aws/recovery_remote_v6.py',
        '--admission',prefix+manifest['recovery']['admission_path'],'--admission-sha256',c.ADMISSION,
        '--recovery-manifest',prefix+manifest['recovery']['source_manifest_path'],'--recovery-manifest-sha256',c.RUNTIME,
        '--packet','/opt/cas-meta2/prior_packet.zip','--inputs','/opt/cas-meta2/recovery_input',
        '--output',prefix+c.PILOT+'/runs/'+c.BASE.rstrip('/'),'--job',job,
        '--max-seconds',outer[-2],'--enable-native-evaluation']
    c.require(outer==expected_outer and 'cloud_job/remote_failure.json' not in packet.inventory,
              'EVIDENCE_COORDINATOR_COMMAND_OR_FAILURE')
    native=process(packet,c.BASE+'native_process/process_receipt.json',command,c)
    c.require(timestamp(native['started_utc'],c)>timestamp(pgpu['finished_utc'],c),'EVIDENCE_GPU_PRECEDES_NATIVE')
    coordinator=packet.json(c.BASE+'coordinator_receipt.json')
    receipt=packet.json(c.NATIVE+'recovery_receipt.json')
    first=packet.json(c.NATIVE+'input_binding.json')
    c.require(coordinator['schema']=='cas-meta2-recovery-coordinator/6' and coordinator['completed'] is True
        and coordinator['job']==job and coordinator['source_and_inputs_rechecked'] is True
        and coordinator['gpu_tests']=={'passed':2,'tests':2,'failures':0,'errors':0,'skipped':0}
        and coordinator['gpu_gate']==gpu and coordinator['sources']==context['sources']
        and coordinator['input_sha256']==context['input_sha256']
        and coordinator['original_packet_sha256']==c.OLD_PACKET,'EVIDENCE_COORDINATOR_BINDING')
    for name,key in (('native/recovery_receipt.json','recovery_receipt_sha256'),
        ('native/evaluation_results.json','evaluation_results_sha256'),
        ('native_process/process_receipt.json','native_process_sha256')):
        packet.same_hash(c.BASE+name,coordinator[key])
    c.require(receipt['schema']=='cas-meta2-contrast-evaluation-recovery/6'
        and receipt['status']=='CAS_META2_V6_EVALUATION_RECOVERY_COMPLETED' and receipt['completed'] is True
        and receipt['job']==job and receipt['original_job']==c.OLD_JOB and receipt['original_packet_sha256']==c.OLD_PACKET
        and receipt['original_source_archive_sha256']==manifest['recovery']['original_source_archive_sha256']
        and receipt['admission_sha256']==c.ADMISSION and receipt['recovery_manifest_sha256']==c.RUNTIME
        and receipt['gpu_gate']==gpu and type(receipt['cases']) is int and receipt['cases']==72
        and type(receipt['reference_cases']) is int and receipt['reference_cases']==72
        and type(receipt['arm_verdicts']) is int and receipt['arm_verdicts']==360
        and type(receipt['workers']) is int and receipt['workers']==8
        and receipt['sources_before']==receipt['sources_after']==context['sources']
        and receipt['original_prediction_seal']==context['seal'] and receipt['input_sha256']==context['input_sha256'],
        'EVIDENCE_RECOVERY_RECEIPT_BINDING')
    for document in (coordinator,receipt):
        c.require(document['training_performed'] is False and document['fresh_test'] is False
            and document['predictions_reused_unchanged'] is True,'EVIDENCE_RECOVERY_CLAIM_BOUNDARY')
    c.require(receipt['original_campaign_completed'] is False and receipt['predictions_regenerated'] is False
        and receipt['learning_accepted'] is False,'EVIDENCE_ORIGINAL_FAILURE_OR_PROMOTION')
    baseline(receipt['baseline_before'],context['registration']['baseline'],c)
    c.require(receipt['baseline_before']==receipt['baseline_after'],'EVIDENCE_BASELINE_BEFORE_AFTER')
    identity_pair(receipt['process_before'],receipt['process_after'],job,c,pid=native['pid'],
        earliest=timestamp(native['started_utc'],c),latest=timestamp(native['finished_utc'],c))
    runtime=packet.json('cloud_job/runtime.json');environment(receipt['environment'],runtime,c)
    expected_first={'admission_sha256':c.ADMISSION,'original_packet_sha256':c.OLD_PACKET,
        'original_source_archive_sha256':receipt['original_source_archive_sha256'],'original_job':c.OLD_JOB,
        'gpu_gate':gpu,'input_sha256':context['input_sha256'],'original_prediction_seal':context['seal'],
        'recovery_manifest_sha256':c.RUNTIME,'source_before':context['sources'],
        'process_before':receipt['process_before'],'baseline_before':receipt['baseline_before'],
        'training_performed':False,'predictions_regenerated':False,'fresh_test':False}
    c.require(first==expected_first,'EVIDENCE_FIRST_LAST_BINDING')
    c.require(timestamp(coordinator['started_utc'],c)<=timestamp(pgpu['started_utc'],c)
        and timestamp(coordinator['finished_utc'],c)>=timestamp(native['finished_utc'],c),'EVIDENCE_COORDINATOR_TIMES')
    for name in ('cloud_job/pip_freeze.txt','cloud_job/torch_install.json','cloud_job/dependency_install.json',
                 'cloud_job/frozen_wheel_install.json','cloud_job/command.json'):
        c.require(name in packet.inventory,'EVIDENCE_ENVIRONMENT_RECORD_MISSING')
    pids=set()
    def worker(value):
        c.require(value['source_sha256']==context['sources'] and value['baseline_before']==value['baseline_after']
            and value['baseline_before']==receipt['baseline_before'],'EVIDENCE_WORKER_SOURCE_BASELINE')
        environment(value['environment'],runtime,c)
        pids.add(identity_pair(value['before'],value['after'],job,c,parent=native['pid'],
            earliest=timestamp(receipt['process_before']['utc'],c),latest=timestamp(receipt['process_after']['utc'],c)))
        c.require(1<=len(pids)<=8,'EVIDENCE_WORKER_COUNT')
    return receipt,worker,{'collection':collection,'gpu_gate':gpu,'original_contract_gpu_gate':gate4,
        'gpu_process':pgpu,'native_process':native,'coordinator':coordinator,'runtime':runtime,'worker_pids':pids}
