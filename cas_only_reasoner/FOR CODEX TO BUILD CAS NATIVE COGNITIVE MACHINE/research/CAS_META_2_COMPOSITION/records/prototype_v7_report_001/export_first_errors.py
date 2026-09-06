"""Lossless CSV export of the externally pinned partial-audit rows; no new audit."""
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RECEIPT=ROOT/'records/prototype_v7_partial_native_001/run_001/partial_native_receipt.json'
PIN='bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f'
ARMS=('cas_untrained','cas_trained','generic_untrained','generic_trained','rule')
FIELDS=('case_index','task_id','arm','depth','condition','execution_status','outcome_available',
    'task_correct','action_sha256','comparison_kind','first_observed_boundary','first_difference_categories_json',
    'first_difference_json','committed_difference_json','evidence_member_directory','evidence_path',
    'evidence_directory_recorded')

def require(ok, why):
    if not ok:raise ValueError(why)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def sha(raw):return sha256(raw).hexdigest()

def build(receipt):
    require(receipt['status']=='PARTIAL_NATIVE_EVIDENCE_CHECKED' and receipt['audit_completed'] is True
        and receipt['campaign_completed'] is False and receipt['native_evaluation_completed'] is False,
        'PINNED_PARTIAL_AUDIT_REQUIRED')
    rows=receipt['diagnostics']['rows'];cases=receipt['outcomes']['cases']
    require(type(rows) is list and len(rows)==360 and len(cases)==72,'EXACT_360_ROWS_REQUIRED')
    require([case['case_index'] for case in cases]==list(range(72)),'EXACT_72_CASES_REQUIRED')
    expected={(i,arm) for i in range(72) for arm in ARMS};seen=set();result=[]
    extraction=ROOT/'records/prototype_v7_partial_review_001/extracted_001'
    for row in rows:
        index,arm=row['case_index'],row['arm']
        require(type(index) is int and (index,arm) in expected and (index,arm) not in seen,'ROW_INDEX_OR_ARM')
        seen.add((index,arm));case=cases[index];original=case['arms'][arm]
        require(row['task_id']==case['task_id'] and row['action']==original['action']
            and row['execution_status']==original['execution_status']
            and row['verification']==original['verification'],'ROW_DIFFERS_FROM_AUDITED_OUTCOME')
        member=row['evidence_path']
        require(member==f'cloud_job/campaign/native/evaluation/case_{index:04d}/'+arm,'EVIDENCE_PATH_ATTRIBUTION')
        difference=row.get('first_observed_difference');committed=row.get('first_committed_run_disagreement')
        categories=difference['categories'] if difference else []
        record={'case_index':str(index),'task_id':row['task_id'],'arm':arm,'depth':str(row['depth']),
            'condition':row['condition'],'execution_status':row['execution_status'],
            'outcome_available':canonical(row['outcome_available']),
            'task_correct':canonical(row['verification']['task_correct']),
            'action_sha256':sha(canonical(row['action']).encode()),'comparison_kind':row['comparison_reference'],
            'first_observed_boundary':row.get('first_observed_boundary') or '',
            'first_difference_categories_json':canonical(categories),'first_difference_json':canonical(difference),
            'committed_difference_json':canonical(committed),'evidence_member_directory':member,
            'evidence_path':str(extraction.joinpath(*member.split('/'))),
            'evidence_directory_recorded':canonical(row['execution_status']!='NOT_STARTED_BEFORE_DEADLINE')}
        require(set(record)==set(FIELDS) and all(type(v) is str for v in record.values()),'CSV_CELL_TYPE')
        # A missing outcome must remain a literal JSON null in CSV, not False.
        if (index,arm) in {(45,'generic_trained'),(45,'rule')}:
            require(record['task_correct']=='null' and record['outcome_available']=='false','UNKNOWN_OUTCOME_LOST')
        result.append(record)
    require(seen==expected,'CSV_COVERAGE')
    return result

def main():
    own=sha(Path(__file__).read_bytes());raw=RECEIPT.read_bytes()
    require(sha(raw)==PIN,'EXTERNAL_AUDIT_RECEIPT_CHANGED')
    receipt=json.loads(raw);rows=build(receipt)
    output=HERE/'first_errors.csv';summary_path=HERE/'first_errors_summary.json';export_path=HERE/'first_errors_export_receipt.json'
    require(not any(path.exists() for path in (output,summary_path,export_path)),'NEW_EXPORT_FILES_REQUIRED')
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=FIELDS,lineterminator='\n')
    writer.writeheader();writer.writerows(rows);csv_raw=buffer.getvalue().encode('utf-8')
    with output.open('xb') as stream:stream.write(csv_raw)
    with output.open('r',encoding='utf-8',newline='') as stream:
        reader=csv.DictReader(stream);require(tuple(reader.fieldnames)==FIELDS,'CSV_HEADER_ROUNDTRIP')
        actual=list(reader)
    require(actual==rows and len(actual)==360,'CSV_CELL_ROUNDTRIP')
    for actual_row,source_row in zip(actual,receipt['diagnostics']['rows'],strict=True):
        require(json.loads(actual_row['first_difference_json'])==source_row.get('first_observed_difference')
            and json.loads(actual_row['committed_difference_json'])==source_row.get('first_committed_run_disagreement')
            and json.loads(actual_row['task_correct']) is source_row['verification']['task_correct'],
            'CSV_JSON_CELL_ROUNDTRIP')
    groups={group:{arm:{k:value[k] for k in ('scheduled','attempted','outcomes_recorded','correct','incorrect','unknown','statuses')}
        for arm,value in values.items()} for group,values in receipt['diagnostics']['summaries'].items()}
    summary={'schema':'cas-meta2-partial-first-errors-summary/7','source_receipt':str(RECEIPT),
        'source_receipt_sha256':PIN,'csv_path':str(output),'csv_sha256':sha(csv_raw),
        'job':receipt['job'],'source_sha':receipt['source_sha'],'packet_sha256':receipt['packet_sha256'],
        'scheduled_rows':360,'scheduled_cases':72,'outcomes_available':358,'unknown_outcomes':2,
        'groups':groups,'all_scheduled_rows_preserved':True,
        'boundary':'Export only, no new scoring or audit. 72 scheduled slots per arm; rule71 attempts and1 not started; '
            'generic-trained72 attempts and1 unfinished. Null remains unknown. Literal first differences are not proven '
            'earliest causal neural decisions. Case45 reference comparisons do not invent a rule execution.'}
    with summary_path.open('xb') as stream:stream.write(canonical(summary).encode()+b'\n')
    require(json.loads(summary_path.read_bytes())==summary,'SUMMARY_ROUNDTRIP')
    require(sha(RECEIPT.read_bytes())==PIN and sha(Path(__file__).read_bytes())==own,'INPUT_OR_EXPORTER_CHANGED')
    export={'schema':'cas-meta2-partial-first-errors-export/7','status':'PINNED_360_ROW_EXPORT_VERIFIED',
        'completed':True,'source_receipt_sha256':PIN,'exporter_sha256':own,
        'csv':{'path':str(output),'sha256':sha(output.read_bytes()),'bytes':output.stat().st_size,'rows':360,'columns':len(FIELDS)},
        'summary':{'path':str(summary_path),'sha256':sha(summary_path.read_bytes()),'bytes':summary_path.stat().st_size},
        'all_cells_roundtrip_verified':True,'full_difference_json_preserved':True,'null_outcomes_preserved':True,
        'new_scoring_or_audit':False,'provider_or_neural_work':False,'command':[sys.executable,*sys.argv],
        'utc':datetime.now(timezone.utc).isoformat()}
    with export_path.open('xb') as stream:stream.write(canonical(export).encode()+b'\n')
    print(canonical({'status':export['status'],'receipt':str(export_path),'sha256':sha(export_path.read_bytes()),
        'csv_sha256':export['csv']['sha256'],'summary_sha256':export['summary']['sha256']}))

if __name__=='__main__':main()
