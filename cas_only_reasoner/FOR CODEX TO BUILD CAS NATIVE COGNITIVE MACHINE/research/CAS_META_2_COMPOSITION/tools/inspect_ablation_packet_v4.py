"""Byte/receipt inspection of the fixed retrospective job, not semantic replay.

Reuses the unchanged archive safety, collection-index and extraction helpers.
Never loads a checkpoint, runs a model, contacts AWS or accepts a learned skill.
"""
import argparse
import ast
from datetime import datetime
from hashlib import sha256
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '3da01c577c47978e595caaff1ebbe9b30c3a87b6'
SOURCE_ARCHIVE = 'e680545e231d7f9f7fca0dd4f84e3fe4988b3d7c129c83a0bfe313ea809fdbc2'
JOB = 'cas-meta2-20260906025939-e933c868'
PILOT = 'research/CAS_META_2_COMPOSITION/'
BASE = 'cloud_job/campaign/'
MODES = ('v3', 'viability_v4')
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
FORBIDDEN = {'torch', 'tensorflow', 'jax', 'cupy', 'casformer', 'cas_cjt', 'boto3', 'botocore'}


def require(value, reason):
    if not value: raise ValueError(reason)


class NoNeuralOrProvider(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in FORBIDDEN, 'AUDIT_NEURAL_OR_PROVIDER_IMPORT_REFUSED')
        return None


def file_hash(path):
    digest = sha256()
    path = Path(path).absolute()
    require(not any(item.is_symlink() or getattr(item, 'is_junction', lambda: False)()
                    for item in (path, *path.parents)), 'AUDIT_LINK_REFUSED')
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''): digest.update(raw)
    return digest.hexdigest()


def load_helpers():
    source_zip = ROOT / 'records/aws_ablation_v4_source_001/source.zip'
    require(file_hash(source_zip) == SOURCE_ARCHIVE, 'FIXED_SOURCE_ARCHIVE_CHANGED')
    with zipfile.ZipFile(source_zip) as source:
        manifest = json.loads(source.read('launch_manifest.json'))
        require(manifest['source_sha'] == SOURCE, 'FIXED_SOURCE_COMMIT_CHANGED')
        relative = 'tools/inspect_cloud_packet.py'
        raw = source.read(PILOT + relative)
        require(sha256(raw).hexdigest() == manifest['files_sha256'][PILOT + relative], 'HELPER_MANIFEST_MISMATCH')
        path = ROOT / relative
        require(file_hash(path) == sha256(raw).hexdigest(), 'LOCAL_ARCHIVE_HELPER_CHANGED')
        repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
        committed = subprocess.check_output(['git', 'show', SOURCE + ':' + path.relative_to(repo).as_posix()], cwd=repo)
        require(raw == committed, 'ARCHIVE_HELPER_NOT_COMMITTED_BYTES')
        spec = importlib.util.spec_from_file_location('_ablation_archive_helper', path)
        helper = importlib.util.module_from_spec(spec)
        exec(compile(raw, str(path), 'exec'), helper.__dict__)
        input_raw = source.read(PILOT + 'records/decoder_ablation_inputs_v4_001/inputs.zip')
        require(sha256(input_raw).hexdigest() == 'bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93',
                'PRESERVED_CHECKPOINT_INPUT_CHANGED')
        with zipfile.ZipFile(io.BytesIO(input_raw)) as inputs:
            checkpoints = helper.json_bytes(inputs.read('checkpoints.json'))
        tree = ast.parse(source.read(PILOT + 'cas_meta2/campaign_v3.py'))
        tests = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'SOURCE_TESTS' for target in node.targets))
    return helper, manifest, checkpoints, tests


def xml_passes(packet, path, expected):
    import xml.etree.ElementTree as ET
    raw = packet.raw(path, 2 * 1024**2)
    require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'XML_DECLARATION_REFUSED')
    tree = ET.fromstring(raw)
    cases = list(tree.iter('testcase'))
    require(len(cases) == expected and len({(row.get('classname'), row.get('name')) for row in cases}) == expected
            and not any(list(tree.iter(tag)) for tag in ('failure', 'error', 'skipped')), 'GPU_XML_FULL_PASS_REQUIRED')
    return {'passed': expected, 'case_names': [row.get('name') for row in cases]}


def complete_checks(packet, helper, manifest, checkpoints, tests):
    campaign = packet.json(BASE + 'campaign_receipt.json')
    require(campaign.get('schema') == 'cas-meta2-retrospective-campaign/0.1'
            and campaign.get('completed') is True and campaign.get('evaluation_completed') is True
            and campaign.get('training_performed') is False and campaign.get('release_accepted') is False
            and campaign.get('fresh_held_out_claim_permitted') is False
            and campaign.get('job') == JOB and campaign.get('experiment') == manifest['experiment'],
            'RETROSPECTIVE_CAMPAIGN_BOUNDARY_MISMATCH')
    mapping = manifest['files_sha256']
    expected = {name.removeprefix(PILOT): digest for name, digest in mapping.items()
                if name.startswith(PILOT + 'cas_meta2/') and name.endswith('.py')
                and '/' not in name.removeprefix(PILOT + 'cas_meta2/')}
    for name in ['cas_meta2/exclusions_v3.json', 'cas_meta2/development_exclusions_v3.json',
                 'EXPERIMENT_V3.json', 'pyproject.toml', 'requirements-gpu.txt',
                 *('tests/' + name for name in tests)]: expected[name] = mapping[PILOT + name]
    require(campaign['source_sha256'] == expected, 'CAMPAIGN_SOURCE_MAPPING_MISMATCH')
    require(campaign['baseline_before']['source'] == {'baseline_sha': manifest['baseline_sha'],
            'files_verified': 316}, 'PROTECTED_BASELINE_COUNT_MISMATCH')
    require({row['wheel_sha256'] for row in campaign['baseline_before']['installed_wheels'].values()}
            == {mapping[path] for path in manifest['wheel_paths']}, 'FROZEN_WHEEL_IDENTITY_MISMATCH')
    for name in ('train.json', 'validation.json', 'test_public.json', 'test_private.json', 'dataset_manifest.json'):
        packet.same_hash(BASE + 'dataset/' + name,
            mapping[PILOT + 'records/decoder_dataset_reconstruction_v4_001/dataset/' + name])
    payload = packet.json(BASE + 'payload_sha256.json')
    expected_payload = {name.removeprefix(BASE): row['sha256'] for name, row in packet.inventory.items()
                        if name.startswith(BASE) and name != BASE + 'payload_sha256.json'}
    require(payload == expected_payload, 'COMPLETE_CAMPAIGN_PAYLOAD_INDEX_MISMATCH')
    prediction = packet.json(BASE + 'prediction/prediction_receipt.json')
    require(prediction['completed'] is True and prediction['job'] == JOB
            and prediction['training_performed'] is False and prediction['fresh_held_out_claim_permitted'] is False
            and prediction['native_evaluation_completed'] is False, 'PREDICTION_BOUNDARY_MISMATCH')
    process = packet.json(BASE + 'processes/prediction/process_receipt.json')
    require(process['completed'] is True and process['returncode'] == 0 and process['timed_out'] is False,
            'SUCCESSFUL_PREDICTION_EXIT_REQUIRED')
    gate = packet.json(BASE + 'prediction_gate.json')
    packet.same_hash(BASE + 'prediction/prediction_receipt.json', gate['prediction_receipt_sha256'])
    packet.same_hash(BASE + 'processes/prediction/process_receipt.json', gate['process_receipt_sha256'])
    require(gate['prediction_pid'] == process['pid'] and gate['returncode'] == 0, 'PREDICTION_PID_GATE_MISMATCH')
    for arm in ARMS[:-1]:
        family = 'cas' if arm.startswith('cas') else 'generic'
        state = 'initial' if arm.endswith('untrained') else 'selected'
        name = 'candidate_' + family + '_' + ('initial' if state == 'initial' else 'best') + '.pt'
        original = checkpoints[family][state]
        relocation = prediction['relocations'][arm]
        require(relocation['original'] == original and {k: v for k, v in relocation['relocated'].items() if k != 'path'}
                == {k: v for k, v in original.items() if k != 'path'}, 'CHECKPOINT_METADATA_CHANGED')
        packet.same_hash(BASE + 'prediction/checkpoint_inputs/' + name, original['sha256'])
        require(prediction['timings'][arm]['original_decoder_parity'] is True
                and prediction['timings'][arm]['state_unchanged'] is True, 'CHECKPOINT_PARITY_RECEIPT_MISSING')
    publics = packet.json(BASE + 'dataset/test_public.json')
    totals = {}
    for mode in MODES:
        folder = BASE + 'prediction/' + mode + '/'
        seal = packet.json(folder + 'predictions_seal.json')
        require(seal == prediction['seals'][mode] and seal['arms'] == list(ARMS)
                and seal['test_examples'] == 72 and seal['prediction_count'] == 360
                and seal['test_private_labels_loaded'] is False, 'MODE_SEAL_INCOMPLETE')
        packet.same_hash(folder + 'predictions.jsonl', seal['sha256'])
        packet.same_hash(folder + 'predictions.jsonl', gate['seals'][mode]['predictions'])
        packet.same_hash(folder + 'predictions_seal.json', gate['seals'][mode]['seal'])
        opening = packet.json(folder + 'test_gold_opening_receipt.json')
        require(datetime.fromisoformat(opening['opened_utc']) > datetime.fromisoformat(process['finished_utc'])
                > datetime.fromisoformat(seal['sealed_utc']), 'GOLD_OPENED_BEFORE_SUCCESSFUL_PREDICTION_EXIT')
        rows = [helper.json_bytes(line) for line in packet.raw(folder + 'predictions.jsonl').splitlines()]
        require(len(rows) == len(publics) == 72, 'MODE_TASK_DENOMINATOR_MISMATCH')
        counts = {arm: {field: 0 for field in helper.VERDICT_FIELDS} for arm in ARMS}
        for index, (row, public) in enumerate(zip(rows, publics)):
            require(row['case_index'] == index and row['public_sha256'] == sha256(helper.canonical(public)).hexdigest()
                    and set(row['actions']) == set(ARMS), 'SEALED_PUBLIC_MAPPING_MISMATCH')
            for arm in ARMS:
                case = packet.json(folder + f'evaluation/case_{index:04d}/' + arm + '/case_receipt.json')
                verdict = packet.json(folder + f'evaluation/case_{index:04d}/' + arm + '/verification.json')
                require(case['case_index'] == index and case['arm'] == arm and case['action'] == row['actions'][arm]
                        and case['verification'] == verdict, 'CASE_SEAL_OR_VERDICT_MISMATCH')
                helper._verdict(verdict)
                for field in helper.VERDICT_FIELDS: counts[arm][field] += int(verdict[field])
        results = packet.json(folder + 'evaluation_results.json')['results']
        for arm in ARMS:
            require(results[arm]['total'] == 72 and results[arm]['all_cases_in_denominator'] is True
                    and all(results[arm][field] == count for field, count in counts[arm].items()), 'SAVED_COUNTS_MISMATCH')
        totals[mode] = counts
    return {'recorded_counts': totals, 'environment': helper._environment(packet),
        'native_gpu_contracts': helper._gpu_gate(packet, 'contract'),
        'policy_gpu_contracts': xml_passes(packet, 'cloud_job/gpu_policy_tests.xml', 27),
        'decoder_gpu_contracts': xml_passes(packet, BASE + 'gpu_tests.xml', 2),
        'boundary': 'Byte and receipt consistency only; stored native semantic replay remains required.'}


def inspect_packet(path, *, expected_sha256, output, extract=None):
    require(type(expected_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', expected_sha256), 'EXTERNAL_PACKET_SHA_REQUIRED')
    require(not any(name.split('.')[0] in FORBIDDEN for name in sys.modules), 'NEURAL_OR_PROVIDER_PRELOADED')
    guard = NoNeuralOrProvider()
    sys.meta_path.insert(0, guard)
    try:
        helper, manifest, checkpoints, tests = load_helpers()
        path = Path(path).absolute()
        require(0 < path.stat().st_size <= helper.MAX_COMPRESSED and file_hash(path) == expected_sha256,
                'PACKET_SIZE_OR_SHA_MISMATCH')
        output = helper._new_output(output)
        target = helper._new_output(extract, extracted=True) if extract else None
        require(target is None or not (output.is_relative_to(target) or target.is_relative_to(output)), 'OUTPUT_EXTRACTION_OVERLAP')
        with zipfile.ZipFile(path) as archive:
            infos, expanded = helper._safe_infos(archive)
            inventory = []
            for name, info in sorted(infos.items()):
                if info.is_dir(): continue
                digest, count = sha256(), 0
                with archive.open(info) as stream:
                    for raw in iter(lambda: stream.read(1024 * 1024), b''):
                        count += len(raw)
                        require(count <= info.file_size, 'MEMBER_EXCEEDS_HEADER')
                        digest.update(raw)
                require(count == info.file_size, 'MEMBER_SIZE_MISMATCH')
                inventory.append({'path': name, 'bytes': count, 'sha256': digest.hexdigest()})
            packet = helper.Packet(archive, infos, inventory)
            collection, full_index = helper._collection(packet, JOB, SOURCE, SOURCE_ARCHIVE)
            require(collection.get('experiment') == manifest['experiment'] and collection['smoke_only'] is False,
                    'RETROSPECTIVE_COLLECTION_PROFILE_MISMATCH')
            details, issues = {}, []
            if collection['returncode'] == 0:
                try: details = complete_checks(packet, helper, manifest, checkpoints, tests)
                except (ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                    issues.append(type(error).__name__ + ':' + str(error))
            extraction = helper._extract(packet, target) if target else None
        require(file_hash(path) == expected_sha256, 'PACKET_CHANGED_DURING_INSPECTION')
        status = ('RETROSPECTIVE_RECEIPT_CHECKS_PASSED' if collection['returncode'] == 0 and not issues
                  else 'RETROSPECTIVE_EVIDENCE_MISMATCH' if issues else 'RETROSPECTIVE_FAILED_OR_PARTIAL_RUN')
        output.mkdir(parents=True, exist_ok=False)
        index_raw = json.dumps({'schema': 'cas-meta2-full-packet-index/1', 'packet_sha256': expected_sha256,
                               'entries': inventory}, sort_keys=True, indent=2).encode() + b'\n'
        (output / 'full_member_index.json').write_bytes(index_raw)
        record = {'schema': 'cas-meta2-retrospective-inspection/0.1', 'status': status,
            'packet_sha256': expected_sha256, 'source_sha': SOURCE, 'job': JOB, 'source_manifest': manifest,
            'archive_safety_and_all_included_bytes_checked': True, 'original_full_index_verified': full_index,
            'member_files': len(inventory), 'expanded_bytes': expanded, 'collection': collection,
            'full_member_index_sha256': sha256(index_raw).hexdigest(), 'extraction': extraction,
            'issues': issues, 'details': details, 'stored_semantic_audit_completed': False,
            'fresh_held_out_claim_permitted': False, 'learning_accepted': False,
            'inspector_sha256': file_hash(Path(__file__))}
        (output / 'inspection_receipt.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        return record
    finally:
        sys.meta_path.remove(guard)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--extract')
    args = parser.parse_args()
    result = inspect_packet(args.packet, expected_sha256=args.sha256, output=args.output, extract=args.extract)
    print(json.dumps({key: result[key] for key in ('status', 'member_files', 'issues', 'stored_semantic_audit_completed')}))
