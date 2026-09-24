"""Pure-Python tests for the unchanged-arm reproduction admission. No launcher import, no torch, no network, no AWS.

What is tested without the package build or the launcher run:
  * the quotes: pins, exactly-once in the real plan blob (commit 197caa32), and refusal of edited plan text;
  * the plan gate (revision 1, BLOCKER 1): status words, tips, and the REAL held plan at commit 7b6e25f8 refused;
  * the policy gate (revision 1, BLOCKER 2): it ships NOT fixed, and the reader stops on it before anything else;
  * the tree rule and the untracked rule, on synthetic git `-z` output;
  * the create-only `.partial` writer, including a failed rename;
  * the record builders (owner record, job name, launch argv, config comparison);
  * the verdict reader on synthetic receipts: job binding (MAJOR 1), all three records (MAJOR 2), the contradiction
    stop, the weights cross-check, and every earlier stop;
  * the --check pieces (MINOR 3): the spend gate and `check_study` on a synthetic frozen folder;
  * the reference hash, read from the real committed Helm 2.0 records at commit c8d5c430 (small JSON blobs only);
  * statically (AST, no import): every `launch.<name>` the writer uses exists, and the gates run before the launcher.

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
HELD_COMMIT = '7b6e25f89cfece977a5c876537671a6d806ee3ad'       # the commit that put the launch on hold
HELD_BLOB = '3172a221f3a12448029b995e87009284fcce453c'
FIXED_POLICY = dict(common.REPRODUCTION_POLICY, status=common.POLICY_FIXED, fixed_in_plan_commit=common.PLAN_COMMIT,
                    fixed_in_plan_blob=common.PLAN_BLOB, rule=reader.READER_RULE)


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


def digest(raw):
    return sha256(raw).hexdigest()


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
        self.assertIn('plan_cost_basis_bookings', common.PLAN_WORDS)       # review NOTE: both $60 readings carried

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


# ---------------------------------------------------------------------------------------------------------------------
# Gate 1: the plan must still be current and approved (review BLOCKER 1).
# ---------------------------------------------------------------------------------------------------------------------
APPROVED_RAW = b'# t\n\n**Status.** Was `DRAFT`; now `APPROVED_FOR_LAUNCH` (section 0). More\ntext `HELD` here.\n'
HELD_RAW = b'# t\n\n**Status.** `LAUNCH_HELD_PENDING_AMENDMENTS` (2026-09-24). The yes (section 0) is held.\n'


def tip(ref=common.PLAN_TRACKING_REF, *, blob=common.PLAN_BLOB, raw=APPROVED_RAW, ancestor=True, commit='f' * 40):
    return {'ref': ref, 'commit': commit, 'blob': blob, 'raw': raw, 'pinned_commit_is_ancestor': ancestor}


class PlanGateTests(unittest.TestCase):
    def test_status_words(self):
        self.assertEqual(common.plan_status_tokens(APPROVED_RAW), ['DRAFT', 'APPROVED_FOR_LAUNCH'])
        self.assertTrue(common.plan_status_approved(common.plan_status_tokens(APPROVED_RAW)))
        self.assertEqual(common.plan_status_tokens(HELD_RAW), ['LAUNCH_HELD_PENDING_AMENDMENTS'])
        self.assertFalse(common.plan_status_approved(common.plan_status_tokens(HELD_RAW)))
        self.assertFalse(common.plan_status_approved(['APPROVED_FOR_LAUNCH', 'LAUNCH_HELD_PENDING_AMENDMENTS']))
        self.assertFalse(common.plan_status_approved(['APPROVED_FOR_LAUNCH', 'WITHDRAWN']))
        self.assertIsNone(common.plan_status_tokens(b'# no status line\n'))
        self.assertFalse(common.plan_status_approved(None))

    def test_the_pinned_approved_tip_passes(self):
        self.assertEqual(common.plan_tip_violations([tip()]), [])
        self.assertEqual(common.plan_tip_violations([tip(), tip(common.PLAN_LOCAL_REF)]), [])

    def test_moved_held_missing_or_unrelated_tips_are_refused(self):
        cases = {'PLAN_TRACKING_REF_MISSING': [], 'BLOB:': [tip(blob=HELD_BLOB)], 'STATUS:': [tip(raw=HELD_RAW)],
                 'PINNED_COMMIT_NOT_IN_THIS_BRANCH': [tip(ancestor=False)],
                 'STATUS:' + common.PLAN_TRACKING_REF: [tip(raw=None, blob=None)]}
        for expected, tips in cases.items():
            violations = common.plan_tip_violations(tips)
            self.assertTrue(any(item.startswith(expected) for item in violations), (expected, violations))
        # the local branch moved on while the fetched tip did not: still refused
        violations = common.plan_tip_violations([tip(), tip(common.PLAN_LOCAL_REF, blob=HELD_BLOB, raw=HELD_RAW)])
        self.assertEqual(len(violations), 2, violations)

    def test_check_plan_is_current_stops_and_fetches(self):
        saved, seen = common.read_plan_tips, []
        try:
            common.read_plan_tips = lambda stop_, *, fetch: seen.append(fetch) or [tip(blob=HELD_BLOB, raw=HELD_RAW)]
            with self.assertRaisesRegex(Stopped, '^PLAN_MOVED_OR_HELD:BLOB:.*STATUS:.*LAUNCH_HELD_PENDING_AMENDMENTS'):
                common.check_plan_is_current(stop)
            common.read_plan_tips = lambda stop_, *, fetch: seen.append(fetch) or [tip()]
            self.assertEqual(common.check_plan_is_current(stop, fetch=False)[0]['blob'], common.PLAN_BLOB)
        finally:
            common.read_plan_tips = saved
        self.assertEqual(seen, [True, False])        # the default fetches

    @unittest.skipUnless(git_has(common.PLAN_COMMIT, common.PLAN_REL), 'plan commit not fetched')
    def test_the_real_approval_commit_passes(self):
        self.assertEqual(common.plan_tip_violations([common.plan_tip(common.PLAN_TRACKING_REF, common.PLAN_COMMIT)]),
                         [])

    @unittest.skipUnless(git_has(HELD_COMMIT, common.PLAN_REL), 'held commit 7b6e25f8 not fetched')
    def test_the_real_held_plan_is_refused(self):
        held = common.plan_tip(common.PLAN_TRACKING_REF, HELD_COMMIT)
        self.assertEqual(held['blob'], HELD_BLOB)
        self.assertTrue(held['pinned_commit_is_ancestor'])
        self.assertEqual(common.plan_status_tokens(held['raw']), ['LAUNCH_HELD_PENDING_AMENDMENTS'])
        violations = common.plan_tip_violations([held])
        self.assertEqual([item.split(':')[0] for item in violations], ['BLOB', 'STATUS'])
        # Every pinned quote still occurs once in the held plan: the quote check alone could not have caught the hold.
        common.check_quotes(common.normalise(held['raw'].decode('utf-8')), stop)


# ---------------------------------------------------------------------------------------------------------------------
# Gate 2: the reproduction policy (review BLOCKER 2).
# ---------------------------------------------------------------------------------------------------------------------
class PolicyGateTests(unittest.TestCase):
    def test_this_revision_ships_the_policy_unfixed(self):
        self.assertNotEqual(common.REPRODUCTION_POLICY['status'], common.POLICY_FIXED)
        with self.assertRaisesRegex(Stopped, 'REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN'):
            common.check_policy_fixed(stop, reader.READER_RULE)

    def test_only_a_policy_fixed_in_the_pinned_plan_for_the_reader_s_rule_passes(self):
        self.assertTrue(common.check_policy_fixed(stop, reader.READER_RULE, FIXED_POLICY))
        for change, reason in (({'fixed_in_plan_blob': HELD_BLOB}, 'NOT_FIXED'),
                               ({'fixed_in_plan_commit': HELD_COMMIT}, 'NOT_FIXED'),
                               ({'status': 'FIXED'}, 'NOT_FIXED'),
                               ({'rule': 'LEARNED_STATE_IDENTITY'}, 'IS_NOT_THE_RULE_THE_READER_IMPLEMENTS')):
            with self.assertRaisesRegex(Stopped, reason):
                common.check_policy_fixed(stop, reader.READER_RULE, dict(FIXED_POLICY, **change))

    def test_the_reader_stops_on_the_policy_before_reading_anything(self):
        saved = reader.stop_unless
        reader.stop_unless = stop

        def refuse(name):
            raise AssertionError('read ' + name + ' before the policy gate')
        try:
            with self.assertRaisesRegex(Stopped, 'REPRODUCTION_POLICY_NOT_FIXED'):
                reader.reading(refuse, refuse, refuse)
        finally:
            reader.stop_unless = saved


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

    def test_a_failed_rename_is_a_named_stop_and_leaves_the_partial(self):
        saved = common.os.rename

        def locked(source, target):
            raise PermissionError('sync lock')
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            try:
                common.os.rename = locked
                with self.assertRaisesRegex(Stopped, 'RENAME_FAILED_PARTIAL_LEFT_INSPECT_BY_HAND.*PermissionError'):
                    common.write_folder_atomically(final, [(final / 'study.json', b'{}\n')], lambda locate: None,
                                                   stop)
            finally:
                common.os.rename = saved
            self.assertTrue(common.partial_of(final).exists())
            self.assertFalse(final.exists())

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
        self.assertEqual(common.stamp_of(common.job_name('20260925120000')), '20260925120000')
        self.assertIsNone(common.stamp_of('cas-meta2-tpntr-20260925120000-20208c92-m-20260918'))

    def test_owner_record_carries_the_owner_words_and_the_bounds(self):
        plan = {'commit': common.PLAN_COMMIT}
        record = common.owner_record(schema='S', candidate='C', job='J', condition=common.HELM2_CONDITION,
                                     bounds=dict(common.EXPECTED_BOUNDS), plan=plan)
        self.assertEqual(record['owner_instruction_raw'], common.OWNER_WORDS['owner_launch_approval_raw'][0])
        self.assertEqual(record['owner_words_verbatim']['owner_option_delegation_raw'],
                         common.OWNER_WORDS['owner_option_delegation_raw'][0])
        self.assertEqual(record['plan_text_verbatim']['plan_test_reproduces'],
                         common.PLAN_WORDS['plan_test_reproduces'][0])
        self.assertEqual(record['plan_text_verbatim']['plan_cost_basis_bookings'],
                         common.PLAN_WORDS['plan_cost_basis_bookings'][0])
        self.assertEqual(record['reproduction_policy'], common.REPRODUCTION_POLICY)
        self.assertIn('Section 4', record['sixty_dollar_readings'])
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
# The verdict reader, on synthetic receipts (under a synthetic FIXED policy; the shipped policy is not fixed).
# ---------------------------------------------------------------------------------------------------------------------
NEW_JOB = common.job_name('20260925120000')
REQUEST = {'schema': 'cncm.typed-pointer-request/0.1', 'job': NEW_JOB, 'source_sha': common.SOURCE_SHA,
           'archive_sha256': common.ARCHIVE_SHA256, 'manifest_sha256': common.MANIFEST_SHA256,
           'launch_authorized': False}
REF = common.REFERENCE_FINAL_PT_SHA256
REF_BYTES = common.REFERENCE_FINAL_PT_BYTES
OTHER = 'ab' * 32
THIRD = 'cd' * 32
MANIFEST, INVENTORY, CHECKPOINT = common.MANIFEST_RECORD, common.INVENTORY_RECORD, common.CHECKPOINT_RECORD


def enc(value):
    return json.dumps(value).encode('utf-8')


def record_set(job, value, size, *, elapsed, run_ids=None, manifest_rows=None, inventory_final=None,
               inventory_drop=()):
    """The three final.pt records of one run, bound to each other the way a real receipt binds them."""
    first, second = run_ids or (job, job)
    meta = {'model_state_identity': 'm1', 'optimizer_state_identity': 'o1', 'encoder_state_identity': 'e1',
            'rng_state_identity': 'r1', 'elapsed_seconds': elapsed, 'run_identity': {'context': {'run_id': first}},
            'init_args': {'run_context': {'run_id': second}}}
    manifest = enc({'artifacts': manifest_rows if manifest_rows is not None
                    else [{'name': 'final.pt', 'sha256': value, 'bytes': size}]})
    checkpoint = enc({'sha256': value, 'bytes': size, 'metadata': meta})
    final_sha, final_size = inventory_final or (value, size)
    rows = [{'relative_path': 'results/artifacts/final.pt', 'sha256': final_sha, 'bytes': final_size},
            {'relative_path': 'results/artifacts/manifest.json', 'sha256': digest(manifest), 'bytes': len(manifest)},
            {'relative_path': 'results/artifacts/final_checkpoint.json', 'sha256': digest(checkpoint),
             'bytes': len(checkpoint)}]
    rows = [row for row in rows if row['relative_path'] not in inventory_drop]
    return {MANIFEST: manifest, INVENTORY: enc({'job': job, 'files': rows}), CHECKPOINT: checkpoint}


def reference_files(value=REF, **options):
    return record_set(common.HELM2_JOB, value, REF_BYTES, elapsed=7817.247307497, **options)


def frozen_files(job=NEW_JOB, request=None, plan=None, policy=None):
    study = {'status': 'FROZEN_BEFORE_FIRST_RUN', 'source_sha': common.SOURCE_SHA,
             'plan_record': plan or {'commit': common.PLAN_COMMIT, 'blob': common.PLAN_BLOB,
                                     'sha256': common.PLAN_SHA256},
             'reproduction_policy': policy or common.REPRODUCTION_POLICY,
             'jobs': [{'job': job, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED}]}
    return {'study.json': enc(study), '20260917/request.json': enc(request or dict(REQUEST, job=job))}


def receipt_files(value=OTHER, size=REF_BYTES, *, delivered=True, drop=(), overrides=None, **options):
    files = {'result.json': enc({'job': NEW_JOB, 'request': REQUEST, 'completed_deliverable': delivered,
                                 'status': 'AWS_CANDIDATE_FINISHED', 'cleanup': {'complete': True}}),
             'reduced_schedule.json': enc({'job': NEW_JOB, 'reduced_schedule': None}),
             'collected/results/result.json': enc({'job': NEW_JOB, 'status': 'TYPED_POINTER_DELIVERED',
                                                   'summary': {'schedule_plan_mode': 'REGISTERED'}}),
             **record_set(NEW_JOB, value, size, elapsed=7900.1, **options)}
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
        self.saved = reader.stop_unless, common.REPRODUCTION_POLICY
        reader.stop_unless = stop
        common.REPRODUCTION_POLICY = dict(FIXED_POLICY)

    def tearDown(self):
        reader.stop_unless, common.REPRODUCTION_POLICY = self.saved

    def test_different_hash_reads_does_not_reproduce_and_names_option_b(self):
        record = run()
        self.assertEqual(record['verdict'], 'DOES_NOT_REPRODUCE')
        self.assertIn('triggers B', record['next_step_per_plan'])
        self.assertEqual(len(record['new']['sources']), 3)
        self.assertEqual(record['new']['weights_file_cross_check'], 'WEIGHTS_FILE_NOT_COMMITTED_AT_THE_RECEIPT_COMMIT')
        diag = record['diagnostics_do_not_decide']
        self.assertIs(diag['deciding'], False)
        self.assertTrue(diag['model_state_identity']['equal'])   # equal weights never rescue the verdict
        self.assertEqual(diag['run_id'], {'reference': common.HELM2_JOB, 'new': NEW_JOB})

    def test_helm2_s_hash_under_the_new_run_id_is_a_contradiction_not_reproduces(self):
        with self.assertRaisesRegex(Stopped, 'CONTRADICTION_HELM2_FILE_HASH_UNDER_THE_NEW_RUN_ID'):
            run(receipt=receipt_files(REF))

    def test_decide_is_the_plain_rule(self):
        reference = {'final_pt_sha256': REF}
        self.assertEqual(reader.decide(reference, None, {'final_pt_sha256': REF}), 'REPRODUCES')
        self.assertEqual(reader.decide(reference, None, {'final_pt_sha256': OTHER}), 'DOES_NOT_REPRODUCE')
        self.assertEqual(reader.decide(reference, 'INCOMPLETE', {}), 'INCOMPLETE')

    def test_records_copied_from_helm2_s_receipt_are_a_stop(self):
        """The reviewer's probe: the new run's own result files, Helm 2.0's inventory and checkpoint pin."""
        old = reference_files()
        with self.assertRaisesRegex(Stopped, 'INVENTORY_IS_FOR_ANOTHER_JOB:' + common.HELM2_JOB):
            run(receipt=receipt_files(REF, overrides={INVENTORY: old[INVENTORY], CHECKPOINT: old[CHECKPOINT]}))
        with self.assertRaisesRegex(Stopped, 'CHECKPOINT_IS_FOR_ANOTHER_JOB'):
            run(receipt=receipt_files(overrides={CHECKPOINT: old[CHECKPOINT]}))
        with self.assertRaisesRegex(Stopped, 'RECORD_IS_NOT_THE_ONE_THIS_JOB_COLLECTED:worker_artifact_manifest'):
            run(receipt=receipt_files(overrides={MANIFEST: old[MANIFEST]}))
        with self.assertRaisesRegex(Stopped, 'CHECKPOINT_IS_FOR_ANOTHER_JOB'):
            run(receipt=receipt_files(run_ids=(NEW_JOB, common.HELM2_JOB)))
        with self.assertRaisesRegex(Stopped, 'CHECKPOINT_IS_FOR_ANOTHER_JOB'):
            run(receipt=receipt_files(run_ids=(None, None)))

    def test_partial_record_sets_read_incomplete(self):
        """The reviewer's four probes, each of which used to read REPRODUCES."""
        probes = {
            'only the inventory states a hash': (
                receipt_files(drop=(MANIFEST, CHECKPOINT)), 'FINAL_PT_RECORD_ABSENT_OR_UNREADABLE'),
            'only the checkpoint pin states a hash': (
                receipt_files(drop=(MANIFEST, INVENTORY)), 'FINAL_PT_RECORD_ABSENT_OR_UNREADABLE'),
            'equal sha256, different bytes': (
                receipt_files(inventory_final=(OTHER, REF_BYTES + 1)), 'NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES'),
            'two final.pt rows in the manifest': (
                receipt_files(manifest_rows=[{'name': 'final.pt', 'sha256': OTHER, 'bytes': REF_BYTES}] * 2),
                'FINAL_PT_ROW_NOT_EXACTLY_ONE_WELL_FORMED:worker_artifact_manifest'),
            'the inventory does not list the checkpoint pin': (
                receipt_files(inventory_drop=('results/artifacts/final_checkpoint.json',)),
                'INVENTORY_HAS_NO_SINGLE_ROW_FOR:worker_final_checkpoint_pin'),
            'a byte count that is not a positive integer': (
                receipt_files(manifest_rows=[{'name': 'final.pt', 'sha256': OTHER, 'bytes': '3670007'}]),
                'FINAL_PT_ROW_NOT_EXACTLY_ONE_WELL_FORMED:worker_artifact_manifest'),
        }
        for label, (receipt, reason) in probes.items():
            record = run(receipt=receipt)
            self.assertEqual(record['verdict'], 'INCOMPLETE', label)
            self.assertTrue(any(item.startswith(reason) for item in record['new']['incomplete_reasons']),
                            (label, record['new']['incomplete_reasons']))

    def test_disagreeing_new_records_read_incomplete(self):
        record = run(receipt=receipt_files(inventory_final=(THIRD, REF_BYTES)))
        self.assertEqual(record['verdict'], 'INCOMPLETE')
        self.assertEqual(record['new']['incomplete_reasons'], ['NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES'])

    def test_the_weights_file_is_a_cross_check_only(self):
        weights = b'not really a checkpoint'
        value, size = digest(weights), len(weights)
        receipt = receipt_files(value, size)
        receipt[common.FINAL_PT_WEIGHTS] = weights
        record = run(receipt=receipt)
        self.assertEqual(record['verdict'], 'DOES_NOT_REPRODUCE')
        self.assertEqual(record['new']['weights_file_cross_check'], 'WEIGHTS_FILE_EQUALS_THE_THREE_RECORDS')
        receipt[common.FINAL_PT_WEIGHTS] = weights + b'x'
        with self.assertRaisesRegex(Stopped, 'WEIGHTS_FILE_IS_NOT_THE_ONE_THE_RECORDS_STATE'):
            run(receipt=receipt)
        alone = receipt_files(drop=common.FINAL_PT_RECORDS)
        alone[common.FINAL_PT_WEIGHTS] = weights           # never the only source
        self.assertEqual(run(receipt=alone)['verdict'], 'INCOMPLETE')

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
        with self.assertRaisesRegex(Stopped, 'FROZEN_JOB_IS_HELM2_S_OWN_JOB'):
            run(frozen=frozen_files(job=common.HELM2_JOB))
        with self.assertRaisesRegex(Stopped, 'FROZEN_UNDER_A_DIFFERENT_PLAN'):
            run(frozen=frozen_files(plan={'commit': HELD_COMMIT, 'blob': HELD_BLOB, 'sha256': '0' * 64}))
        with self.assertRaisesRegex(Stopped, 'FROZEN_UNDER_A_DIFFERENT_REPRODUCTION_POLICY'):
            run(frozen=frozen_files(policy=dict(FIXED_POLICY, rule='OUTPUT_REPRODUCTION')))

    def test_a_changed_reference_is_a_stop(self):
        with self.assertRaisesRegex(Stopped, 'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE'):
            run(reference=reference_files(OTHER))
        broken = reference_files()
        broken.pop(INVENTORY)
        with self.assertRaisesRegex(Stopped, 'REFERENCE_RECORD_MISSING'):
            run(reference=broken)
        with self.assertRaisesRegex(Stopped, 'INVENTORY_IS_FOR_ANOTHER_JOB'):
            run(reference=record_set(NEW_JOB, REF, REF_BYTES, elapsed=1.0))

    def test_the_verdict_is_always_one_of_three_words(self):
        for receipt in (receipt_files(), receipt_files(THIRD), receipt_files(delivered=False),
                        receipt_files(drop=(MANIFEST,))):
            self.assertIn(run(receipt=receipt)['verdict'], ('REPRODUCES', 'DOES_NOT_REPRODUCE', 'INCOMPLETE'))


class RealReferenceTests(unittest.TestCase):
    """The committed Helm 2.0 records at c8d5c430: small JSON blobs only, never a weights file."""

    @unittest.skipUnless(git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected_inventory.json'),
                         'reference commit not fetched')
    def test_reference_hash_from_git_with_the_job_binding(self):
        saved = reader.stop_unless
        reader.stop_unless = stop
        try:
            read = reader.git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL)
            reference, checkpoint = reader.reference_reading(read, lambda name: common.blob_id(
                common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name))
            # The same real records, read as if they were a NEW run's: they belong to Helm 2.0's job, so a stop.
            with self.assertRaisesRegex(Stopped, 'INVENTORY_IS_FOR_ANOTHER_JOB'):
                reader.bound_records(read, NEW_JOB)
        finally:
            reader.stop_unless = saved
        self.assertEqual(reference['final_pt_sha256'],
                         'c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb')
        self.assertEqual(len(reference['sources']), 3)
        self.assertEqual(reader.checkpoint_run_ids(checkpoint), (common.HELM2_JOB, common.HELM2_JOB))
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
# --check: the spend gate and the frozen-study check (review MINOR 1 part, MINOR 3).
# ---------------------------------------------------------------------------------------------------------------------
class SpendGateTests(unittest.TestCase):
    def test_measured_spend_plus_the_per_job_bound_must_fit_the_ceiling(self):
        self.assertEqual(common.spend_gate('45.00', stop)['after_this_job_at_most_usd'], '60.00')
        self.assertEqual(common.spend_gate('30', stop)['after_this_job_at_most_usd'], '45.00')
        self.assertEqual(common.spend_gate('0', stop)['spend_so_far_usd'], '0')
        with self.assertRaisesRegex(Stopped, 'SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING:60.01'):
            common.spend_gate('45.01', stop)
        for bad in (None, '', '-1', '1e3', 'NaN', 'inf', '12.345', ' 12', '12,00', '99999'):
            with self.assertRaisesRegex(Stopped, 'SPEND_FIGURE_FORM'):
                common.spend_gate(bad, stop)


ARCHIVE = common.ROOT / common.PACKAGE_REL / 'source.zip'


class CheckStudyTests(unittest.TestCase):
    """`check_study` on a synthetic frozen folder in a temporary directory. The ledger here is an empty temp file."""

    def setUp(self):
        self.saved = prepare.stop_unless
        prepare.stop_unless = stop
        self.scratch = tempfile.TemporaryDirectory()
        base = Path(self.scratch.name)
        self.output, self.ledger = base / 'frozen', base / 'ledger.json'
        self.ledger.write_bytes(b'')
        folder = self.output / '20260917'
        folder.mkdir(parents=True)
        self.plan = {'commit': common.PLAN_COMMIT, 'blob': common.PLAN_BLOB, 'sha256': common.PLAN_SHA256}
        job = common.job_name('20260925120000')
        owner = {'job': job, 'bounds': dict(common.EXPECTED_BOUNDS), 'plan_record': self.plan,
                 'reproduction_policy': dict(common.REPRODUCTION_POLICY)}
        request = dict(REQUEST, job=job)
        pins = {}
        for name, value in (('owner', owner), ('request', request)):
            raw = common.canonical(value)
            (folder / (name + '.json')).write_bytes(raw)
            pins[name] = common.pin(folder / (name + '.json'), raw)
        authority = {'job': job, 'owner_authorization_sha256': pins['owner']['sha256'], **common.HELM2_BINDINGS}
        raw = common.canonical(authority)
        (folder / 'authority.json').write_bytes(raw)
        pins['authority'] = common.pin(folder / 'authority.json', raw)
        argv = common.launch_argv(launcher=common.ROOT / common.LAUNCHER_REL, request=pins['request'],
                                  authority=pins['authority'], owner=pins['owner'], receipt_dir=common.RECEIPT_DIR,
                                  ledger=str(self.ledger))
        self.study = {'schema': prepare.STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN',
                      'source_sha': common.SOURCE_SHA, 'source_checkout': str(common.ROOT), 'plan_record': self.plan,
                      'reproduction_policy': dict(common.REPRODUCTION_POLICY), 'automatic_retries': 0,
                      'numeric_runs_completed': 0, 'canonical_ledger': str(self.ledger),
                      'package': {'archive_the_launcher_locates': str(ARCHIVE)},
                      'jobs': [{'job': job, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED,
                                'receipt_dir': str(common.RECEIPT_DIR), 'reduced_schedule': None, **pins,
                                'launch_argv': argv}]}

    def tearDown(self):
        prepare.stop_unless = self.saved
        self.scratch.cleanup()

    def check(self, study=None):
        return prepare.check_study(json.loads(json.dumps(study or self.study)), self.plan, output=self.output)

    @unittest.skipUnless(ARCHIVE.is_file(), 'package archive not in this checkout')
    def test_a_consistent_frozen_folder_passes(self):
        self.assertEqual(self.check()['job'], common.job_name('20260925120000'))

    @unittest.skipUnless(ARCHIVE.is_file(), 'package archive not in this checkout')
    def test_every_moved_piece_is_refused(self):
        def changed(path, value):
            study = json.loads(json.dumps(self.study))
            target = study
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return study
        cases = [(changed(('plan_record',), {'commit': HELD_COMMIT}), 'FROZEN_UNDER_A_DIFFERENT_PLAN'),
                 (changed(('reproduction_policy',), FIXED_POLICY), 'FROZEN_UNDER_A_DIFFERENT_REPRODUCTION_POLICY'),
                 (changed(('source_checkout',), 'C:/elsewhere'), 'NOT_THE_CHECKOUT_THE_RECORDS_WERE_WRITTEN_IN'),
                 (changed(('package', 'archive_the_launcher_locates'), str(self.ledger) + '.gone'),
                  'LOCATED_ARCHIVE_GONE'),
                 (changed(('package', 'archive_the_launcher_locates'), str(self.ledger)), 'LOCATED_ARCHIVE_CHANGED'),
                 (changed(('canonical_ledger',), str(self.ledger) + '.gone'), 'LAUNCH_ARGV'),
                 (changed(('jobs', 0, 'receipt_dir'), 'R'), 'STUDY_JOB'),
                 (changed(('jobs', 0, 'job'), common.HELM2_JOB), 'STUDY_JOB'),
                 (changed(('jobs', 0, 'launch_argv'), self.study['jobs'][0]['launch_argv'] + ['--reduced-schedule']),
                  'LAUNCH_ARGV')]
        for study, reason in cases:
            with self.assertRaisesRegex(Stopped, reason):
                self.check(study)
        (self.output / '20260917' / 'owner.json').write_bytes(b'{}\n')
        with self.assertRaisesRegex(Stopped, '^PIN:'):
            self.check()

    @unittest.skipUnless(ARCHIVE.is_file(), 'package archive not in this checkout')
    def test_a_missing_ledger_is_refused(self):
        self.ledger.unlink()
        with self.assertRaisesRegex(Stopped, 'CANONICAL_LEDGER_NOT_FOUND'):
            self.check()


# ---------------------------------------------------------------------------------------------------------------------
# Static: every launcher name the writer uses exists in the launcher sources (AST only; nothing is imported), and the
# gates run before the launcher is imported.
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


def function(path, name):
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def calls(node):
    """`[(line, name)]` of every call inside `node`, by the called name's last part."""
    out = []
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            func = item.func
            out.append((item.lineno, func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', None)))
    return sorted(out)


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

    def test_the_gates_run_before_the_launcher_is_imported(self):
        writer = HERE / 'prepare_unchanged_repro.py'
        order = [name for _, name in calls(function(writer, 'prepare'))]
        self.assertLess(order.index('gates'), order.index('load_launcher'))
        self.assertLess(order.index('check_repository'), order.index('gates'))
        gate = function(writer, 'gates')
        fetches = [item for item in ast.walk(gate) if isinstance(item, ast.Call)
                   and getattr(item.func, 'attr', None) == 'check_plan_is_current']
        self.assertEqual([(kw.arg, kw.value.value) for kw in fetches[0].keywords], [('fetch', True)])
        self.assertIn('check_policy_fixed', [name for _, name in calls(gate)])
        for name in ('check_before_launch', 'check_study', 'check_frozen_committed', 'check_pin'):
            node = function(writer, name)
            self.assertFalse(any(isinstance(item, ast.Name) and item.id in ('launch', 'load_launcher')
                                 for item in ast.walk(node)), name)
        self.assertIn('gates', [name for _, name in calls(function(writer, 'check_before_launch'))])

    def test_the_reader_checks_the_policy_first(self):
        path = HERE / 'read_reproduction.py'
        for name in ('reading', 'main'):
            first = [item for item in function(path, name).body if not isinstance(item, ast.Expr)
                     or not isinstance(item.value, ast.Constant)]
            if name == 'main':
                first = [item for item in first if not (isinstance(item, ast.Assign) or (
                    isinstance(item, ast.Expr) and getattr(item.value.func, 'attr', None) == 'add_argument'))]
            self.assertEqual(getattr(first[0].value.func, 'attr', None), 'check_policy_fixed', name)

    def test_this_folder_s_files_are_ascii_and_lf(self):
        for path in list(HERE.glob('*.py')) + list(HERE.glob('*.md')):
            raw = path.read_bytes()
            self.assertNotIn(b'\r', raw, path.name)
            self.assertTrue(raw.isascii(), path.name)


if __name__ == '__main__':
    unittest.main()
