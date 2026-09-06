"""Render only the pinned training recount. No models, tasks or provider reads."""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPECTED_RECEIPT = ROOT/'records/prototype_v7_training_recount_001/receipt_001.json'
RECEIPT_SHA = '452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76'
SOURCE_SHA = '42f9164754312f12850d9b8789c062fa7fb8069f'
PACKET_SHA = 'f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799'
ARCHIVE_SHA = 'f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
JOB = 'cas-meta2-20260906094002-39762c47'
FAMILIES = ('cas', 'generic')
DEPTHS = ('1', '2', '3')
METRICS = ('joint_correct', 'program_correct', 'binding_correct', 'valid_programs')
CURVE_FIELDS = ('family', 'epoch', 'depth', 'validation_joint_correct', 'validation_total',
    'training_probe_joint_correct', 'training_probe_total', 'selected_at_epoch', 'final_selected_checkpoint',
    'validation_program_correct', 'validation_binding_correct', 'validation_valid_programs',
    'training_probe_program_correct', 'training_probe_binding_correct', 'training_probe_valid_programs')
CHECKPOINT_FIELDS = ('family', 'stage', 'epoch', 'optimizer_steps', 'bytes', 'recorded_filename', 'sha256',
    'recorded_remote_path', 'validation_joint_correct', 'validation_total')


def require(value, code):
    if not value: raise ValueError(code)


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda:False)()
        for p in (path, *path.parents)), 'REGULAR_INPUT_REQUIRED')
    return path


def file_hash(path):
    with regular(path).open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def decode(raw):
    require(len(raw) <= 4*1024**2, 'RECEIPT_SIZE_BOUND')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'DUPLICATE_JSON_KEY'); value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def integer(value, minimum, maximum, code):
    require(type(value) is int and minimum <= value <= maximum, code)


def validate(r):
    require(r['status'] == 'V7_SAVED_TRAINING_RECOUNT_PASSED' and r['completed'] is True
        and r['campaign_completed'] is False and r['native_evaluation_completed'] is False
        and r['learning_accepted'] is False and r['neural_execution'] is False
        and r['source_sha'] == SOURCE_SHA and r['source_archive_sha256'] == ARCHIVE_SHA
        and r['packet_sha256'] == PACKET_SHA and r['job'] == JOB
        and r['source_files_checked'] == 603 and r['protected_files_checked'] == 316,
        'PINNED_TRAINING_RECOUNT_IDENTITY_OR_BOUNDARY')
    require(r['completed_epochs'] == 200 and r['optimizer_steps'] == {'cas':11200, 'generic':11200},
        'REGISTERED_COMPLETED_TRAINING_COUNTS')
    require(r['dataset']['splits'] == {'train':{'tasks':896,'depths':{'1':128,'2':384,'3':384}},
        'validation':{'tasks':96,'depths':{'1':32,'2':32,'3':32}}, 'test':{'tasks':72,'depths':{'3':48,'4':24}}},
        'ASSEMBLED_SPLITS_CHANGED')
    require(r['dataset']['base']['config']['test_triplets'] == 24
        and r['dataset']['prototype']['tasks'] == 256 and r['dataset']['prototype']['allowed_split'] == 'train',
        'TRIPLET_OR_TRAINING_IMPORT_BOUNDARY')
    curves = r['curves']; require(type(curves) is list, 'CURVE_LIST_REQUIRED')
    expected_epochs = [0, 1, *range(10, 201, 10)]
    lookup = {}
    for row in curves:
        require(set(row) == {'epoch','family','selected','training_probe','validation'}
            and row['family'] in FAMILIES and type(row['selected']) is bool, 'CURVE_ROW_FIELDS')
        integer(row['epoch'], 0, 200, 'CURVE_EPOCH')
        key = row['family'], row['epoch']
        require(key not in lookup, 'DUPLICATE_CURVE_ROW'); lookup[key] = row
        for split, denominator in (('validation',32), ('training_probe',8)):
            group = row[split]
            require(group['expected_depths'] == [1,2,3] and set(group['by_depth']) == set(DEPTHS), 'MEASURED_DEPTH_COVERAGE')
            for depth in DEPTHS:
                metric = group['by_depth'][depth]
                require(metric['total'] == denominator and type(metric['total']) is int
                    and metric['native_execution_performed'] is False and metric['all_cases_in_denominator'] is True,
                    'METRIC_DENOMINATOR_OR_BOUNDARY')
                for name in METRICS: integer(metric[name], 0, denominator, 'METRIC_INTEGER_RANGE')
                require(metric['joint_correct'] <= min(metric['program_correct'], metric['binding_correct']), 'JOINT_SCORE_BOUND')
            overall = group['overall']
            for name in (*METRICS, 'total'):
                require(overall[name] == sum(group['by_depth'][d][name] for d in DEPTHS), 'OVERALL_RECOUNT_MISMATCH')
    require(set(lookup) == {(f,e) for f in FAMILIES for e in expected_epochs}, 'ALL_MEASURED_EPOCHS_REQUIRED')
    checkpoints = r['training_gate']['checkpoints']
    require(set(checkpoints) == set(FAMILIES), 'CHECKPOINT_FAMILIES')
    for family in FAMILIES:
        require(set(checkpoints[family]) == {'initial','selected','final'}, 'CHECKPOINT_STAGES')
        selected_epochs = [e for f,e in lookup if f == family and lookup[(f,e)]['selected']]
        require(checkpoints[family]['selected']['epoch'] == max(selected_epochs), 'FINAL_SELECTED_HISTORY_MISMATCH')
        for stage, cp in checkpoints[family].items():
            require(cp['family'] == family and (family,cp['epoch']) in lookup
                and cp['validation']['generation'] == lookup[(family,cp['epoch'])]['validation'], 'CHECKPOINT_CURVE_COPY')
            integer(cp['bytes'], 1, 64*1024**2, 'CHECKPOINT_BYTES')
            integer(cp['optimizer_steps'], 0, 11200, 'CHECKPOINT_STEPS')
            require(type(cp['sha256']) is str and re.fullmatch('[0-9a-f]{64}',cp['sha256'])
                and type(cp['path']) is str and Path(cp['path']).name == cp['path']
                and '/' not in cp['path'] and '\\' not in cp['path'], 'CHECKPOINT_HASH_OR_FILENAME')
            if stage == 'initial': require(cp['epoch'] == 0 and cp['optimizer_steps'] == 0, 'INITIAL_CHECKPOINT')
            if stage == 'final': require(cp['epoch'] == 200 and cp['optimizer_steps'] == 11200, 'FINAL_CHECKPOINT')
    return lookup


def curve_rows(r):
    result = []
    for row in sorted(r['curves'], key=lambda x:(x['family'],x['epoch'])):
        for depth in DEPTHS:
            v,p = row['validation']['by_depth'][depth],row['training_probe']['by_depth'][depth]
            item = {'family':row['family'], 'epoch':row['epoch'], 'depth':int(depth),
                'validation_joint_correct':v['joint_correct'], 'validation_total':v['total'],
                'training_probe_joint_correct':p['joint_correct'], 'training_probe_total':p['total'],
                'selected_at_epoch':row['selected'],
                'final_selected_checkpoint':row['epoch'] == r['training_gate']['checkpoints'][row['family']]['selected']['epoch']}
            for name in METRICS[1:]:
                item['validation_'+name] = v[name]; item['training_probe_'+name] = p[name]
            result.append(item)
    return result


def checkpoint_rows(r):
    command = r['processes']['training']['command']
    output = command[command.index('--output')+1]
    require(output.endswith('/runs/cloud_job/campaign/training'), 'RECORDED_TRAINING_OUTPUT')
    rows = []
    for family in FAMILIES:
        for stage in ('initial','selected','final'):
            cp = r['training_gate']['checkpoints'][family][stage]
            metric = cp['validation']['generation']['overall']
            rows.append({'family':family, 'stage':stage,
                **{k:cp[k] for k in ('epoch','optimizer_steps','bytes','sha256')},
                'recorded_filename':cp['path'], 'recorded_remote_path':output+'/'+cp['path'],
                'validation_joint_correct':metric['joint_correct'], 'validation_total':metric['total']})
    return rows


def cell(value):
    return ('true' if value else 'false') if type(value) is bool else str(value)


def csv_text(fields, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n')
    writer.writeheader(); writer.writerows({k:cell(row[k]) for k in fields} for row in rows)
    return buffer.getvalue()


def tables(r):
    lookup = {(row['family'],row['epoch']):row for row in r['curves']}
    values = []
    values.append(('dataset', ['Split','Tasks','Depth 1','Depth 2','Depth 3','Depth 4'],
        [[name,r['dataset']['splits'][name]['tasks'],*[r['dataset']['splits'][name]['depths'].get(str(d),0)
            for d in range(1,5)]] for name in ('train','validation','test')]))
    values.append(('checkpoints', ['Family','Stage','Epoch','Optimizer steps','Bytes','Recorded filename','SHA-256'],
        [[row[k] for k in ('family','stage','epoch','optimizer_steps','bytes','recorded_filename','sha256')]
            for row in checkpoint_rows(r)]))
    summary = []
    for family in FAMILIES:
        for stage in ('initial','selected','final'):
            epoch = r['training_gate']['checkpoints'][family][stage]['epoch']
            row = lookup[family,epoch]
            summary.append([family,stage,epoch,*[f"{row['validation']['by_depth'][d]['joint_correct']}/32" for d in DEPTHS],
                *[f"{row['training_probe']['by_depth'][d]['joint_correct']}/8" for d in DEPTHS]])
    values.append(('snapshot', ['Family','Stage','Epoch','Val d1','Val d2','Val d3','Probe d1','Probe d2','Probe d3'], summary))
    epochs = sorted({row['epoch'] for row in r['curves']})
    for depth in DEPTHS:
        rows = []
        for epoch in epochs:
            row = [epoch]
            for family in FAMILIES:
                value = lookup[family,epoch]
                row += [f"{value['validation']['by_depth'][depth]['joint_correct']}/32",
                    f"{value['training_probe']['by_depth'][depth]['joint_correct']}/8", value['selected'],
                    epoch == r['training_gate']['checkpoints'][family]['selected']['epoch']]
            rows.append(row)
        values.append(('depth_'+depth, ['Epoch','CAS validation','CAS probe','CAS selected then','CAS final choice',
            'Generic validation','Generic probe','Generic selected then','Generic final choice'], rows))
    return [(name,head,[[cell(x) for x in row] for row in rows]) for name,head,rows in values]


def table_text(name, headings, rows):
    return '\n'.join(['<!-- table:'+name+' -->','| '+' | '.join(headings)+' |',
        '| '+' | '.join('---' for _ in headings)+' |', *['| '+' | '.join(row)+' |' for row in rows],
        '<!-- endtable:'+name+' -->'])


def markdown(r):
    rendered = {name:table_text(name,heads,rows) for name,heads,rows in tables(r)}
    return '\n\n'.join(['# V7 training learning curves — action selection only',
        'Training finished, but the full experiment did not. These scores measure whether the freely generated '
        'program and input binding both exactly match the checked target. They are not native task correctness '
        'scores, proof of CAS advantage, or a neural rerun.',
        'The source receipt recounts saved validation/probe actions and replays the existing validation-only checkpoint '
        'selection. Checkpoint bytes were already checked there; this report only reads that pinned JSON receipt.',
        '## Data and test limits', rendered['dataset'],
        'The training split includes the exact original 256 records, used only for training. Validation has 32 '
        'examples at each measured depth. The training probe has 8 examples per depth and is part of development, '
        'not a test result.',
        'The separate test combines fresh instances with unseen program combinations. It does not isolate those '
        'two changes into separate experiments. Its 72 variants are 24 related triplets, not 72 independent program '
        'structures. There is no depth-2 test group; depth-2 validation is present. No test or native outcome score '
        'is included in this report, and no task graphs were recomputed.',
        '## Before, selected, and final',
        'Initial means before training. Selected means the final validation-selected checkpoint. Final means the '
        'last training epoch; it need not be the selected checkpoint. Ratios below are exact counts, not rounded percentages.',
        rendered['snapshot'], rendered['checkpoints'],
        'The checkpoint CSV also preserves the exact recorded remote file addresses. Those are historical AWS '
        'paths, not claims that the terminated worker is still available.',
        '## Every measured depth curve',
        'All 22 measured epochs per family are shown: epoch 0, epoch 1, and every tenth epoch through 200. '
        'The receipt has no generation measurement for intervening epochs; none was filled in. '
        '“Selected then” preserves the recorded best-so-far flag. “Final choice” marks only the checkpoint retained '
        'after the complete training run. Every validation ratio uses 32 cases; every probe ratio uses 8.',
        *[part for d in DEPTHS for part in ('### Depth '+d, rendered['depth_'+d])],
        '## Evidence boundary and source',
        '> '+r['boundary'], '> '+r['training_gate']['boundary'],
        'Training-recount receipt SHA-256: `'+RECEIPT_SHA+'`.',
        'Source commit: `'+r['source_sha']+'`. Source archive: `'+r['source_archive_sha256']+'`.',
        'Collected packet: `'+r['packet_sha256']+'`. Job: `'+r['job']+'`.',
        'The CSV retains joint correctness plus its separate program, binding, and valid-program counts. '
        'A valid program alone is not a correct program or a correct task answer.'])+'\n'


def verify_rendered(r, curve_csv, cp_csv, report):
    lookup = {(row['family'],row['epoch']):row for row in r['curves']}
    rows = list(csv.DictReader(io.StringIO(curve_csv)))
    require(rows and tuple(rows[0]) == CURVE_FIELDS, 'CSV_FIELDS_CHANGED')
    seen = set()
    for row in rows:
        key = row['family'],int(row['epoch']),row['depth']
        require(key not in seen and key[:2] in lookup and key[2] in DEPTHS, 'CSV_ROW_COVERAGE'); seen.add(key)
        source = lookup[key[:2]]
        expected = {'family':key[0], 'epoch':key[1], 'depth':int(key[2]), 'selected_at_epoch':source['selected'],
            'final_selected_checkpoint':key[1] == r['training_gate']['checkpoints'][key[0]]['selected']['epoch']}
        for split in ('validation','training_probe'):
            for metric in (*METRICS, 'total'):
                expected[split+'_'+metric] = source[split]['by_depth'][key[2]][metric]
        require(row == {k:cell(v) for k,v in expected.items()}, 'CSV_VALUE_DIFFERS_FROM_RECEIPT')
    require(seen == {(f,e,d) for f,e in lookup for d in DEPTHS}, 'CSV_MISSING_MEASUREMENT')
    cp_rows = list(csv.DictReader(io.StringIO(cp_csv)))
    require(cp_rows == [{k:cell(row[k]) for k in CHECKPOINT_FIELDS} for row in checkpoint_rows(r)], 'CHECKPOINT_CSV_CHANGED')
    table_cells = 0
    for name,head,expected in tables(r):
        start,end = '<!-- table:'+name+' -->','<!-- endtable:'+name+' -->'
        require(report.count(start) == report.count(end) == 1, 'MARKDOWN_TABLE_COVERAGE')
        lines = report.split(start)[1].split(end)[0].strip().splitlines()
        parsed = [[cell.strip() for cell in line.strip().strip('|').split('|')] for line in lines]
        require(parsed[0] == head and parsed[1] == ['---']*len(head) and parsed[2:] == expected,
            'MARKDOWN_CELL_DIFFERS_FROM_RECEIPT')
        table_cells += sum(len(row) for row in expected)
    return {'family_epoch_measurements':len(lookup), 'measured_epochs_per_family':len(lookup)//2,
        'curve_csv_rows':len(rows), 'curve_csv_fields_checked':len(rows)*len(CURVE_FIELDS),
        'checkpoint_csv_rows':len(cp_rows), 'checkpoint_csv_fields_checked':len(cp_rows)*len(CHECKPOINT_FIELDS),
        'markdown_data_cells_checked':table_cells, 'all_rendered_tables_and_csv_fields_match_receipt':True}


def run(args):
    source = regular(args.receipt)
    require(source.resolve() == EXPECTED_RECEIPT.resolve() and args.receipt_sha256 == RECEIPT_SHA
        and file_hash(source) == RECEIPT_SHA, 'EXTERNAL_TRAINING_RECEIPT_PIN')
    helper_pin = file_hash(__file__)
    r = decode(source.read_bytes()); validate(r)
    output = Path(args.output).absolute()
    require(not output.exists() and output.resolve().is_relative_to(HERE.resolve())
        and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (output,*output.parents)),
        'NEW_OWNED_OUTPUT_REQUIRED')
    artifacts = {'learning_curve.csv':csv_text(CURVE_FIELDS,curve_rows(r)),
        'checkpoints.csv':csv_text(CHECKPOINT_FIELDS,checkpoint_rows(r)), 'learning_curve.md':markdown(r)}
    checks = verify_rendered(r, artifacts['learning_curve.csv'], artifacts['checkpoints.csv'], artifacts['learning_curve.md'])
    output.mkdir(parents=True,exist_ok=False)
    for name, content in artifacts.items():
        with (output/name).open('x',encoding='utf-8',newline='') as stream: stream.write(content)
    checked_again = verify_rendered(r, *( (output/name).read_text(encoding='utf-8')
        for name in ('learning_curve.csv','checkpoints.csv','learning_curve.md')))
    require(checks == checked_again and file_hash(source) == RECEIPT_SHA and file_hash(__file__) == helper_pin,
        'INPUT_OR_RENDER_CHANGED_DURING_BUILD')
    receipt = {'schema':'cas-meta2-prototype-training-curve-render/7', 'status':'PINNED_TRAINING_CURVES_RENDERED_AND_VERIFIED',
        'completed':True, 'input_receipt':str(source), 'input_receipt_sha256':RECEIPT_SHA,
        'source_sha':r['source_sha'], 'source_archive_sha256':r['source_archive_sha256'],
        'packet_sha256':r['packet_sha256'], 'job':r['job'], 'helper_sha256':helper_pin,
        'output_files_sha256':{name:file_hash(output/name) for name in artifacts}, 'checks':checks,
        'completed_training_epochs':r['completed_epochs'], 'checkpoint_map':r['training_gate']['checkpoints'],
        'measured_epochs':sorted({row['epoch'] for row in r['curves']}),
        'campaign_completed':False, 'native_task_scores_included':False, 'graph_recomputation':False,
        'model_or_tensor_loads':False, 'provider_calls':False, 'neural_execution':False,
        'learning_accepted':False, 'input_rechecked_after_render':True,
        'command':[sys.executable,'-B',*sys.argv], 'finished_utc':datetime.now(timezone.utc).isoformat(),
        'boundary':'Presentation of the pinned recorded-action recount only. No additional learning, native task, '
            'arithmetic, or capability claim. Historic best-so-far flags are distinct from final selected checkpoints.'}
    with (output/'render_receipt.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,sort_keys=True,indent=2,allow_nan=False); stream.write('\n')
    print(json.dumps({'status':receipt['status'], 'output':str(output), 'checks':checks,
        'output_files_sha256':receipt['output_files_sha256']},sort_keys=True,indent=2))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--receipt',required=True,type=Path)
    parser.add_argument('--receipt-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args(argv))


if __name__ == '__main__': main()
