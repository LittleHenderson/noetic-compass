"""Small synthetic byte-only tests; no task generator or project imports."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('v7_partial_extractor_tested', HERE/'extract.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def archive(rows):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as z:
        for name, value in rows:
            z.writestr(name, value)
    raw.seek(0)
    return zipfile.ZipFile(raw)


class TestBytes(unittest.TestCase):
    def fixture(self, count=2):
        rows = [{'path': 'a/%04d.txt'%i, 'bytes': i, 'sha256': sha256(b'x'*i).hexdigest()} for i in range(count)]
        inventory = {row['path']: row for row in rows}
        inventory[m.COLLECTION] = {'path': m.COLLECTION, 'bytes': 4, 'sha256': sha256(b'null').hexdigest()}
        value = dict(job='job', source_sha='source', archive_sha256='archive', experiment={'p': 1},
            returncode=1, smoke_only=False, partial_evidence=False, omitted_full_file_count=0,
            original_file_count=count, included_full_file_count=count, original_bytes=sum(r['bytes'] for r in rows),
            original_file_index_sha256=sha256(b''.join(m.canonical(row)+b'\n' for row in rows)).hexdigest(),
            index_hash_format=m.FORMAT, index_entries=rows[:1000], index_entries_omitted=max(0, count-1000))
        return value, inventory

    def check(self, value, inventory):
        return m.collection_check(value, inventory, job='job', source='source', archive_hash='archive', experiment={'p': 1})

    def test_all_original_bytes_indexed(self):
        value, inventory = self.fixture()
        self.assertEqual(self.check(value, inventory)['all_original_index_entries_reconstructed'], 2)

    def test_preview_omission_is_not_file_omission(self):
        value, inventory = self.fixture(1002)
        self.assertEqual(self.check(value, inventory)['all_original_index_entries_reconstructed'], 1002)
        self.assertEqual(value['index_entries_omitted'], 2)

    def test_original_index_uses_linux_path_order_not_string_order(self):
        value, inventory = self.fixture(0)
        rows = [{'path': name, 'bytes': 0, 'sha256': sha256(b'').hexdigest()} for name in ('a/z.txt', 'a.txt')]
        inventory.update({row['path']: row for row in rows})
        value.update(original_file_count=2, included_full_file_count=2, index_entries=rows,
            original_file_index_sha256=sha256(b''.join(m.canonical(row)+b'\n' for row in rows)).hexdigest())
        self.assertEqual(self.check(value, inventory)['all_original_index_entries_reconstructed'], 2)

    def test_file_omission_refused(self):
        value, inventory = self.fixture(); value['omitted_full_file_count'] = 1
        with self.assertRaisesRegex(ValueError, 'OMITTED_FILES'): self.check(value, inventory)

    def test_success_refused(self):
        value, inventory = self.fixture(); value['returncode'] = 0
        with self.assertRaisesRegex(ValueError, 'FAILED_FULL_RUN'): self.check(value, inventory)

    def test_boolean_return_code_refused(self):
        value, inventory = self.fixture(); value['returncode'] = True
        with self.assertRaisesRegex(ValueError, 'FAILED_FULL_RUN'): self.check(value, inventory)

    def test_job_identity_refused(self):
        value, inventory = self.fixture(); value['job'] = 'other'
        with self.assertRaisesRegex(ValueError, 'IDENTITY'): self.check(value, inventory)

    def test_archive_identity_refused(self):
        value, inventory = self.fixture(); value['archive_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'IDENTITY'): self.check(value, inventory)

    def test_missing_original_refused(self):
        value, inventory = self.fixture(); del inventory['a/0001.txt']
        with self.assertRaisesRegex(ValueError, 'COUNTS'): self.check(value, inventory)

    def test_changed_hash_refused(self):
        value, inventory = self.fixture(); inventory['a/0001.txt']['sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'INDEX_HASH'): self.check(value, inventory)

    def test_preview_reordering_refused(self):
        value, inventory = self.fixture(); value['index_entries'].reverse()
        with self.assertRaisesRegex(ValueError, 'PREVIEW'): self.check(value, inventory)

    def test_payload_exact(self):
        inventory = {m.BASE+'a.txt': {'sha256': 'a'}, m.INDEX: {'sha256': 'index'}, 'outside.txt': {'sha256': 'b'}}
        self.assertEqual(m.payload_check({'a.txt': 'a'}, inventory)['files_verified'], 1)

    def test_payload_missing_entry(self):
        inventory = {m.BASE+'a.txt': {'sha256': 'a'}, m.INDEX: {'sha256': 'index'}}
        with self.assertRaisesRegex(ValueError, 'PAYLOAD_INDEX'): m.payload_check({}, inventory)

    def test_payload_unindexed_entry(self):
        with self.assertRaisesRegex(ValueError, 'PAYLOAD_INDEX'): m.payload_check({'a.txt': 'a'}, {m.INDEX: {'sha256': 'index'}})

    def test_bad_paths(self):
        for name in ('../a', '/a', 'a//b', 'a/./b', 'C:a', 'a\\b', 'a/NUL.txt', 'a/foo.', 'a/foo ', 'a/COM1', 'a\0b'):
            with self.subTest(name=name), self.assertRaises(ValueError): m.safe_name(name)

    def test_case_alias(self):
        with archive([('A/a.txt', b'a'), ('a/b.txt', b'b')]) as z:
            with self.assertRaisesRegex(ValueError, 'CASE_ALIAS'): m.scan(z)

    def test_file_directory_alias(self):
        with archive([('a', b'a'), ('a/b', b'b')]) as z:
            with self.assertRaisesRegex(ValueError, 'DIRECTORY_ALIAS'): m.scan(z)

    def test_symlink_refused(self):
        info = zipfile.ZipInfo('link'); info.create_system = 3; info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with archive([(info, b'target')]) as z:
            with self.assertRaisesRegex(ValueError, 'MEMBER_TYPE'): m.scan(z)

    def test_directory_refused(self):
        with archive([('directory/', b'')]) as z:
            with self.assertRaises(ValueError): m.scan(z)

    def test_json_duplicate_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): m.decode(raw)

    def test_extraction_roundtrip_and_reseal_detection(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            with patch.object(m, 'HERE', root), archive([('a/x.bin', b'\0\xffabc'), ('b.txt', b'')]) as z:
                inventory = m.scan(z)
                target = root/'extracted'
                m.extract(z, inventory, target)
                self.assertEqual((target/'a/x.bin').read_bytes(), b'\0\xffabc')
                (target/'a/x.bin').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'EXTRACTED_BYTES'): m.verify_extraction(target, inventory)

    def test_extra_extracted_file_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            with patch.object(m, 'HERE', root), archive([('a.txt', b'a')]) as z:
                inventory = m.scan(z); target = root/'extracted'; m.extract(z, inventory, target)
                (target/'extra.txt').write_bytes(b'x')
                with self.assertRaisesRegex(ValueError, 'UNINDEXED'): m.verify_extraction(target, inventory)

    def test_existing_destination_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            with patch.object(m, 'HERE', root), archive([('a.txt', b'a')]) as z:
                with self.assertRaisesRegex(ValueError, 'NEW_OWNED'): m.extract(z, m.scan(z), root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
