"""Pure complete candidate bindings, schedule report and optional committed package."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aws import complementary_teaching_launch as launch
from cas_meta2.complementary_teaching import course, runner, data
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.graph_teaching import face_worker, face_schedule, face_evaluation


def prepare(output, *, package_output=None, source_sha=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = data.validate_manifest(json.loads((ROOT / runner.DATA_PATH).read_bytes()))
    source_conditions = [(x['condition'], x['organization'], x['cue']) for x in face_schedule.comparison_conditions()]
    publics = face_worker.public_corpus(None, face_evaluation.panel(), source_conditions)
    tokenizer = LosslessPublicTokenizer.fit_train(publics['publics'], max_length=1024)
    previous_path = output / 'TASK_BINDINGS.json'
    previous = json.loads(previous_path.read_bytes()) if previous_path.exists() else {}
    prior_courses = {(row['seed'],row['condition']):row for row in previous.get('course_summaries',[])}
    summaries = []
    initial_example = None
    for seed in course.SEEDS:
        for condition in course.CONDITIONS:
            schedule = course.compile_complementary_course(seed, condition)
            task_hashes = [course.public_identity(task) for batch in schedule['batches'] for task in batch['tasks']]
            prior = prior_courses.get((seed,condition),{})
            prior_hashes = [value for batch in prior.get('batch_schedule',[]) for value in batch['public_input_sha256']]
            reused = (previous.get('tokenizer_sha256') == tokenizer.digest and prior_hashes == task_hashes)
            lengths = [prior['maximum_input_tokens']] if reused else [len(tokenizer.encode_public(task['public'])['ids'])
                       for batch in schedule['batches'] for task in batch['tasks']]
            summaries.append({'seed':seed,'condition':condition,'schedule_sha256':schedule['schedule_sha256'],
                'counts':schedule['counts'],'maximum_input_tokens':max(lengths),
                'input_check_reused_only_after_exact_public_hash_equality':reused,'batch_schedule':[
                    {key:batch[key] for key in ('cursor','round','phase','depth')} | {
                        'sample_ids':[task['record_id'] for task in batch['tasks']],
                        'public_input_sha256':[course.public_identity(task) for task in batch['tasks']]}
                    for batch in schedule['batches']]})
            if initial_example is None:
                initial_example = schedule['pairs_by_round'][0][0]
    audits = {key:{'count':len(rows),'maximum_input_tokens':max(len(tokenizer.encode_public(task['public'])['ids']) for task in rows)}
              for key,rows in manifest['panels'].items()}
    archive_path = ROOT / 'records/recurrent_cjt_001/receipt_cas-meta2-rdcjt-20260912152001-abf38e1e/source.zip'
    inherited = {}
    with ZipFile(archive_path) as archive:
        for relative in ('cas_meta2/features_v2.py','cas_meta2/graph_teaching/real_framework.py',
                         'cas_meta2/graph_teaching/face_worker.py','cas_meta2/graph_teaching/face_tasks.py',
                         'cas_meta2/graph_teaching/face_corpus.py','cas_meta2/graph_teaching/face_evaluation.py'):
            historical = archive.read('research/CAS_META_2_COMPOSITION/' + relative)
            current = (ROOT / relative).read_bytes()
            # These exact inherited files define tokenizer/projection and source
            # corpus reconstruction. Any difference blocks this initializer.
            equal = ast.dump(ast.parse(historical)) == ast.dump(ast.parse(current))
            course.require(equal,'COMPLEMENTARY_INITIAL_ENCODER_SOURCE_CHANGED:'+relative)
            inherited[relative]={'archive_sha256':launch.infrastructure.digest(historical),
                                 'current_sha256':runner.file_sha(ROOT/relative),'ast_equal':equal}
    files = list(launch.MODULES) + ['aws/complementary_teaching_launch.py',
            'tools/compile_complementary_data.py','tools/prepare_complementary_teaching.py',
            'tests/test_complementary_teaching.py',runner.DATA_PATH,
            'records/complementary_teaching_001/preparation_20260916/historical_exclusions.json']
    binding = {'schema':'cas.complementary-bindings/0.1','candidate':launch.IMPLEMENTATION_ID,
        'status':'COMPLEMENTARY_SOURCE_READY_PACKAGE_PENDING_NEURAL_UNTESTED','actual_neural_presentations':0,
        'actual_optimizer_updates':0,'actual_provider_calls':0,
        'data_sha256':manifest['data_sha256'],'tokenizer_sha256':tokenizer.digest,
        'unchanged_original_encoder_fitting_corpus_sha256':course.digest(publics),
        'inherited_encoder_source':inherited,
        'initial_checkpoint':{'path':runner.INITIAL_PATH,'sha256':runner.file_sha(ROOT/runner.INITIAL_PATH),
            'selection':'Earliest retained successful recurrent course seed20260912 by chronology; no score selection',
            'optimizer':'New identical AdamW initialization per condition; accumulated continuously within each course'},
        'sources':{relative:runner.file_sha(ROOT/relative) for relative in files},
        'source_sha':source_sha,'source_identity_scope':'File SHA-256 binds current candidate bytes; source_sha when present is exact committed package basis',
        'course_summaries':summaries,'audit_input_checks':audits,
        'claim_boundaries':['One inherited weight initialization, three paired course-order seeds',
            'New 8-10-node topologies compared with 3-4-node CFC; structural/size transfer amendment',
            'Six-face earlier-skill role recognition only, not all-six application retention',
            '600 batched-equivalent update-depth units/course; actual sequential training corecalls4320',
            'Native CAS flow not instrumented by this raw transform; no physical current or causal attribution']}
    runner.write_json(output/'example_pair.json',initial_example)
    runner.write_json(output/'TASK_BINDINGS.json',binding)
    package = None
    if package_output:
        course.require(source_sha is not None,'COMPLEMENTARY_PACKAGE_EXACT_SOURCE_SHA_REQUIRED')
        package = launch.build_complementary_package(package_output,source_sha=source_sha)
        binding['status']='COMPLEMENTARY_TEACHING_READY_NEURAL_UNTESTED'
        binding['package']={key:package[key] for key in ('source_sha','archive_sha256','manifest_sha256','archive_bytes','archive')}
        runner.write_json(output/'TASK_BINDINGS.json',binding)
    request=launch.costed_request(package=binding.get('package'))
    if package:
        request['job']='cas-meta2-complementary-20260916000000-'+package['archive_sha256'][:8]
        request['worker_config']['job']=request['job']
    runner.write_json(output/'UNSIGNED_EXECUTION_REQUEST.json',request)
    print(json.dumps({'status':binding['status'],'courses':len(summaries),'maximum_training_tokens':max(x['maximum_input_tokens'] for x in summaries),
                      'audit_input_checks':audits,'package':binding.get('package'),'neural_execution':False}))
    return binding


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'records/complementary_teaching_001/preparation_20260916')
    parser.add_argument('--package-output',type=Path)
    parser.add_argument('--source-sha')
    args=parser.parse_args()
    prepare(args.output,package_output=args.package_output,source_sha=args.source_sha)
