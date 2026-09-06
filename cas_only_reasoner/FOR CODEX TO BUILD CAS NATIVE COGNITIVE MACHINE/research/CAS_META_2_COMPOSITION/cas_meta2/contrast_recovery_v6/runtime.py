"""AWS-gated native evaluation of old, byte-pinned predictions only."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import multiprocessing
import os
from pathlib import Path
import sqlite3
import sys
import time
import traceback

from . import binding as b
from .core import ARMS, FAILURE, MESSAGE, aggregate_cases, canonical, evaluate_case, require, write_new

_WORKER = None


def _integer_sum(value):
    if type(value) is list:
        return sum(_integer_sum(item) for item in value)
    require(type(value) is int and value >= 0, 'RECOVERY_PARTIAL_PLAN_INVALID')
    return value


def partial_work(directory):
    """Read a closed failed database without loading artifacts or changing it.

    This is a durable-work lower bound, not a full semantic trace audit. The
    uncommitted failed tick has no receipt and its compute is explicitly unknown.
    """
    directory = b.no_links(directory)
    require(directory.is_dir(), 'RECOVERY_FAILURE_DIRECTORY_MISSING')
    files = {p.name:b.file_hash(p) for p in directory.iterdir() if p.is_file()}
    require({'native.db','failure.json'} <= set(files)
            and all(not p.is_dir() for p in directory.iterdir())
            and not any(name.endswith(('-wal','-shm')) for name in files)
            and sum(p.stat().st_size for p in directory.iterdir()) <= 64*1024**2,
            'RECOVERY_CLOSED_FAILURE_EVIDENCE_REQUIRED')
    failure = b.decode(b.read(directory/'failure.json'))
    require(failure == {'status':'INFRASTRUCTURE_FAILURE','type':'RuntimeContractError','message':MESSAGE},
            'RECOVERY_ORIGINAL_FAILURE_MISMATCH')
    database = b.no_links(directory/'native.db').resolve()
    con = sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1', uri=True)
    try:
        con.execute('PRAGMA query_only=ON')
        require(con.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'RECOVERY_PARTIAL_SQLITE_INTEGRITY')
        require(con.execute('select value from store_metadata where key=?', ('schema_version',)).fetchone()
                == ('cas.neural-cjt.sqlite-store/0.2',), 'RECOVERY_PARTIAL_STORE_SCHEMA')
        traces = con.execute('select sequence,payload_sha256,payload_json,trace_digest from trace_events order by sequence').fetchall()
        units, previous = 0, None
        for index, (sequence, pin, raw, trace_digest) in enumerate(traces):
            require(sequence == index+1 and sha256(raw.encode()).hexdigest() == pin,
                    'RECOVERY_PARTIAL_PAYLOAD_HASH')
            trace = b.decode(raw)
            require(trace['tick'] == index+1 and trace['previous_trace_digest'] == previous
                    and trace['trace_digest'] == trace_digest and len(trace['published_effect_ids']) == 1
                    and len(trace['verifier_receipts']) == 1
                    and trace['verifier_receipts'][0]['disposition'] == 'ACCEPT',
                    'RECOVERY_PARTIAL_ACCEPT_PREFIX')
            previous = trace_digest
            units += sum(_integer_sum(trace['compute_plan'][key]) for key in
                ('route_quanta','reasoning_step_quanta','branch_quanta','memory_read_quanta','diagnostic_probe_quanta'))
        require(con.execute('select count(*) from commit_receipts').fetchone()[0] == len(traces)
                and con.execute('select count(*) from published_effects').fetchone()[0] == len(traces),
                'RECOVERY_PARTIAL_COMMIT_COUNTS')
        head = con.execute('select state_version,trace_digest from active_head').fetchone()
        require(head == (len(traces),previous), 'RECOVERY_PARTIAL_HEAD_MISMATCH')
    finally:
        con.close()
    require({p.name:b.file_hash(p) for p in directory.iterdir() if p.is_file()} == files,
            'RECOVERY_PARTIAL_EVIDENCE_CHANGED')
    return {'committed_native_runs':len(traces), 'committed_reserved_policy_units':units,
        'failed_tick_compute':None, 'compute_complete':False, 'database_sha256':files['native.db'],
        'evidence_sha256':files, 'sqlite_integrity_checked':True, 'payload_hashes_checked':True,
        'stored_trace_semantics_checked':False, 'full_execution_trace_available':False,
        'boundary':'Committed ACCEPT prefix only. Failed-tick compute and final output are unavailable; '
                   'this does not declare a complete integrity-valid execution trace.'}


def _baseline_bytes(identity):
    return {'source':identity['source'], 'installed_wheels':{name:{key:value for key,value in record.items()
            if key != 'path'} for name,record in identity['installed_wheels'].items()}}


class FrozenOperations:
    """Construct only after AWS request and source admission, including in GPU tests."""
    def __init__(self, context, *, job, enabled):
        b.require_request(job, enabled)
        self.context = context
        # Source validation precedes imports of the trusted execution helpers.
        require(b.source_identity(context['admission'],context['recovery_manifest']) == context['sources'],
                'RECOVERY_SOURCE_CHANGED_BEFORE_NATIVE_IMPORT')
        from ..contrast_v6 import train
        from ..campaign_v3 import _baseline_identity, admission_error
        from .. import native
        self.train, self.baseline_identity = train, _baseline_identity
        self.native, self.admission_error = native, admission_error
        self.before_baseline = _baseline_identity()
        require(_baseline_bytes(self.before_baseline) == _baseline_bytes(context['registration']['baseline']),
                'RECOVERY_FROZEN_BASELINE_CHANGED')
        self.assert_identity()
        from ..train_v3 import setup_cuda, environment_identity
        torch, device = setup_cuda()
        require('T4' not in torch.cuda.get_device_name(device).upper(), 'T4_NOT_AUTHORIZED')
        from cas_cjt.runtime import RuntimeContractError
        self.runtime_contract_error = RuntimeContractError
        self.device = str(device)
        self.environment = environment_identity(device)
        self.verify_task = native.verify_task
        self.verify_reference_task = native.verify_reference_task
        self.partial_work = partial_work

    def assert_identity(self):
        require(self.train.source_identity() == self.context['admission']['training_gate']['source_sha256'],
                'RECOVERY_EXECUTION_SOURCE_CHANGED')
        current = self.baseline_identity()
        require(current == self.before_baseline, 'RECOVERY_BASELINE_CHANGED_DURING_PROCESS')
        for name,pin in self.context['sources']['recovery_files_sha256'].items():
            require(b.file_hash(b.relative(b.ROOT,name)) == pin, 'RECOVERY_OWN_SOURCE_CHANGED')

    def reference_task(self, task, directory):
        return self.native.reference_task(task,directory,device=self.device)

    def execute_task(self, public, action, directory):
        return self.native.execute_task(public,action,directory,device=self.device)


def process_identity(job):
    return {'pid':os.getpid(), 'ppid':os.getppid(), 'executable':sys.executable,
            'python':sys.version, 'platform':sys.platform, 'argv':list(sys.argv),
            'job':job, 'cwd':str(Path.cwd()), 'utc':datetime.now(timezone.utc).isoformat()}


def _initialize(arguments, job, enabled, gate_path, gate_pin):
    global _WORKER
    b.require_request(job,enabled)
    gate = b.check_gpu_gate(gate_path,gate_pin,job=job,
                          recovery_manifest_sha256=arguments['recovery_manifest_sha256'])
    context = b.load_inputs(**arguments)
    operations = FrozenOperations(context,job=job,enabled=enabled)
    _WORKER = {'context':context,'operations':operations,'job':job,'gate':gate}


def _case(index, output):
    require(_WORKER is not None, 'RECOVERY_WORKER_NOT_INITIALIZED')
    context, ops = _WORKER['context'],_WORKER['operations']
    directory = Path(output)/'evaluation'/f'case_{index:04d}'
    before = process_identity(_WORKER['job'])
    try:
        result = evaluate_case(index,context['tasks'][index],context['predictions'][index]['actions'],directory,ops)
        ops.assert_identity()
        write_new(directory/'worker_identity.json',{'before':before,'after':process_identity(_WORKER['job']),
            'environment':ops.environment,'baseline_before':ops.before_baseline,
            'baseline_after':ops.baseline_identity(),'source_sha256':context['sources']})
        return result
    except BaseException as error:
        write_new(directory/'worker_failure.json',{'type':type(error).__name__,'message':str(error),
            'case_index':index,'completed':False,'traceback':traceback.format_exc(),
            'process_before':before,'process_after':process_identity(_WORKER['job'])})
        raise


def run(*, admission_path, admission_sha256, recovery_manifest_path, recovery_manifest_sha256,
        inputs, packet, output, job, gpu_gate_path, gpu_gate_sha256, max_seconds=2400, enabled=False):
    b.require_request(job,enabled)
    require(type(max_seconds) is int and 60 <= max_seconds <= 3600, 'RECOVERY_DEADLINE_BOUND')
    output = b.no_links(output).resolve()
    require(output.is_relative_to(b.ROOT) and output != b.ROOT and not output.exists()
            and not output.is_relative_to(Path(inputs).resolve())
            and not Path(inputs).resolve().is_relative_to(output), 'RECOVERY_NEW_ISOLATED_OUTPUT_REQUIRED')
    started, before = time.monotonic(), process_identity(job)
    arguments = dict(admission_path=admission_path,admission_sha256=admission_sha256,
        recovery_manifest_path=recovery_manifest_path,recovery_manifest_sha256=recovery_manifest_sha256,
        inputs=inputs,packet=packet)
    gate = b.check_gpu_gate(gpu_gate_path,gpu_gate_sha256,job=job,recovery_manifest_sha256=recovery_manifest_sha256)
    context = b.load_inputs(**arguments)
    # Setup occurs only after both independent admission and the real GPU gate.
    ops = FrozenOperations(context,job=job,enabled=enabled)
    output.mkdir(parents=True,exist_ok=False)
    write_new(output/'input_binding.json',{'admission_sha256':admission_sha256,'original_packet_sha256':b.PACKET,
        'original_source_archive_sha256':b.SOURCE_ARCHIVE,'original_job':b.ORIGINAL_JOB,'gpu_gate':gate,
        'input_sha256':context['input_sha256'],'original_prediction_seal':context['seal'],
        'recovery_manifest_sha256':recovery_manifest_sha256,'source_before':context['sources'],
        'process_before':before,'baseline_before':ops.before_baseline,
        'training_performed':False,'predictions_regenerated':False,'fresh_test':False})
    pool = ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn'),
        initializer=_initialize,initargs=(arguments,job,enabled,gpu_gate_path,gpu_gate_sha256))
    futures, completed, succeeded = [],[],False
    try:
        for index in range(72):
            futures.append(pool.submit(_case,index,str(output)))
        for future in as_completed(futures,timeout=max(0.01,max_seconds-(time.monotonic()-started))):
            require(time.monotonic()-started < max_seconds,'RECOVERY_DEADLINE')
            completed.append(future.result())
            from ..campaign_v3 import _output_bytes
            size = _output_bytes(output)
            print(canonical({'stage':'evaluation_only_recovery','completed_cases':len(completed),
                'expected_cases':72,'output_bytes':size}).decode(),flush=True)
        completed.sort(key=lambda case:case['case_index'])
        results = aggregate_cases(completed)
        after_context = b.load_inputs(**arguments)
        require(after_context == context,'RECOVERY_INPUTS_CHANGED_AFTER_EXECUTION')
        require(b.check_gpu_gate(gpu_gate_path,gpu_gate_sha256,job=job,
            recovery_manifest_sha256=recovery_manifest_sha256) == gate,'RECOVERY_GATE_CHANGED')
        ops.assert_identity()
        write_new(output/'evaluation_results.json',{'cases':completed,'results':results})
        receipt = {'schema':'cas-meta2-contrast-evaluation-recovery/6',
            'status':'CAS_META2_V6_EVALUATION_RECOVERY_COMPLETED','completed':True,
            'job':job,'original_job':b.ORIGINAL_JOB,'original_packet_sha256':b.PACKET,
            'original_source_archive_sha256':b.SOURCE_ARCHIVE,'admission_sha256':admission_sha256,
            'recovery_manifest_sha256':recovery_manifest_sha256,'gpu_gate':gate,
            'cases':72,'reference_cases':72,'arm_verdicts':360,'workers':8,'results':results,
            'original_campaign_completed':False,'fresh_test':False,'training_performed':False,
            'predictions_reused_unchanged':True,'predictions_regenerated':False,'learning_accepted':False,
            'original_prediction_seal':context['seal'],'input_sha256':context['input_sha256'],
            'sources_before':context['sources'],'sources_after':after_context['sources'],
            'baseline_before':ops.before_baseline,'baseline_after':ops.baseline_identity(),
            'process_before':before,'process_after':process_identity(job),
            'wall_seconds':time.monotonic()-started,'environment':ops.environment,
            'boundary':'Separate evaluation-only recovery on already-exposed fixed test cases. '
                'No retraining, new prediction, new fresh test, changed executor/verifier, or automatic promotion. '
                'Only the exact unsupported durable repair-round-trip error is contained after execution starts.'}
        write_new(output/'recovery_receipt.json',receipt)
        succeeded = True
        return receipt
    except BaseException as error:
        write_new(output/'recovery_failure.json',{'completed':False,'job':job,'type':type(error).__name__,
            'message':str(error),'traceback':traceback.format_exc(),'original_packet_sha256':b.PACKET,
            'all72_completed':False,'fresh_test':False,'training_performed':False})
        raise
    finally:
        if succeeded:
            pool.shutdown(wait=True)
        else:
            processes = list(getattr(pool,'_processes',{}).values())
            for future in futures:
                future.cancel()
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
            pool.shutdown(wait=False,cancel_futures=True)
            write_new(output/'evaluation_partial.json',{'completed':False,'cases':completed,'expected':72,
                'expected_arm_verdicts':360,'automatic_retry':False,'partial_files_retained':True})
