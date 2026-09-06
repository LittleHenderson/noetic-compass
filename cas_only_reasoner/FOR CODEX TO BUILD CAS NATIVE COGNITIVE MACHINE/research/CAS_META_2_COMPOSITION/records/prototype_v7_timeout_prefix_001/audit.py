"""Read-only semantic checks on the separately copied timeout prefix."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COPY_SHA = '9e1708bba0701ae79e9fea2dd12044250db3c999c74de97eecb49031cf3940cd'
COPY_HELPER_SHA = '0f9d69688b63eb1d4c80063f2e22d9071d75907fc59c6724b5455576572f80bc'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def run():
    assert sha256((HERE/'copy_view.py').read_bytes()).hexdigest() == COPY_HELPER_SHA
    copied_helper = load('_v7_timeout_copy', HERE/'copy_view.py')
    m = copied_helper.load_extractor()
    m.pin(copied_helper.ADMISSION, copied_helper.ADMISSION_SHA)
    admitted = m.decode(copied_helper.ADMISSION.read_bytes())
    m.pin(HERE/'copy_receipt.json', COPY_SHA)
    copy = m.decode((HERE/'copy_receipt.json').read_bytes())
    m.require(copy['admission_sha256'] == copied_helper.ADMISSION_SHA
        and copy['packet_sha256'] == m.PACKET and copy['source_sha'] == m.SOURCE
        and copy['original_bytes_unchanged'] is True and copy['integrity_check'] == 'ok', 'TIMEOUT_COPY_IDENTITY')
    m.pin(admitted['packet']['path'], m.PACKET)
    m.pin(admitted['source_archive']['path'], m.SOURCE_ARCHIVE)
    m.pin(m.COMMON, m.COMMON_SHA)
    c = load('_v7_timeout_common', m.COMMON)
    used, inventory, root = {}, admitted['inventory'], Path(admitted['extraction']['path'])
    def raw(name):
        m.require(name in inventory and inventory[name]['bytes'] <= 64*1024**2, 'TIMEOUT_MEMBER_BOUND')
        path = root/name; m.pin(path, inventory[name]['sha256'])
        used[name] = inventory[name]['sha256']
        return path.read_bytes()
    def read(name): return m.decode(raw(name))
    started = datetime.now(timezone.utc).isoformat()
    with c.pure_guard():
        manifest, prior = c.source_preflight(admitted['source_archive']['path'], m.SOURCE_ARCHIVE, m.SOURCE)
        from jsonschema import Draft202012Validator
        from cas_meta2.curriculum import check_native_topology, parse_problem
        from cas_meta2.native import admit_action
        engine = c.load('_v7_timeout_stored_engine', ROOT/'tools/audit_stored_packet_v3.py')
        engine.Draft202012Validator = Draft202012Validator
        engine.check_native_topology = check_native_topology
        validator, schema = engine.protected_schema()
        native = m.BASE+'native/'
        dataset = read(m.BASE+'dataset/manifest.json')
        public_raw = raw(m.BASE+'dataset/test_public.json')
        m.require(sha256(public_raw).hexdigest() == dataset['sha256']['test_public.json'], 'TIMEOUT_PUBLIC_MANIFEST_BINDING')
        publics = m.decode(public_raw)
        predicted_raw = raw(native+'predictions.jsonl')
        predictions = [m.decode(line) for line in predicted_raw.splitlines()]
        neural_raw = raw(m.BASE+'training/neural_predictions.jsonl')
        neural = [m.decode(line) for line in neural_raw.splitlines()]
        gate = read(native+'training_parent_gate.json')
        m.require(gate == read(m.BASE+'training_gate.json') and gate['completed'] is True
            and gate['predictions_sha256'] == sha256(neural_raw).hexdigest()
            and gate['manifest_sha256'] == inventory[m.BASE+'dataset/manifest.json']['sha256'], 'TIMEOUT_STORED_GATE_BINDING')
        seal = read(native+'predictions_seal.json')
        m.require(seal == {'schema':'cas-meta2-contrast-evaluation-seal/7', 'sha256':sha256(predicted_raw).hexdigest(),
            'neural_predictions_sha256':gate['predictions_sha256'], 'parent_gate_sha256':c.digest(gate),
            'manifest_sha256':gate['manifest_sha256'], 'arms':list(c.ARMS), 'test_examples':72,
            'prediction_count':360, 'rule_input':'public problem and permitted observations only',
            'sealed_utc':seal['sealed_utc']}, 'TIMEOUT_NATIVE_SEAL_BINDING')
        m.require(len(publics) == len(predictions) == len(neural) == 72, 'TIMEOUT_EXACT_PREDICTION_COUNT')
        for index, (public, prediction, row) in enumerate(zip(publics, predictions, neural, strict=True)):
            m.require(type(prediction['case_index']) is int and prediction['case_index'] == index
                and set(prediction) == {'case_index', 'public_sha256', 'actions'}
                and prediction['public_sha256'] == c.digest(public) and set(prediction['actions']) == set(c.ARMS)
                and row == {**prediction, 'actions': {arm:prediction['actions'][arm] for arm in c.ARMS[:-1]}}
                and prediction['actions']['rule'] == parse_problem(public), 'TIMEOUT_PUBLIC_ACTION_ATTRIBUTION')
        action = predictions[45]['actions']['generic_trained']; public = publics[45]
        admit_action(public, action)
        partial = read(native+'evaluation_partial.json')
        indices = [row['case_index'] for row in partial['cases']]
        m.require(partial['completed'] is False and partial['expected'] == 72
            and partial['automatic_retry'] is False and partial['partial_files_retained'] is True
            and len(indices) == len(set(indices)) == 71 and set(indices) == set(range(72))-{45},
            'TIMEOUT_PARTIAL_CASE_IDENTITY')
        process = read(m.BASE+'processes/evaluate/process_receipt.json')
        m.require(process['completed'] is False and type(process['returncode']) is int
            and process['returncode'] != 0 and process['automatic_retry'] is False, 'TIMEOUT_EVALUATION_FAILURE_IDENTITY')
        for stream in ('stdout', 'stderr'):
            name = m.BASE+'processes/evaluate/'+stream+'.txt'
            m.require(sha256(raw(name)).hexdigest() == process[stream+'_sha256'], 'TIMEOUT_PROCESS_LOG_BINDING')
        identity = prior['outcomes']['runtime_identity']
        reference = read(native+'evaluation/case_0045/reference_result.json')
        m.require(reference['runtime_identity'] == reference['runtime_identity_after'] == identity,
            'TIMEOUT_FIXED_REFERENCE_RUNTIME_IDENTITY')
        prefix_path = copied_helper.PREFIX
        m.require({name[len(prefix_path):] for name in inventory if name.startswith(prefix_path)}
            == {'native.db', 'native.db-wal', 'native.db-shm'}, 'TIMEOUT_EXACT_TRIPLET')
        for name in ('native.db', 'native.db-wal', 'native.db-shm'):
            m.require(inventory[prefix_path+name]['sha256'] == copy['original_sha256_before'][name], 'TIMEOUT_COPY_ORIGINAL_BINDING')
            raw(prefix_path+name)
        arm = native+'evaluation/case_0045/generic_trained/'
        m.require(not any(arm+name in inventory for name in ('case_receipt.json', 'verification.json', 'execution_result.json')),
            'TIMEOUT_ARM_COMPLETION_UNEXPECTED')
        m.pin(copy['derived_database'], copy['derived_sha256'])
        con = sqlite3.connect(Path(copy['derived_database']).as_uri()+'?mode=ro&immutable=1', uri=True)
        con.row_factory = sqlite3.Row
        helper = c.load('_v7_timeout_prefix_semantics', HERE/'prefix.py')
        helper_pins = {name:m.file_hash(HERE/name) for name in ('audit.py', 'prefix.py', 'copy_view.py')}
        try:
            con.execute('PRAGMA query_only=ON')
            prefix = helper.verify_prefix(con, public, action, identity, engine, validator, c)
        finally:
            con.close()
        c.check_source_again(manifest)
        for name, value in used.items(): m.pin(root/name, value)
        for name, value in helper_pins.items(): m.pin(HERE/name, value)
        m.pin(copy['derived_database'], copy['derived_sha256'])
        m.pin(HERE/'copy_receipt.json', COPY_SHA)
        m.pin(copied_helper.ADMISSION, copied_helper.ADMISSION_SHA)
        m.pin(admitted['packet']['path'], m.PACKET)
        m.pin(admitted['source_archive']['path'], m.SOURCE_ARCHIVE)
    record = {'schema':'cas-meta2-prototype-timeout-prefix-review/7', 'status':'TIMEOUT_COMMITTED_PREFIX_VERIFIED',
        'case_index':45, 'arm':'generic_trained', 'job':m.JOB, 'source_sha':m.SOURCE,
        'packet_sha256':m.PACKET, 'extraction_admission_sha256':copied_helper.ADMISSION_SHA,
        'sqlite_copy_receipt_sha256':COPY_SHA, 'derived_database_sha256':copy['derived_sha256'],
        'started_utc':started, 'finished_utc':datetime.now(timezone.utc).isoformat(),
        'schema_checked':schema, 'prefix':prefix, 'selected_action':action, 'public_sha256':c.digest(public),
        'all_72_prediction_rows_bound':True, 'all_72_cases_completed':False,
        'unfinished_case':45, 'original_db_wal_shm_unchanged':True,
        'source603_and_protected316_rechecked':True, 'input_files_sha256':used,
        'helper_files_sha256':helper_pins, 'model_or_tensor_loaded':False,
        'learning_accepted':False, 'runtime_root_cause_determined':False,
        'command':[sys.executable,'-B',*sys.argv],
        'boundary':'Interrupted by evaluation timeout. This verifies a durable committed prefix only. '
            'It does not prove a deadlock or why the remaining execution took so long, and does not certify '
            'the next tick, remaining compute, final output, full-task verdict, or a completed experiment. '
            'No fabricated RuntimeContractError receipt or old partial.audit_prefix call was used.'}
    with (HERE/'timeout_prefix_receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k:record[k] for k in ('status','case_index','arm','unfinished_case',
        'original_db_wal_shm_unchanged','runtime_root_cause_determined')}, indent=2))
    print(json.dumps({k:v for k,v in prefix.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    run()
