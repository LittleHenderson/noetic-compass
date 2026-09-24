"""Pure-Python tests for the unchanged-arm reproduction (revision 2, policy bc46b36e). No launcher, torch, network or AWS.

What is tested:
  * decide(): every one of the 32 combinations of evidence validity x file x learned state x output x continuation,
    plus non-boolean inputs (fail closed), and that it reads nothing but its arguments;
  * the label set: the exact spellings of REPRODUCTION_POLICY.json / .md, and the level labels;
  * the pins: every policy file at bc46b36e (blob, sha256, size), LAUNCH_REQUEST's own pins, the reader rule against the
    policy, the panel manifest (file bytes, 564 record ids, rebuilt from git), the numerical environment, the reader's
    own source digest, and the classification of every checkpoint field;
  * owner_authorization and execution_admission as explicit states, including refusal of prose-only approval and of
    approval words placed in a state field; the preparation-only path (dry run) needing neither;
  * the reader over synthetic evidence: every valid-mismatch kind reads DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY,
    every invalid kind reads ADMISSION_INVALID_STOP, equal state with a different envelope reads
    STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED, and file / continuation differences never decide;
  * the receipt bindings (job, three records, contradiction, weights cross-check) now as named invalid reasons;
  * the recompute module's pure helpers, and that it stops with GPU_REQUIRED on this laptop BEFORE importing torch;
  * the tree / untracked rules, the atomic writer, the record builders, the spend gate and --check's study check;
  * statically (AST): launcher names exist, the gates run before the launcher, no prose status parser remains.

Run:  python -B test_unchanged_repro.py -v      (from the worktree root, with the full path)
LABEL. CLAUDE_BUILT_CLAUDE_CHECKED.
"""
import ast
from copy import deepcopy
from hashlib import sha256
import io
from itertools import product
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402
import read_reproduction as reader  # noqa: E402
import prepare_unchanged_repro as prepare  # noqa: E402  (imports no launcher at module level)
import recompute_reproduction_evidence as recompute  # noqa: E402  (imports no torch at module level)

P = common.GIT_PREFIX
REPRODUCED, DOES_NOT_REPRODUCE, INVALID = common.REPRODUCED, common.DOES_NOT_REPRODUCE, common.INVALID_STOP


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


def enc(value):
    return json.dumps(value).encode('utf-8')


POLICY_PRESENT = git_has(common.POLICY_COMMIT, common.POLICY_FILES['reproduction_policy_json'][0])
OWNER_PRESENT = all(git_has(commit, relative) for commit, relative, _, _ in common.OWNER_RECORDS.values())


def policy_json(name):
    return json.loads(common.show(common.POLICY_COMMIT, common.POLICY_FILES[name][0]))


# =====================================================================================================================
# decide() and the labels.
# =====================================================================================================================
class DecideTests(unittest.TestCase):
    def test_every_combination_of_validity_and_the_four_levels(self):
        seen = 0
        for valid, file_, state, output, continuation in product((True, False), repeat=5):
            verdict = reader.decide(valid, file_, state, output, continuation)
            if not valid:
                expected = INVALID
            elif state and output:
                expected = REPRODUCED
            else:
                expected = DOES_NOT_REPRODUCE
            self.assertEqual(verdict, expected, (valid, file_, state, output, continuation))
            seen += 1
        self.assertEqual(seen, 32)

    def test_file_and_continuation_never_decide(self):
        for valid, state, output in product((True, False), repeat=3):
            verdicts = {reader.decide(valid, file_, state, output, continuation)
                        for file_, continuation in product((True, False), repeat=2)}
            self.assertEqual(len(verdicts), 1, (valid, state, output))

    def test_output_never_overrides_state_and_state_never_overrides_output(self):
        self.assertEqual(reader.decide(True, True, False, True, True), DOES_NOT_REPRODUCE)
        self.assertEqual(reader.decide(True, True, True, False, True), DOES_NOT_REPRODUCE)

    def test_non_boolean_inputs_fail_closed(self):
        for bad in (None, 1, 0, 'True', 'yes', [True]):
            self.assertEqual(reader.decide(bad, True, True, True, True), INVALID, bad)
            for position in range(4):
                flags = [True, True, True, True]
                flags[position] = bad
                self.assertEqual(reader.decide(True, *flags), INVALID, (bad, position))

    def test_decide_reads_nothing_but_its_arguments(self):
        node = function(HERE / 'read_reproduction.py', 'decide')
        arguments = {arg.arg for arg in node.args.args}
        names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
        self.assertLessEqual(names - arguments, {'INVALID_STOP', 'REPRODUCED', 'DOES_NOT_REPRODUCE', 'any', 'type',
                                                 'bool', 'flag'})
        self.assertFalse([item for item in ast.walk(node) if isinstance(item, ast.Attribute)])

    def test_level_labels(self):
        self.assertEqual(common.level_labels({'file': True, 'learned_state': False, 'output': None}),
                         {'file': 'FILE_IDENTICAL', 'learned_state': 'LEARNED_STATE_DIFFERENT',
                          'output': common.LEVEL_NOT_ESTABLISHED, 'continuation': common.LEVEL_NOT_ESTABLISHED})
        self.assertEqual(common.level_label('continuation', False), 'CONTINUATION_DIFFERENT')
        self.assertEqual(common.level_label('output', 1), common.LEVEL_NOT_ESTABLISHED)      # 1 is not True
        self.assertEqual(set(reader.NEXT_STEP), set(common.VERDICTS))
        self.assertIn(common.COMPARISON_INCOMPLETE, reader.NEXT_STEP[DOES_NOT_REPRODUCE])

    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_labels_are_the_policy_spellings(self):
        policy = policy_json('reproduction_policy_json')
        self.assertEqual(policy['missing_or_invalid_evidence'], INVALID)
        self.assertEqual(policy['valid_state_or_output_mismatch'], DOES_NOT_REPRODUCE)
        text = common.show(common.POLICY_COMMIT, common.POLICY_FILES['reproduction_policy_md'][0]).decode('utf-8')
        for word in (REPRODUCED, DOES_NOT_REPRODUCE, INVALID, common.COMPARISON_INCOMPLETE,
                     *[label for pair in common.LEVEL_LABELS.values() for label in pair]):
            self.assertIn(word, text, word)


# =====================================================================================================================
# Pins: policy, panel, environment, sources, checkpoint field classes.
# =====================================================================================================================
class PolicyPinTests(unittest.TestCase):
    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_every_pinned_policy_file_is_the_committed_one_and_conformed(self):
        files = common.read_policy_files(stop)
        self.assertEqual(set(files), set(common.POLICY_FILES))
        self.assertEqual(common.policy_conformance(json.loads(files['reproduction_policy_json'])), [])
        self.assertEqual(common.launch_request_violations(json.loads(files['launch_request'])), [])

    def test_conformance_names_every_changed_deciding_field(self):
        good = dict(common.READER_RULE)
        self.assertEqual(common.policy_conformance(good), [])
        for key, value in common.READER_RULE.items():
            changed = dict(good)
            changed[key] = [value] if not isinstance(value, list) else value[:-1]
            self.assertEqual(common.policy_conformance(changed), ['POLICY_FIELD:' + key])
            missing = {name: item for name, item in good.items() if name != key}
            self.assertEqual(common.policy_conformance(missing), ['POLICY_FIELD:' + key])
        self.assertEqual(common.policy_conformance(dict(good, learned_state_tolerance=0.0)),
                         ['POLICY_FIELD:learned_state_tolerance'])            # 0.0 is not the integer 0
        self.assertEqual(common.policy_conformance(None), ['POLICY_NOT_AN_OBJECT'])

    def test_launch_request_must_pin_the_same_hashes(self):
        request = {'policy_file_sha256': {label: common.POLICY_FILES[name][2]
                                          for label, name in common.LAUNCH_REQUEST_POLICY_NAMES.items()},
                   'preparation_document_sha256': {label: common.POLICY_FILES[name][2]
                                                   for label, name in common.LAUNCH_REQUEST_DOCUMENT_NAMES.items()}}
        request['policy_file_sha256'].update({'OWNER_STANDING_AUTHORIZATION_20260924.json':
                                              common.OWNER_RECORDS['codex_standing_json'][3],
                                              'OWNER_STANDING_AUTHORIZATION_20260924.md':
                                              common.OWNER_RECORDS['codex_standing_md'][3]})
        self.assertEqual(common.launch_request_violations(request), [])
        moved = deepcopy(request)
        moved['policy_file_sha256']['REPRODUCTION_POLICY.json'] = '0' * 64
        self.assertEqual(common.launch_request_violations(moved), ['LAUNCH_REQUEST_POLICY_PIN:REPRODUCTION_POLICY.json'])

    def test_policy_tip_currency(self):
        tip = {'commit': 'f' * 40, 'blobs': {name: pin[1] for name, pin in common.POLICY_FILES.items()},
               'pinned_commit_is_ancestor': True}
        self.assertEqual(common.policy_tip_violations(tip), [])
        moved = deepcopy(tip)
        moved['blobs']['plan'] = '3172a221f3a12448029b995e87009284fcce453c'
        self.assertEqual(common.policy_tip_violations(moved),
                         ['MOVED_AT_TIP:plan:3172a221f3a12448029b995e87009284fcce453c'])
        self.assertEqual(common.policy_tip_violations(dict(tip, pinned_commit_is_ancestor=False)),
                         ['PINNED_COMMIT_NOT_IN_TIP'])
        self.assertTrue(common.policy_tip_violations({'commit': None})[0].startswith('POLICY_TRACKING_REF_MISSING'))

    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_a_moved_tip_stops_only_the_admitted_paths(self):
        saved = common.read_policy_tip
        moved = {'ref': common.POLICY_TRACKING_REF, 'commit': 'f' * 40, 'pinned_commit_is_ancestor': True,
                 'blobs': dict({name: pin[1] for name, pin in common.POLICY_FILES.items()}, launch_request='5' * 40)}
        try:
            common.read_policy_tip = lambda stop_, *, fetch: moved
            report = common.check_policy(stop, fetch=False, require_current=False)
            self.assertEqual(report['tip']['violations'], ['MOVED_AT_TIP:launch_request:' + '5' * 40])
            with self.assertRaisesRegex(Stopped, '^POLICY_OR_PLAN_MOVED:MOVED_AT_TIP:launch_request'):
                common.check_policy(stop, fetch=False, require_current=True)
        finally:
            common.read_policy_tip = saved

    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_the_pinned_policy_is_not_frozen_so_admission_cannot_pass_today(self):
        violations = common.policy_freeze_violations(
            policy_json('reproduction_policy_json'), policy_json('execution_manifest'), policy_json('launch_request'),
            common.expected_admission_bindings(), {})
        for reason in ('POLICY_PANEL_MANIFEST_NOT_FROZEN_TO_THIS_PANEL', 'POLICY_READER_SOURCE_NOT_FROZEN_TO_THIS_READER',
                       'POLICY_READER_ACCEPTANCE_RECEIPT_NOT_FROZEN', 'POLICY_MAIN_LAUNCH_READY_IS_NOT_TRUE',
                       'MANIFEST_LAUNCH_PACKET_NOT_FROZEN', 'MANIFEST_LAUNCH_ENABLED_IS_NOT_TRUE',
                       'LAUNCH_REQUEST_LAUNCH_ENABLED_IS_NOT_TRUE'):
            self.assertIn(reason, violations)

    def test_no_prose_status_parser_remains(self):
        for name in ('plan_status_tokens', 'plan_status_approved', 'PLAN_STATUS_REFUSING_PARTS',
                     'PLAN_STATUS_APPROVED', 'check_plan_is_current', 'REPRODUCTION_POLICY'):
            self.assertFalse(hasattr(common, name), name)
        for path in HERE.glob('*.py'):
            if path.name != Path(__file__).name:
                self.assertNotIn('APPROVED_FOR_LAUNCH', path.read_text(encoding='utf-8'), path.name)


class PanelAndEnvironmentPinTests(unittest.TestCase):
    def test_the_panel_manifest_file_is_the_pinned_one(self):
        raw = (HERE / common.PANEL_MANIFEST_NAME).read_bytes()
        self.assertEqual(common.panel_manifest_violations(raw), [])
        manifest = common.load_panel_manifest(stop, raw)
        self.assertEqual(len(manifest['record_ids']), common.PANEL_RECORD_COUNT)
        self.assertEqual(manifest['registered_expected_refusals'], [])
        self.assertIs(manifest['hset2_material_used'], False)
        self.assertEqual(sum(1 for row in manifest['rows'] if row['grader_correct']), 495)
        self.assertEqual(manifest['split_counts_per_reference_worker_report'],
                         {'held_back': 127, 'trained': 358, 'excluded': 79})
        self.assertEqual(manifest['inputs']['course']['sha256'],
                         'cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987')
        self.assertTrue(all(set(common.PANEL_DECIDING_FIELDS) <= set(row) for row in manifest['rows']))

    def test_a_tampered_panel_manifest_is_refused(self):
        raw = (HERE / common.PANEL_MANIFEST_NAME).read_bytes()
        self.assertTrue(common.panel_manifest_violations(raw + b' ')[0].startswith('PANEL_MANIFEST_SHA256'))
        manifest = json.loads(raw)
        manifest['record_ids'] = manifest['record_ids'][1:] + manifest['record_ids'][:1]
        self.assertIn('PANEL_RECORD_IDS', common.panel_manifest_violations(enc(manifest)))
        with self.assertRaisesRegex(Stopped, 'PANEL_MANIFEST_IS_NOT_THE_PINNED_ONE'):
            common.load_panel_manifest(stop, enc(manifest))
        self.assertEqual(common.panel_manifest_violations(None), ['PANEL_MANIFEST_ABSENT'])

    @unittest.skipUnless(git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL
                                 + '/collected/results/artifacts/course_p10_predictions.json'),
                         'reference commit c8d5c430 not fetched')
    def test_the_panel_manifest_rebuilds_byte_for_byte_from_git(self):
        import build_panel_manifest
        self.assertEqual(build_panel_manifest.encode(build_panel_manifest.build()),
                         (HERE / common.PANEL_MANIFEST_NAME).read_bytes())

    def test_numerical_environment_pin(self):
        pinned = dict(common.NUMERICAL_ENVIRONMENT)
        self.assertEqual(common.environment_violations(pinned), [])
        self.assertEqual(common.environment_violations(dict(pinned, gpu_name='Tesla T4')), ['gpu_name'])
        self.assertEqual(common.environment_violations(dict(pinned, deterministic_algorithms=1)),
                         ['deterministic_algorithms'])
        self.assertEqual(common.environment_violations({key: value for key, value in pinned.items()
                                                        if key != 'torch_version'}), ['torch_version'])
        self.assertEqual(len(common.environment_violations(None)), len(pinned))
        self.assertEqual(pinned['torch_version'], '2.11.0+cu128')
        self.assertEqual(pinned['gpu_name'], 'NVIDIA RTX PRO 4500 Blackwell Server Edition')

    def test_reader_source_digest(self):
        hashes = common.source_hashes()
        self.assertEqual(set(hashes), set(common.READER_SOURCE_FILES))
        self.assertEqual(common.reader_source_digest(hashes), common.reader_source_digest(dict(hashes)))
        self.assertNotEqual(common.reader_source_digest(hashes),
                            common.reader_source_digest(dict(hashes, **{'repro_common.py': '0' * 64})))
        bindings = common.expected_admission_bindings(hashes)
        self.assertEqual(bindings['reader_source_sha256'], common.reader_source_digest(hashes))
        self.assertEqual(bindings['panel_manifest_sha256'], common.PANEL_MANIFEST_SHA256)
        self.assertEqual(bindings['policy_files_sha256']['plan'], common.POLICY_FILES['plan'][2])

    def test_every_checkpoint_field_is_in_exactly_one_class(self):
        metadata = (common.PREDICTIVE_METADATA + common.CONTINUATION_METADATA + common.ENVELOPE_METADATA
                    + common.PRODUCER_IDENTITY_FIELDS + ('run_identity', 'init_args'))
        self.assertEqual(sorted(metadata), sorted(common.METADATA_FIELDS))
        identity = (common.PREDICTIVE_RUN_IDENTITY + common.TRAINING_RUN_IDENTITY + common.CONTINUATION_RUN_IDENTITY
                    + common.ENVELOPE_RUN_IDENTITY + ('context',))
        self.assertEqual(sorted(identity), sorted(common.RUN_IDENTITY_FIELDS))
        self.assertEqual(sorted(common.TRAINING_INIT_ARGS + common.ENVELOPE_INIT_ARGS + ('run_context',)),
                         sorted(common.INIT_ARGS_FIELDS))
        self.assertEqual(sorted(common.TRAINING_CONTEXT + ('run_id',)), sorted(common.CONTEXT_FIELDS))


# =====================================================================================================================
# State 1: owner authorization.
# =====================================================================================================================
def real_owner_records():
    return common.read_owner_records()


def synthetic_owner(json_changes=None, claude_text=None):
    """Owner records built in memory, with OWNER_RECORDS pins swapped to match them (restored by the caller)."""
    body = {'schema': 'helm.owner-standing-authorization/1', 'status': common.OWNER_AUTHORIZED,
            'owner_instruction_verbatim': common.OWNER_QUOTES['standing_authorization'][0],
            'further_owner_approval_required_for_in_scope_work': False, 'study_option': 'C',
            'study_actual_spend_ceiling_usd': 60, 'execution_owner': 'Claude', **(json_changes or {})}
    raws = {'codex_standing_json': enc(body), 'codex_standing_md': b'# record\n',
            'claude_extension_md': (claude_text if claude_text is not None
                                    else '> ' + common.OWNER_QUOTES['extends_to_claude_as_runner'][0] + '\n'
                                    ).encode('utf-8')}
    pins = {name: (commit, relative, common.git_object_id(raws[name]), digest(raws[name]))
            for name, (commit, relative, _, _) in common.OWNER_RECORDS.items()}
    return {name: {'blob': common.git_object_id(raw), 'raw': raw} for name, raw in raws.items()}, pins


class OwnerAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(common.OWNER_RECORDS)

    def tearDown(self):
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(self.saved)

    def evaluate(self, **options):
        records, pins = synthetic_owner(**options)
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(pins)
        return common.owner_authorization_state(records)

    @unittest.skipUnless(OWNER_PRESENT, 'owner record commits not fetched')
    def test_the_real_recorded_owner_files_give_standing_authorization(self):
        state = common.owner_authorization_state(real_owner_records())
        self.assertEqual((state['state'], state['reasons']), (common.OWNER_AUTHORIZED, []))
        self.assertEqual(state['records']['claude_extension_md']['blob'], 'f707ce455c08e51c5ce18ae5114a7d5b530a9f82')

    def test_machine_fields_decide_not_prose(self):
        self.assertEqual(self.evaluate()['state'], common.OWNER_AUTHORIZED)
        for field, value in (('status', 'APPROVED_FOR_LAUNCH'), ('status', 'standing_project_authorization'),
                             ('further_owner_approval_required_for_in_scope_work', 0),
                             ('study_actual_spend_ceiling_usd', 60.0), ('execution_owner', 'Codex'),
                             ('owner_instruction_verbatim', 'I approve.')):
            state = self.evaluate(json_changes={field: value})
            self.assertEqual(state['state'], common.OWNER_NOT_ESTABLISHED, field)
            self.assertIn('OWNER_JSON_FIELD:' + field, state['reasons'])

    def test_prose_only_approval_is_refused(self):
        records, pins = synthetic_owner()
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(pins)
        prose = b'**Status.** `APPROVED_FOR_LAUNCH`. The owner approved everything; STANDING_PROJECT_AUTHORIZATION.\n'
        records['codex_standing_json'] = {'blob': common.git_object_id(prose), 'raw': prose}
        state = common.owner_authorization_state(records)
        self.assertEqual(state['state'], common.OWNER_NOT_ESTABLISHED)
        self.assertIn('OWNER_RECORD_BLOB:codex_standing_json', state['reasons'])
        self.assertIn('OWNER_JSON_UNREADABLE', state['reasons'])

    def test_blob_binding_missing_records_and_the_extension_quote(self):
        records, pins = synthetic_owner()
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(pins)
        records['codex_standing_md'] = {'blob': '0' * 40, 'raw': b'# record\n'}
        self.assertIn('OWNER_RECORD_BLOB:codex_standing_md', common.owner_authorization_state(records)['reasons'])
        records.pop('claude_extension_md')
        self.assertIn('OWNER_RECORD_MISSING:claude_extension_md', common.owner_authorization_state(records)['reasons'])
        self.assertIn('OWNER_EXTENSION_QUOTE_NOT_EXACTLY_ONCE',
                      self.evaluate(claude_text='approved, yes it extends')['reasons'])
        self.assertEqual(common.owner_authorization_state(None)['state'], common.OWNER_NOT_ESTABLISHED)


# =====================================================================================================================
# State 2: execution admission.
# =====================================================================================================================
FAKE_SOURCES = {name: (str(index) * 64)[:64] for index, name in enumerate(common.READER_SOURCE_FILES, start=1)}
RECEIPT = 'a1' * 32
PACKET = 'b2' * 32


def admitted_record(job, **changes):
    record = {'schema': common.ADMISSION_SCHEMA, 'label': common.LABEL, 'state': common.ADMITTED,
              'job_kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED, 'source_sha': common.SOURCE_SHA,
              'job': job, 'owner_authorization': {'state': common.OWNER_AUTHORIZED,
                                                  'records': {name: pin[2]
                                                              for name, pin in common.OWNER_RECORDS.items()}},
              'bindings': common.expected_admission_bindings(FAKE_SOURCES),
              'prerequisites': {name: {'status': 'PASS', 'receipt_sha256': (RECEIPT if name == 'reader_acceptance_on_aws_p1'
                                                                            else PACKET if name == 'final_launch_packet_frozen'
                                                                            else 'c3' * 32)}
                                for name in common.REQUIRED_PREREQUISITES},
              'admitted_by': 'Claude technical admission under standing project authorization',
              'admitted_utc': '2026-09-25T10:00:00Z', 'note': 'synthetic'}
    record.update(changes)
    return record


def frozen_policy():
    return ({'output_panel_manifest_sha256': common.PANEL_MANIFEST_SHA256,
             'reader_source_sha256': common.reader_source_digest(FAKE_SOURCES),
             'reader_acceptance_receipt_sha256': RECEIPT, 'main_launch_ready': True},
            {'launch_enabled': True, 'final_freeze': {'frozen_launch_packet_sha256': PACKET}},
            {'launch_enabled': True})


NEW_JOB = common.job_name('20260925120000')


def admission(record, *, owner=common.OWNER_AUTHORIZED, committed=True, job=NEW_JOB, raw=None, freeze=None):
    policy, manifest, launch_request = freeze or frozen_policy()
    return common.execution_admission_state(
        enc(record) if raw is None else raw, expected_bindings=common.expected_admission_bindings(FAKE_SOURCES),
        owner_state={'state': owner}, policy=policy, manifest=manifest, launch_request=launch_request,
        committed=committed, job=job)


class ExecutionAdmissionTests(unittest.TestCase):
    def test_a_complete_bound_admission_is_admitted(self):
        state = admission(admitted_record(NEW_JOB))
        self.assertEqual((state['state'], state['reasons']), (common.ADMITTED, []))
        self.assertEqual(state['job'], NEW_JOB)

    def test_approval_words_in_the_state_field_are_refused(self):
        for word in ('APPROVED_FOR_LAUNCH', 'APPROVED', 'admitted', 'ADMITTED ', 'YES', True, None):
            state = admission(admitted_record(NEW_JOB, state=word))
            self.assertEqual(state['state'], common.NOT_READY, word)
            self.assertTrue(any(reason.startswith('ADMISSION_STATE_UNKNOWN') for reason in state['reasons']), word)
        self.assertIn('ADMISSION_STATE_IS:NOT_READY',
                      admission(admitted_record(NEW_JOB, state=common.NOT_READY))['reasons'])

    def test_a_prose_approval_file_is_not_an_admission(self):
        prose = b'Execution admission: APPROVED_FOR_LAUNCH. State ADMITTED. The owner said yes to everything.\n'
        state = admission(None, raw=prose)
        self.assertEqual((state['state'], state['reasons']), (common.NOT_READY, ['ADMISSION_RECORD_ABSENT_OR_NOT_JSON']))
        self.assertEqual(admission(None, raw=None)['state'], common.NOT_READY)

    def test_every_binding_is_exact(self):
        for key in common.expected_admission_bindings(FAKE_SOURCES):
            record = admitted_record(NEW_JOB)
            record['bindings'][key] = 'changed'
            state = admission(record)
            self.assertEqual(state['state'], common.NOT_READY, key)
            self.assertIn('ADMISSION_BINDING:' + key, state['reasons'])
        record = admitted_record(NEW_JOB)
        record['bindings']['extra'] = 1
        self.assertIn('ADMISSION_BINDING:extra', admission(record)['reasons'])

    def test_job_owner_prerequisites_commit_and_freeze(self):
        cases = [
            (admitted_record(common.job_name('20260925120001')), {}, 'ADMISSION_IS_FOR_ANOTHER_JOB'),
            (admitted_record(common.HELM2_JOB), {}, 'ADMISSION_JOB_NAME'),
            (admitted_record(NEW_JOB, model_seed=20260918), {}, 'ADMISSION_IS_FOR_ANOTHER_JOB_KIND'),
            (admitted_record(NEW_JOB), {'owner': common.OWNER_NOT_ESTABLISHED}, 'OWNER_AUTHORIZATION_NOT_ESTABLISHED_NOW'),
            (admitted_record(NEW_JOB, owner_authorization={'state': 'APPROVED'}), {},
             'ADMISSION_OWNER_AUTHORIZATION_BINDING'),
            (admitted_record(NEW_JOB), {'committed': False}, 'ADMISSION_RECORD_NOT_COMMITTED_AS_IS'),
            (admitted_record(NEW_JOB, admitted_utc='yesterday'), {}, 'ADMISSION_ADMITTED_BY_OR_TIME'),
            (admitted_record(NEW_JOB, extra_field=1), {}, 'ADMISSION_FIELDS'),
        ]
        for record, options, reason in cases:
            state = admission(record, **options)
            self.assertEqual(state['state'], common.NOT_READY, reason)
            self.assertTrue(any(item.startswith(reason) for item in state['reasons']), (reason, state['reasons']))
        record = admitted_record(NEW_JOB)
        record['prerequisites']['fresh_review_of_this_revision'] = {'status': 'PASS', 'receipt_sha256': None}
        self.assertIn('PREREQUISITE_NOT_PASSED:fresh_review_of_this_revision', admission(record)['reasons'])
        record = admitted_record(NEW_JOB)
        record['prerequisites']['budget_headroom_verified'] = {'status': 'APPROVED', 'receipt_sha256': 'c3' * 32}
        self.assertIn('PREREQUISITE_NOT_PASSED:budget_headroom_verified', admission(record)['reasons'])
        policy, manifest, launch_request = frozen_policy()
        state = admission(admitted_record(NEW_JOB), freeze=(dict(policy, reader_source_sha256=None), manifest,
                                                             dict(launch_request, launch_enabled='true')))
        self.assertIn('POLICY_READER_SOURCE_NOT_FROZEN_TO_THIS_READER', state['reasons'])
        self.assertIn('LAUNCH_REQUEST_LAUNCH_ENABLED_IS_NOT_TRUE', state['reasons'])

    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_the_shipped_admission_record_is_not_ready_and_bound_to_this_revision(self):
        raw = common.ADMISSION_PATH.read_bytes()
        record = json.loads(raw)
        self.assertEqual(record['state'], common.NOT_READY)
        self.assertIsNone(record['job'])
        self.assertEqual(record['bindings'], common.expected_admission_bindings())
        self.assertEqual(record['owner_authorization']['state'], common.OWNER_AUTHORIZED)
        state = common.execution_admission_state(
            raw, expected_bindings=common.expected_admission_bindings(), owner_state={'state': common.OWNER_AUTHORIZED},
            policy=policy_json('reproduction_policy_json'), manifest=policy_json('execution_manifest'),
            launch_request=policy_json('launch_request'), committed=True)
        self.assertEqual(state['state'], common.NOT_READY)
        for name in common.REQUIRED_PREREQUISITES:
            self.assertIn('PREREQUISITE_NOT_PASSED:' + name, state['reasons'])
        self.assertIn('ADMISSION_STATE_IS:NOT_READY', state['reasons'])


# =====================================================================================================================
# The preparation-only path: the dry run needs neither state; --write and --check need both.
# =====================================================================================================================
class PreparationOnlyPathTests(unittest.TestCase):
    def setUp(self):
        self.saved = (common.check_policy, common.read_owner_records, common.read_execution_admission,
                      prepare.stop_unless, dict(common.OWNER_RECORDS))
        records, pins = synthetic_owner()
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(pins)
        common.check_policy = lambda stop_, *, fetch=True, require_current=True: {
            'policy': {}, 'manifest': {}, 'launch_request': {}, 'pointers': {},
            'tip': {'ref': 'r', 'commit': 'c', 'violations': []}}
        common.read_owner_records = lambda: records
        common.read_execution_admission = lambda: (None, False)
        prepare.stop_unless = stop

    def tearDown(self):
        (common.check_policy, common.read_owner_records, common.read_execution_admission, prepare.stop_unless,
         owner_records) = self.saved
        common.OWNER_RECORDS.clear()
        common.OWNER_RECORDS.update(owner_records)

    def test_the_dry_run_gates_need_no_approval_and_report_both_states(self):
        gate = prepare.gates(fetch=False, require_admitted=False)
        summary = prepare.admission_summary(gate)
        self.assertEqual(summary['owner_authorization'], common.OWNER_AUTHORIZED)
        self.assertEqual(summary['execution_admission'], common.NOT_READY)

    def test_write_and_check_refuse_without_an_admitted_record(self):
        with self.assertRaisesRegex(Stopped, '^EXECUTION_ADMISSION_IS_NOT_ADMITTED:ADMISSION_RECORD_ABSENT'):
            prepare.gates(fetch=False, require_admitted=True)
        common.read_execution_admission = lambda: (b'APPROVED_FOR_LAUNCH\n', True)
        with self.assertRaisesRegex(Stopped, 'EXECUTION_ADMISSION_IS_NOT_ADMITTED'):
            prepare.gates(fetch=False, require_admitted=True)
        common.read_owner_records = lambda: {}
        with self.assertRaisesRegex(Stopped, '^OWNER_AUTHORIZATION_NOT_ESTABLISHED'):
            prepare.gates(fetch=False, require_admitted=True)

    def test_print_admission_bindings_is_read_only_and_needs_no_approval(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(prepare.main(['--print-admission-bindings']), 0)
        printed = json.loads(out.getvalue())
        self.assertEqual(printed['path'], prepare.PREPARATION_ONLY)
        self.assertEqual(printed['bindings'], common.expected_admission_bindings())

    def test_the_writer_wires_the_states_to_the_modes(self):
        writer = HERE / 'prepare_unchanged_repro.py'
        calls_in_prepare = [item for item in ast.walk(function(writer, 'prepare')) if isinstance(item, ast.Call)
                            and getattr(item.func, 'id', None) == 'gates']
        self.assertEqual([(kw.arg, getattr(kw.value, 'id', None)) for kw in calls_in_prepare[0].keywords
                          if kw.arg == 'require_admitted'], [('require_admitted', 'write')])
        in_check = [item for item in ast.walk(function(writer, 'check_before_launch')) if isinstance(item, ast.Call)
                    and getattr(item.func, 'id', None) == 'gates']
        self.assertEqual([getattr(kw.value, 'value', None) for kw in in_check[0].keywords
                          if kw.arg == 'require_admitted'], [True])
        stamp_source = ast.unparse(function(writer, 'prepare'))
        self.assertIn("stamp_of(gate['execution_admission']['job'])", stamp_source)

    def test_the_owner_record_quotes_the_owner_and_inserts_no_approval_word(self):
        owner = common.owner_authorization_state(common.read_owner_records())
        record = common.owner_record(schema='S', candidate='C', job=NEW_JOB, condition=common.HELM2_CONDITION,
                                     bounds=dict(common.EXPECTED_BOUNDS), owner_state=owner,
                                     admission={'state': common.NOT_READY, 'record_sha256': None, 'job': None})
        self.assertEqual(record['owner_instruction_raw'], common.OWNER_QUOTES['standing_authorization'][0])
        self.assertIs(record['approval_words_inserted_by_builder'], False)
        self.assertIs(record['is_owner_signature'], False)
        self.assertEqual(record['reading_rule'], common.reading_rule_record())
        self.assertTrue(common.canonical(record).isascii())


# =====================================================================================================================
# The reader over synthetic evidence (valid mismatches, invalid evidence, envelope-only differences).
# =====================================================================================================================
class T:
    """A fake tensor: the recompute module's walk takes `is_tensor` and `tensor_row` as arguments."""

    def __init__(self, *values, dtype='torch.float32', offset=0):
        self.values, self.dtype, self.offset = values, dtype, offset


def fake_row(path, tensor):
    return {'path': path, 'kind': 'tensor', 'dtype': tensor.dtype, 'shape': [len(tensor.values)],
            'layout': 'torch.strided', 'numel': len(tensor.values),
            'envelope': {'stride': [1], 'storage_offset': tensor.offset, 'device': 'cpu', 'is_contiguous': True},
            'sha256': digest(repr((tensor.dtype, tensor.values)).encode())}


def is_fake(value):
    return isinstance(value, T)


IDS = ['typed-input-a', 'typed-input-b', 'typed-input-c']
ANSWERS = [{'kind': 'reach', 'value': 'VIA_n1'}, {'kind': 'parts', 'value': ['n0', 'n2']}, {'kind': 'analogy',
                                                                                           'value': 'W2'}]
DECISIONS = [{'selected': {'s1': 'VIA_n1'}}, {'selected': {'s2': 'PRESENT'}}, {'selected': {'s3': 'W2'}}]
CORRECT = [True, False, True]
MANIFEST = {'record_ids': IDS, 'rows': [
    {'record_id': rid, 'status': 'ANSWERED', 'answer_sha256': common.value_digest(ANSWERS[i]),
     'decisions_sha256': common.value_digest(DECISIONS[i]), 'grader_correct': CORRECT[i],
     'grader_check_sha256': common.value_digest({'correct': CORRECT[i], 'kind': ANSWERS[i]['kind']}),
     'scores_sha256': 'x', 'packet_digest': 'p', 'slot_plan_digest': 'q'} for i, rid in enumerate(IDS)]}
REF = common.REFERENCE_FINAL_PT_SHA256
REF_BYTES = common.REFERENCE_FINAL_PT_BYTES
OTHER = 'ab' * 32
THIRD = 'cd' * 32
RUNTIME = {key: common.NUMERICAL_ENVIRONMENT[key] for key in reader.RUNTIME_KEYS}


def meta(job, *, core_rounds=8, lr=0.003, cursor=1470, counters=1470, root=common.HISTORICAL_PACKAGE_ROOT,
         initial='i' * 64):
    elapsed = 7817.247307497 if job == common.HELM2_JOB else 7900.125
    context = {'run_id': job, 'course_sha256': 'c' * 64, 'condition': common.HELM2_CONDITION, 'source_seed': 101}
    optimizer = {'learning_rate': lr, 'weight_decay': 0.01, 'betas': [0.9, 0.999], 'eps': 1e-08}
    identity = {key: 'fixed:' + key for key in common.RUN_IDENTITY_FIELDS}
    identity.update(context=context, core_rounds=core_rounds, optimizer_config=optimizer,
                    limits={'max_updates': 1486, 'max_core_calls': 600000, 'max_wall_seconds': 12300},
                    initial_model_identity=initial)
    return {'run_identity': identity, 'run_identity_digest': common.value_digest([job, elapsed]),
            'model_revision': cursor, 'cursor': cursor, 'counters': {'optimizer_updates': counters},
            'elapsed_seconds': elapsed, 'training_mode': True, 'model_state_identity': 'm' * 64,
            'optimizer_state_identity': 'o' * 64, 'encoder_state_identity': 'e' * 64, 'rng_state_identity': 'r' * 64,
            'init_args': {'optimizer_config': dict(optimizer), 'run_context': dict(context),
                          'limits': dict(identity['limits']), 'device': 'cuda:0', 'python_seed': 20260917,
                          'root': root},
            'learnable_names': ['left.weight', 'round_rate']}


def parts(**changes):
    value = {'model_state': {'left.weight': T(1.0, 2.0), 'round_rate': T(0.5)},
             'encoder_state': {'schema': 'enc/1', 'readout': T(0.125, -0.125), 'tokenizer': {'tokens': ['a', 'b']}},
             'optimizer_state': {'state': {0: {'exp_avg': T(0.01), 'step': T(1470.0)}},
                                 'param_groups': [{'lr': 0.003, 'betas': (0.9, 0.999), 'params': [0, 1]}]},
             'rng_state': {'torch_cpu': T(7.0, dtype='torch.uint8'), 'torch_cuda': [T(9.0, dtype='torch.uint8')],
                           'python': (3, (1, 2, 3), None)}}
    for part, update in changes.items():
        value[part] = update(deepcopy(value[part]))
    return value


def panel(answers=ANSWERS, correct=CORRECT, refuse=()):
    rows = []
    for index, record_id in enumerate(IDS):
        if index in refuse:
            rows.append(recompute.panel_row(record_id, status='REFUSED', reason='TYPED_MATCHED:X', prediction=None,
                                            checked=None))
            continue
        prediction = {'record_id': record_id, 'answer': answers[index], 'decisions': DECISIONS[index],
                      'scores': {'s': [0.25 * index]}, 'packet_digest': 'p', 'slot_plan_digest': 'q'}
        checked = {'correct': correct[index], 'kind': answers[index]['kind'], 'record_id': record_id,
                   'prediction_id': 'typed-prediction-' + record_id}
        rows.append(recompute.panel_row(record_id, status='ANSWERED', reason=None, prediction=prediction,
                                        checked=checked))
    return rows


def side(job, sha, *, state=None, metadata=None, rows=None, restore='RESTORED', consistent=True, inference=None):
    state = parts() if state is None else state
    value = {'file': {'path': '/opt/in/' + sha[:8] + '.pt', 'sha256': sha, 'bytes': REF_BYTES},
             'payload_keys': list(common.PAYLOAD_KEYS), 'payload_schema': common.CHECKPOINT_SCHEMA,
             'metadata': meta(job) if metadata is None else metadata,
             'producer_identities_consistent': {key: consistent for key in ('model', 'optimizer', 'encoder', 'rng')},
             'restore': {'status': restore, 'reason': None if restore == 'RESTORED' else 'ValueError:LAYOUT',
                         'loader': recompute.LOADER},
             'state_dict_keys': sorted(state['model_state']), 'buffers': [],
             'inference_mode': dict(common.INFERENCE_MODE) if inference is None else inference,
             'panel': (panel() if rows is None else rows) if restore == 'RESTORED' else [],
             'panel_left_learned_state_unchanged': True}
    for part in common.STATE_PARTS:
        value[part] = recompute.walk_rows(state[part], is_fake, fake_row)
    return value


def evidence(reference=None, candidate=None, *, environment=None, reasons=(), sources=None, candidate_sha=OTHER,
             root=common.HISTORICAL_PACKAGE_ROOT, levels=None):
    reference = side(common.HELM2_JOB, REF) if reference is None else reference
    candidate = side(NEW_JOB, OTHER) if candidate is None else candidate
    document = recompute.assemble(
        'READING', environment=dict(common.NUMERICAL_ENVIRONMENT) if environment is None else environment,
        inputs={'package_root': root, 'reference': {'sha256': REF, 'bytes': REF_BYTES},
                'candidate': {'sha256': candidate_sha, 'bytes': REF_BYTES}},
        sides={'reference': reference, 'candidate': candidate}, producer_reasons=list(reasons), manifest=MANIFEST,
        sources=FAKE_SOURCES if sources is None else sources)
    if levels is not None:
        document['producer_levels'] = levels
    return json.loads(recompute.encode(document))


def verdict_of(document, *, job=NEW_JOB, sha=OTHER, reference_record=None, candidate_record=None):
    evaluated = reader.evaluate_evidence(document, MANIFEST, expected_candidate_job=job, expected_candidate_sha256=sha,
                                         admitted_sources=FAKE_SOURCES, reference_record_metadata=reference_record,
                                         candidate_record_metadata=candidate_record)
    levels = evaluated['levels']
    return (reader.decide(not evaluated['invalid_reasons'], levels['file'], levels['learned_state'], levels['output'],
                          levels['continuation']), common.level_labels(levels), evaluated)


class EvidenceVerdictTests(unittest.TestCase):
    def assertVerdict(self, document, expected, levels=None, reason=None, **options):
        verdict, labels, evaluated = verdict_of(document, **options)
        self.assertEqual(verdict, expected, evaluated['invalid_reasons'])
        for level, label in (levels or {}).items():
            self.assertEqual(labels[level], label, level)
        if reason is not None:
            self.assertTrue(any(item.startswith(reason) for item in evaluated['invalid_reasons']),
                            (reason, evaluated['invalid_reasons']))
        return evaluated

    # ---- STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED ----
    def test_equal_state_with_a_different_envelope_reproduces(self):
        candidate = side(NEW_JOB, OTHER, state=parts(model_state=lambda m: {**m, 'round_rate': T(0.5, offset=7)}))
        evaluated = self.assertVerdict(
            evidence(candidate=candidate), REPRODUCED,
            {'file': 'FILE_DIFFERENT', 'learned_state': 'LEARNED_STATE_IDENTICAL', 'output': 'OUTPUT_REPRODUCED',
             'continuation': 'CONTINUATION_IDENTICAL'},
            reference_record=meta(common.HELM2_JOB), candidate_record=meta(NEW_JOB))
        self.assertIn('run_identity.context.run_id', evaluated['envelope']['metadata'])
        self.assertIn('elapsed_seconds', evaluated['envelope']['metadata'])
        self.assertTrue(evaluated['envelope']['tensor_layout'])                    # stride/offset reported only

    def test_identical_files_reproduce_and_file_identity_is_printed(self):
        self.assertVerdict(evidence(candidate=side(common.HELM2_JOB, REF), candidate_sha=REF), REPRODUCED,
                           {'file': 'FILE_IDENTICAL'}, job=common.HELM2_JOB, sha=REF)

    def test_a_continuation_difference_alone_never_decides(self):
        for candidate in (
                side(NEW_JOB, OTHER, state=parts(optimizer_state=lambda o: {**o, 'state': {0: {
                    'exp_avg': T(0.02), 'step': T(1470.0)}}})),
                side(NEW_JOB, OTHER, state=parts(rng_state=lambda r: {**r, 'python': (3, (1, 2, 4), None)})),
                side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, counters=1471)),
                side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, initial='j' * 64))):
            self.assertVerdict(evidence(candidate=candidate), REPRODUCED,
                               {'continuation': 'CONTINUATION_DIFFERENT', 'learned_state': 'LEARNED_STATE_IDENTICAL'})

    # ---- DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY (valid evidence) ----
    def test_every_learned_state_difference_is_a_valid_mismatch(self):
        cases = {
            'changed value': parts(model_state=lambda m: {**m, 'round_rate': T(0.5000001)}),
            'changed buffer': parts(model_state=lambda m: {**m, 'running_mean': T(1.0)}),
            'missing key': parts(model_state=lambda m: {'left.weight': m['left.weight']}),
            'dtype change': parts(model_state=lambda m: {**m, 'round_rate': T(0.5, dtype='torch.float64')}),
            'encoder readout': parts(encoder_state=lambda e: {**e, 'readout': T(0.125, 0.125)}),
            'vocabulary': parts(encoder_state=lambda e: {**e, 'tokenizer': {'tokens': ['a', 'c']}}),
            'tuple became list': parts(encoder_state=lambda e: {**e, 'tokenizer': {'tokens': ('a', 'b')}}),
        }
        for label, state in cases.items():
            candidate = side(NEW_JOB, OTHER, state=state)
            evaluated = self.assertVerdict(evidence(candidate=candidate), DOES_NOT_REPRODUCE,
                                           {'learned_state': 'LEARNED_STATE_DIFFERENT', 'output': 'OUTPUT_REPRODUCED'})
            self.assertGreater(evaluated['differences']['learned_state_row_count'], 0, label)

    def test_a_predictive_configuration_difference_is_a_valid_mismatch(self):
        evaluated = self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, core_rounds=9))),
                                       DOES_NOT_REPRODUCE, {'learned_state': 'LEARNED_STATE_DIFFERENT'})
        self.assertEqual(evaluated['differences']['predictive_configuration_keys'], ['run_identity.core_rounds'])

    def test_any_panel_difference_is_a_valid_mismatch_even_with_equal_state(self):
        altered = deepcopy(ANSWERS)
        altered[1] = {'kind': 'parts', 'value': ['n0']}
        for rows, label in ((panel(answers=altered), 'answer'), (panel(correct=[True, True, True]), 'grader flag'),
                            (panel(refuse=(2,)), 'unregistered refusal')):
            evaluated = self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, rows=rows)), DOES_NOT_REPRODUCE,
                                           {'learned_state': 'LEARNED_STATE_IDENTICAL', 'output': 'OUTPUT_DIFFERENT'})
            self.assertEqual(evaluated['differences']['panel_record_count'], 1, label)

    # ---- ADMISSION_INVALID_STOP (never the fallback) ----
    def test_invalid_evidence_never_reads_as_a_mismatch(self):
        reference_rows = panel()
        reference_rows[0]['answer'] = {'kind': 'reach', 'value': 'ABSENT'}
        tampered_levels = evidence()['producer_levels']
        tampered_levels['output'] = False
        cases = [
            (None, 'EVIDENCE_ABSENT_OR_NOT_AN_OBJECT'),
            (evidence(environment=dict(common.NUMERICAL_ENVIRONMENT, gpu_name='Tesla T4')),
             'ENVIRONMENT_NOT_THE_PINNED_NUMERICAL_ENVIRONMENT:gpu_name'),
            (evidence(candidate=side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, lr=0.004))),
             'TRAINING_CONFIGURATION_DIFFERS'),
            (evidence(reference=side(common.HELM2_JOB, REF, rows=reference_rows)),
             'REFERENCE_PANEL_NOT_REPRODUCED_IN_THIS_ENVIRONMENT:1_RECORDS'),
            (evidence(candidate=side(NEW_JOB, OTHER, restore='REFUSED')),
             'CANDIDATE_RESTORE_REFUSED_BY_THE_HISTORICAL_LOADER'),
            (evidence(candidate=side(NEW_JOB, OTHER, consistent=False)), 'CANDIDATE_CHECKPOINT_INTEGRITY'),
            (evidence(reasons=['REFERENCE_FILE_SHA256_IS_NOT_THE_EXPECTED_ONE']), 'PRODUCER_REPORTED'),
            (evidence(levels=tampered_levels), 'PRODUCER_AND_READER_DISAGREE:output'),
            (evidence(sources=dict(FAKE_SOURCES, **{'repro_common.py': '9' * 64})),
             'PRODUCER_IS_NOT_THE_ADMITTED_SOURCE'),
            (evidence(candidate=side(common.HELM2_JOB, OTHER)), 'CANDIDATE_CHECKPOINT_IS_FOR_ANOTHER_JOB'),
            (evidence(candidate_sha=THIRD), 'CANDIDATE_INPUT_IS_NOT_THE_BOUND_CHECKPOINT'),
            (evidence(root='/opt/elsewhere'), 'REFERENCE_PACKAGE_ROOT_IS_NOT_THE_RECORDED_ROOT'),
            (evidence(candidate=side(NEW_JOB, OTHER, rows=list(reversed(panel())))),
             'CANDIDATE_PANEL_RECORD_IDS_OR_ORDER'),
            (evidence(candidate=side(NEW_JOB, OTHER, inference={'module_training': True})),
             'CANDIDATE_INFERENCE_MODE'),
        ]
        for document, reason in cases:
            self.assertVerdict(document, INVALID, reason=reason)
        unhashed = evidence()
        unhashed['sides']['candidate']['model_state'][1]['sha256'] = None
        self.assertVerdict(unhashed, INVALID, reason='CANDIDATE_MODEL_STATE_ROW_UNHASHED')
        corrupt = evidence(reasons=['REFERENCE_FILE_SHA256_IS_NOT_THE_EXPECTED_ONE'])
        corrupt['sides']['reference'] = {'file': {'sha256': '0' * 64}}
        self.assertVerdict(corrupt, INVALID, reason='REFERENCE_FILE_IS_NOT_THE_EXPECTED_CHECKPOINT')

    def test_committed_record_binding(self):
        self.assertVerdict(evidence(), INVALID, reason='CANDIDATE_METADATA_IS_NOT_THE_COMMITTED_RECORD',
                           candidate_record=meta(NEW_JOB, counters=1))

    def test_invalid_evidence_still_shows_the_state_difference(self):
        candidate = side(NEW_JOB, OTHER, state=parts(model_state=lambda m: {'left.weight': m['left.weight']}),
                         restore='REFUSED')
        self.assertVerdict(evidence(candidate=candidate), INVALID, {'learned_state': 'LEARNED_STATE_DIFFERENT',
                                                                    'output': common.LEVEL_NOT_ESTABLISHED})


class RecomputePureTests(unittest.TestCase):
    def test_typed_digests_are_exact(self):
        self.assertNotEqual(recompute.typed_bytes((1, 2)), recompute.typed_bytes([1, 2]))
        self.assertNotEqual(recompute.typed_bytes(0.0), recompute.typed_bytes(-0.0))
        self.assertNotEqual(recompute.typed_bytes(0.1), recompute.typed_bytes(0.1 + 2 ** -56))
        self.assertNotEqual(recompute.typed_bytes(1), recompute.typed_bytes(True))
        self.assertEqual(recompute.typed_bytes({'b': 1, 'a': 2}), recompute.typed_bytes({'a': 2, 'b': 1}))
        self.assertEqual(recompute.typed(float('nan'))[0], 'float')
        for bad in (object(), {1.5: 'x'}, {(1,): 2}):
            with self.assertRaises(recompute.UnsupportedValue):
                recompute.typed(bad)

    def test_walk_rows(self):
        rows = recompute.walk_rows(parts()['optimizer_state'], is_fake, fake_row)
        paths = [row['path'] for row in rows]
        self.assertEqual(paths[0], [])
        self.assertIn(['str:state', 'int:0', 'str:exp_avg'], paths)
        self.assertIn(['str:param_groups'], paths)                       # tensor-free subtree: ONE value row
        kinds = {tuple(row['path']): row['kind'] for row in rows}
        self.assertEqual(kinds[('str:param_groups',)], 'value')
        self.assertEqual(kinds[('str:state', 'int:0')], 'container')
        self.assertEqual(recompute.walk_rows(T(1.0), is_fake, fake_row)[0]['kind'], 'tensor')
        with self.assertRaises(recompute.UnsupportedValue):
            recompute.walk_rows({'x': object(), 'y': T(1.0)}, is_fake, fake_row)

    def test_panel_row_and_grader_digest(self):
        row = panel()[0]
        self.assertEqual(row['grader_check_sha256'], MANIFEST['rows'][0]['grader_check_sha256'])
        self.assertEqual(row['answer'], ANSWERS[0])
        refused = panel(refuse=(0,))[0]
        self.assertEqual((refused['status'], refused['answer'], refused['grader_correct']), ('REFUSED', None, None))
        self.assertEqual(reader.panel_view(refused)['status'], 'REFUSED')
        self.assertIsNone(reader.panel_view(dict(row, grader_correct='yes')))

    def test_producer_levels_agree_with_the_reader(self):
        document = evidence()
        self.assertEqual(document['producer_levels'], {'file': False, 'learned_state': True, 'output': True,
                                                       'continuation': True})

    def test_it_stops_on_this_laptop_before_importing_torch(self):
        had_torch = 'torch' in sys.modules
        argv = ['--mode', 'reading', '--package-root', 'x', '--package-archive', 'x', '--reference-checkpoint', 'x',
                '--reference-record', 'x', '--panel-manifest', 'x', '--out', 'x', '--candidate-checkpoint', 'x',
                '--candidate-sha256', OTHER, '--candidate-job', NEW_JOB]
        for mode in (argv, ['--mode', 'acceptance'] + argv[2:14] + ['--work-dir', 'w']):
            with self.assertRaisesRegex(SystemExit, 'GPU_REQUIRED:(LINUX_WORKER_REQUIRED|EXPLICIT_ENABLE_REQUIRED)'):
                recompute.main(mode)
        self.assertEqual('torch' in sys.modules, had_torch)

    def test_no_top_level_torch_import_and_the_acceptance_table(self):
        tree = ast.parse((HERE / 'recompute_reproduction_evidence.py').read_text(encoding='utf-8'))
        top = [alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
               for alias in node.names] + [node.module for node in tree.body if isinstance(node, ast.ImportFrom)]
        self.assertNotIn('torch', top)
        table = {case: (verdict, levels) for case, _, verdict, levels in recompute.acceptance_specs(None)}
        self.assertEqual({case: verdict for case, (verdict, _) in table.items()},
                         {'equal_state_different_envelope': REPRODUCED, 'continuation_only_different': REPRODUCED,
                          'changed_value': DOES_NOT_REPRODUCE, 'changed_encoder_state': DOES_NOT_REPRODUCE,
                          'missing_key': INVALID, 'dtype_change': INVALID, 'altered_output': DOES_NOT_REPRODUCE})
        source = ast.unparse(function(HERE / 'recompute_reproduction_evidence.py', 'acceptance_mode'))
        for case in ('self_identity', 'state_equal_output_tampered', 'corrupt_reference'):
            self.assertIn("'" + case + "'", source)


# =====================================================================================================================
# The full reading: receipt bindings + evidence.
# =====================================================================================================================
def record_set(job, value, size, *, metadata, run_ids=None, manifest_rows=None, inventory_final=None,
               inventory_drop=()):
    document = deepcopy(metadata)
    if run_ids is not None:
        document['run_identity']['context']['run_id'], document['init_args']['run_context']['run_id'] = run_ids
    manifest = enc({'artifacts': manifest_rows if manifest_rows is not None
                    else [{'name': 'final.pt', 'sha256': value, 'bytes': size}]})
    checkpoint = enc({'sha256': value, 'bytes': size, 'metadata': document})
    final_sha, final_size = inventory_final or (value, size)
    rows = [{'relative_path': 'results/artifacts/final.pt', 'sha256': final_sha, 'bytes': final_size},
            {'relative_path': 'results/artifacts/manifest.json', 'sha256': digest(manifest), 'bytes': len(manifest)},
            {'relative_path': 'results/artifacts/final_checkpoint.json', 'sha256': digest(checkpoint),
             'bytes': len(checkpoint)}]
    rows = [row for row in rows if row['relative_path'] not in inventory_drop]
    return {common.MANIFEST_RECORD: manifest, common.INVENTORY_RECORD: enc({'job': job, 'files': rows}),
            common.CHECKPOINT_RECORD: checkpoint, reader.WORKER_REPORT: enc({'runtime': RUNTIME})}


REQUEST = {'schema': 'cncm.typed-pointer-request/0.1', 'job': NEW_JOB, 'source_sha': common.SOURCE_SHA,
           'archive_sha256': common.ARCHIVE_SHA256, 'manifest_sha256': common.MANIFEST_SHA256,
           'launch_authorized': False}


def reference_files(value=REF, **options):
    return record_set(common.HELM2_JOB, value, REF_BYTES, metadata=meta(common.HELM2_JOB), **options)


def frozen_files(job=NEW_JOB, state=common.ADMITTED, sources=None, rule=None):
    sources = FAKE_SOURCES if sources is None else sources
    study = {'status': 'FROZEN_BEFORE_FIRST_RUN', 'source_sha': common.SOURCE_SHA,
             'reading_rule': common.reading_rule_record() if rule is None else rule,
             'execution_admission': {'state': state, 'job': job, 'bindings': {
                 'reader_sources_sha256': sources, 'reader_source_sha256': common.reader_source_digest(sources)}},
             'jobs': [{'job': job, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED}]}
    return {'study.json': enc(study), '20260917/request.json': enc(dict(REQUEST, job=job))}


def receipt_files(value=OTHER, size=REF_BYTES, *, delivered=True, drop=(), overrides=None, **options):
    files = {'result.json': enc({'job': NEW_JOB, 'request': REQUEST, 'completed_deliverable': delivered,
                                 'status': 'AWS_CANDIDATE_FINISHED', 'cleanup': {'complete': True}}),
             'reduced_schedule.json': enc({'job': NEW_JOB, 'reduced_schedule': None}),
             'collected/results/result.json': enc({'job': NEW_JOB, 'status': 'TYPED_POINTER_DELIVERED',
                                                   'summary': {'schedule_plan_mode': 'REGISTERED'}}),
             **record_set(NEW_JOB, value, size, metadata=meta(NEW_JOB), **options)}
    files.update(overrides or {})
    for name in drop:
        files.pop(name, None)
    return files


def run(reference=None, frozen=None, receipt=None, document=None, sources=None):
    reference = reference_files() if reference is None else reference
    frozen = frozen_files() if frozen is None else frozen
    receipt = receipt_files() if receipt is None else receipt
    raw = recompute.encode(evidence() if document is None else document) if document != 'ABSENT' else None
    return reader.reading(reference.get, frozen.get, receipt.get, lambda: raw, MANIFEST, receipt_commit='c' * 40,
                          running_sources=FAKE_SOURCES if sources is None else sources)


class ReadingTests(unittest.TestCase):
    def assertInvalid(self, record, reason):
        self.assertEqual(record['verdict'], INVALID)
        self.assertTrue(any(item.startswith(reason) for item in record['invalid_reasons']),
                        (reason, record['invalid_reasons']))
        self.assertIn('authorizes no fallback', record['next_step_per_policy'])

    def test_a_valid_equal_state_reading_reproduces(self):
        record = run()
        self.assertEqual(record['verdict'], REPRODUCED, record['invalid_reasons'])
        self.assertEqual(record['printed_separately_never_deciding'], {'file': 'FILE_DIFFERENT',
                                                                       'continuation': 'CONTINUATION_IDENTICAL'})
        self.assertEqual(record['new']['weights_file_cross_check'], 'WEIGHTS_FILE_NOT_COMMITTED_AT_THE_RECEIPT_COMMIT')
        self.assertIn('seed 20260917 only', record['next_step_per_policy'])
        self.assertEqual(record['reader_source_sha256'], common.reader_source_digest(FAKE_SOURCES))

    def test_a_valid_state_mismatch_reads_does_not_reproduce_and_names_the_fallback_condition(self):
        document = evidence(candidate=side(NEW_JOB, OTHER, state=parts(
            model_state=lambda m: {**m, 'round_rate': T(0.75)})))
        record = run(document=document)
        self.assertEqual(record['verdict'], DOES_NOT_REPRODUCE, record['invalid_reasons'])
        self.assertIn(common.COMPARISON_INCOMPLETE, record['next_step_per_policy'])

    def test_missing_or_misbound_receipt_evidence_is_invalid_never_a_fallback(self):
        old = reference_files()
        cases = [
            (run(receipt=receipt_files(delivered=False)), 'COMPLETED_DELIVERABLE_NOT_TRUE'),
            (run(receipt=receipt_files(drop=['result.json'])), 'RECEIPT_RESULT_JSON_ABSENT_OR_UNREADABLE'),
            (run(document='ABSENT'), 'EVIDENCE_ABSENT_OR_NOT_AN_OBJECT'),
            (run(receipt=receipt_files(REF, overrides={common.INVENTORY_RECORD: old[common.INVENTORY_RECORD],
                                                       common.CHECKPOINT_RECORD: old[common.CHECKPOINT_RECORD]})),
             'INVENTORY_IS_FOR_ANOTHER_JOB'),
            (run(receipt=receipt_files(overrides={common.CHECKPOINT_RECORD: old[common.CHECKPOINT_RECORD]})),
             'CHECKPOINT_IS_FOR_ANOTHER_JOB'),
            (run(receipt=receipt_files(overrides={common.MANIFEST_RECORD: old[common.MANIFEST_RECORD]})),
             'RECORD_IS_NOT_THE_ONE_THIS_JOB_COLLECTED:worker_artifact_manifest'),
            (run(receipt=receipt_files(run_ids=(None, None))), 'CHECKPOINT_RUN_ID_MISSING'),
            (run(receipt=receipt_files(drop=(common.MANIFEST_RECORD,))), 'FINAL_PT_RECORD_ABSENT_OR_UNREADABLE'),
            (run(receipt=receipt_files(inventory_final=(THIRD, REF_BYTES))),
             'NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES'),
            (run(receipt=receipt_files(manifest_rows=[{'name': 'final.pt', 'sha256': OTHER, 'bytes': REF_BYTES}] * 2)),
             'FINAL_PT_ROW_NOT_EXACTLY_ONE_WELL_FORMED:worker_artifact_manifest'),
            (run(receipt=receipt_files(REF)), 'CONTRADICTION_HELM2_FILE_HASH_UNDER_THE_NEW_RUN_ID'),
            (run(receipt=receipt_files(overrides={'reduced_schedule.json': enc({
                'job': NEW_JOB, 'reduced_schedule': {'passes': 1}})})), 'RECEIPT_RAN_A_REDUCED_SCHEDULE'),
            (run(receipt=receipt_files(overrides={reader.WORKER_REPORT: enc({'runtime': dict(
                RUNTIME, gpu_name='Tesla T4')})})), 'CANDIDATE_TRAINING_ENVIRONMENT_NOT_PINNED'),
            (run(frozen={}), 'NOTHING_FROZEN_AT_THIS_COMMIT'),
            (run(frozen=frozen_files(state=common.NOT_READY)), 'FROZEN_WITHOUT_AN_ADMITTED_EXECUTION_ADMISSION'),
            (run(frozen=frozen_files(rule={'reader_rule': 'CHECKPOINT_FILE_IDENTITY'})),
             'FROZEN_UNDER_A_DIFFERENT_READING_RULE'),
            (run(sources=dict(FAKE_SOURCES, **{'read_reproduction.py': '8' * 64})),
             'THIS_READER_IS_NOT_THE_ADMITTED_READER'),
            (run(reference=reference_files(OTHER)), 'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE'),
        ]
        for record, reason in cases:
            self.assertInvalid(record, reason)

    def test_the_weights_file_is_a_cross_check_only(self):
        receipt = receipt_files()
        receipt[common.FINAL_PT_WEIGHTS] = b'not the weights'
        self.assertInvalid(run(receipt=receipt), 'WEIGHTS_FILE_IS_NOT_THE_ONE_THE_RECORDS_STATE')

    def test_a_reader_whose_source_is_not_admitted_gives_no_verdict_at_all(self):
        saved = reader.stop_unless
        reader.stop_unless = stop
        try:
            with self.assertRaisesRegex(Stopped, 'READER_IS_NOT_THE_ADMITTED_READER'):
                reader.admitted_reader_check(frozen_files().get, dict(FAKE_SOURCES, **{'repro_common.py': '7' * 64}))
            reader.admitted_reader_check(frozen_files().get, FAKE_SOURCES)
        finally:
            reader.stop_unless = saved

    def test_the_verdict_is_always_one_of_three_words(self):
        for record in (run(), run(receipt=receipt_files(delivered=False)), run(document='ABSENT')):
            self.assertIn(record['verdict'], common.VERDICTS)


class RealReferenceTests(unittest.TestCase):
    """The committed Helm 2.0 records at c8d5c430: small JSON blobs only, never a weights file."""

    @unittest.skipUnless(git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected_inventory.json'),
                         'reference commit not fetched')
    def test_reference_hash_from_git_with_the_job_binding(self):
        read = reader.git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL)
        ev = reader.Evidence()
        reference, checkpoint = reader.reference_reading(read, lambda name: common.blob_id(
            common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name), ev)
        self.assertEqual(ev.reasons, [])
        self.assertEqual(reference['final_pt_sha256'], REF)
        self.assertEqual(len(reference['sources']), 3)
        self.assertEqual(reader.checkpoint_run_ids(checkpoint), (common.HELM2_JOB, common.HELM2_JOB))
        split = reader.split_metadata(checkpoint['metadata'], ev, 'REAL')
        self.assertEqual(ev.reasons, [])
        self.assertEqual(split['envelope']['init_args.root'], common.HISTORICAL_PACKAGE_ROOT)
        self.assertEqual(split['predictive']['run_identity.core_rounds'], 8)
        other = reader.Evidence()
        reader.bound_records(read, NEW_JOB, other, '')                   # the same real records, as a NEW run's
        self.assertTrue(any(item.startswith('INVENTORY_IS_FOR_ANOTHER_JOB') for item in other.reasons))

    @unittest.skipUnless(git_has(common.PACKAGE_COMMIT, common.HELM2_ADMISSION_REL + '/request.json'),
                         'package commit not fetched')
    def test_pinned_blobs_are_the_committed_ones(self):
        for name, blob in common.HELM2_ADMISSION_BLOBS.items():
            self.assertEqual(common.blob_id(common.PACKAGE_COMMIT, common.HELM2_ADMISSION_REL + '/' + name), blob)
        for name, blob in common.PACKAGE_BLOBS.items():
            self.assertEqual(common.blob_id(common.PACKAGE_COMMIT, common.PACKAGE_REL + '/' + name), blob)
        self.assertEqual(common.blob_id(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL
                                        + '/collected/input/source.zip'), common.PACKAGE_BLOBS['source.zip'])


# =====================================================================================================================
# Kept from revision 1: tree / untracked rules, the atomic writer, builders, spend gate, --check's study check.
# =====================================================================================================================
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

    def test_status_parser_and_untracked_rule(self):
        self.assertEqual(common.parse_status_z(b'R  new.py\0old.py\0?? a.txt\0 M b.py\0'),
                         [('R ', 'new.py'), ('??', 'a.txt'), (' M', 'b.py')])
        own = P + common.HERE_REL
        self.assertEqual(common.status_violations([('??', own + '/frozen/20260917/owner.json'),
                                                   ('??', own + '/reproduction_reading.json')]), [])
        for entry in [('??', own + '/frozen.partial/study.json'), ('??', own + '/notes.txt'),
                      (' M', own + '/EXECUTION_ADMISSION.json'), (' M', P + 'cncm/typed_pointer_worker.py')]:
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

    def test_failed_recheck_or_rename_leaves_the_partial(self):
        saved = common.os.rename
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'

            def bad(locate):
                raise Stopped('RECHECK_FAILED')
            with self.assertRaisesRegex(Stopped, 'RECHECK_FAILED'):
                common.write_folder_atomically(final, [(final / 'study.json', b'{}\n')], bad, stop)
            self.assertTrue(common.partial_of(final).exists())
            with self.assertRaisesRegex(Stopped, 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND'):
                common.write_folder_atomically(final, [(final / 'study.json', b'{}\n')], lambda locate: None, stop)
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            try:
                common.os.rename = lambda source, target: (_ for _ in ()).throw(PermissionError('sync lock'))
                with self.assertRaisesRegex(Stopped, 'RENAME_FAILED_PARTIAL_LEFT_INSPECT_BY_HAND.*PermissionError'):
                    common.write_folder_atomically(final, [(final / 'study.json', b'{}\n')], lambda locate: None, stop)
            finally:
                common.os.rename = saved
            self.assertTrue(common.partial_of(final).exists())

    def test_cr_bytes_and_outside_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            final = Path(scratch) / 'frozen'
            with self.assertRaisesRegex(Stopped, 'ENTRY_HAS_CR_BYTES'):
                common.write_folder_atomically(final, [(final / 'a.json', b'{}\r\n')], lambda locate: None, stop)
            with self.assertRaisesRegex(Stopped, 'ENTRY_OUTSIDE_TARGET'):
                common.write_folder_atomically(final, [(Path(scratch) / 'b.json', b'{}\n')], lambda locate: None,
                                               stop)


class BuilderTests(unittest.TestCase):
    def test_job_name_is_fresh_and_never_helm2_s(self):
        self.assertEqual(common.check_stamp('20260925120000', stop), NEW_JOB)
        with self.assertRaisesRegex(Stopped, 'STAMP_IS_HELM2_S_OWN_STAMP'):
            common.check_stamp(common.HELM2_STAMP, stop)
        with self.assertRaisesRegex(Stopped, 'STAMP_FORM'):
            common.check_stamp('2026092512000', stop)
        self.assertEqual(len(NEW_JOB + '-807562639912'), 63)
        self.assertEqual(common.stamp_of(NEW_JOB), '20260925120000')
        self.assertIsNone(common.stamp_of('cas-meta2-tpntr-20260925120000-20208c92-m-20260918'))
        self.assertIsNone(common.stamp_of(None))

    def test_launch_argv_and_config_comparison(self):
        pin = {'path': 'p', 'sha256': 'h'}
        argv = common.launch_argv(launcher='L', request=pin, authority=pin, owner=pin, receipt_dir='R', ledger='G')
        self.assertEqual([item for item in argv if item.startswith('--')],
                         ['--execute', '--request', '--request-sha256', '--authority', '--authority-sha256',
                          '--owner-authorization', '--receipt-dir', '--ledger-path'])

        def config(job, extra=0):
            return common.canonical({'job': job, 'bucket': job + '-807562639912', 'design': {'x': extra}}).decode()
        self.assertTrue(common.config_equal_except_job(config(NEW_JOB), config(common.HELM2_JOB), NEW_JOB,
                                                       common.HELM2_JOB))
        self.assertFalse(common.config_equal_except_job(config(NEW_JOB, 1), config(common.HELM2_JOB), NEW_JOB,
                                                        common.HELM2_JOB))


class SpendGateTests(unittest.TestCase):
    def test_measured_spend_plus_the_per_job_bound_must_fit_the_ceiling(self):
        self.assertEqual(common.spend_gate('45.00', stop)['after_this_job_at_most_usd'], '60.00')
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
        self.admission = {'record_sha256': 'e' * 64, 'job': NEW_JOB}
        owner = {'job': NEW_JOB, 'bounds': dict(common.EXPECTED_BOUNDS), 'reading_rule': common.reading_rule_record(),
                 'execution_admission': {'record_sha256': 'e' * 64}, 'approval_words_inserted_by_builder': False}
        pins = {}
        for name, value in (('owner', owner), ('request', dict(REQUEST))):
            raw = common.canonical(value)
            (folder / (name + '.json')).write_bytes(raw)
            pins[name] = common.pin(folder / (name + '.json'), raw)
        raw = common.canonical({'job': NEW_JOB, 'owner_authorization_sha256': pins['owner']['sha256'],
                                **common.HELM2_BINDINGS})
        (folder / 'authority.json').write_bytes(raw)
        pins['authority'] = common.pin(folder / 'authority.json', raw)
        argv = common.launch_argv(launcher=common.ROOT / common.LAUNCHER_REL, request=pins['request'],
                                  authority=pins['authority'], owner=pins['owner'], receipt_dir=common.RECEIPT_DIR,
                                  ledger=str(self.ledger))
        self.study = {'schema': prepare.STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN',
                      'source_sha': common.SOURCE_SHA, 'source_checkout': str(common.ROOT),
                      'reading_rule': common.reading_rule_record(),
                      'execution_admission': {'state': common.ADMITTED, 'record_sha256': 'e' * 64, 'job': NEW_JOB,
                                              'bindings': common.expected_admission_bindings()},
                      'automatic_retries': 0, 'numeric_runs_completed': 0, 'canonical_ledger': str(self.ledger),
                      'package': {'archive_the_launcher_locates': str(ARCHIVE)},
                      'jobs': [{'job': NEW_JOB, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED,
                                'receipt_dir': str(common.RECEIPT_DIR), 'reduced_schedule': None, **pins,
                                'launch_argv': argv}]}

    def tearDown(self):
        prepare.stop_unless = self.saved
        self.scratch.cleanup()

    def check(self, study=None, admission=None):
        return prepare.check_study(json.loads(json.dumps(study or self.study)), admission or self.admission,
                                   output=self.output)

    @unittest.skipUnless(ARCHIVE.is_file(), 'package archive not in this checkout')
    def test_a_consistent_frozen_folder_passes(self):
        self.assertEqual(self.check()['job'], NEW_JOB)

    @unittest.skipUnless(ARCHIVE.is_file(), 'package archive not in this checkout')
    def test_every_moved_piece_is_refused(self):
        def changed(path, value):
            study = json.loads(json.dumps(self.study))
            target = study
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return study
        cases = [(changed(('reading_rule', 'reader_rule'), {'rule': 'CHECKPOINT_FILE_IDENTITY'}),
                  'FROZEN_UNDER_A_DIFFERENT_READING_RULE'),
                 (changed(('execution_admission', 'state'), common.NOT_READY),
                  'FROZEN_UNDER_A_DIFFERENT_EXECUTION_ADMISSION'),
                 (changed(('execution_admission', 'record_sha256'), 'f' * 64),
                  'FROZEN_UNDER_A_DIFFERENT_EXECUTION_ADMISSION'),
                 (changed(('source_checkout',), 'C:/elsewhere'), 'NOT_THE_CHECKOUT_THE_RECORDS_WERE_WRITTEN_IN'),
                 (changed(('package', 'archive_the_launcher_locates'), str(self.ledger)), 'LOCATED_ARCHIVE_CHANGED'),
                 (changed(('canonical_ledger',), str(self.ledger) + '.gone'), 'LAUNCH_ARGV'),
                 (changed(('jobs', 0, 'job'), common.HELM2_JOB), 'STUDY_JOB'),
                 (changed(('jobs', 0, 'launch_argv'), self.study['jobs'][0]['launch_argv'] + ['--reduced-schedule']),
                  'LAUNCH_ARGV')]
        for study, reason in cases:
            with self.assertRaisesRegex(Stopped, reason):
                self.check(study)
        with self.assertRaisesRegex(Stopped, 'FROZEN_UNDER_A_DIFFERENT_EXECUTION_ADMISSION'):
            self.check(admission={'record_sha256': 'e' * 64, 'job': common.job_name('20260925120001')})
        (self.output / '20260917' / 'owner.json').write_bytes(b'{}\n')
        with self.assertRaisesRegex(Stopped, '^PIN:'):
            self.check()


# =====================================================================================================================
# Static: launcher names exist (AST only; nothing is imported); gates run before the launcher; files ASCII and LF.
# =====================================================================================================================
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
                names.update(item.id for item in ast.walk(target) if isinstance(item, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split('.')[0] for alias in node.names)
    return names


def function(path, name):
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def calls(node):
    out = []
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            func = item.func
            out.append((item.lineno, func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', None)))
    return sorted(out)


class StaticTests(unittest.TestCase):
    def test_every_launch_attribute_exists(self):
        used = set()
        for node in ast.walk(ast.parse((HERE / 'prepare_unchanged_repro.py').read_text(encoding='utf-8'))):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'launch':
                used.add((None, node.attr))
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                    and isinstance(node.value.value, ast.Name) and node.value.value.id == 'launch'
                    and node.value.attr in MODULE_FILES):
                used.add((node.value.attr, node.attr))
        self.assertGreater(len(used), 30)
        cache = {key: top_level_names(path) for key, path in MODULE_FILES.items()}
        missing = []
        for module, name in sorted(used, key=str):
            if module not in cache:
                missing.append('UNMAPPED:' + str(module) + '.' + name)
            elif name not in cache[module]:
                missing.append(str(module) + '.' + name)
        self.assertEqual(missing, [])

    def test_the_gates_run_before_the_launcher_is_imported(self):
        writer = HERE / 'prepare_unchanged_repro.py'
        order = [name for _, name in calls(function(writer, 'prepare'))]
        self.assertLess(order.index('gates'), order.index('load_launcher'))
        self.assertLess(order.index('check_repository'), order.index('gates'))
        gate_calls = [name for _, name in calls(function(writer, 'gates'))]
        for name in ('check_policy', 'owner_authorization_state', 'execution_admission_state'):
            self.assertIn(name, gate_calls)
        for name in ('check_before_launch', 'check_study', 'check_frozen_committed', 'check_pin', 'gates',
                     'print_admission_bindings'):
            node = function(writer, name)
            self.assertFalse(any(isinstance(item, ast.Name) and item.id in ('launch', 'load_launcher')
                                 for item in ast.walk(node)), name)

    def test_the_reader_checks_the_policy_before_reading(self):
        order = [name for _, name in calls(function(HERE / 'read_reproduction.py', 'main'))]
        self.assertLess(order.index('read_policy_files'), order.index('reading'))
        self.assertLess(order.index('admitted_reader_check'), order.index('reading'))

    def test_this_folder_s_files_are_ascii_and_lf(self):
        for path in list(HERE.glob('*.py')) + list(HERE.glob('*.md')) + list(HERE.glob('*.json')):
            raw = path.read_bytes()
            self.assertNotIn(b'\r', raw, path.name)
            self.assertTrue(raw.isascii(), path.name)


if __name__ == '__main__':
    unittest.main()
