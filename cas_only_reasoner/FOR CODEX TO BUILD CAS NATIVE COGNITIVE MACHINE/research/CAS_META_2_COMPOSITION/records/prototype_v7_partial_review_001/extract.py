"""Byte-only extraction of the failed fixed v7 run. No success or learning gate."""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JOB = 'cas-meta2-20260906094002-39762c47'
SOURCE = '42f9164754312f12850d9b8789c062fa7fb8069f'
SOURCE_ARCHIVE = 'f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
PACKET = 'f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799'
PACKET_BYTES = 131895861
COMMON = ROOT/'records/prototype_v7_stored_review_001/common.py'
COMMON_SHA = 'bb13cd57b88beafefd1546f504ee38b8595855430dfc55e5d66ecba8bf4684c7'
COLLECTION = 'artifact_collection_receipt.json'
BASE = 'cloud_job/campaign/'
INDEX = BASE+'payload_sha256.json'
FORMAT = 'SHA256 of canonical JSON entry plus LF for every sorted original path'
RESERVED = re.compile(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z', re.I)


def require(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    require(len(raw) <= 64*1024**2, 'JSON_SIZE_BOUND')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(value)
    return value


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'PATH_LINK_REFUSED')
    return path


def file_hash(path):
    path = no_links(path)
    require(path.is_file(), 'REGULAR_FILE_REQUIRED')
    h = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            h.update(raw)
    return h.hexdigest()


def pin(path, expected):
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected)
            and file_hash(path) == expected, 'EXTERNAL_HASH_MISMATCH')


def safe_name(name):
    require(type(name) is str and name and not name.startswith('/')
            and not any(ord(x) < 32 or x in '\\:<>"|?*' for x in name), 'UNSAFE_MEMBER_PATH')
    parts = name.split('/')
    require(all(p not in ('', '.', '..') and not p.endswith((' ', '.'))
                and not RESERVED.fullmatch(p) for p in parts), 'UNSAFE_MEMBER_COMPONENT')
    return name


def headers(archive):
    infos = archive.infolist()
    require(0 < len(infos) <= 65536 and sum(i.file_size for i in infos) <= 2*1024**3,
            'ARCHIVE_SIZE_OR_MEMBER_BOUND')
    names, spellings = set(), {}
    for info in infos:
        name = safe_name(info.filename)
        require(not info.is_dir() and not info.flag_bits & 1
                and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                and name not in names, 'MEMBER_TYPE_ENCRYPTION_OR_DUPLICATE')
        names.add(name)
        for i in range(1, len(name.split('/'))+1):
            part = '/'.join(name.split('/')[:i])
            require(part.casefold() not in spellings or spellings[part.casefold()] == part,
                    'CASE_ALIAS')
            spellings[part.casefold()] = part
    require(not any('/'.join(name.split('/')[:i]) in names
                    for name in names for i in range(1, len(name.split('/')))), 'FILE_DIRECTORY_ALIAS')
    return infos


def scan(archive):
    inventory = {}
    for info in headers(archive):
        h, count = sha256(), 0
        with archive.open(info) as stream:
            for raw in iter(lambda: stream.read(1024**2), b''):
                count += len(raw)
                require(count <= info.file_size, 'MEMBER_SIZE_MISMATCH')
                h.update(raw)
        require(count == info.file_size, 'MEMBER_SIZE_MISMATCH')
        inventory[info.filename] = {'path': info.filename, 'bytes': count, 'sha256': h.hexdigest()}
    return inventory


def collection_check(value, inventory, *, job, source, archive_hash, experiment):
    require(value.get('job') == job and value.get('source_sha') == source
            and value.get('archive_sha256') == archive_hash and value.get('experiment') == experiment,
            'COLLECTION_IDENTITY_MISMATCH')
    require(type(value.get('returncode')) is int and value['returncode'] == 1
            and value.get('smoke_only') is False, 'FAILED_FULL_RUN_REQUIRED')
    require(value.get('partial_evidence') is False and value.get('omitted_full_file_count') == 0,
            'OMITTED_FILES_REFUSED_BY_THIS_EXTRACTOR')
    # The Linux collector sorts pathlib.Path objects (path parts), not strings.
    # Preserve that exact order, including a/file preceding a.txt.
    originals = sorted((row for name, row in inventory.items() if name != COLLECTION),
        key=lambda row: PurePosixPath(row['path']))
    require(COLLECTION in inventory and not any(r['path'].startswith('failure_log_tails/') for r in originals),
            'FULL_ORIGINAL_COLLECTION_REQUIRED')
    require(value.get('original_file_count') == value.get('included_full_file_count') == len(originals)
            and value.get('original_bytes') == sum(row['bytes'] for row in originals), 'COLLECTION_COUNTS')
    expected = sha256(b''.join(canonical(row)+b'\n' for row in originals)).hexdigest()
    require(value.get('index_hash_format') == FORMAT and value.get('original_file_index_sha256') == expected,
            'COMPLETE_ORIGINAL_INDEX_HASH_MISMATCH')
    require(value.get('index_entries') == originals[:1000]
            and value.get('index_entries_omitted') == max(0, len(originals)-1000), 'INDEX_PREVIEW_MISMATCH')
    return {'all_original_index_entries_reconstructed': len(originals),
        'original_file_index_sha256': expected, 'all_original_file_bytes_verified': True,
        'index_preview_omissions_are_not_file_omissions': True}


def payload_check(mapping, inventory):
    require(type(mapping) is dict, 'CAMPAIGN_INDEX_MAPPING_REQUIRED')
    expected = {name[len(BASE):]: row['sha256'] for name, row in inventory.items()
                if name.startswith(BASE) and name != INDEX}
    require(mapping == expected, 'CAMPAIGN_PAYLOAD_INDEX_COVERAGE_OR_HASH_MISMATCH')
    return {'files_verified': len(expected), 'all_campaign_files_except_index_covered': True,
            'payload_sha256_json_sha256': inventory[INDEX]['sha256']}


def extract(archive, inventory, destination):
    destination = no_links(destination)
    require(not destination.exists() and destination.resolve().is_relative_to(HERE.resolve()),
            'NEW_OWNED_EXTRACTION_REQUIRED')
    destination.mkdir(parents=True, exist_ok=False)
    for name, row in inventory.items():
        target = no_links(destination.joinpath(*safe_name(name).split('/')))
        require(target.resolve().is_relative_to(destination.resolve()), 'EXTRACTION_ESCAPE')
        target.parent.mkdir(parents=True, exist_ok=True)
        h, count = sha256(), 0
        with archive.open(name) as source, target.open('xb') as output:
            for raw in iter(lambda: source.read(1024**2), b''):
                count += len(raw)
                require(count <= row['bytes'], 'EXTRACTION_SIZE_CHANGED')
                h.update(raw)
                output.write(raw)
        require(count == row['bytes'] and h.hexdigest() == row['sha256'], 'EXTRACTION_BYTES_CHANGED')
    verify_extraction(destination, inventory)


def verify_extraction(destination, inventory):
    actual = set()
    for directory, dirs, files in os.walk(no_links(destination), followlinks=False):
        for name in dirs:
            no_links(Path(directory)/name)
        for name in files:
            path = no_links(Path(directory)/name)
            member = path.relative_to(destination).as_posix()
            require(member in inventory, 'UNINDEXED_EXTRACTION_FILE')
            row = inventory[member]
            require(path.stat().st_size == row['bytes'] and file_hash(path) == row['sha256'],
                    'EXTRACTED_BYTES_CHANGED')
            actual.add(member)
    require(actual == set(inventory), 'EXTRACTION_COVERAGE')


def run(args):
    require(args.job == JOB and args.source_sha == SOURCE and args.sha256 == PACKET
            and args.archive_sha256 == SOURCE_ARCHIVE, 'FIXED_EXTERNAL_IDENTITIES_REQUIRED')
    packet, source_archive = no_links(args.packet), no_links(args.archive)
    pin(packet, args.sha256)
    require(packet.stat().st_size == PACKET_BYTES, 'EXTERNAL_PACKET_SIZE')
    pin(source_archive, args.archive_sha256)
    require(source_archive.stat().st_size == 7882289, 'EXTERNAL_SOURCE_ARCHIVE_SIZE')
    pin(COMMON, COMMON_SHA)
    helper_hash = file_hash(__file__)
    spec = importlib.util.spec_from_file_location('_v7_partial_bound_common', COMMON)
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    destination, receipt_path = no_links(args.output), no_links(args.receipt)
    require(receipt_path.parent.resolve() == HERE.resolve() and not receipt_path.exists(), 'NEW_RECEIPT_REQUIRED')
    started = datetime.now(timezone.utc).isoformat()
    with common.pure_guard():
        manifest, _ = common.source_preflight(source_archive, args.archive_sha256, args.source_sha)
        with zipfile.ZipFile(packet) as archive:
            inventory = scan(archive)
            require(len(inventory) == 2941, 'EXACT_PACKET_MEMBER_COUNT')
            collection = decode(archive.read(COLLECTION))
            checked = collection_check(collection, inventory, job=args.job, source=args.source_sha,
                archive_hash=args.archive_sha256, experiment=manifest['experiment'])
            require(collection['baseline_sha'] == manifest['baseline_sha'], 'COLLECTION_BASELINE_MISMATCH')
            payload = payload_check(decode(archive.read(INDEX)), inventory)
            # No writes until every member and both stored indexes are authenticated.
            pin(packet, args.sha256)
            extract(archive, inventory, destination)
        common.check_source_again(manifest)
        pin(source_archive, args.archive_sha256)
        pin(packet, args.sha256)
        pin(COMMON, COMMON_SHA)
        pin(__file__, helper_hash)
        verify_extraction(destination, inventory)
    record = {'schema': 'cas-meta2-prototype-failed-packet-byte-extraction/7',
        'status': 'FAILED_RUN_ALL_PACKET_BYTES_VERIFIED', 'byte_audit_completed': True,
        'run_completed': False, 'run_returncode': 1, 'learning_accepted': False,
        'stored_trace_semantics_checked': False, 'model_or_tensor_loaded': False,
        'provider_calls': 0, 'automatic_retry': False, 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(), 'job': args.job,
        'source_sha': args.source_sha, 'source_archive': {'path': str(source_archive),
            'sha256': args.archive_sha256, 'bytes': source_archive.stat().st_size},
        'source_preflight': {'git_archive_and_local_files_verified': 603, 'protected_files_verified': 316,
            'original_source_files': 538, 'additional_source_files': 65,
            'source_rechecked_at_end': True},
        'packet': {'path': str(packet), 'sha256': args.sha256, 'bytes': packet.stat().st_size,
            'members': len(inventory), 'expanded_bytes_including_collection_receipt': sum(r['bytes'] for r in inventory.values()),
            'hash_rechecked_at_end': True},
        'collection': {k: v for k, v in collection.items() if k != 'index_entries'},
        'collection_receipt_sha256': inventory[COLLECTION]['sha256'],
        'collection_checks': checked, 'campaign_payload_index': payload,
        'extraction': {'path': str(destination), 'files_verified': len(inventory),
            'all_member_bytes_verified_before_write': True, 'all_member_bytes_verified_after_write': True,
            'inventory_coverage_exact': True},
        'inventory': dict(sorted(inventory.items())),
        'helper_files_sha256': {'extract.py': helper_hash, 'common.py': COMMON_SHA},
        'command': [sys.executable, '-B', *sys.argv],
        'boundary': 'Failed run, complete original-file collection. This receipt authenticates and extracts bytes only. '
            'It does not certify training, task correctness, completed native evaluation, trace semantics, cleanup, '
            'cost, model capability, or a neural rerun. The 1,940 omitted preview entries are not omitted files.'}
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('packet', 'archive', 'output', 'receipt'):
        parser.add_argument('--'+name, required=True, type=Path)
    for name in ('sha256', 'archive-sha256', 'source-sha', 'job'):
        parser.add_argument('--'+name, required=True)
    result = run(parser.parse_args(argv))
    print(json.dumps({'status': result['status'], 'extraction': result['extraction'],
        'packet': result['packet'], 'source_preflight': result['source_preflight'],
        'collection_checks': result['collection_checks'], 'campaign_payload_index': result['campaign_payload_index']},
        sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
