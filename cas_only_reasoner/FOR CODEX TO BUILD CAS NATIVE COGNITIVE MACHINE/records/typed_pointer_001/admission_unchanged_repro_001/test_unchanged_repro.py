"""Pure-Python tests for the unchanged-arm reproduction admission. No launcher import, no torch, no network, no AWS.

What is tested without the package build or the launcher run:
  * the quotes: pins, exactly-once in the real plan blob (commit 197caa32), and refusal of edited plan text;
  * the tree rule and the untracked rule, on synthetic git `-z` output;
  * the create-only `.partial` writer;
  * the record builders (owner record, job name, launch argv, config comparison);
  * the verdict reader on synthetic receipts (REPRODUCES / DOES_NOT_REPRODUCE / INCOMPLETE and every stop);
  * the reference hash, read from the real committed Helm 2.0 records at commit c8d5c430 (small JSON blobs only);
  * statically (AST, no import), that every `launch.<name>` the writer uses exists in the launcher sources.

Run:  python -B -m unittest test_unchanged_repro -v     (from this folder)
LABEL. CLAUDE_BUILT_CLAUDE_CHECKED.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402
import read_reproduction as reader  # noqa: E402
import prepare_unchanged_repro as prepare  # noqa: E402  (imports no launcher at module level)

P = common.GIT_PREFIX


class Stopped(Exception):
    pass


def stop(condition, reason):
    if not condition:
        raise Stopped(reason)


def git_has(commit, relative):
    try:
        return common.has_object(commit, relative)
    except Exception:            # noqa: BLE001 - git missing means the git-backed tests are skipped
        return False


class QuoteTests(unittest.TestCase):
    def test_pins_match_the_quotes(self):
        for group in (common.OWNER_WORDS, common.PLAN_WORDS):
            for name, (words, pinned) in group.items():
                self.assertEqual(sha256(words.encode('utf-8')).hexdigest(), pinned, name)
                self.assertTrue(words.isascii(), name)

    def test_normalise_joins_lines_but_keeps_inner_spaces(self):
        self.assertEqual(common.normalise('a\n  b\nc'), 'a b c')
        self.assertEqual(common.normalise('PROJECT:   A: x\nC'), 'PROJECT:   A: x C')

    @unittest.skipUnless(git_has(common.PLAN_COMMIT, common.PLAN_REL), 'plan commit not fetched')
    def test_every_quote_is_exactly_once_in_the_real_plan_blob(self):
        record = common.read_plan(stop)
        self.assertEqual(record['blob'], common.PLAN_BLOB)
        self.assertEqual(record['sha256'], common.PLAN_SHA256)

    @unittest.skipUnless(git_has(common.PLAN_COMMIT, common.PLAN_REL), 'plan commit not fetched')
    def test_edited_plan_text_is_refused(self):
        text = common.normalise(common.show(common.PLAN_COMMIT, common.PLAN_REL).decode('utf-8'))
        approval = common.OWNER_WORDS['owner_launch_approval_raw'][0]
        with self.assertRaisesRegex(Stopped, 'QUOTE_NOT_EXACTLY_ONCE_IN_PLAN:owner_launch_approval_raw'):
            common.check_quotes(text.replace(approval, approval.replace('$60', '$600')), stop)
        with self.assertRaisesRegex(Stopped, 'QUOTE_NOT_EXACTLY_ONCE_IN_PLAN:owner_launch_approval_raw'):
            common.check_quotes(text + ' ' + approval, stop)
        rule = common.PLAN_WORDS['plan_test_reproduces'][0]
        with self.assertRaisesRegex(Stopped, 'QUOTE_NOT_EXACTLY_ONCE_IN_PLAN:plan_test_reproduces'):
            common.check_quotes(text.replace(rule, rule.replace('equals', 'matches')), stop)

    def test_an_edited_quote_constant_is_refused_by_its_pin(self):
        saved = dict(common.OWNER_WORDS)
        try:
            words, pinned = common.OWNER_WORDS['owner_launch_approval_raw']
            common.OWNER_WORDS['owner_launch_approval_raw'] = (words.replace('YES', 'Yes'), pinned)
            with self.assertRaisesRegex(Stopped, 'QUOTE_EDITED:owner_launch_approval_raw'):
                common.check_quotes('anything', stop)
        finally:
            common.OWNER_WORDS.clear()
            common.OWNER_WORDS.update(saved)


class TreeAndUntrackedRuleTests(unittest.TestCase):
    def test_only_added_files_in_this_folder_and_the_package_pass(self):
        raw = b'\0'.join([b'A', (P + common.HERE_REL + '/x.py').encode(),
                          b'A', (P + common.PACKAGE_REL + '/source.zip').encode()]) + b'\0'
        self.assertEqual(common.tree_violations(common.parse_name_status_z(raw)), [])

    def test_inventory_trees_are_refused_even_for_an_added_file(self):
        for path in ('cncm/typed_pointer_worker.py', 'cncm/new_module.py',
                     'research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py',
                     'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py',
                     'records/typed_course_001/checks_002/public_course.json'):
            for status in ('A', 'M', 'D'):
                violations = common.tree_violations([(status, P + path)])
                self.assertEqual(len(violations), 1, path)
                self.assertTrue(violations[0].startswith('INVENTORY:'), violations)

    def test_modified_or_deleted_or_outside_paths_are_refused(self):
        cases = [('M', P + common.HERE_REL + '/x.py'), ('D', P + common.PACKAGE_REL + '/receipt.json'),
                 ('A', P + 'records/typed_pointer_001/prepare_study.py'),
                 ('A', P + common.RECEIPT_REL + '/result.json'), ('A', 'CHANGELOG.md')]
        for entry in cases:
            self.assertTrue(common.tree_violations([entry])[0].startswith('OUTSIDE_THIS_ADMISSION:'), entry)

    def test_status_parser_consumes_rename_sources(self):
        raw = b'R  new.py\0old.py\0?? a.txt\0 M b.py\0'
        self.assertEqual(common.parse_status_z(raw), [('R ', 'new.py'), ('??', 'a.txt'), (' M', 'b.py')])

    def test_untracked_rule(self):
        own = P + common.HERE_REL
        entries = [('??', own + '/frozen/20260917/owner.json'), ('??', own + '/reproduction_reading.json')]
        self.assertEqual(common.status_violations(entries), [])
        refused = [('??', own + '/frozen.partial/study.json'), ('??', own + '/notes.txt'),
                   ('??', P + common.RECEIPT_REL + '/result.json'), ('??', P + 'cncm/x.py'),
                   (' M', own + '/prepare_unchanged_repro.py'), ('A ', own + '/frozen/study.json'),
                   (' M', P + 'cncm/typed_pointer_worker.py')]
        for entry in refused:
            self.assertEqual(len(common.status_violations([entry])), 1, entry)


class WriterTests(unittest.TestCase):
    def test_atomic_write_and_refusals(self):
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            entries = [(final / '20260917' / 'owner.json', b'{}\n'), (final / 'study.json', b'{"a":1}\n')]
            seen = []
            pins = common.write_folder_atomically(final, entries, lambda locate: seen.append(
                locate(final / 'study.json').read_bytes()), stop)
            self.assertEqual(seen, [b'{"a":1}\n'])
            self.assertFalse(common.partial_of(final).exists())
            self.assertEqual({Path(item['path']).name for item in pins}, {'owner.json', 'study.json'})
            with self.assertRaisesRegex(Stopped, 'TARGET_EXISTS_NO_OVERWRITE'):
                common.write_folder_atomically(final, entries, lambda locate: None, stop)

    def test_failed_recheck_leaves_the_partial_and_blocks_the_next_run(self):
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            entries = [(final / 'study.json', b'{}\n')]

            def bad(locate):
                raise Stopped('RECHECK_FAILED')
            with self.assertRaisesRegex(Stopped, 'RECHECK_FAILED'):
                common.write_folder_atomically(final, entries, bad, stop)
            self.assertTrue(common.partial_of(final).exists())
            self.assertFalse(final.exists())
            with self.assertRaisesRegex(Stopped, 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND'):
                common.write_folder_atomically(final, entries, lambda locate: None, stop)

    def test_cr_bytes_and_outside_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            with self.assertRaisesRegex(Stopped, 'ENTRY_HAS_CR_BYTES'):
                common.write_folder_atomically(final, [(final / 'a.json', b'{}\r\n')], lambda locate: None, stop)
            with self.assertRaisesRegex(Stopped, 'ENTRY_OUTSIDE_TARGET'):
                common.write_folder_atomically(final, [(Path(scratch) / 'b.json', b'{}\n')], lambda locate: None,
                                               stop)
            self.assertFalse(common.partial_of(final).exists())


class BuilderTests(unittest.TestCase):
    def test_job_name_is_fresh_and_never_helm2_s(self):
        self.assertEqual(common.check_stamp('20260925120000', stop),
                         'cas-meta2-tpntr-20260925120000-20208c92-m-20260917')
        with self.assertRaisesRegex(Stopped, 'STAMP_IS_HELM2_S_OWN_STAMP'):
            common.check_stamp(common.HELM2_STAMP, stop)
        with self.assertRaisesRegex(Stopped, 'STAMP_FORM'):
            common.check_stamp('2026092512000', stop)
        # 63 characters with the account suffix: the bucket-name limit the launcher documents.
        self.assertEqual(len(common.job_name('20260925120000') + '-807562639912'), 63)

    def test_owner_record_carries_the_owner_words_and_the_bounds(self):
        plan = {'commit': common.PLAN_COMMIT}
        record = common.owner_record(schema='S', candidate='C', job='J', condition=common.HELM2_CONDITION,
                                     bounds=dict(common.EXPECTED_BOUNDS), plan=plan)
        self.assertEqual(record['owner_instruction_raw'], common.OWNER_WORDS['owner_launch_approval_raw'][0])
        self.assertEqual(record['owner_words_verbatim']['owner_option_delegation_raw'],
                         common.OWNER_WORDS['owner_option_delegation_raw'][0])
        self.assertEqual(record['plan_text_verbatim']['plan_test_reproduces'],
                         common.PLAN_WORDS['plan_test_reproduces'][0])
        self.assertIs(record['is_owner_signature'], False)
        self.assertEqual(record['bounds'], common.EXPECTED_BOUNDS)
        self.assertEqual(record['comparison_target']['final_pt_sha256'], common.REFERENCE_FINAL_PT_SHA256)
        self.assertEqual(record['label'], 'CLAUDE_BUILT_CLAUDE_CHECKED')
        self.assertTrue(common.canonical(record).isascii())

    def test_launch_argv_is_execute_study_s_order_and_full_schedule(self):
        pin = {'path': 'p', 'sha256': 'h'}
        argv = common.launch_argv(launcher='L', request=pin, authority=pin, owner=pin, receipt_dir='R', ledger='G')
        self.assertEqual(argv[:4], ['python', '-B', 'L', '--execute'])
        flags = [item for item in argv if item.startswith('--')]
        self.assertEqual(flags, ['--execute', '--request', '--request-sha256', '--authority', '--authority-sha256',
                                 '--owner-authorization', '--receipt-dir', '--ledger-path'])
        self.assertNotIn('--reduced-schedule', argv)

    def test_config_comparison_swaps_only_the_job_name(self):
        old_job, new_job = common.HELM2_JOB, common.job_name('20260925120000')

        def config(job, extra=0):
            return common.canonical({'job': job, 'bucket': job + '-807562639912', 'design': {'x': extra}}).decode()
        self.assertTrue(common.config_equal_except_job(config(new_job), config(old_job), new_job, old_job))
        self.assertFalse(common.config_equal_except_job(config(new_job, 1), config(old_job), new_job, old_job))
        self.assertFalse(common.config_equal_except_job(config(old_job), config(old_job), old_job, old_job))


# ---------------------------------------------------------------------------------------------------------------------
# The verdict reader, on synthetic receipts.
# ---------------------------------------------------------------------------------------------------------------------
NEW_JOB = common.job_name('20260925120000')
REQUEST = {'schema': 'cncm.typed-pointer-request/0.1', 'job': NEW_JOB, 'source_sha': common.SOURCE_SHA,
           'archive_sha256': common.ARCHIVE_SHA256, 'manifest_sha256': common.MANIFEST_SHA256,
           'launch_authorized': False}
REF = common.REFERENCE_FINAL_PT_SHA256
OTHER = 'ab' * 32


def enc(value):
    return json.dumps(value).encode('utf-8')


def reference_files(value=REF, size=common.REFERENCE_FINAL_PT_BYTES):
    meta = {'model_state_identity': 'm1', 'optimizer_state_identity': 'o1', 'encoder_state_identity': 'e1',
            'rng_state_identity': 'r1', 'elapsed_seconds': 7817.247307497,
            'run_identity': {'context': {'run_id': common.HELM2_JOB}}}
    return {'collected/results/artifacts/manifest.json': enc({'artifacts': [{'name': 'final.pt', 'sha256': value,
                                                                               'bytes': size}]}),
            'collected_inventory.json': enc({'files': [{'relative_path': 'results/artifacts/final.pt',
                                                         'sha256': value, 'bytes': size}]}),
            'collected/results/artifacts/final_checkpoint.json': enc({'sha256': value, 'bytes': size,
                                                                        'metadata': meta})}


def frozen_files(job=NEW_JOB, request=None):
    study = {'status': 'FROZEN_BEFORE_FIRST_RUN', 'source_sha': common.SOURCE_SHA,
             'jobs': [{'job': job, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED}]}
    return {'study.json': enc(study), '20260917/request.json': enc(request or dict(REQUEST, job=job))}


def receipt_files(value=REF, *, delivered=True, drop=(), overrides=None):
    meta = {'model_state_identity': 'm1', 'optimizer_state_identity': 'o1', 'encoder_state_identity': 'e1',
            'rng_state_identity': 'r1', 'elapsed_seconds': 7900.1, 'run_identity': {'context': {'run_id': NEW_JOB}}}
    files = {'result.json': enc({'job': NEW_JOB, 'request': REQUEST, 'completed_deliverable': delivered,
                                 'status': 'AWS_CANDIDATE_FINISHED', 'cleanup': {'complete': True}}),
             'reduced_schedule.json': enc({'job': NEW_JOB, 'reduced_schedule': None}),
             'collected/results/result.json': enc({'job': NEW_JOB, 'status': 'TYPED_POINTER_DELIVERED',
                                                   'summary': {'schedule_plan_mode': 'REGISTERED'}}),
             'collected/results/artifacts/manifest.json': enc({'artifacts': [{'name': 'final.pt', 'sha256': value,
                                                                                'bytes': 3670007}]}),
             'collected_inventory.json': enc({'files': [{'relative_path': 'results/artifacts/final.pt',
                                                          'sha256': value, 'bytes': 3670007}]}),
             'collected/results/artifacts/final_checkpoint.json': enc({'sha256': value, 'bytes': 3670007,
                                                                         'metadata': meta})}
    files.update(overrides or {})
    for name in drop:
        files.pop(name, None)
    return files


def run(reference=None, frozen=None, receipt=None):
    reference = reference_files() if reference is None else reference
    frozen = frozen_files() if frozen is None else frozen
    receipt = receipt_files() if receipt is None else receipt
    return reader.reading(reference.get, frozen.get, receipt.get, receipt_commit='c' * 40)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.saved = reader.stop_unless
        reader.stop_unless = stop

    def tearDown(self):
        reader.stop_unless = self.saved

    def test_equal_hash_reads_reproduces(self):
        record = run()
        self.assertEqual(record['verdict'], 'REPRODUCES')
        self.assertEqual(record['new']['final_pt_sha256'], REF)
        self.assertEqual(len(record['new']['sources']), 3)
        self.assertFalse(record['new']['weights_file_read'])

    def test_different_hash_reads_does_not_reproduce_and_names_option_b(self):
        record = run(receipt=receipt_files(OTHER))
        self.assertEqual(record['verdict'], 'DOES_NOT_REPRODUCE')
        self.assertIn('triggers B', record['next_step_per_plan'])
        diag = record['diagnostics_do_not_decide']
        self.assertIs(diag['deciding'], False)
        self.assertTrue(diag['model_state_identity']['equal'])   # equal weights never rescue the verdict

    def test_not_delivered_reads_incomplete(self):
        for receipt, reason in ((receipt_files(delivered=False), 'COMPLETED_DELIVERABLE_NOT_TRUE'),
                                (receipt_files(drop=['result.json']), 'RECEIPT_RESULT_JSON_ABSENT_OR_UNREADABLE'),
                                (receipt_files(drop=['collected/results/result.json']), 'WORKER_RESULT_ABSENT'),
                                (receipt_files(overrides={'collected/results/result.json': enc({
                                    'job': NEW_JOB, 'status': 'TYPED_POINTER_FAILED',
                                    'summary': {'schedule_plan_mode': 'REGISTERED'}})}), 'WORKER_STATUS')):
            record = run(receipt=receipt)
            self.assertEqual(record['verdict'], 'INCOMPLETE')
            self.assertTrue(any(item.startswith(reason) for item in record['new']['incomplete_reasons']), reason)
            self.assertIn('not launched', record['next_step_per_plan'])

    def test_disagreeing_new_records_read_incomplete(self):
        receipt = receipt_files(overrides={'collected_inventory.json': enc({'files': [{
            'relative_path': 'results/artifacts/final.pt', 'sha256': OTHER, 'bytes': 3670007}]})})
        record = run(receipt=receipt)
        self.assertEqual(record['verdict'], 'INCOMPLETE')
        self.assertEqual(record['new']['incomplete_reasons'], ['NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256'])

    def test_weights_file_is_hashed_only_when_no_record_states_a_hash(self):
        weights = b'not really a checkpoint'
        receipt = receipt_files(drop=common.FINAL_PT_RECORDS)
        receipt[common.FINAL_PT_WEIGHTS] = weights
        record = run(receipt=receipt)
        self.assertEqual(record['new']['final_pt_sha256'], sha256(weights).hexdigest())
        self.assertTrue(record['new']['weights_file_read'])
        self.assertEqual(record['verdict'], 'DOES_NOT_REPRODUCE')
        receipt.pop(common.FINAL_PT_WEIGHTS)
        self.assertEqual(run(receipt=receipt)['verdict'], 'INCOMPLETE')

    def test_weights_file_is_not_read_when_a_record_states_a_hash(self):
        class Guard(dict):
            def get(self, name, default=None):
                if name == common.FINAL_PT_WEIGHTS:
                    raise AssertionError('weights file read although a record states a sha256')
                return super().get(name, default)
        self.assertEqual(run(receipt=Guard(receipt_files()))['verdict'], 'REPRODUCES')

    def test_wrong_run_is_a_stop_not_a_verdict(self):
        with self.assertRaisesRegex(Stopped, 'RECEIPT_IS_FOR_ANOTHER_JOB'):
            run(receipt=receipt_files(overrides={'result.json': enc({'job': common.HELM2_JOB})}))
        with self.assertRaisesRegex(Stopped, 'RECEIPT_REQUEST_IS_NOT_THE_FROZEN_REQUEST'):
            run(receipt=receipt_files(overrides={'result.json': enc({
                'job': NEW_JOB, 'request': dict(REQUEST, archive_sha256='0' * 64)})}))
        with self.assertRaisesRegex(Stopped, 'RECEIPT_RAN_A_REDUCED_SCHEDULE'):
            run(receipt=receipt_files(overrides={'reduced_schedule.json': enc({
                'job': NEW_JOB, 'reduced_schedule': {'passes': 1}})}))
        with self.assertRaisesRegex(Stopped, 'WORKER_RAN_A_NON_REGISTERED_SCHEDULE'):
            run(receipt=receipt_files(overrides={'collected/results/result.json': enc({
                'job': NEW_JOB, 'status': 'TYPED_POINTER_DELIVERED', 'summary': {'schedule_plan_mode': 'REDUCED'}})}))
        with self.assertRaisesRegex(Stopped, 'FROZEN_REQUEST_IS_NOT_THE_HELM2_PACKAGE'):
            run(frozen=frozen_files(request=dict(REQUEST, source_sha='1' * 40)))
        with self.assertRaisesRegex(Stopped, 'NOTHING_FROZEN_AT_THIS_COMMIT'):
            run(frozen={})

    def test_a_changed_reference_is_a_stop(self):
        with self.assertRaisesRegex(Stopped, 'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE'):
            run(reference=reference_files(OTHER))
        broken = reference_files()
        broken.pop('collected_inventory.json')
        with self.assertRaisesRegex(Stopped, 'REFERENCE_RECORD_MISSING'):
            run(reference=broken)

    def test_the_verdict_is_always_one_of_three_words(self):
        for receipt in (receipt_files(), receipt_files(OTHER), receipt_files(delivered=False)):
            self.assertIn(run(receipt=receipt)['verdict'], ('REPRODUCES', 'DOES_NOT_REPRODUCE', 'INCOMPLETE'))


class RealReferenceTests(unittest.TestCase):
    """The committed Helm 2.0 records at c8d5c430: small JSON blobs only, never a weights file."""

    @unittest.skipUnless(git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected_inventory.json'),
                         'reference commit not fetched')
    def test_reference_hash_from_git(self):
        saved = reader.stop_unless
        reader.stop_unless = stop
        try:
            read = reader.git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL)
            reference, checkpoint = reader.reference_reading(read, lambda name: common.blob_id(
                common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name))
        finally:
            reader.stop_unless = saved
        self.assertEqual(reference['final_pt_sha256'],
                         'c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb')
        self.assertEqual(checkpoint['metadata']['run_identity']['context']['run_id'], common.HELM2_JOB)
        self.assertIn('elapsed_seconds', checkpoint['metadata'])      # the fact behind the builder finding

    @unittest.skipUnless(git_has(common.PACKAGE_COMMIT, common.HELM2_ADMISSION_REL + '/request.json'),
                         'package commit not fetched')
    def test_pinned_blobs_are_the_committed_ones(self):
        for name, blob in common.HELM2_ADMISSION_BLOBS.items():
            self.assertEqual(common.blob_id(common.PACKAGE_COMMIT, common.HELM2_ADMISSION_REL + '/' + name), blob)
        for name, blob in common.PACKAGE_BLOBS.items():
            self.assertEqual(common.blob_id(common.PACKAGE_COMMIT, common.PACKAGE_REL + '/' + name), blob)
        self.assertEqual(common.blob_id(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL
                                        + '/collected/input/source.zip'), common.PACKAGE_BLOBS['source.zip'])
        request = json.loads(common.show(common.PACKAGE_COMMIT, common.HELM2_ADMISSION_REL + '/request.json'))
        self.assertEqual((request['job'], request['archive_sha256'], request['manifest_sha256']),
                         (common.HELM2_JOB, common.ARCHIVE_SHA256, common.MANIFEST_SHA256))


# ---------------------------------------------------------------------------------------------------------------------
# Static: every launcher name the writer uses exists in the launcher sources (AST only; nothing is imported).
# ---------------------------------------------------------------------------------------------------------------------
PILOT = common.ROOT / 'research/CAS_META_2_COMPOSITION'
MODULE_FILES = {None: PILOT / 'aws/typed_pointer_launch.py',
                'shared': PILOT / 'aws/graph_training_curriculum_launch.py',
                'lifecycle': PILOT / 'aws/graph_training_candidate_launch.py',
                'run_evidence': PILOT / 'aws/run_evidence.py',
                'contract': PILOT / 'cas_meta2/typed_teaching/pointer_contract.py'}


def top_level_names(path):
    names = set()
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for item in ast.walk(target):
                    if isinstance(item, ast.Name):
                        names.add(item.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split('.')[0] for alias in node.names)
    return names


class StaticLauncherNameTests(unittest.TestCase):
    def test_every_launch_attribute_exists(self):
        used = set()
        for node in ast.walk(ast.parse((HERE / 'prepare_unchanged_repro.py').read_text(encoding='utf-8'))):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'launch':
                used.add((None, node.attr))
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                    and isinstance(node.value.value, ast.Name) and node.value.value.id == 'launch'
                    and node.value.attr in MODULE_FILES):          # launch.<module alias>.<name>
                used.add((node.value.attr, node.attr))
        self.assertGreater(len(used), 30)
        cache = {key: top_level_names(path) for key, path in MODULE_FILES.items()}
        missing = []
        for module, name in sorted(used, key=str):
            if module is None:
                if name not in cache[None]:
                    missing.append(name)
            elif module in cache:
                if name not in cache[module]:
                    missing.append(module + '.' + name)
            else:
                missing.append('UNMAPPED:' + module + '.' + name)
        self.assertEqual(missing, [])

    def test_this_folder_s_files_are_ascii_and_lf(self):
        for path in HERE.glob('*.py'):
            raw = path.read_bytes()
            self.assertNotIn(b'\r', raw, path.name)
            self.assertTrue(raw.isascii(), path.name)


if __name__ == '__main__':
    unittest.main()
