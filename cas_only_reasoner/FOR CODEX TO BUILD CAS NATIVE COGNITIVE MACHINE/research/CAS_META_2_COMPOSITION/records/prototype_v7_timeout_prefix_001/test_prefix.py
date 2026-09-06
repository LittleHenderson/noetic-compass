"""Pure SQLite-copy tests plus negative checks on an authenticated stored fixture.

The stored fixture is the already-collected timeout prefix, not generated data.
Only new temporary copies are mutated. No tensor/model/provider imports occur.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


copier = load('_timeout_test_copier', HERE/'copy_view.py')
m = copier.load_extractor()


class CopyTests(unittest.TestCase):
    def test_committed_wal_rows_in_backup_and_original_triplet_unchanged(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary); original = root/'original'; original.mkdir()
            writer = sqlite3.connect(original/'native.db')
            try:
                writer.execute('PRAGMA journal_mode=WAL'); writer.execute('PRAGMA wal_autocheckpoint=0')
                writer.execute('CREATE TABLE records (x INTEGER)')
                writer.executemany('INSERT INTO records VALUES (?)', [(1,), (2,), (3,)]); writer.commit()
                sources = {n:original/n for n in ('native.db', 'native.db-wal', 'native.db-shm')}
                before = {n:m.file_hash(p) for n,p in sources.items()}
                result = copier.make_copy(m, sources, root/'copy')
                self.assertEqual(before, {n:m.file_hash(p) for n,p in sources.items()})
                con = sqlite3.connect(Path(result['derived_database']).as_uri()+'?mode=ro&immutable=1', uri=True)
                try: self.assertEqual(con.execute('SELECT x FROM records ORDER BY x').fetchall(), [(1,), (2,), (3,)])
                finally: con.close()
                self.assertFalse(result['original_database_opened'])
            finally:
                writer.close()

    def test_existing_output_refused_before_copy(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            with self.assertRaisesRegex(ValueError, 'NEW_SQLITE_COPY'):
                copier.make_copy(m, {}, Path(temporary))

    def test_corrupt_database_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary); original = root/'native.db'; original.write_bytes(b'not a sqlite database')
            with self.assertRaises(sqlite3.DatabaseError):
                copier.make_copy(m, {'native.db': original}, root/'copy')


class StoredNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.pin(copier.ADMISSION, copier.ADMISSION_SHA)
        cls.admission = m.decode(copier.ADMISSION.read_bytes())
        m.pin(m.COMMON, m.COMMON_SHA)
        cls.c = load('_timeout_test_common', m.COMMON)
        cls.guard = cls.c.pure_guard(); cls.guard.__enter__()
        try:
            cls.manifest, prior = cls.c.source_preflight(cls.admission['source_archive']['path'], m.SOURCE_ARCHIVE, m.SOURCE)
            from jsonschema import Draft202012Validator
            from cas_meta2.curriculum import check_native_topology
            cls.engine = cls.c.load('_timeout_test_engine', m.ROOT/'tools/audit_stored_packet_v3.py')
            cls.engine.Draft202012Validator = Draft202012Validator; cls.engine.check_native_topology = check_native_topology
            cls.validator, _ = cls.engine.protected_schema()
            cls.helper = cls.c.load('_timeout_test_prefix', HERE/'prefix.py')
            m.pin(HERE/'timeout_prefix_receipt.json', 'fc444ba90f71cca2d1b539884da56f5ddc32d41b3e841c3dbf4c94867fd17fbe')
            cls.receipt = m.decode((HERE/'timeout_prefix_receipt.json').read_bytes())
            cls.identity = prior['outcomes']['runtime_identity']
            cls.action = cls.receipt['selected_action']
            root = Path(cls.admission['extraction']['path'])
            name = m.BASE+'dataset/test_public.json'
            m.pin(root/name, cls.admission['inventory'][name]['sha256'])
            cls.public = m.decode((root/name).read_bytes())[45]
            cls.database = HERE/'copy_001/derived_committed.db'
            m.pin(cls.database, cls.receipt['derived_database_sha256'])
        except BaseException:
            cls.guard.__exit__(*__import__('sys').exc_info()); raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.c.check_source_again(cls.manifest)
            m.pin(cls.database, cls.receipt['derived_database_sha256'])
        finally:
            cls.guard.__exit__(None, None, None)

    def verify(self, database=None, public=None, action=None, identity=None, query_only=True):
        path = database or self.database
        con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        con.row_factory = sqlite3.Row
        try:
            if query_only: con.execute('PRAGMA query_only=ON')
            return self.helper.verify_prefix(con, public or self.public, action or self.action,
                identity or self.identity, self.engine, self.validator, self.c)
        finally: con.close()

    def test_actual_authenticated_stored_prefix(self):
        got = self.verify()
        self.assertEqual((got['committed_native_runs'], got['committed_traces'],
            got['committed_reserved_policy_units_lower_bound'], got['scheduled_program_native_runs']), (37, 37, 2664, 39))
        self.assertFalse(got['compute_complete']); self.assertIsNone(got['full_task_correctness'])

    def test_query_only_required(self):
        with self.assertRaisesRegex(ValueError, 'QUERY_ONLY'): self.verify(query_only=False)

    def test_wrong_binding_rejected(self):
        action = deepcopy(self.action); action['binding'] = (action['binding']+1)%3
        with self.assertRaisesRegex(ValueError, 'OBSERVATION_BINDING'): self.verify(action=action)

    def test_wrong_public_bytes_rejected(self):
        public = deepcopy(self.public); public['observations'][0]['values'][0] += 0.125
        with self.assertRaisesRegex(ValueError, 'OBSERVATION_BINDING'): self.verify(public=public)

    def test_wrong_fixed_model_identity_rejected(self):
        identity = deepcopy(self.identity); identity['stored_model_digest'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'FIXED_MODEL_IDENTITY'): self.verify(identity=identity)

    def test_modified_trace_copy_rejected_and_original_unchanged(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            copied = Path(temporary)/'mutated.db'; shutil.copyfile(self.database, copied)
            con = sqlite3.connect(copied)
            try:
                # This is a disposable corruption fixture, never original evidence.
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute("UPDATE trace_events SET payload_sha256=? WHERE sequence=1", ('a'*64,))
                con.execute('DROP TRIGGER trace_events_immutable_update')
                con.execute("UPDATE trace_events SET payload_sha256=? WHERE sequence=1", ('a'*64,)); con.commit()
            finally: con.close()
            with self.assertRaisesRegex(ValueError, 'TRACE_CHAIN'): self.verify(database=copied)
            m.pin(self.database, self.receipt['derived_database_sha256'])

    def test_missing_commit_receipt_copy_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            copied = Path(temporary)/'mutated.db'; shutil.copyfile(self.database, copied)
            con = sqlite3.connect(copied)
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute('DELETE FROM commit_receipts WHERE receipt_id=(SELECT receipt_id FROM commit_receipts LIMIT 1)')
                con.execute('DROP TRIGGER commit_receipts_immutable_delete')
                con.execute('DELETE FROM commit_receipts WHERE receipt_id=(SELECT receipt_id FROM commit_receipts LIMIT 1)'); con.commit()
            finally: con.close()
            with self.assertRaisesRegex(ValueError, 'DOCUMENT_MISSING'): self.verify(database=copied)


if __name__ == '__main__':
    unittest.main(verbosity=2)
