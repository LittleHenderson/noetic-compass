"""Copy an authenticated interrupted SQLite triplet and inspect only the copy."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADMISSION = ROOT/'records/prototype_v7_partial_review_001/extraction_receipt.json'
ADMISSION_SHA = '9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98'
EXTRACTOR_SHA = '92217722ce8b7b01b2792833042e38322f3ba9352863f7eee1e84737de2a046e'
PREFIX = 'cloud_job/campaign/native/evaluation/case_0045/generic_trained/native/'


def load_extractor():
    path = ROOT/'records/prototype_v7_partial_review_001/extract.py'
    assert sha256(path.read_bytes()).hexdigest() == EXTRACTOR_SHA
    spec = importlib.util.spec_from_file_location('_v7_timeout_extractor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def make_copy(m, source_paths, output):
    output = m.no_links(output)
    m.require(not output.exists(), 'NEW_SQLITE_COPY_REQUIRED')
    output.mkdir(parents=True, exist_ok=False)
    before = {name: m.file_hash(path) for name, path in source_paths.items()}
    for name, path in source_paths.items():
        shutil.copyfile(path, output/name)
        m.require(m.file_hash(output/name) == before[name], 'SQLITE_COPY_CHANGED')
    source = sqlite3.connect((output/'native.db').as_uri()+'?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    derived = output/'derived_committed.db'
    try:
        source.execute('PRAGMA query_only=ON')
        m.require(source.execute('PRAGMA query_only').fetchone()[0] == 1, 'SQLITE_QUERY_ONLY_REQUIRED')
        # immutable=1 is deliberately absent: the copied WAL must be considered.
        integrity = [tuple(r) for r in source.execute('PRAGMA integrity_check')]
        m.require(integrity == [('ok',)], 'COPIED_SQLITE_INTEGRITY')
        dest = sqlite3.connect(derived)
        try:
            source.backup(dest)
            m.require(dest.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'BACKUP_INTEGRITY')
        finally:
            dest.close()
    finally:
        source.close()
    after = {name: m.file_hash(path) for name, path in source_paths.items()}
    m.require(before == after, 'ORIGINAL_SQLITE_BYTES_CHANGED')
    return {'original_sha256_before': before, 'original_sha256_after': after,
        'original_bytes_unchanged': True, 'original_database_opened': False,
        'copied_connection': 'mode=ro; PRAGMA query_only=ON; WAL enabled; immutable not used',
        'copy_path': str(output), 'derived_database': str(derived),
        'derived_sha256': m.file_hash(derived), 'integrity_check': 'ok',
        'boundary': 'The derived database contains SQLite-visible committed rows from the copied database/WAL. '
            'A copied SHM may be updated by SQLite; original DB/WAL/SHM remain untouched. '
            'Integrity is not task correctness, semantic validation, or a complete execution receipt.'}


def run():
    m = load_extractor()
    m.pin(ADMISSION, ADMISSION_SHA)
    admitted = m.decode(ADMISSION.read_bytes())
    m.require(admitted['status'] == 'FAILED_RUN_ALL_PACKET_BYTES_VERIFIED'
        and admitted['packet']['sha256'] == m.PACKET and admitted['source_sha'] == m.SOURCE,
        'TIMEOUT_ADMISSION_IDENTITY')
    m.pin(admitted['packet']['path'], m.PACKET)
    m.pin(admitted['source_archive']['path'], m.SOURCE_ARCHIVE)
    inventory = admitted['inventory']; root = Path(admitted['extraction']['path'])
    names = {name[len(PREFIX):] for name in inventory if name.startswith(PREFIX)}
    m.require(names == {'native.db', 'native.db-wal', 'native.db-shm'}, 'EXACT_INTERRUPTED_SQLITE_TRIPLET')
    sources = {name: root/PREFIX/name for name in names}
    for name, path in sources.items():
        m.pin(path, inventory[PREFIX+name]['sha256'])
    record = make_copy(m, sources, HERE/'copy_001')
    record.update(schema='cas-meta2-prototype-timeout-sqlite-copy/7', case_index=45, arm='generic_trained',
        admission_sha256=ADMISSION_SHA, packet_sha256=m.PACKET, source_sha=m.SOURCE,
        completed_execution=False, task_correctness=None, semantic_prefix_checked=False)
    m.pin(ADMISSION, ADMISSION_SHA); m.pin(admitted['packet']['path'], m.PACKET)
    with (HERE/'copy_receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps(record, sort_keys=True, indent=2))


if __name__ == '__main__':
    run()
