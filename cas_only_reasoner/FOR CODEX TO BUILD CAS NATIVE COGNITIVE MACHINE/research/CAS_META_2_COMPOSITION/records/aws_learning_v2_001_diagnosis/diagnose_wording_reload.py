"""Read-only diagnosis of saved JSON's procedure dictionary presentation order.

This detached-data helper does not change meaning, stored bytes, or frozen code.
It is not a release acceptance waiver. Run only on the completed exposed packet.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnose_saved as guard
from cas_meta2.curriculum import parse_problem
from cas_meta2.curriculum_v2 import render_problem


def restore_public_definition_order(task):
    """Recover presentation order only after independent exact meaning equality."""
    before = guard.canonical(task)
    parsed = parse_problem(task['public'])
    if parsed != task['target']:
        raise ValueError('PUBLIC_MEANING_DOES_NOT_MATCH_STORED_TARGET')
    original = task['target']['program']['procedures']
    names = list(parsed['program']['procedures'])
    restored = deepcopy(task)
    restored['target']['program']['procedures'] = {
        name: restored['target']['program']['procedures'][name] for name in names}
    after = guard.canonical(restored)
    if before != after or restored != task:
        raise ValueError('ORDER_RESTORATION_CHANGED_CANONICAL_DATA')
    return restored, {'changed_order': list(original) != names,
                      'stored_definition_order': list(original),
                      'public_definition_order': names,
                      'canonical_sha256_before': sha256(before).hexdigest(),
                      'canonical_sha256_after': sha256(after).hexdigest()}


def render_matches(task):
    tag = next(row['tag'] for row in task['public']['observations']
               if row['slot'] == task['target']['binding'])
    return render_problem(task['target']['program'], tag,
                          task['provenance']['wording_combination']) == task['public']['problem']


def main():
    root = guard.ROOT
    packet = root / 'records/aws_learning_v2_001/cloud_artifacts.zip'
    output = Path(__file__).with_name('wording_reload_diagnostic.json')
    if output.exists():
        raise SystemExit('REFUSING_EXISTING_OUTPUT')
    report = {'schema': 'cas-meta2-v2-wording-reload-diagnostic/0.1',
              'status': 'DIAGNOSED_PRESENTATION_ORDER_ONLY_NOT_RELEASE_ACCEPTANCE',
              'source_sha': '410bce98307a5644db51928459b73391c7066b72',
              'packet_sha256': sha256(packet.read_bytes()).hexdigest(),
              'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
              'helper_import_sha256': sha256(Path(guard.__file__).read_bytes()).hexdigest(),
              'frozen_checker_code_sha256': {
                  name: sha256((root / 'cas_meta2' / name).read_bytes()).hexdigest()
                  for name in ('curriculum.py', 'curriculum_v2.py', 'codec.py')},
              'original_files_edited': False, 'neural_or_provider_calls': False,
              'gate_boundary': 'GPU cleanup gate and successful stored audit remain open.',
              'partitions': {}, 'rows': [], 'first_mismatch': None}
    with zipfile.ZipFile(packet) as archive:
        for split, filename in [('train', 'train.json'), ('validation', 'validation.json'),
                                ('test', 'test_private.json')]:
            path = 'cloud_job/campaign/dataset/' + filename
            raw = archive.read(path)
            tasks = json.loads(raw)
            summary = {'count': len(tasks), 'member': path, 'member_sha256': sha256(raw).hexdigest(),
                       'independent_meaning_equal': 0, 'stored_order_render_equal': 0,
                       'restored_order_render_equal': 0, 'changed_order': 0,
                       'canonical_bytes_preserved': 0}
            for index, task in enumerate(tasks):
                restored, row = restore_public_definition_order(task)
                row.update({'split': split, 'index': index, 'task_id': task['task_id'],
                            'stored_order_render_equal': render_matches(task),
                            'restored_order_render_equal': render_matches(restored)})
                summary['independent_meaning_equal'] += 1
                summary['stored_order_render_equal'] += row['stored_order_render_equal']
                summary['restored_order_render_equal'] += row['restored_order_render_equal']
                summary['changed_order'] += row['changed_order']
                summary['canonical_bytes_preserved'] += row['canonical_sha256_before'] == row['canonical_sha256_after']
                report['rows'].append(row)
                if not row['stored_order_render_equal'] and report['first_mismatch'] is None:
                    report['first_mismatch'] = row
            report['partitions'][split] = summary
    report['rows_sha256'] = sha256(guard.canonical(report['rows'])).hexdigest()
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(output), 'sha256': sha256(output.read_bytes()).hexdigest(),
                      'partitions': report['partitions'], 'first_mismatch': report['first_mismatch']}, indent=2))


if __name__ == '__main__':
    main()
