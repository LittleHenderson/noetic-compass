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
Revision 3 (review of 303c281b) adds:
  * BLOCKER 1: no reader source carries any pinned policy/owner hash (the pins live in policy_pins.json), and a
    simulated freeze + re-pin leaves the reader digest unchanged;
  * MAJOR 2: every prerequisite receipt is opened and checked (PASS + any hex no longer passes; a
    READER_ACCEPTANCE_FAIL receipt whose hash is written is refused; the spend is read from the spend record);
  * MAJOR 3: an ERROR panel row or an uncoded refusal is ADMISSION_INVALID_STOP, never DOES_NOT_REPRODUCE;
  * the minors: the admission at the receipt commit, the frozen-before-result history rule (with real git log on this
    branch), the AMI / shipped-package checks, the starting state as training configuration, the READING mode, a
    SYNTHETIC buffer case, and missing-key / dtype-change as the pinned loader treats them.

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
import subprocess
import sys
import tempfile
import unittest
import zipfile
import contextlib
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
ARCHIVE = common.ROOT / common.PACKAGE_REL / 'source.zip'
ARCHIVE_RAW = ARCHIVE.read_bytes() if ARCHIVE.is_file() else None          # the committed package (about 6 MB)
PREFLIGHT_OK = {'ami': common.HISTORICAL_AMI, 'instance_type': 'g7.2xlarge', 'region': 'us-west-2',
                'visible_gpu_count': 1}
RECORDED_ENV = dict(common.NUMERICAL_ENVIRONMENT, python_version='3.12.3', cudnn_version=91002,
                    driver_version='580.65.06', platform_release='6.8.0-1024-aws',
                    python_implementation='CPython', machine='x86_64', compute_capability='12.0')   # synthetic values


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

    def current_tips(self):
        return {branch: {'ref': common.tracking_ref(branch), 'commit': 'f' * 40,
                         'blobs': {name: blob for name, (_, blob) in entry['files'].items()},
                         'pinned_commits_are_ancestors': True}
                for branch, entry in common.tip_watch().items()}

    def test_policy_tip_currency(self):
        tips = self.current_tips()
        self.assertEqual(common.policy_tip_violations(tips), [])
        self.assertEqual(set(tips), {common.POLICY_BRANCH, 'research/helm-integration-20260923'})
        moved = deepcopy(tips)
        moved[common.POLICY_BRANCH]['blobs']['plan'] = '3172a221f3a12448029b995e87009284fcce453c'
        self.assertEqual(common.policy_tip_violations(moved),
                         ['MOVED_AT_TIP:plan:3172a221f3a12448029b995e87009284fcce453c'])
        not_in = deepcopy(tips)
        not_in[common.POLICY_BRANCH]['pinned_commits_are_ancestors'] = False
        self.assertEqual(common.policy_tip_violations(not_in), ['PINNED_COMMIT_NOT_IN_TIP:' + common.POLICY_BRANCH])
        missing = deepcopy(tips)
        missing[common.POLICY_BRANCH]['commit'] = None
        self.assertTrue(common.policy_tip_violations(missing)[0].startswith('TRACKING_REF_MISSING'))

    def test_owner_records_are_watched_at_their_branch_tips(self):
        """Review NOTE 12: a later owner record at a tip (a withdrawal) stops the admitted paths until a re-pin."""
        tips = self.current_tips()
        for branch, name in ((common.POLICY_BRANCH, 'owner:codex_standing_json'),
                             ('research/helm-integration-20260923', 'owner:claude_extension_md')):
            moved = deepcopy(tips)
            moved[branch]['blobs'][name] = '6' * 40
            self.assertEqual(common.policy_tip_violations(moved), ['MOVED_AT_TIP:' + name + ':' + '6' * 40])
            gone = deepcopy(tips)
            gone[branch]['blobs'][name] = None
            self.assertEqual(common.policy_tip_violations(gone), ['MOVED_AT_TIP:' + name + ':None'])

    @unittest.skipUnless(POLICY_PRESENT, 'policy commit bc46b36e not fetched')
    def test_a_moved_tip_stops_only_the_admitted_paths(self):
        saved = common.read_policy_tips
        moved = self.current_tips()
        moved[common.POLICY_BRANCH]['blobs']['launch_request'] = '5' * 40
        try:
            common.read_policy_tips = lambda stop_, *, fetch: moved
            report = common.check_policy(stop, fetch=False, require_current=False)
            self.assertEqual(report['tip']['violations'], ['MOVED_AT_TIP:launch_request:' + '5' * 40])
            with self.assertRaisesRegex(Stopped, '^POLICY_OR_PLAN_MOVED:MOVED_AT_TIP:launch_request'):
                common.check_policy(stop, fetch=False, require_current=True)
        finally:
            common.read_policy_tips = saved

    # ---- BLOCKER 1 (review of 303c281b): no hash cycle between the policy and the reader digest ----
    def test_no_reader_source_carries_a_pinned_policy_hash(self):
        """Codex freezes REPRODUCTION_POLICY.json with the reader digest. If a reader source held any policy or
        owner-record hash, every re-pin would change that digest: a cycle. So none may, and the pins file is not a
        reader source."""
        self.assertNotIn(common.PINS_NAME, common.READER_SOURCE_FILES)
        pinned = {common.POLICY_COMMIT}
        for _, blob, sha, _ in common.POLICY_FILES.values():
            pinned.update((blob, sha))
        for commit, _, blob, sha in common.OWNER_RECORDS.values():
            pinned.update((commit, blob, sha))
        for name in common.READER_SOURCE_FILES:
            text = (HERE / name).read_text(encoding='ascii')
            for value in pinned:
                for width in (8, len(value)):                      # neither the full hash nor its short form
                    self.assertNotIn(value[:width], text, (name, value))

    def test_a_policy_freeze_and_re_pin_leave_the_reader_digest_unchanged(self):
        before = common.reader_source_digest()
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            for name in common.READER_SOURCE_FILES:
                (folder / name).write_bytes((HERE / name).read_bytes())
            pins = json.loads(common.PINS_RAW)
            frozen = {'reader_source_sha256': before, 'output_panel_manifest_sha256': common.PANEL_MANIFEST_SHA256}
            raw = common.canonical(frozen)
            pins['policy']['commit'] = '7' * 40                   # the re-pin after Codex's freeze
            pins['policy']['files']['reproduction_policy_json'].update(
                blob=common.git_object_id(raw), sha256=digest(raw), bytes=len(raw))
            (folder / common.PINS_NAME).write_bytes(enc(pins))
            self.assertEqual(common.pins_violations(pins), [])
            self.assertEqual(common.reader_source_digest(common.source_hashes(folder)), before)
        violations = common.policy_freeze_violations(frozen, {}, {}, common.expected_admission_bindings(), {})
        self.assertNotIn('POLICY_READER_SOURCE_NOT_FROZEN_TO_THIS_READER', violations)
        self.assertNotIn('POLICY_PANEL_MANIFEST_NOT_FROZEN_TO_THIS_PANEL', violations)

    def test_the_pins_file_form(self):
        pins = json.loads(common.PINS_RAW)
        self.assertEqual(common.pins_violations(pins), [])
        self.assertEqual(common.load_pins(common.PINS_RAW), pins)
        self.assertEqual(common.PINS_SHA256, digest(common.PINS_RAW))
        self.assertEqual(common.expected_admission_bindings()['policy_pins_sha256'], common.PINS_SHA256)
        self.assertEqual(common.evidence_policy_block()['policy_pins_sha256'], common.PINS_SHA256)
        for change, reason in (
                (lambda p: p.update(label='APPROVED'), 'PINS_TOP_FIELDS_SCHEMA_OR_LABEL'),
                (lambda p: p['policy'].update(commit='BC46B36E' * 5), 'PINS_POLICY_HEAD'),
                (lambda p: p['policy']['files'].pop('plan'), 'PINS_POLICY_FILE_SET'),
                (lambda p: p['policy']['files']['plan'].update(bytes=True), 'PINS_POLICY_FILE:plan'),
                (lambda p: p['policy']['files']['plan'].update(path='../x.md'), 'PINS_POLICY_FILE:plan'),
                (lambda p: p['owner_records']['codex_standing_md'].update(branch='a..b'),
                 'PINS_OWNER_RECORD:codex_standing_md')):
            bad = deepcopy(pins)
            change(bad)
            self.assertIn(reason, common.pins_violations(bad))
        with self.assertRaisesRegex(SystemExit, '^UNCHANGED_REPRO_POLICY_PINS_INVALID'):
            common.load_pins(b'{"schema": "x"}')
        with self.assertRaisesRegex(SystemExit, 'PINS_NOT_AN_OBJECT'):
            common.load_pins(b'not json')

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
        self.assertEqual(common.environment_unrecorded(RECORDED_ENV), [])
        self.assertEqual(common.environment_unrecorded(pinned), list(common.ENVIRONMENT_RECORDED_NOT_PINNED))

    def test_training_machine_and_shipped_package(self):
        """Review MINOR 7: the preflight AMI, instance and region; the shipped archive and its requirements file."""
        self.assertEqual(common.preflight_violations(PREFLIGHT_OK), [])
        self.assertEqual(common.preflight_violations(dict(PREFLIGHT_OK, ami='ami-0123456789abcdef0')),
                         ['ami=ami-0123456789abcdef0'])
        self.assertEqual(common.preflight_violations(dict(PREFLIGHT_OK, instance_type='g4dn.xlarge')),
                         ['instance_type=g4dn.xlarge'])
        self.assertEqual(len(common.preflight_violations(None)), 3)
        self.assertEqual(common.shipped_package_violations(None), ['SHIPPED_PACKAGE_ABSENT'])
        self.assertIn('SHIPPED_PACKAGE_HAS_NO_REQUIREMENTS_MEMBER', common.shipped_package_violations(b'not a zip'))
        other = io.BytesIO()
        with zipfile.ZipFile(other, 'w') as bundle:
            bundle.writestr(common.REQUIREMENTS_MEMBER, b'torch==2.4.0\n')
        found = common.shipped_package_violations(other.getvalue())
        self.assertIn('SHIPPED_PACKAGE_IS_NOT_THE_PINNED_ARCHIVE', found)
        self.assertTrue(any(item.startswith('SHIPPED_REQUIREMENTS_SHA256:') for item in found))
        if ARCHIVE_RAW is not None:
            self.assertEqual(common.shipped_package_violations(ARCHIVE_RAW), [])

    def test_historical_refusal_codes(self):
        """Review MAJOR 3: only the historical `require` form is model behaviour. REVISION 4 (Codex R3-B): only a code
        on the published allowlist; 'TYPED_MATCHED:X' had the shape but is not a historical code, so it moved from
        the accepted list to the refused list."""
        for message in ('POINTER_SLOT_COVERAGE', 'TYPED_LEARNER_DEPTH', 'TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:3'):
            self.assertTrue(common.is_historical_refusal(message), message)
        for message in ('CUDA error: an illegal memory access was encountered', 'out of memory', 'pointer_slot',
                        'POINTER_', 'TYPED_X:\nnext line', '', None, 3, 'TYPED_MATCHED:X'):
            self.assertFalse(common.is_historical_refusal(message), message)

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
NEW_JOB = common.job_name('20260925120000')
RECEIPT_COMMIT = 'e' * 40                     # a synthetic receipt commit; `read_prerequisite_receipts` is not used here
LOCK_RAW, PACKET_RAW = b'synthetic dependency lock\n', b'synthetic launch packet\n'


def acceptance_case(case):
    """One case exactly as `recompute_reproduction_evidence.judge` records it when it meets the frozen table (rev. 4)."""
    expected = common.ACCEPTANCE_EXPECTED[case]
    if case == 'changed_buffer':
        return {'case': case, 'status': common.VACUOUS, 'reference_buffers': [], 'reference_buffer_count': 0,
                'pass': True, 'why': 'zero buffers (synthetic)'}
    levels = {'file': False, 'learned_state': True, 'output': True, 'continuation': True}
    levels.update(expected['levels'])
    reasons = ['CANDIDATE_RESTORE_REFUSED_BY_THE_HISTORICAL_LOADER:x'] if expected['verdict'] == INVALID else []
    return {'case': case, 'expected_verdict': expected['verdict'], 'expected_levels': dict(expected['levels']),
            'observed_verdict': expected['verdict'], 'observed_levels': common.level_labels(levels),
            'invalid_reasons': reasons, 'panel_record_differences': 0, 'evidence_sha256': 'e' * 64, 'pass': True}


def acceptance_receipt(sources=FAKE_SOURCES, **changes):
    """A synthetic P1 acceptance receipt, as `recompute_reproduction_evidence.acceptance_mode` writes it."""
    receipt = {'schema': common.ACCEPTANCE_SCHEMA, 'label': common.LABEL, 'status': common.ACCEPTANCE_PASS,
               'cases': [acceptance_case(case) for case in common.ACCEPTANCE_CASES],
               'producer': {'sources_sha256': dict(sources), 'reader_source_sha256': common.reader_source_digest(sources)},
               'panel_manifest_sha256': common.PANEL_MANIFEST_SHA256,
               'numerical_environment_sha256': common.environment_digest(), 'environment': dict(RECORDED_ENV),
               'environment_violations': []}
    receipt.update(changes)
    return receipt


def frozen_policy(acceptance_raw=None):
    """The three Codex records as they would read after the freeze (synthetic)."""
    acceptance_raw = enc(acceptance_receipt()) if acceptance_raw is None else acceptance_raw
    return ({'output_panel_manifest_sha256': common.PANEL_MANIFEST_SHA256,
             'reader_source_sha256': common.reader_source_digest(FAKE_SOURCES),
             'reader_acceptance_receipt_sha256': digest(acceptance_raw), 'main_launch_ready': True},
            {'launch_enabled': True, 'dependencies': {'status': 'FROZEN'},
             'final_freeze': {'frozen_launch_packet_sha256': digest(PACKET_RAW),
                              'dependency_lock_sha256': digest(LOCK_RAW)}},
            {'launch_enabled': True})


SPEND_SOURCE_RAW = b'{"synthetic": "cost state"}\n'


def spend_record(job=NEW_JOB, **changes):
    record = {'schema': common.SPEND_RECORD_SCHEMA, 'label': common.LABEL, 'study': common.STUDY_NAME, 'job': job,
              'measured_spend_so_far_usd': '21.40', 'measured_utc': '2026-09-25T09:58:00Z',   # 120 s before admission
              'basis': 'conservative bound including unbilled runtime (synthetic)',
              'sources': [{'commit': RECEIPT_COMMIT, 'path': 'records/helm_controlled_prelaunch_20260924/COST_STATE.json',
                           'sha256': digest(SPEND_SOURCE_RAW)}]}
    record.update(changes)
    return record


REVIEW_CLOSURE = {name: (str(index % 10) * 40) for index, name in enumerate(common.REVIEW_CLOSURE_FILES, start=1)}


def review_receipt(**changes):
    receipt = {'schema': common.REVIEW_RECEIPT_SCHEMA, 'label': common.LABEL, 'verdict': common.REVIEW_PASS,
               'reviewed_reader_sources_sha256': dict(FAKE_SOURCES),
               'reviewed_reader_source_sha256': common.reader_source_digest(FAKE_SOURCES),
               'reviewed_policy_pins_sha256': common.PINS_SHA256,
               'reviewed_panel_manifest_sha256': common.PANEL_MANIFEST_SHA256, 'job_kind': common.JOB_KIND,
               'model_seed': common.MODEL_SEED, 'reviewed_commit': 'd' * 40, 'reviewer': 'Codex (synthetic)',
               'reviewed_branch': 'claude/helm-unchanged-reader-rev-20260924', 'closure': dict(REVIEW_CLOSURE),
               'unresolved_findings': [{'id': 'N1', 'severity': 'NOTE', 'execution_consequence': 'record only'}],
               'reviewer_provenance': {'source': 'agent bus (synthetic)', 'reference': 'codex-0000'},
               'attribution': {'builder': common.LABEL, 'independence': common.INDEPENDENCE_LABEL},
               'scope': 'reader revision 4 (synthetic)'}
    receipt.update(changes)
    return receipt


def review_facts(**changes):
    """The git facts `common.review_facts` gathers, consistent with `review_receipt()` (synthetic)."""
    facts = {'reviewed_commit_resolves': True, 'reviewed_commit_pushed': True,
             'closure_at_reviewed_commit': dict(REVIEW_CLOSURE), 'closure_running': dict(REVIEW_CLOSURE),
             'writer_blobs_at_freeze': {name: REVIEW_CLOSURE[name] for name in common.WRITER_FILES}}
    facts.update(changes)
    return facts


def synthetic_receipts(job=NEW_JOB, **raws):
    """`{name: {'commit', 'path', 'raw'}}` exactly as `read_prerequisite_receipts` returns committed receipts
    (revision 4: the budget receipt carries its opened `sources`, the review receipt its git `facts`)."""
    policy = frozen_policy()[0]
    default = {'reader_acceptance_on_aws_p1': enc(acceptance_receipt()),
               'reproduction_policy_frozen_with_panel_and_reader': enc(policy),
               'numerical_environment_frozen': LOCK_RAW, 'final_launch_packet_frozen': PACKET_RAW,
               'budget_headroom_verified': enc(spend_record(job)), 'fresh_review_of_this_revision': enc(review_receipt())}
    default.update(raws)
    out = {}
    for name, raw in default.items():
        if name == 'reproduction_policy_frozen_with_panel_and_reader':
            commit, path = common.POLICY_COMMIT, common.POLICY_FILES['reproduction_policy_json'][0]
        else:
            commit, path = RECEIPT_COMMIT, common.HERE_REL + '/receipts/' + name + '.json'
        out[name] = {'commit': commit, 'path': path, 'raw': raw}
    out['budget_headroom_verified']['sources'] = [SPEND_SOURCE_RAW]
    out['fresh_review_of_this_revision']['facts'] = review_facts()
    return out


def admitted_record(job, receipts=None, **changes):
    receipts = synthetic_receipts(job) if receipts is None else receipts
    record = {'schema': common.ADMISSION_SCHEMA, 'label': common.LABEL, 'state': common.ADMITTED,
              'job_kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED, 'source_sha': common.SOURCE_SHA,
              'job': job, 'owner_authorization': {'state': common.OWNER_AUTHORIZED,
                                                  'records': {name: pin[2]
                                                              for name, pin in common.OWNER_RECORDS.items()}},
              'bindings': common.expected_admission_bindings(FAKE_SOURCES),
              'prerequisites': {name: {'status': 'PASS', 'receipt_commit': receipts[name]['commit'],
                                       'receipt_path': receipts[name]['path'],
                                       'receipt_sha256': digest(receipts[name]['raw']), 'what_passes_it': 'synthetic'}
                                for name in common.REQUIRED_PREREQUISITES},
              'admitted_by': 'Claude technical admission under standing project authorization',
              'admitted_utc': '2026-09-25T10:00:00Z', 'note': 'synthetic'}
    record.update(changes)
    return record


def admission(record, *, owner=common.OWNER_AUTHORIZED, committed=True, job=NEW_JOB, raw=None, freeze=None,
              receipts=None):
    policy, manifest, launch_request = freeze or frozen_policy()
    return common.execution_admission_state(
        enc(record) if raw is None else raw, expected_bindings=common.expected_admission_bindings(FAKE_SOURCES),
        owner_state={'state': owner}, policy=policy, manifest=manifest, launch_request=launch_request,
        committed=committed, job=job, receipts=synthetic_receipts(job) if receipts is None else receipts)


class ExecutionAdmissionTests(unittest.TestCase):
    def test_a_complete_bound_admission_is_admitted(self):
        state = admission(admitted_record(NEW_JOB))
        self.assertEqual((state['state'], state['reasons']), (common.ADMITTED, []))
        self.assertEqual(state['job'], NEW_JOB)
        self.assertEqual(state['spend'], {'spend_so_far_usd': '21.40', 'per_job_bound_usd': '15.00',
                                          'after_this_job_at_most_usd': '36.40', 'ceiling_usd': '60.00'})

    # ---- MAJOR 2 (review of 303c281b): a prerequisite is never self-asserted ----
    def test_pass_plus_any_hex_without_a_committed_receipt_is_refused(self):
        """The reviewer's exact scenario: {'status': 'PASS', 'receipt_sha256': 'c3' * 32} with nothing behind it."""
        record = admitted_record(NEW_JOB)
        for name in common.REQUIRED_PREREQUISITES:
            record['prerequisites'][name]['receipt_sha256'] = 'c3' * 32
        state = admission(record, receipts={})
        self.assertEqual(state['state'], common.NOT_READY)
        for name in common.REQUIRED_PREREQUISITES:
            self.assertIn('PREREQUISITE_RECEIPT_NOT_A_COMMITTED_ANCHORED_BLOB:' + name, state['reasons'])
        state = admission(record)                                      # committed receipts, but other bytes
        for name in common.REQUIRED_PREREQUISITES:
            self.assertIn('PREREQUISITE_RECEIPT_SHA256:' + name, state['reasons'])
        receipts = synthetic_receipts()
        receipts['budget_headroom_verified']['path'] = 'records/elsewhere/spend.json'
        self.assertIn('PREREQUISITE_RECEIPT_NOT_A_COMMITTED_ANCHORED_BLOB:budget_headroom_verified',
                      admission(admitted_record(NEW_JOB), receipts=receipts)['reasons'])

    def assertReceiptRefused(self, name, raw, reason, *, freeze=None):
        receipts = synthetic_receipts(**{name: raw})
        state = admission(admitted_record(NEW_JOB, receipts=receipts), receipts=receipts, freeze=freeze)
        self.assertEqual(state['state'], common.NOT_READY, (name, reason))
        self.assertTrue(any(item.startswith('PREREQUISITE_RECEIPT:' + name + ':' + reason) for item in state['reasons']),
                        (name, reason, state['reasons']))
        self.assertIsNone(state['spend'])
        return state

    def test_a_failed_acceptance_receipt_is_refused_even_when_its_hash_is_written(self):
        name = 'reader_acceptance_on_aws_p1'
        failed = enc(acceptance_receipt(status=common.ACCEPTANCE_FAIL))
        state = self.assertReceiptRefused(name, failed, 'STATUS:READER_ACCEPTANCE_FAIL', freeze=frozen_policy(failed))
        self.assertNotIn('POLICY_READER_ACCEPTANCE_RECEIPT_NOT_FROZEN', state['reasons'])  # the hash WAS written
        cases = acceptance_receipt()['cases']
        for bad, reason in (
                (acceptance_receipt(cases=cases[:-1]), 'CASE_SET_OR_ORDER'),
                (acceptance_receipt(cases=[dict(cases[0], **{'pass': False})] + cases[1:]), 'A_CASE_DID_NOT_PASS'),
                (acceptance_receipt(cases=[dict(case, reference_buffers=['running_mean'])
                                           if case['case'] == 'changed_buffer' else case for case in cases]),
                 'CHANGED_BUFFER_NOT_RECORDED_AS_VACUOUS_WITH_NO_BUFFERS'),
                (acceptance_receipt(sources=dict(FAKE_SOURCES, **{'repro_common.py': '9' * 64})),
                 'NOT_MADE_BY_THE_ADMITTED_READER'),
                (acceptance_receipt(panel_manifest_sha256='0' * 64), 'PANEL_MANIFEST'),
                (acceptance_receipt(environment=dict(RECORDED_ENV, gpu_name='Tesla T4')), 'ENVIRONMENT')):
            raw = enc(bad)
            self.assertReceiptRefused(name, raw, reason, freeze=frozen_policy(raw))

    def test_policy_environment_and_packet_receipts_are_the_files_codex_names(self):
        self.assertReceiptRefused('reproduction_policy_frozen_with_panel_and_reader',
                                  enc(dict(frozen_policy()[0], main_launch_ready=False)),
                                  'NOT_THE_POLICY_THE_GATE_READ')
        receipts = synthetic_receipts()
        receipts['reproduction_policy_frozen_with_panel_and_reader']['commit'] = RECEIPT_COMMIT
        state = admission(admitted_record(NEW_JOB, receipts=receipts), receipts=receipts)
        self.assertIn('PREREQUISITE_RECEIPT:reproduction_policy_frozen_with_panel_and_reader:'
                      'NOT_THE_PINNED_POLICY_FILE', state['reasons'])
        self.assertReceiptRefused('numerical_environment_frozen', b'another lock\n',
                                  'NOT_THE_DEPENDENCY_LOCK_THE_MANIFEST_NAMES')
        policy, manifest, launch_request = frozen_policy()
        not_ready = (policy, dict(manifest, dependencies={'status': 'NOT_READY_FULL_ENVIRONMENT_NOT_FROZEN'}),
                     launch_request)
        self.assertReceiptRefused('numerical_environment_frozen', LOCK_RAW,
                                  'MANIFEST_DEPENDENCIES_STATUS:NOT_READY_FULL_ENVIRONMENT_NOT_FROZEN', freeze=not_ready)
        self.assertReceiptRefused('final_launch_packet_frozen', b'another packet\n', 'NOT_THE_PACKET_THE_MANIFEST_NAMES')

    def test_the_budget_is_read_from_a_spend_record_for_this_job(self):
        name = 'budget_headroom_verified'
        for bad, reason in ((spend_record(measured_spend_so_far_usd='45.01'),
                             'SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING:60.01>60.00'),
                            (spend_record(measured_spend_so_far_usd='21.4O'), 'SPEND_FIGURE_FORM:21.4O'),
                            (spend_record(common.job_name('20260925120001')), 'FOR_ANOTHER_JOB'),
                            (spend_record(sources=[]), 'SOURCES'),
                            (spend_record(study='HELM-OTHER'), 'SCHEMA_FIELDS_LABEL_OR_STUDY'),
                            (spend_record(measured_utc='yesterday'), 'MEASURED_UTC')):
            self.assertReceiptRefused(name, enc(bad), reason)
        self.assertEqual(common.spend_record_violations(spend_record(measured_spend_so_far_usd='45.00'), NEW_JOB,
                                                        opened_sources=[SPEND_SOURCE_RAW],
                                                        admitted_utc='2026-09-25T10:00:00Z'),
                         ([], {'spend_so_far_usd': '45.00', 'per_job_bound_usd': '15.00',
                               'after_this_job_at_most_usd': '60.00', 'ceiling_usd': '60.00'}))

    def test_the_review_receipt_is_a_fresh_reviewers_machine_verdict_on_this_revision(self):
        name = 'fresh_review_of_this_revision'
        for bad, reason in ((review_receipt(verdict='CHANGES_REQUIRED'), 'VERDICT:CHANGES_REQUIRED'),
                            (review_receipt(verdict='APPROVED'), 'VERDICT:APPROVED'),
                            (review_receipt(reviewed_reader_source_sha256='0' * 64), 'NOT_THIS_READER_REVISION'),
                            (review_receipt(reviewed_policy_pins_sha256='0' * 64), 'NOT_THESE_POLICY_PINS'),
                            (review_receipt(reviewer=common.RUNNER), 'REVIEWER_NOT_NAMED_OR_IS_THE_BUILDER'),
                            (review_receipt(model_seed=20260918), 'NOT_THIS_JOB_KIND'),
                            (review_receipt(note='prose'), 'SCHEMA_FIELDS_OR_LABEL')):
            self.assertReceiptRefused(name, enc(bad), reason)

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
        """UPDATED IN REVISION 4. The record is frozen as it was at 3344ae5d (byte-identical, never flipped), so it now
        binds the FROZEN revision-3 reader, not this revision; everything else it binds is unchanged."""
        raw = common.ADMISSION_PATH.read_bytes()
        record = json.loads(raw)
        self.assertEqual(digest(raw), common.FROZEN_ADMISSION_SHA256)
        self.assertEqual(record['state'], common.NOT_READY)
        self.assertIsNone(record['job'])
        frozen_reader = {'read_reproduction.py': '1c8bdfa88f43fd4f63f8b12935499e78abe8974ca9128ca3ad87e5ad5c076f3d',
                         'recompute_reproduction_evidence.py':
                             '0bd93daf7a3c3496549eb2da85af28abffc4e0d0d51ae1232483a6763db71383',
                         'repro_common.py': '4fb2a5e319e2a219bf1f10bd4be60e64ad52af32b6cb9bac14280d3bfd0e683f'}
        self.assertEqual(record['bindings']['reader_sources_sha256'], frozen_reader)
        self.assertNotEqual(record['bindings']['reader_sources_sha256'], common.source_hashes())
        expected = common.expected_admission_bindings()
        for key in expected:
            if key not in ('reader_sources_sha256', 'reader_source_sha256'):
                self.assertEqual(record['bindings'][key], expected[key], key)
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
        if index in refuse:                 # revision 4: a code on the published allowlist (was 'TYPED_MATCHED:X')
            rows.append(recompute.panel_row(record_id, status='REFUSED',
                                            reason='TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:3', prediction=None,
                                            checked=None))
            continue
        prediction = {'record_id': record_id, 'answer': answers[index], 'decisions': DECISIONS[index],
                      'scores': {'s': [0.25 * index]}, 'packet_digest': 'p', 'slot_plan_digest': 'q'}
        checked = {'correct': correct[index], 'kind': answers[index]['kind'], 'record_id': record_id,
                   'prediction_id': 'typed-prediction-' + record_id}
        rows.append(recompute.panel_row(record_id, status='ANSWERED', reason=None, prediction=prediction,
                                        checked=checked))
    return rows


def side(job, sha, *, state=None, metadata=None, rows=None, restore='RESTORED', consistent=True, inference=None,
         buffers=()):
    state = parts() if state is None else state
    value = {'file': {'path': '/opt/in/' + sha[:8] + '.pt', 'sha256': sha, 'bytes': REF_BYTES},
             'payload_keys': list(common.PAYLOAD_KEYS), 'payload_schema': common.CHECKPOINT_SCHEMA,
             'metadata': meta(job) if metadata is None else metadata,
             'producer_identities_consistent': {key: consistent for key in ('model', 'optimizer', 'encoder', 'rng')},
             'restore': {'status': restore, 'reason': None if restore == 'RESTORED' else 'ValueError:LAYOUT',
                         'loader': recompute.LOADER},
             'state_dict_keys': sorted(state['model_state']), 'buffers': list(buffers),
             'inference_mode': dict(common.INFERENCE_MODE) if inference is None else inference,
             'panel': (panel() if rows is None else rows) if restore == 'RESTORED' else [],
             'panel_left_learned_state_unchanged': True}
    for part in common.STATE_PARTS:
        value[part] = recompute.walk_rows(state[part], is_fake, fake_row)
    return value


def evidence(reference=None, candidate=None, *, environment=None, reasons=(), sources=None, candidate_sha=OTHER,
             root=common.HISTORICAL_PACKAGE_ROOT, levels=None, mode='READING'):
    reference = side(common.HELM2_JOB, REF) if reference is None else reference
    candidate = side(NEW_JOB, OTHER) if candidate is None else candidate
    document = recompute.assemble(
        mode, environment=dict(RECORDED_ENV) if environment is None else environment,
        inputs={'package_root': root, 'reference': {'sha256': REF, 'bytes': REF_BYTES},
                'candidate': {'sha256': candidate_sha, 'bytes': REF_BYTES}},
        sides={'reference': reference, 'candidate': candidate}, producer_reasons=list(reasons), manifest=MANIFEST,
        sources=FAKE_SOURCES if sources is None else sources)
    if levels is not None:
        document['producer_levels'] = levels
    return json.loads(recompute.encode(document))


def verdict_of(document, *, job=NEW_JOB, sha=OTHER, reference_record=None, candidate_record=None,
               required_mode='READING'):
    evaluated = reader.evaluate_evidence(document, MANIFEST, expected_candidate_job=job, expected_candidate_sha256=sha,
                                         admitted_sources=FAKE_SOURCES, reference_record_metadata=reference_record,
                                         candidate_record_metadata=candidate_record, required_mode=required_mode)
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
                side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, counters=1471))):
            self.assertVerdict(evidence(candidate=candidate), REPRODUCED,
                               {'continuation': 'CONTINUATION_DIFFERENT', 'learned_state': 'LEARNED_STATE_IDENTICAL'})

    def test_a_different_starting_state_is_training_configuration_so_invalid(self):
        """Review finding 8 (revision 3): the starting state is a frozen pre-update check, not continuation."""
        self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, metadata=meta(NEW_JOB, initial='j' * 64))),
                           INVALID, reason='TRAINING_CONFIGURATION_DIFFERS:run_identity.initial_model_identity')

    # ---- DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY (valid evidence) ----
    def test_every_learned_state_difference_is_a_valid_mismatch(self):
        """Reader semantics on COMPLETE evidence. 'extra key', 'missing key' and 'dtype change' here assume a loader
        that accepted the checkpoint; the pinned historical loader refuses the last two (next test)."""
        cases = {
            'changed value': parts(model_state=lambda m: {**m, 'round_rate': T(0.5000001)}),
            'extra key': parts(model_state=lambda m: {**m, 'running_mean': T(1.0)}),
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

    def test_a_changed_buffer_is_a_valid_mismatch_SYNTHETIC(self):
        """Review MINOR 6. SYNTHETIC: the historical architecture has no buffers (changed-buffer is VACUOUS there).
        A persistent buffer is an ordinary model_state row and is compared exactly like a parameter."""
        with_buffer = parts(model_state=lambda m: {**m, 'running_mean': T(1.0)})
        changed = parts(model_state=lambda m: {**m, 'running_mean': T(2.0)})
        reference = side(common.HELM2_JOB, REF, state=with_buffer, buffers=['running_mean'])
        self.assertVerdict(evidence(reference=reference, candidate=side(NEW_JOB, OTHER, state=with_buffer,
                                                                        buffers=['running_mean'])), REPRODUCED)
        evaluated = self.assertVerdict(
            evidence(reference=reference, candidate=side(NEW_JOB, OTHER, state=changed, buffers=['running_mean'])),
            DOES_NOT_REPRODUCE, {'learned_state': 'LEARNED_STATE_DIFFERENT', 'output': 'OUTPUT_REPRODUCED'})
        self.assertEqual([row['path'] for row in evaluated['differences']['learned_state_rows']],
                         [['str:running_mean']])
        self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, buffers=['not_in_the_state'])), INVALID,
                           reason='CANDIDATE_BUFFER_NOT_IN_THE_STATE_INVENTORY')

    def test_missing_key_and_dtype_change_as_the_pinned_loader_treats_them(self):
        """Review NOTE 9: `restore_checkpoint` at 20208c92 refuses both (strict layout fingerprint and restored-identity
        check), so no panel evidence can exist: ADMISSION_INVALID_STOP, the same answer the AWS acceptance registers.
        The two readings differ only in whether a loader accepted the checkpoint. Open question 3 stays with Codex."""
        for state in (parts(model_state=lambda m: {'left.weight': m['left.weight']}),
                      parts(model_state=lambda m: {**m, 'round_rate': T(0.5, dtype='torch.float64')})):
            self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, state=state, restore='REFUSED')), INVALID,
                               {'learned_state': 'LEARNED_STATE_DIFFERENT'},
                               reason='CANDIDATE_RESTORE_REFUSED_BY_THE_HISTORICAL_LOADER')
        specs = {case: verdict for case, _, verdict, _ in recompute.acceptance_specs(None)}
        self.assertEqual((specs['missing_key'], specs['dtype_change']), (INVALID, INVALID))

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

    def test_infrastructure_faults_are_invalid_never_a_mismatch(self):
        """Review MAJOR 3: a CUDA fault or out-of-memory partway through the candidate panel, AFTER the reference panel
        reproduced, must read ADMISSION_INVALID_STOP (no fallback), not DOES_NOT_REPRODUCE."""
        faulted = panel()
        for index in (1, 2):                                    # the remaining rows after a device fault
            faulted[index] = recompute.panel_row(IDS[index], status='ERROR', reason='AcceleratorError:CUDA error',
                                                 prediction=None, checked=None)
        # Even if a producer failed to report it, the reader refuses the rows by itself.
        self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, rows=faulted)), INVALID,
                           reason='CANDIDATE_PANEL_INFRASTRUCTURE_FAULT_ROWS:2')
        self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, rows=faulted),
                                    reasons=['CANDIDATE_PANEL_INFRASTRUCTURE_FAULTS:2:first=typed-input-b:x']),
                           INVALID, reason='PRODUCER_REPORTED')
        uncoded = panel()
        uncoded[0] = recompute.panel_row(IDS[0], status='REFUSED', reason='ValueError:math domain error',
                                         prediction=None, checked=None)
        self.assertVerdict(evidence(candidate=side(NEW_JOB, OTHER, rows=uncoded)), INVALID,
                           reason='CANDIDATE_PANEL_REFUSAL_WITHOUT_A_HISTORICAL_CODE:1')
        grader = panel()
        grader[2] = recompute.panel_row(IDS[2], status='ERROR', reason='GRADER:KeyError:kind', prediction=None,
                                        checked=None)
        self.assertVerdict(evidence(reference=side(common.HELM2_JOB, REF, rows=grader)), INVALID,
                           reason='REFERENCE_PANEL_INFRASTRUCTURE_FAULT_ROWS:1')

    def test_acceptance_mode_evidence_is_not_a_reading(self):
        """Review NOTE 11: the production reading requires mode READING; the acceptance requires ACCEPTANCE."""
        self.assertVerdict(evidence(mode='ACCEPTANCE'), INVALID, reason='EVIDENCE_MODE_IS_NOT:READING')
        self.assertVerdict(evidence(), INVALID, reason='EVIDENCE_MODE_IS_NOT:ACCEPTANCE', required_mode='ACCEPTANCE')
        self.assertVerdict(evidence(mode='ACCEPTANCE'), REPRODUCED, required_mode='ACCEPTANCE')

    def test_the_evidence_must_carry_these_policy_pins_and_the_recorded_environment(self):
        document = evidence()
        document['policy']['policy_pins_sha256'] = '0' * 64
        self.assertVerdict(document, INVALID, reason='EVIDENCE_POLICY_OR_PINS')
        unrecorded = {key: value for key, value in RECORDED_ENV.items() if key != 'driver_version'}
        self.assertVerdict(evidence(environment=unrecorded), INVALID, reason='ENVIRONMENT_NOT_RECORDED:driver_version')
        _, _, evaluated = verdict_of(evidence())
        self.assertEqual(evaluated['environment_recorded_not_pinned']['python_version'], '3.12.3')

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
        for case in ('self_identity', 'changed_buffer', 'state_equal_output_tampered', 'corrupt_reference'):
            self.assertIn("'" + case + "'", source)
        # every registered case is built somewhere, and the receipt passes only with the full registered list
        self.assertEqual(set(common.ACCEPTANCE_CASES), set(table) | {'self_identity', 'changed_buffer',
                                                                     'state_equal_output_tampered',
                                                                     'corrupt_reference'})
        self.assertEqual(len(common.ACCEPTANCE_CASES), 11)
        self.assertEqual(list(common.ACCEPTANCE_CASES[1:8]), list(table))          # the recorded order
        self.assertIn('common.ACCEPTANCE_CASES', source)
        self.assertIn('VACUOUS', source)

    def test_prediction_errors_are_split_into_refusals_and_infrastructure_faults(self):
        """Review MAJOR 3: only a plain ValueError with a historical code is a refusal."""
        self.assertEqual(recompute.classify_prediction_error(ValueError('POINTER_SLOT_COVERAGE')),
                         ('REFUSED', 'POINTER_SLOT_COVERAGE'))
        self.assertEqual(recompute.classify_prediction_error(ValueError('TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:3')),
                         ('REFUSED', 'TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:3'))
        for error in (RuntimeError('CUDA error: an illegal memory access was encountered'), MemoryError('oom'),
                      ValueError('math domain error'), TypeError('POINTER_SLOT_COVERAGE'),
                      recompute.UnsupportedValue('TYPED_X'), KeyError('answer')):
            status, reason = recompute.classify_prediction_error(error)
            self.assertEqual(status, 'ERROR', error)
            self.assertTrue(reason.startswith(type(error).__name__ + ':'), reason)
        source = ast.unparse(function(HERE / 'recompute_reproduction_evidence.py', 'run_panel'))
        self.assertIn('classify_prediction_error', source)
        self.assertNotIn('except ValueError', source)                   # no bare ValueError-means-refusal any more
        self.assertIn('_PANEL_INFRASTRUCTURE_FAULTS', ast.unparse(function(HERE / 'recompute_reproduction_evidence.py',
                                                                           'load_side')))


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
            common.CHECKPOINT_RECORD: checkpoint, reader.WORKER_REPORT: enc({'runtime': RUNTIME}),
            common.PREFLIGHT_RECORD: enc(PREFLIGHT_OK)}


REQUEST = {'schema': 'cncm.typed-pointer-request/0.1', 'job': NEW_JOB, 'source_sha': common.SOURCE_SHA,
           'archive_sha256': common.ARCHIVE_SHA256, 'manifest_sha256': common.MANIFEST_SHA256,
           'launch_authorized': False}


def reference_files(value=REF, **options):
    return record_set(common.HELM2_JOB, value, REF_BYTES, metadata=meta(common.HELM2_JOB), **options)


ADMISSION_SHA = '9' * 64


def frozen_files(job=NEW_JOB, state=common.ADMITTED, sources=None, rule=None, pins=None):
    sources = FAKE_SOURCES if sources is None else sources
    study = {'status': 'FROZEN_BEFORE_FIRST_RUN', 'source_sha': common.SOURCE_SHA,
             'reading_rule': common.reading_rule_record() if rule is None else rule,
             'execution_admission': {'state': state, 'job': job, 'record_sha256': ADMISSION_SHA, 'bindings': {
                 'reader_sources_sha256': sources, 'reader_source_sha256': common.reader_source_digest(sources),
                 'policy_pins_sha256': common.PINS_SHA256 if pins is None else pins}},
             'jobs': [{'job': job, 'kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED}]}
    return {'study.json': enc(study), '20260917/request.json': enc(dict(REQUEST, job=job))}


def receipt_files(value=OTHER, size=REF_BYTES, *, delivered=True, drop=(), overrides=None, job=NEW_JOB,
                  request=None, **options):
    request = REQUEST if request is None else request
    files = {'result.json': enc({'job': job, 'request': request, 'completed_deliverable': delivered,
                                 'status': 'AWS_CANDIDATE_FINISHED', 'cleanup': {'complete': True}}),
             'reduced_schedule.json': enc({'job': job, 'reduced_schedule': None}),
             'collected/results/result.json': enc({'job': job, 'status': 'TYPED_POINTER_DELIVERED',
                                                   'summary': {'schedule_plan_mode': 'REGISTERED'}}),
             common.SHIPPED_PACKAGE_RECORD: ARCHIVE_RAW,
             **record_set(job, value, size, metadata=meta(job), **options)}
    files.update(overrides or {})
    for name in drop:
        files.pop(name, None)
    return files


def admitted_state(job=NEW_JOB, **changes):
    """EXECUTION_ADMISSION.json as `committed_admission_state` would evaluate it at the receipt commit (synthetic)."""
    return dict({'state': common.ADMITTED, 'recorded_state': common.ADMITTED, 'reasons': [],
                 'record_sha256': ADMISSION_SHA, 'job': job, 'spend': None}, **changes)


FROZEN_BLOBS = {name: (str(index) * 40) for index, name in enumerate(common.FROZEN_FILES, start=4)}
HISTORY = {'freeze_commits': ['1' * 40], 'evidence_commits': ['2' * 40], 'receipt_result_commits': ['3' * 40],
           'freeze_has_receipt': False, 'freeze_has_evidence': False, 'freeze_precedes_receipt': True,
           'freeze_precedes_evidence': True, 'admission_blob_at_freeze': 'a' * 40,
           'admission_blob_at_receipt': 'a' * 40,
           # revision 4 (fix 2): merge-inclusive facts, clean
           'blob_versions': {'evidence': ['b' * 40], 'receipt_result': ['c' * 40], 'eligibility': [],
                             **{name: [blob] for name, blob in FROZEN_BLOBS.items()}},
           'after_freeze_changes': {'admission': [], **{name: [] for name in common.FROZEN_FILES}},
           'frozen_blobs_at_freeze': dict(FROZEN_BLOBS), 'eligibility_commits': [],
           'eligibility_follows_freeze': False, 'eligibility_precedes_evidence': False,
           'eligibility_has_evidence': None}


def run(reference=None, frozen=None, receipt=None, document=None, sources=None, state=None, history=None,
        eligibility=None):
    reference = reference_files() if reference is None else reference
    frozen = frozen_files() if frozen is None else frozen
    receipt = receipt_files() if receipt is None else receipt
    raw = recompute.encode(evidence() if document is None else document) if document != 'ABSENT' else None
    return reader.reading(reference.get, frozen.get, receipt.get, lambda: raw, MANIFEST, receipt_commit='c' * 40,
                          running_sources=FAKE_SOURCES if sources is None else sources,
                          admission_state=admitted_state() if state is None else state,
                          history=dict(HISTORY) if history is None else history, eligibility=eligibility)


@unittest.skipUnless(ARCHIVE_RAW is not None, 'package archive not in this checkout')
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

    def test_the_admission_at_the_receipt_commit_decides_not_the_frozen_copy(self):
        """Review MINOR 4: a hand-written frozen/ folder that claims ADMITTED is not enough."""
        cases = [
            (run(state=admitted_state(state=common.NOT_READY, reasons=['ADMISSION_STATE_IS:NOT_READY'])),
             'EXECUTION_ADMISSION_AT_THE_RECEIPT_COMMIT_IS_NOT_ADMITTED:ADMISSION_STATE_IS:NOT_READY'),
            (run(state=admitted_state(record_sha256='8' * 64)), 'FROZEN_ADMISSION_IS_NOT_THE_COMMITTED_ADMISSION_RECORD'),
            (run(state=admitted_state(job=common.job_name('20260925120001'))),
             'FROZEN_ADMISSION_IS_NOT_THE_COMMITTED_ADMISSION_RECORD'),
            (run(state={}), 'EXECUTION_ADMISSION_AT_THE_RECEIPT_COMMIT_IS_NOT_ADMITTED:NOT_EVALUATED'),
            (run(frozen=frozen_files(pins='0' * 64)), 'FROZEN_UNDER_OTHER_POLICY_PINS'),
        ]
        for record, reason in cases:
            self.assertInvalid(record, reason)
        record = run()
        self.assertEqual(record['execution_admission_at_receipt_commit']['record_sha256'], ADMISSION_SHA)
        self.assertEqual(record['policy_pins_sha256'], common.PINS_SHA256)

    def test_frozen_before_the_result_and_one_version_of_the_evidence(self):
        """Review MINOR 5: a regenerated evidence file, or a freeze after the result, reads ADMISSION_INVALID_STOP."""
        for change, reason in (({'evidence_commits': ['2' * 40, '4' * 40]}, 'EVIDENCE_NOT_EXACTLY_ONE_COMMITTED_VERSION:2'),
                               ({'receipt_result_commits': []}, 'RECEIPT_RESULT_NOT_EXACTLY_ONE_COMMITTED_VERSION:0'),
                               ({'freeze_commits': ['1' * 40, '5' * 40]}, 'FROZEN_RECORDS_NOT_IN_EXACTLY_ONE_COMMIT:2'),
                               ({'freeze_has_evidence': True}, 'FROZEN_IN_A_COMMIT_THAT_ALREADY_HELD_THE_RESULT'),
                               ({'freeze_precedes_evidence': False}, 'FREEZE_IS_NOT_AN_ANCESTOR_OF_THE_RESULT'),
                               ({'admission_blob_at_receipt': 'b' * 40}, 'ADMISSION_RECORD_CHANGED_AFTER_THE_FREEZE')):
            self.assertInvalid(run(history=dict(HISTORY, **change)), reason)
        self.assertInvalid(run(history={}), 'FROZEN_RECORDS_NOT_IN_EXACTLY_ONE_COMMIT:None')
        record = run()
        self.assertEqual(record['recorded_by_commit'], {'receipt_commit': 'c' * 40, 'freeze_commit': '1' * 40,
                                                        'evidence_commit': '2' * 40, 'receipt_result_commit': '3' * 40})

    def test_the_training_machine_and_the_shipped_package(self):
        """Review MINOR 7: both receipts' preflight AMI; the new receipt's shipped archive and requirements file."""
        self.assertInvalid(run(receipt=receipt_files(overrides={common.PREFLIGHT_RECORD: enc(dict(
            PREFLIGHT_OK, ami='ami-0123456789abcdef0'))})),
            'CANDIDATE_TRAINING_MACHINE_NOT_THE_HISTORICAL_ONE:ami=ami-0123456789abcdef0')
        self.assertInvalid(run(receipt=receipt_files(drop=(common.PREFLIGHT_RECORD,))),
                           'CANDIDATE_TRAINING_MACHINE_NOT_THE_HISTORICAL_ONE')
        reference = reference_files()
        reference[common.PREFLIGHT_RECORD] = enc(dict(PREFLIGHT_OK, region='us-east-1'))
        self.assertInvalid(run(reference=reference), 'REFERENCE_TRAINING_MACHINE_NOT_THE_PINNED_ONE:region=us-east-1')
        self.assertInvalid(run(receipt=receipt_files(overrides={common.SHIPPED_PACKAGE_RECORD: b'PK\x05\x06' + bytes(18)})),
                           'CANDIDATE_SHIPPED_PACKAGE:SHIPPED_PACKAGE_IS_NOT_THE_PINNED_ARCHIVE')
        self.assertInvalid(run(receipt=receipt_files(drop=(common.SHIPPED_PACKAGE_RECORD,))),
                           'CANDIDATE_SHIPPED_PACKAGE:SHIPPED_PACKAGE_ABSENT')


class HistoryTests(unittest.TestCase):
    """The frozen-before-result facts (review MINOR 5): pure rule, plus real `git log` on this branch."""

    def test_the_pure_rule(self):
        """UPDATED IN REVISION 4: the six revision-3 reasons, plus the merge-inclusive ones (fix 2), for no facts."""
        self.assertEqual(reader.history_violations(HISTORY), [])
        found = reader.history_violations(None)
        self.assertEqual(len([item for item in found if 'INCLUDING_MERGES' not in item]), 6)
        self.assertEqual(len([item for item in found if 'INCLUDING_MERGES' in item]),
                         2 * len(common.FROZEN_FILES) + 3)

    @unittest.skipUnless(git_has('HEAD', common.HERE_REL + '/repro_common.py'), 'this folder is not committed here')
    def test_git_log_pathspecs_resolve_from_the_cncm_root(self):
        """UPDATED IN REVISION 4 (this test encoded the PRE-FREEZE state: 'nothing frozen'). This branch starts at the
        freeze 3344ae5d, so the frozen records sit in exactly that one commit; there is no receipt or evidence yet."""
        touched = reader.commits_touching('HEAD', common.HERE_REL + '/repro_common.py')
        self.assertGreaterEqual(len(touched), 1)
        self.assertTrue(all(common.is_hex(commit, 40) for commit in touched))
        history = reader.collect_history('HEAD')
        self.assertEqual((history['freeze_commits'], history['evidence_commits'], history['receipt_result_commits']),
                         ([common.FREEZE_COMMIT], [], []))
        self.assertEqual(history['blob_versions']['frozen/study.json'],
                         [common.blob_id(common.FREEZE_COMMIT, common.HERE_REL + '/frozen/study.json')])
        self.assertIsNotNone(history['admission_blob_at_freeze'])
        self.assertEqual(history['admission_blob_at_freeze'], history['admission_blob_at_receipt'])
        found = reader.history_violations(history)
        self.assertNotIn('FROZEN_RECORDS_NOT_IN_EXACTLY_ONE_COMMIT:1', found)
        self.assertNotIn('ADMISSION_RECORD_CHANGED_AFTER_THE_FREEZE', found)
        self.assertIn('EVIDENCE_NOT_EXACTLY_ONE_COMMITTED_VERSION:0', found)


class ReceiptReaderTests(unittest.TestCase):
    """`read_prerequisite_receipts` against real git: only committed blobs at anchored commits are opened."""

    @unittest.skipUnless(git_has('HEAD', common.HERE_REL + '/repro_common.py'), 'this folder is not committed here')
    def test_anchoring_and_path_form(self):
        head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
        relative = common.HERE_REL + '/repro_common.py'

        def record(commit, path):
            entry = {'status': 'PASS', 'receipt_commit': commit, 'receipt_path': path, 'receipt_sha256': '0' * 64,
                     'what_passes_it': 'test'}
            return enc({'prerequisites': {name: entry for name in common.REQUIRED_PREREQUISITES}})
        found = common.read_prerequisite_receipts(record(head, relative), anchors=('HEAD',))
        self.assertEqual(set(found), set(common.REQUIRED_PREREQUISITES))
        self.assertEqual(found['budget_headroom_verified']['raw'], common.show(head, relative))
        self.assertEqual(common.read_prerequisite_receipts(record(head, '../' + relative), anchors=('HEAD',)), {})
        self.assertEqual(common.read_prerequisite_receipts(record(head, relative + '.missing'), anchors=('HEAD',)), {})
        self.assertEqual(common.read_prerequisite_receipts(record('0' * 40, relative), anchors=('HEAD',)), {})
        self.assertEqual(common.read_prerequisite_receipts(b'not json', anchors=('HEAD',)), {})
        if git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected_inventory.json') and not \
                common.git_ok('merge-base', '--is-ancestor', common.REFERENCE_COMMIT, 'HEAD'):
            unanchored = record(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected_inventory.json')
            self.assertEqual(common.read_prerequisite_receipts(unanchored, anchors=('HEAD',)), {})


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
        found, summary = common.spend_violations('45.00')
        self.assertEqual((found, summary['after_this_job_at_most_usd']), ([], '60.00'))
        found, summary = common.spend_violations('45.01')
        self.assertEqual(found, ['SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING:60.01>60.00'])
        for bad in (None, '', '-1', '1e3', 'NaN', 'inf', '12.345', ' 12', '12,00', '99999', 21.4):
            found, summary = common.spend_violations(bad)
            self.assertTrue(found[0].startswith('SPEND_FIGURE_FORM'), bad)
            self.assertIsNone(summary)

    def test_check_takes_no_typed_spend_figure(self):
        """Review MAJOR 2: --check reads the spend from the admitted spend record, never from operator text."""
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                prepare.main(['--check', '--study-sha256', '0' * 64, '--spend-so-far-usd', '1.00'])
        source = ast.unparse(function(HERE / 'prepare_unchanged_repro.py', 'check_before_launch'))
        self.assertIn("gate['execution_admission'].get('spend')", source)
        self.assertNotIn('spend_so_far_usd', source)


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
        for name in ('committed_admission_state', 'collect_history'):          # revision 3: MINOR 4 and MINOR 5
            self.assertLess(order.index(name), order.index('reading'), name)
        main_source = ast.unparse(function(HERE / 'read_reproduction.py', 'main'))
        self.assertIn('common.PINS_RAW', main_source)                           # pins at the receipt commit
        self.assertIn("required_mode='READING'", ast.unparse(function(HERE / 'read_reproduction.py', 'reading')))
        state_source = ast.unparse(function(HERE / 'read_reproduction.py', 'committed_admission_state'))
        self.assertIn('read_prerequisite_receipts', state_source)
        gate_source = ast.unparse(function(HERE / 'prepare_unchanged_repro.py', 'gates'))
        self.assertIn('read_prerequisite_receipts', gate_source)

    def test_this_folder_s_files_are_ascii_and_lf(self):
        for path in list(HERE.glob('*.py')) + list(HERE.glob('*.md')) + list(HERE.glob('*.json')):
            raw = path.read_bytes()
            self.assertNotIn(b'\r', raw, path.name)
            self.assertTrue(raw.isascii(), path.name)


# =====================================================================================================================
# REVISION 4: one test per fix (Codex READER_STATIC_REVIEW_20260924 fixes 1-7), the eligibility route, decide().
# =====================================================================================================================
def lock_document(**changes):
    """A synthetic `helm.reproduction-environment/1` lock that matches RECORDED_ENV and the training RUNTIME."""
    lock = {'schema': common.ENVIRONMENT_LOCK_SCHEMA, 'status': common.ENVIRONMENT_LOCK_STATUS,
            'source_commit': '5' * 40,
            'image': {'provider': 'aws', 'region': 'us-west-2', 'ami_id': common.HISTORICAL_AMI},
            'runtime': {'python_implementation': 'CPython', 'python_version': '3.12.3', 'os': 'Linux',
                        'kernel': '6.8.0-1024-aws', 'machine': 'x86_64'},
            'accelerator': {'instance_type': 'g7.2xlarge', 'gpu_model': common.NUMERICAL_ENVIRONMENT['gpu_name'],
                            'compute_capability': '12.0', 'driver_version': '580.65.06'},
            'libraries': {'torch': '2.11.0+cu128', 'cuda_runtime': '12.8', 'cudnn': '9.10.2',
                          'packages': [{'name': 'torch', 'version': '2.11.0+cu128', 'sha256': 'a' * 64}]},
            'numerics': {'dtype': 'float32', 'deterministic_algorithms': True, 'matmul_allow_tf32': False,
                         'cudnn_allow_tf32': False, 'float32_matmul_precision': 'highest',
                         'seeds': {'model': 20260917}, 'thread_counts': {'torch': 8},
                         'environment_variables': {'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}},
            # revision 5 (Codex R3-I, Q-G): EVERY lock field required-equal; only envelope fields are diagnostic
            'comparison': {'required_equal': list(common.ENVIRONMENT_LOCK_LEAVES),
                           'diagnostic_only': [{'path': 'envelope.instance_id',
                                                'reason': 'hardware instance ID: differs every run, predicts nothing'}]}}
    for path, value in changes.items():
        section, key = path.split('.') if '.' in path else (path, None)
        if key is None:
            lock[section] = value
        else:
            lock[section][key] = value
    return lock


LOCK = lock_document()


class RevisionFourFixTests(unittest.TestCase):
    # ---- fix 1 (Codex R3-B): the COMPLETE message, against the published allowlist, before any truncation ----
    def test_fix1_the_complete_message_is_validated_before_any_truncation(self):
        status, reason = recompute.classify_prediction_error(ValueError('POINTER_' + 'A' * 292 + '\nCUDA fault'))
        self.assertEqual(status, 'ERROR')
        self.assertEqual(reason, 'ValueError:' + ('POINTER_' + 'A' * 292 + '\nCUDA fault')[:300])  # display only
        for message in ('POINTER_SLOT_COVERAGE extra prose', 'POINTER_SLOT_COVERAGE\n', 'TYPED_MATCHED:X'):
            self.assertEqual(recompute.classify_prediction_error(ValueError(message))[0], 'ERROR', message)
        self.assertEqual(recompute.classify_prediction_error(ValueError('POINTER_SLOT_COVERAGE')),
                         ('REFUSED', 'POINTER_SLOT_COVERAGE'))
        # A coded ValueError followed by a CUDA fault reads INVALID, never REFUSED and never DOES_NOT_REPRODUCE.
        rows = panel()
        rows[1] = recompute.panel_row(IDS[1], status=status, reason=reason, prediction=None, checked=None)
        verdict, _, evaluated = verdict_of(evidence(candidate=side(NEW_JOB, OTHER, rows=rows)))
        self.assertEqual(verdict, INVALID)
        self.assertIn('CANDIDATE_PANEL_INFRASTRUCTURE_FAULT_ROWS:1', evaluated['invalid_reasons'])
        rows = panel()                                  # a REFUSED row carrying a truncated coded display
        rows[1] = recompute.panel_row(IDS[1], status='REFUSED', reason='POINTER_' + 'A' * 292, prediction=None,
                                      checked=None)
        verdict, _, evaluated = verdict_of(evidence(candidate=side(NEW_JOB, OTHER, rows=rows)))
        self.assertEqual(verdict, INVALID)
        self.assertIn('CANDIDATE_PANEL_REFUSAL_WITHOUT_A_HISTORICAL_CODE:1', evaluated['invalid_reasons'])

    @unittest.skipUnless(git_has(common.PACKAGE_COMMIT, common.PACKAGE_REL + '/source.zip'), 'package commit absent')
    def test_fix1_the_published_allowlist_rebuilds_from_the_pinned_archive(self):
        import build_refusal_allowlist
        self.assertEqual(build_refusal_allowlist.encode(build_refusal_allowlist.build()), common.REFUSAL_ALLOWLIST_RAW)
        document = json.loads(common.REFUSAL_ALLOWLIST_RAW)
        self.assertEqual(common.refusal_allowlist_violations(document), [])
        self.assertEqual((document['source']['archive_sha256'], document['unresolved']), (common.ARCHIVE_SHA256, []))
        self.assertIn(common.REFUSAL_ALLOWLIST_NAME, common.READER_SOURCE_FILES)          # covered by the digest
        self.assertEqual(common.source_hashes()[common.REFUSAL_ALLOWLIST_NAME], common.REFUSAL_ALLOWLIST_SHA256)

    # ---- fix 2 (Codex R3-G): merge commits are counted, and an edit inside a merge is caught (real git) ----
    def test_fix2_an_edit_made_inside_a_merge_is_caught(self):
        with tempfile.TemporaryDirectory() as scratch:
            repo = Path(scratch)

            def g(*args):
                return subprocess.run(['git', '-c', 'user.name=reader-test', '-c', 'user.email=reader-test@invalid',
                                       '-c', 'core.autocrlf=false', *args], cwd=str(repo), check=True,
                                      capture_output=True, timeout=60).stdout.decode('utf-8').strip()
            g('init', '-q')
            (repo / 'evidence.json').write_bytes(b'{"v": 1}\n')
            g('add', 'evidence.json')
            g('commit', '-q', '-m', 'evidence, one version')
            first = g('rev-parse', 'HEAD')
            g('checkout', '-q', '-b', 'side')
            (repo / 'side.txt').write_bytes(b'side\n')
            g('add', 'side.txt')
            g('commit', '-q', '-m', 'side')
            g('checkout', '-q', first)
            (repo / 'main.txt').write_bytes(b'main\n')
            g('add', 'main.txt')
            g('commit', '-q', '-m', 'main')
            g('merge', '-q', '--no-ff', '--no-commit', 'side')
            (repo / 'evidence.json').write_bytes(b'{"v": 2}\n')              # the edit inside the merge
            g('add', 'evidence.json')
            g('commit', '-q', '-m', 'merge that rewrites the evidence')
            tip = g('rev-parse', 'HEAD')
            self.assertEqual(len(g('rev-parse', tip + '^@').split()), 2)
            counted = g('log', '--format=%H', '--full-history', '--no-merges', tip, '--', 'evidence.json').split()
            self.assertEqual(counted, [first])                               # revision 3 saw ONE version
            versions = sorted(set(reader.blob_changes([tip], ['evidence.json'], cwd=repo)['evidence.json'])
                              - {reader.ZERO_BLOB})
            self.assertEqual(len(versions), 2)                               # revision 4 sees the merge edit
            after = reader.blob_changes([first + '..' + tip], ['evidence.json'], ancestry_path=True, cwd=repo)
            self.assertTrue(after['evidence.json'])
        history = dict(HISTORY, blob_versions=dict(HISTORY['blob_versions'], evidence=versions))
        self.assertIn('NOT_ONE_BLOB_VERSION_INCLUDING_MERGES:evidence:2', reader.history_violations(history))
        history = dict(HISTORY, after_freeze_changes=dict(HISTORY['after_freeze_changes'], admission=['b' * 40]))
        self.assertIn('CHANGED_AFTER_THE_FREEZE_INCLUDING_MERGES:admission', reader.history_violations(history))
        self.assertInvalidReading(history, 'NOT_ONE_BLOB_VERSION_INCLUDING_MERGES:frozen/study.json:2',
                                  blob_versions=dict(HISTORY['blob_versions'],
                                                     **{'frozen/study.json': ['4' * 40, '9' * 40]}))

    def assertInvalidReading(self, _, reason, **changes):
        if ARCHIVE_RAW is None:
            self.skipTest('package archive not in this checkout')
        record = run(history=dict(HISTORY, **changes))
        self.assertEqual(record['verdict'], INVALID)
        self.assertIn(reason, record['invalid_reasons'])

    # ---- fix 3 (Codex R3-G): a missing pinned object is a recoverable TOOL_STOP (exit 1) before evaluation ----
    def test_fix3_a_missing_owner_object_is_a_tool_stop_with_exit_1(self):
        specs = reader.fixed_object_specs()
        self.assertEqual({label for label, _, _ in specs if label.startswith('owner:')},
                         {'owner:' + name for name in common.OWNER_RECORDS})
        owner_commit = common.OWNER_RECORDS['claude_extension_md'][0]
        with self.assertRaises(SystemExit) as caught:
            reader.require_objects(specs, exists=lambda commit, relative: commit != owner_commit)
        code = caught.exception.code
        self.assertIsInstance(code, str)                                    # a string code exits with status 1
        self.assertTrue(code.startswith('UNCHANGED_REPRO_READING_STOPPED:PINNED_OBJECT_MISSING:owner:'
                                        'claude_extension_md:' + owner_commit), code)
        self.assertIn('no verdict was recorded', code)
        reader.require_objects(specs, exists=lambda commit, relative: True)
        # A real process: a commit git does not hold stops with exit status 1 and prints the named stop.
        probe = ('import sys; sys.path.insert(0, %r); import read_reproduction as r; '
                 "r.require_objects([('owner:probe', '%s', None)])" % (str(HERE), '0' * 40))
        done = subprocess.run([sys.executable, '-B', '-c', probe], capture_output=True, timeout=120)
        self.assertEqual(done.returncode, 1)
        self.assertIn(b'PINNED_OBJECT_MISSING:owner:probe', done.stderr)
        # The stops run in main() before the admission is evaluated and before any reading.
        order = [name for _, name in calls(function(HERE / 'read_reproduction.py', 'main'))]
        for name in ('require_objects', 'fetch_and_require_on_branch'):
            self.assertLess(order.index(name), order.index('committed_admission_state'), name)
            self.assertLess(order.index(name), order.index('reading'), name)

    @unittest.skipUnless(OWNER_PRESENT and git_has(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL
                                                   + '/collected_inventory.json'), 'pinned commits not fetched')
    def test_fix3_the_real_pinned_objects_are_present_here(self):
        reader.require_objects(reader.fixed_object_specs())

    # ---- fix 4: the spend sources are opened and the figure is fresh ----
    def test_fix4_spend_sources_are_opened_and_the_figure_is_fresh(self):
        admitted = '2026-09-25T10:00:00Z'

        def check(record, sources=(SPEND_SOURCE_RAW,), at=admitted):
            return common.spend_record_violations(record, NEW_JOB, opened_sources=list(sources), admitted_utc=at)[0]
        self.assertEqual(check(spend_record()), [])
        self.assertIn('SOURCE_NOT_OPENED_AS_A_COMMITTED_ANCHORED_BLOB:0', check(spend_record(), sources=(None,)))
        self.assertIn('SOURCE_SHA256:0', check(spend_record(), sources=(b'other bytes\n',)))
        self.assertIn('STALE:420_SECONDS', check(spend_record(measured_utc='2026-09-25T09:53:00Z')))
        self.assertIn('MEASURED_AFTER_THE_ADMISSION', check(spend_record(measured_utc='2026-09-25T10:00:01Z')))
        self.assertIn('FRESHNESS_NOT_ESTABLISHED:NO_ADMISSION_TIME', check(spend_record(), at=None))
        self.assertIn('SOURCES', check(spend_record(sources=[{'path': 'records/x.json', 'sha256': 'f' * 64}])))
        receipts = synthetic_receipts()
        receipts['budget_headroom_verified']['sources'] = [None]
        state = admission(admitted_record(NEW_JOB), receipts=receipts)
        self.assertEqual(state['state'], common.NOT_READY)
        self.assertIn('PREREQUISITE_RECEIPT:budget_headroom_verified:SOURCE_NOT_OPENED_AS_A_COMMITTED_ANCHORED_BLOB:0',
                      state['reasons'])
        if git_has('HEAD', common.HERE_REL + '/repro_common.py'):           # the real opener: anchored blobs only
            relative = common.HERE_REL + '/repro_common.py'
            head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
            self.assertEqual(common.anchored_blob(head, relative, ('HEAD',)), common.show(head, relative))
            self.assertIsNone(common.anchored_blob('0' * 40, relative, ('HEAD',)))

    # ---- fix 5 (Codex R3-H): the review resolves its PUSHED commit and binds the complete closure and the writers ----
    def test_fix5_the_review_resolves_a_pushed_commit_and_binds_the_writers(self):
        bindings = common.expected_admission_bindings(FAKE_SOURCES)
        self.assertEqual(common.review_receipt_violations(review_receipt(), bindings, review_facts()), [])
        self.assertTrue(set(common.WRITER_FILES) <= set(common.REVIEW_CLOSURE_FILES))
        for facts, reason in (
                (review_facts(reviewed_commit_resolves=False), 'REVIEWED_COMMIT_NOT_RESOLVED'),
                (review_facts(reviewed_commit_pushed=False), 'REVIEWED_COMMIT_NOT_ON_THE_FETCHED_REVIEWED_BRANCH'),
                (review_facts(writer_blobs_at_freeze={name: 'f' * 40 for name in common.WRITER_FILES}),
                 'WRITER_IS_NOT_THE_ONE_THAT_WROTE_THE_FREEZE:prepare_unchanged_repro.py'),
                (review_facts(closure_running=dict(REVIEW_CLOSURE, **{'read_reproduction.py': 'e' * 40})),
                 'CLOSURE_IS_NOT_WHAT_RUNS_HERE:read_reproduction.py'),
                (review_facts(closure_at_reviewed_commit=dict(REVIEW_CLOSURE, **{'prepare_unchanged_repro.py':
                                                                                 'e' * 40})),
                 'CLOSURE_IS_NOT_THE_REVIEWED_COMMIT:prepare_unchanged_repro.py'),
                (None, 'REVIEW_FACTS_NOT_GATHERED')):
            self.assertIn(reason, common.review_receipt_violations(review_receipt(), bindings, facts), reason)
        for document, reason in (
                (review_receipt(unresolved_findings=[{'id': 'M1', 'severity': 'MAJOR', 'execution_consequence': 'x'}]),
                 'UNRESOLVED_BLOCKING_FINDING:M1'),
                (review_receipt(verdict='NO_BLOCKER_OR_MAJOR_FINDING_OPEN'), 'VERDICT:NO_BLOCKER_OR_MAJOR_FINDING_OPEN'),
                (review_receipt(reviewer_provenance={}), 'REVIEWER_PROVENANCE'),
                (review_receipt(closure={key: value for key, value in REVIEW_CLOSURE.items()
                                         if key != 'prepare_unchanged_repro.py'}), 'CLOSURE_FORM'),
                (review_receipt(attribution={'builder': common.LABEL, 'independence': 'INDEPENDENT'}), 'ATTRIBUTION'),
                (review_receipt(schema='cncm.helm-unchanged-reproduction-review-receipt/1'), 'SCHEMA_FIELDS_OR_LABEL')):
            self.assertIn(reason, common.review_receipt_violations(document, bindings, review_facts()), reason)
        if git_has('HEAD', common.HERE_REL + '/repro_common.py') and git_has(common.FREEZE_COMMIT,
                                                                             common.HERE_REL + '/repro_common.py'):
            head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
            facts = common.review_facts({'reviewed_commit': head, 'reviewed_branch': 'no-such/branch-for-this-test'},
                                        freeze_commit=common.FREEZE_COMMIT)
            self.assertEqual((facts['reviewed_commit_resolves'], facts['reviewed_commit_pushed']), (True, False))
            for name in common.WRITER_FILES:        # this revision leaves both writers exactly as they wrote the freeze
                self.assertEqual(facts['writer_blobs_at_freeze'][name], facts['closure_running'][name], name)

    # ---- fix 6 (Codex R3-I): the environment lock, parsed strictly and compared with the observed runtime ----
    def test_fix6_the_environment_lock_is_parsed_and_compared(self):
        raw = enc(LOCK)
        self.assertEqual(common.environment_lock_violations(raw), ([], LOCK))
        duplicate = raw.replace(b'"status": ', b'"status": "OTHER", "status": ', 1)
        self.assertEqual(common.environment_lock_violations(duplicate), (['LOCK_NOT_A_STRICT_JSON_OBJECT'], None))
        for changes, reason in (({'runtime.python_version': None}, 'LOCK_VALUE:runtime.python_version'),
                                ({'extra': 1}, 'LOCK_TOP_FIELDS'),
                                ({'libraries.cudnn': 'nine'}, 'LOCK_VALUE_UNPARSEABLE:libraries.cudnn'),
                                ({'status': 'DRAFT'}, 'LOCK_SCHEMA_STATUS_OR_SOURCE_COMMIT')):
            self.assertIn(reason, common.environment_lock_violations(enc(lock_document(**changes)))[0], reason)
        moved = lock_document()
        moved['comparison']['required_equal'].remove('libraries.cudnn')
        moved['comparison']['diagnostic_only'].append({'path': 'libraries.cudnn', 'reason': 'x'})
        found = common.environment_lock_violations(enc(moved))[0]
        self.assertIn('LOCK_REQUIRED_EQUAL_LACKS:libraries.cudnn', found)
        self.assertIn('LOCK_DIAGNOSTIC_ONLY_MAY_NAME_ENVELOPE_FIELDS_ONLY:libraries.cudnn', found)
        self.assertEqual(common.parse_cudnn_version(91002), common.parse_version('9.10.2'))
        self.assertEqual(common.parse_version('12.8.0'), common.parse_version('12.8'))
        self.assertNotEqual(common.parse_torch_version('2.11.0+cu128'), common.parse_torch_version('2.11.0+cu126'))
        compare = common.environment_lock_comparison
        self.assertEqual(compare(LOCK, RECORDED_ENV, 'E', must_observe=True)[0], [])
        for key, value, path in (('python_version', '3.12.4', 'runtime.python_version'),
                                 ('cudnn_version', 91100, 'libraries.cudnn'),
                                 ('torch_version', '2.11.0+cu126', 'libraries.torch'),
                                 ('cuda_version', '12.6', 'libraries.cuda_runtime'),
                                 ('gpu_name', 'Tesla T4', 'accelerator.gpu_model'),
                                 ('python_implementation', 'PyPy', 'runtime.python_implementation'),
                                 # revision 5 (Q-G): driver and kernel are required-equal, no longer diagnostic
                                 ('driver_version', '590.1', 'accelerator.driver_version'),
                                 ('platform_release', '6.8.0-1030-aws', 'runtime.kernel')):
            self.assertEqual(compare(LOCK, dict(RECORDED_ENV, **{key: value}), 'E', must_observe=True)[0],
                             ['ENVIRONMENT_DIFFERS_FROM_LOCK:E:' + path], key)
        missing = {key: value for key, value in RECORDED_ENV.items() if key != 'python_version'}
        self.assertEqual(compare(LOCK, missing, 'E', must_observe=True)[0],
                         ['ENVIRONMENT_NOT_OBSERVED:E:runtime.python_version'])
        invalid, _, not_observed = compare(LOCK, RUNTIME, 'TRAINING', must_observe=False)
        self.assertEqual(invalid, [])
        self.assertIn('TRAINING:runtime.python_version', not_observed)
        # Through the reader: a different Python in the evidence reads INVALID, never DOES_NOT_REPRODUCE.
        evaluated = reader.evaluate_evidence(
            evidence(environment=dict(RECORDED_ENV, python_version='3.12.4')), MANIFEST, expected_candidate_job=NEW_JOB,
            expected_candidate_sha256=OTHER, admitted_sources=FAKE_SOURCES, required_mode='READING',
            environment_lock=LOCK)
        self.assertIn('ENVIRONMENT_DIFFERS_FROM_LOCK:READING_EVIDENCE:runtime.python_version',
                      evaluated['invalid_reasons'])
        self.assertEqual(evaluated['levels']['learned_state'], True)       # the state itself still matched

    # ---- fix 7 (and R3-C): every acceptance case against the frozen table; `pass: true` is never trusted ----
    def test_fix7_each_acceptance_case_is_compared_with_the_frozen_table(self):
        bindings = common.expected_admission_bindings(FAKE_SOURCES)
        self.assertEqual(common.acceptance_receipt_violations(acceptance_receipt(), bindings), [])
        self.assertEqual(set(common.ACCEPTANCE_EXPECTED), set(common.ACCEPTANCE_CASES))
        self.assertEqual({case: (verdict, levels) for case, _, verdict, levels in recompute.acceptance_specs(None)},
                         {case: (row['verdict'], row['levels']) for case, row in common.ACCEPTANCE_EXPECTED.items()
                          if case in [spec[0] for spec in recompute.acceptance_specs(None)]})

        def replaced(name, **fields):
            return acceptance_receipt(cases=[dict(case, **fields) if case['case'] == name else case
                                             for case in acceptance_receipt()['cases']])
        wrong_levels = common.level_labels({'file': True, 'learned_state': False, 'output': True,
                                            'continuation': True})
        found = common.acceptance_receipt_violations(
            replaced('self_identity', observed_verdict=DOES_NOT_REPRODUCE, observed_levels=wrong_levels), bindings)
        for reason in ('A_CASE_DID_NOT_PASS', 'CASE:CASE_OBSERVED_IS_NOT_THE_REGISTERED_OUTCOME:self_identity',
                       'CASE:CASE_PASS_FIELD_CONTRADICTS_THE_OBSERVED_FIELDS:self_identity'):
            self.assertIn(reason, found)
        found = common.acceptance_receipt_violations(replaced(
            'missing_key', expected_verdict=DOES_NOT_REPRODUCE, observed_verdict=DOES_NOT_REPRODUCE,
            invalid_reasons=[], observed_levels=wrong_levels), bindings)
        self.assertIn('CASE:CASE_EXPECTATION_IS_NOT_THE_FROZEN_TABLE:missing_key', found)
        found = common.acceptance_receipt_violations(replaced('changed_value', observed_verdict=INVALID), bindings)
        self.assertIn('CASE:CASE_VERDICT_IS_NOT_DERIVED_FROM_ITS_OBSERVED_FIELDS:changed_value', found)
        found = common.acceptance_receipt_violations(replaced('changed_buffer', reference_buffer_count=None), bindings)
        self.assertIn('CHANGED_BUFFER_NOT_RECORDED_AS_VACUOUS_WITH_NO_BUFFERS', found)
        found = common.acceptance_receipt_violations(acceptance_receipt(environment=dict(
            RECORDED_ENV, cudnn_version=91100)), bindings, environment_lock=LOCK)
        self.assertIn('ENVIRONMENT_LOCK:ENVIRONMENT_DIFFERS_FROM_LOCK:P1B_ACCEPTANCE:libraries.cudnn', found)

    @unittest.skipUnless(git_has(common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py'), 'freeze absent')
    def test_decide_is_byte_identical_to_the_freeze(self):
        frozen = common.show(common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py')
        running = (HERE / 'read_reproduction.py').read_bytes()
        self.assertIsNotNone(common.function_source(running.decode('utf-8'), 'decide'))
        self.assertEqual(common.function_source(running.decode('utf-8'), 'decide'),
                         common.function_source(frozen.decode('utf-8'), 'decide'))
        self.assertEqual(common.decide_source_sha256(running), common.decide_source_sha256(frozen))


# =====================================================================================================================
# REVISION 5: Codex R3-I / Q-G (every lock field required-equal; UNESTABLISHED reads UNVERIFIED) and Q-F (frozen rule).
# =====================================================================================================================
class RevisionFiveEnvironmentTests(unittest.TestCase):
    def test_rev5_driver_and_kernel_are_required_equal_and_only_envelope_fields_are_diagnostic(self):
        """The revision-4 lock (driver and kernel diagnostic) is refused; an envelope field is reported, never deciding;
        an envelope name that reuses a predictive key (driver_version) is refused."""
        old = lock_document()
        old['comparison'] = {'required_equal': [path for path in common.ENVIRONMENT_LOCK_LEAVES
                                                if path not in ('runtime.kernel', 'accelerator.driver_version')],
                             'diagnostic_only': [{'path': 'runtime.kernel', 'reason': 'Q-G default'},
                                                 {'path': 'accelerator.driver_version', 'reason': 'Q-G default'}]}
        found, lock = common.environment_lock_violations(enc(old))
        self.assertIsNone(lock)
        self.assertIn('LOCK_REQUIRED_EQUAL_LACKS:runtime.kernel,accelerator.driver_version', found)
        self.assertIn('LOCK_DIAGNOSTIC_ONLY_MAY_NAME_ENVELOPE_FIELDS_ONLY:runtime.kernel,accelerator.driver_version',
                      found)
        for path in ('envelope.driver_version', 'envelope.platform_release', 'envelope.python_version', 'kernel',
                     'envelope.', 'envelope.Instance'):
            bad = lock_document(comparison={'required_equal': list(common.ENVIRONMENT_LOCK_LEAVES),
                                            'diagnostic_only': [{'path': path, 'reason': 'x'}]})
            self.assertIn('LOCK_DIAGNOSTIC_ONLY_MAY_NAME_ENVELOPE_FIELDS_ONLY:' + path,
                          common.environment_lock_violations(enc(bad))[0], path)
        twice = lock_document(comparison={'required_equal': list(common.ENVIRONMENT_LOCK_LEAVES) + ['runtime.kernel'],
                                          'diagnostic_only': []})
        self.assertIn('LOCK_REQUIRED_EQUAL_UNKNOWN_OR_DUPLICATE', common.environment_lock_violations(enc(twice))[0])
        invalid, diagnostic, _ = common.environment_lock_comparison(
            LOCK, dict(RECORDED_ENV, instance_id='i-0123456789abcdef0'), 'E', must_observe=True)
        self.assertEqual(invalid, [])
        self.assertEqual([(row['path'], row['observed']) for row in diagnostic],
                         [('envelope.instance_id', 'i-0123456789abcdef0')])
        for key, value, path in (('driver_version', '590.1', 'accelerator.driver_version'),
                                 ('platform_release', '6.8.0-1030-aws', 'runtime.kernel')):
            evaluated = reader.evaluate_evidence(
                evidence(environment=dict(RECORDED_ENV, **{key: value})), MANIFEST, expected_candidate_job=NEW_JOB,
                expected_candidate_sha256=OTHER, admitted_sources=FAKE_SOURCES, required_mode='READING',
                environment_lock=LOCK)
            self.assertIn('ENVIRONMENT_DIFFERS_FROM_LOCK:READING_EVIDENCE:' + path, evaluated['invalid_reasons'])

    def test_rev5_an_unestablished_historical_value_reads_unverified_never_the_current_machine(self):
        lock = lock_document(**{'runtime.python_version': common.ENVIRONMENT_UNESTABLISHED,
                                'numerics.dtype': common.ENVIRONMENT_UNESTABLISHED})
        found, parsed = common.environment_lock_violations(enc(lock))
        self.assertEqual((found, parsed), ([], lock))                       # an explicit blocker is a legal lock
        self.assertEqual(common.environment_lock_unestablished(lock), ['runtime.python_version', 'numerics.dtype'])
        for observed, must in ((RECORDED_ENV, True), (RUNTIME, False), ({}, False)):
            invalid, diagnostic, _ = common.environment_lock_comparison(lock, observed, 'S', must_observe=must)
            self.assertIn('ENVIRONMENT_ADMISSION_UNVERIFIED:S:runtime.python_version', invalid)
            self.assertIn('ENVIRONMENT_ADMISSION_UNVERIFIED:S:numerics.dtype', invalid)
            shown = [row for row in diagnostic if row['path'] == 'runtime.python_version']
            if 'python_version' in observed:                               # shown for disclosure, never accepted
                self.assertEqual(shown, [{'source': 'S', 'path': 'runtime.python_version',
                                          'lock': common.ENVIRONMENT_UNESTABLISHED, 'observed': '3.12.3',
                                          'accepted': False}])
        evaluated = reader.evaluate_evidence(
            evidence(), MANIFEST, expected_candidate_job=NEW_JOB, expected_candidate_sha256=OTHER,
            admitted_sources=FAKE_SOURCES, required_mode='READING', environment_lock=lock)
        self.assertIn('ENVIRONMENT_ADMISSION_UNVERIFIED:READING_EVIDENCE:runtime.python_version',
                      evaluated['invalid_reasons'])
        found = common.acceptance_receipt_violations(acceptance_receipt(), common.expected_admission_bindings(
            FAKE_SOURCES), environment_lock=lock)
        self.assertIn('ENVIRONMENT_LOCK:ENVIRONMENT_ADMISSION_UNVERIFIED:P1B_ACCEPTANCE:runtime.python_version', found)

    def test_rev5_a_lock_may_not_contradict_the_historical_pins(self):
        for changes, path in (({'image.ami_id': 'ami-0123456789abcdef0'}, 'image.ami_id'),
                              ({'image.region': 'us-east-1'}, 'image.region'),
                              ({'accelerator.instance_type': 'g4dn.xlarge'}, 'accelerator.instance_type'),
                              ({'accelerator.gpu_model': 'Tesla T4'}, 'accelerator.gpu_model'),
                              ({'libraries.torch': '2.11.0+cu126'}, 'libraries.torch'),
                              ({'libraries.cuda_runtime': '12.6'}, 'libraries.cuda_runtime'),
                              ({'numerics.matmul_allow_tf32': True}, 'numerics.matmul_allow_tf32'),
                              ({'accelerator.gpu_model': common.ENVIRONMENT_UNESTABLISHED}, 'accelerator.gpu_model'),
                              ({'numerics.environment_variables': {'CUBLAS_WORKSPACE_CONFIG': ':16:8'}},
                               'numerics.environment_variables.CUBLAS_WORKSPACE_CONFIG')):
            found, lock = common.environment_lock_violations(enc(lock_document(**changes)))
            self.assertIsNone(lock, path)
            self.assertIn('LOCK_CONTRADICTS_THE_HISTORICAL_PIN:' + path, found, path)
        self.assertEqual(common.environment_lock_historical_contradictions(LOCK), [])
        self.assertIn('accelerator.driver_version', common.ENVIRONMENT_REQUIRED_EQUAL)
        self.assertIn('runtime.kernel', common.ENVIRONMENT_REQUIRED_EQUAL)
        self.assertEqual(set(common.ENVIRONMENT_NOT_OBSERVED_ANYWHERE) | set(common.ENVIRONMENT_OBSERVED),
                         set(common.ENVIRONMENT_LOCK_LEAVES))


OWNER_DIRECTION_PRESENT = git_has(common.OWNER_DIRECTION['commit'], common.OWNER_DIRECTION['path'])
OWNER_DIRECTION_RAW = (common.show(common.OWNER_DIRECTION['commit'], common.OWNER_DIRECTION['path'])
                       if OWNER_DIRECTION_PRESENT else None)
RULE_RAW = (HERE / common.ELIGIBILITY_RULE_NAME).read_bytes()


class RevisionFiveRuleTests(unittest.TestCase):
    def test_rev5_the_frozen_rule_is_committed_here_conforms_and_is_a_reader_source(self):
        self.assertIsNotNone(common.ELIGIBILITY_RULE)
        self.assertEqual(common.ELIGIBILITY_RULE_SHA256, digest(RULE_RAW))
        self.assertEqual(common.eligibility_rule_violations(common.strict_json_object(RULE_RAW)), [])
        self.assertIn(common.ELIGIBILITY_RULE_NAME, common.READER_SOURCE_FILES)          # the fingerprint covers it
        rule = json.loads(RULE_RAW)
        self.assertEqual(rule['fixed_now']['execution_admission_as_is'],
                         {'path': P + common.ADMISSION_REL, 'sha256': common.FROZEN_ADMISSION_SHA256,
                          'state': common.NOT_READY})
        self.assertEqual(rule['preserved_never_rewritten']['execution_admission_state'], common.NOT_READY)
        self.assertEqual(rule['decide_unchanged']['source_sha256_at_freeze'], common.FROZEN_DECIDE_SHA256)
        self.assertEqual(rule['record']['chronology'], 'POST_TRAINING_ELIGIBILITY_BEFORE_COMPARISON')
        self.assertEqual([row['field'] for row in rule['appended_later']][:4],
                         ['reader_acceptance', 'environment_lock', 'review', 'reader'])
        self.assertEqual(rule['fixed_now']['panel_manifest_sha256'], common.PANEL_MANIFEST_SHA256)
        self.assertEqual(rule['fixed_now']['owner_direction_record']['commit'],
                         '33d2e7893948152221501da3902781a3babb9a4d')
        self.assertEqual(rule['environment_rule']['required_equal'], list(common.ENVIRONMENT_LOCK_LEAVES))
        self.assertNotIn(b'PRELAUNCH_ADMISSION', RULE_RAW)
        self.assertNotIn(common.PINS_SHA256.encode('ascii'), RULE_RAW)           # appended later, never fixed here
        self.assertEqual(json.loads(common.canonical(rule)), rule)              # plain JSON, no NaN

    def test_rev5_a_changed_rule_stops_every_tool(self):
        rule = json.loads(RULE_RAW)
        for mutate, reason in (
                (lambda r: r['fixed_now'].update(chronology='PRELAUNCH_ADMISSION'), 'RULE_SECTION:fixed_now'),
                (lambda r: r['fixed_now']['execution_admission_as_is'].update(state='ADMITTED'),
                 'RULE_SECTION:fixed_now'),
                (lambda r: r['decide_unchanged'].update(source_sha256_at_freeze='0' * 64),
                 'RULE_SECTION:decide_unchanged'),
                (lambda r: r['environment_rule']['required_equal'].remove('accelerator.driver_version'),
                 'RULE_SECTION:environment_rule'),
                (lambda r: r['appended_later'].pop(0), 'RULE_APPENDED_LATER'),
                (lambda r: r['record']['fields'].remove('runner_attestation'), 'RULE_SECTION:record'),
                (lambda r: r['never'].append('two\nlines'), 'RULE_PROSE_LIST:never'),
                (lambda r: r.update(status='DRAFT'), 'RULE_SCHEMA_LABEL_STATUS_OR_STUDY')):
            changed = deepcopy(rule)
            mutate(changed)
            self.assertIn(reason, common.eligibility_rule_violations(changed), reason)
            with self.assertRaisesRegex(SystemExit, 'UNCHANGED_REPRO_ELIGIBILITY_RULE_INVALID'):
                common.load_eligibility_rule(enc(changed))
        self.assertIsNone(common.load_eligibility_rule(None))                  # absent: every record is refused
        self.assertEqual(common.eligibility_rule_violations(None), ['RULE_NOT_A_STRICT_JSON_OBJECT'])

    @unittest.skipUnless(git_has(common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py'), 'freeze absent')
    def test_rev5_the_fixed_values_are_the_committed_facts(self):
        frozen_reader = common.show(common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py')
        self.assertEqual(common.decide_source_sha256(frozen_reader), common.FROZEN_DECIDE_SHA256)
        self.assertEqual(common.decide_source_sha256((HERE / 'read_reproduction.py').read_bytes()),
                         common.FROZEN_DECIDE_SHA256)
        for name, blob in common.WRITER_BLOBS_AT_FREEZE.items():
            self.assertEqual(common.blob_id(common.FREEZE_COMMIT, common.HERE_REL + '/' + name), blob, name)
            self.assertEqual(common.git_object_id((HERE / name).read_bytes()), blob, name)   # writers unchanged
        study = json.loads(common.show(common.FREEZE_COMMIT, common.HERE_REL + '/frozen/study.json'))
        self.assertEqual(study['jobs'][0]['job'], common.FROZEN_JOB)
        self.assertEqual(study['writer_blob_at_head'], common.WRITER_BLOBS_AT_FREEZE[
            'write_launch_under_owner_direction.py'])
        self.assertEqual(reader.owner_direction_path(study), common.OWNER_DIRECTION['path'])
        self.assertEqual(common.ELIGIBILITY_FIXED['numerical_environment_sha256'], common.environment_digest())
        self.assertEqual(common.ELIGIBILITY_FIXED['numerical_environment_sha256'],
                         study['execution_admission']['bindings']['numerical_environment_sha256'])

    @unittest.skipUnless(OWNER_DIRECTION_PRESENT, 'owner-direction commit 33d2e789 absent')
    def test_rev5_the_owner_direction_pin_is_the_committed_record(self):
        self.assertEqual(common.git_object_id(OWNER_DIRECTION_RAW), common.OWNER_DIRECTION['blob'])
        self.assertEqual(digest(OWNER_DIRECTION_RAW), common.OWNER_DIRECTION['sha256'])
        self.assertEqual(common.blob_id(common.OWNER_DIRECTION['commit'], common.OWNER_DIRECTION['path']),
                         common.OWNER_DIRECTION['blob'])


# ---- the eligibility route (route B), over the REAL frozen study and request of 3344ae5d ----
FROZEN_DIR = HERE / 'frozen'
REAL_STUDY_RAW = (FROZEN_DIR / 'study.json').read_bytes() if (FROZEN_DIR / 'study.json').is_file() else None
REAL_REQUEST_RAW = ((FROZEN_DIR / '20260917' / 'request.json').read_bytes()
                    if (FROZEN_DIR / '20260917' / 'request.json').is_file() else None)
DECIDE_SHA = common.decide_source_sha256((HERE / 'read_reproduction.py').read_bytes())


RULE_COMMIT = '8' * 40                        # a synthetic commit that carries the frozen rule
ATTESTATION = {'attester': 'Claude coordinator (synthetic)', 'rule_on_launch_checkout_before_u17_launch': True,
               'deciding_outputs_viewed': [], 'statement': 'synthetic attestation for the tests'}


def receipt_reference(name, raw):
    return {'receipt_commit': str(len(name) % 10) * 40, 'receipt_path': common.HERE_REL + '/receipts/' + name + '.json',
            'receipt_sha256': digest(raw)}


def eligibility_bundle(record_changes=None, fact_changes=None, raws=None):
    """`(record, facts)`: a synthetic eligibility record and the git facts `eligibility_facts` would gather."""
    study = json.loads(REAL_STUDY_RAW)
    closure = dict(REVIEW_CLOSURE, **{'write_launch_under_owner_direction.py': study['writer_blob_at_head']})
    raws = dict({'reader_acceptance': enc(acceptance_receipt()), 'environment_lock': enc(LOCK),
                 'review': enc(review_receipt(closure=closure))}, **(raws or {}))
    record = {'schema': common.ELIGIBILITY_SCHEMA, 'label': common.LABEL, 'state': common.ELIGIBLE,
              'job': study['jobs'][0]['job'], 'job_kind': common.JOB_KIND, 'model_seed': common.MODEL_SEED,
              'source_sha': common.SOURCE_SHA,
              'frozen_study': {'commit': common.FREEZE_COMMIT,
                               'path': common.GIT_PREFIX + common.HERE_REL + '/frozen/study.json',
                               'sha256': common.FROZEN_STUDY_SHA256},
              'execution_admission_as_is': {'path': common.GIT_PREFIX + common.ADMISSION_REL,
                                            'sha256': common.FROZEN_ADMISSION_SHA256, 'state': common.NOT_READY},
              'reader': {'reader_sources_sha256': dict(FAKE_SOURCES),
                         'reader_source_sha256': common.reader_source_digest(FAKE_SOURCES)},
              'policy_pins_sha256': common.PINS_SHA256, 'panel_manifest_sha256': common.PANEL_MANIFEST_SHA256,
              'launch_basis': common.LAUNCH_BASIS,
              'owner_direction_record': dict(common.OWNER_DIRECTION),         # the real 33d2e789 record
              'decide_source_sha256': DECIDE_SHA,
              # revision 5 (Codex Q-F): chronology label, the frozen rule, environment digest, writers, attestation
              'chronology': common.ELIGIBILITY_CHRONOLOGY,
              'eligibility_rule': {'commit': RULE_COMMIT, 'path': common.ELIGIBILITY_RULE_REL, 'sha256': digest(RULE_RAW)},
              'numerical_environment_sha256': common.environment_digest(),
              'writer_blobs': dict(common.WRITER_BLOBS_AT_FREEZE),
              'runner_attestation': dict(ATTESTATION),
              **{name: receipt_reference(name, raw) for name, raw in raws.items()},
              'written_by': 'Claude builder (synthetic)', 'written_utc': '2026-09-25T02:00:00Z', 'note': 'synthetic'}
    record.update(record_changes or {})
    facts = {'receipts': {name: {'commit': record[name]['receipt_commit'], 'path': record[name]['receipt_path'],
                                 'raw': raw, 'anchored': True} for name, raw in raws.items()},
             'owner_direction': {'blob': common.git_object_id(OWNER_DIRECTION_RAW or b''), 'raw': OWNER_DIRECTION_RAW},
             'rule': {'commit': RULE_COMMIT, 'raw': RULE_RAW, 'anchored': True, 'precedes_training_result': True},
             'lock_precedes_acceptance': True,
             'review_facts': review_facts(closure_at_reviewed_commit=dict(closure), closure_running=dict(closure),
                                          writer_blobs_at_freeze={name: closure[name] for name in common.WRITER_FILES}),
             'decide_running': DECIDE_SHA, 'decide_at_freeze': DECIDE_SHA}
    facts.update(fact_changes or {})
    facts['raw'] = enc(record)
    return record, facts


AS_IS_ADMISSION = {'state': common.NOT_READY, 'recorded_state': common.NOT_READY,
                   'reasons': ['ADMISSION_STATE_IS:NOT_READY'], 'record_sha256': common.FROZEN_ADMISSION_SHA256,
                   'job': None, 'spend': None}
HISTORY_B = dict(HISTORY, freeze_commits=[common.FREEZE_COMMIT], eligibility_commits=['6' * 40],
                 eligibility_follows_freeze=True, eligibility_precedes_evidence=True, eligibility_has_evidence=False,
                 eligibility_follows_training_result=True,
                 blob_versions=dict(HISTORY['blob_versions'], eligibility=['7' * 40]))


@unittest.skipUnless(ARCHIVE_RAW is not None and REAL_STUDY_RAW is not None and REAL_REQUEST_RAW is not None
                     and OWNER_DIRECTION_PRESENT, 'package archive, frozen records or owner direction not here')
class EligibilityRouteTests(unittest.TestCase):
    def read_b(self, record_changes=None, fact_changes=None, raws=None, **options):
        study = json.loads(REAL_STUDY_RAW)
        job = study['jobs'][0]['job']
        _, facts = eligibility_bundle(record_changes, fact_changes, raws)
        frozen = {'study.json': REAL_STUDY_RAW, '20260917/request.json': REAL_REQUEST_RAW}
        receipt = receipt_files(job=job, request=json.loads(REAL_REQUEST_RAW))
        document = options.pop('document', None) or evidence(candidate=side(job, OTHER))
        return run(frozen=frozen, receipt=receipt, document=document,
                   state=options.pop('state', dict(AS_IS_ADMISSION)), history=options.pop('history', dict(HISTORY_B)),
                   eligibility=facts, **options)

    def test_an_eligibility_record_with_the_admission_byte_identical_is_accepted(self):
        self.assertEqual(digest(REAL_STUDY_RAW), common.FROZEN_STUDY_SHA256)
        self.assertEqual(digest(common.ADMISSION_PATH.read_bytes()), common.FROZEN_ADMISSION_SHA256)
        record = self.read_b()
        self.assertEqual(record['verdict'], REPRODUCED, record['invalid_reasons'])
        self.assertEqual(record['route'], common.ROUTE_ELIGIBILITY)
        self.assertEqual(record['refusal_allowlist_sha256'], common.REFUSAL_ALLOWLIST_SHA256)
        self.assertEqual(sorted(record['environment_lock_reported_only']),
                         ['CANDIDATE_TRAINING', 'READING_EVIDENCE', 'REFERENCE_TRAINING',
                          'required_equal_not_observed_by_any_source', 'unestablished_historical_values'])
        self.assertEqual(record['environment_lock_reported_only']['unestablished_historical_values'], [])
        self.assertEqual(record['eligibility']['rule_sha256'], digest(RULE_RAW))
        self.assertEqual(record['eligibility']['chronology'], 'POST_TRAINING_ELIGIBILITY_BEFORE_COMPARISON')
        # Q-F: a viewed deciding output is DISCLOSED (printed), never a reason to revise eligibility or the verdict.
        viewed = dict(ATTESTATION, deciding_outputs_viewed=['reproduction_reading.json of an earlier reader'])
        disclosed = self.read_b({'runner_attestation': viewed})
        self.assertEqual(disclosed['verdict'], REPRODUCED, disclosed['invalid_reasons'])
        self.assertEqual(disclosed['eligibility']['runner_attestation_disclosed'], viewed)
        mismatch = self.read_b(document=evidence(candidate=side(json.loads(REAL_STUDY_RAW)['jobs'][0]['job'], OTHER,
                                                                state=parts(model_state=lambda m: {
                                                                    **m, 'round_rate': T(0.75)}))))
        self.assertEqual(mismatch['verdict'], DOES_NOT_REPRODUCE, mismatch['invalid_reasons'])

    def test_every_broken_binding_reads_invalid_never_a_mismatch(self):
        other_job = common.job_name('20260925120001')
        cases = [
            ({'state': dict(AS_IS_ADMISSION, record_sha256='8' * 64)},
             'EXECUTION_ADMISSION_AT_THE_RECEIPT_COMMIT_IS_NOT_BYTE_IDENTICAL_TO_THE_FROZEN_ONE'),
            ({'record_changes': {'job': other_job}}, 'ELIGIBILITY:NOT_FOR_THE_FROZEN_JOB:' + other_job),
            ({'record_changes': {'reader': {'reader_sources_sha256': dict(FAKE_SOURCES, **{
                'repro_common.py': '7' * 64}), 'reader_source_sha256': '7' * 64}}}, 'ELIGIBILITY:NOT_THIS_READER'),
            ({'record_changes': {'state': 'ADMITTED'}}, 'ELIGIBILITY:FIELDS_SCHEMA_LABEL_OR_STATE'),
            ({'fact_changes': {'decide_at_freeze': '0' * 64}}, 'ELIGIBILITY:DECIDE_IS_NOT_THE_FROZEN_DECIDE'),
            ({'fact_changes': {'owner_direction': None}}, 'ELIGIBILITY:OWNER_DIRECTION_RECORD'),
            ({'raws': {'reader_acceptance': enc(acceptance_receipt(status=common.ACCEPTANCE_FAIL))}},
             'ELIGIBILITY:READER_ACCEPTANCE:STATUS:READER_ACCEPTANCE_FAIL'),
            ({'raws': {'environment_lock': enc(lock_document(**{'runtime.python_version': '3.11.9'}))}},
             'ELIGIBILITY:READER_ACCEPTANCE:ENVIRONMENT_LOCK:ENVIRONMENT_DIFFERS_FROM_LOCK:P1B_ACCEPTANCE:'
             'runtime.python_version'),
            ({'raws': {'review': enc(review_receipt(verdict='CHANGES_REQUIRED'))}},
             'ELIGIBILITY:REVIEW:VERDICT:CHANGES_REQUIRED'),
            ({'history': dict(HISTORY_B, eligibility_precedes_evidence=False)},
             'ELIGIBILITY_RECORD_IS_NOT_BEFORE_THE_EVIDENCE'),
            ({'history': dict(HISTORY_B, freeze_commits=['1' * 40])}, 'FREEZE_IS_NOT_THE_REGISTERED_FREEZE_COMMIT'),
            ({'history': dict(HISTORY_B, eligibility_commits=['6' * 40, '6' * 39 + '7'])},
             'ELIGIBILITY_RECORD_NOT_EXACTLY_ONE_COMMITTED_VERSION:2'),
            ({'document': evidence(candidate=side(json.loads(REAL_STUDY_RAW)['jobs'][0]['job'], OTHER),
                                   environment=dict(RECORDED_ENV, python_version='3.12.4'))},
             'ENVIRONMENT_DIFFERS_FROM_LOCK:READING_EVIDENCE:runtime.python_version'),
            # ---- revision 5 (Codex R3-I, Q-G, Q-F) ----
            ({'document': evidence(candidate=side(json.loads(REAL_STUDY_RAW)['jobs'][0]['job'], OTHER),
                                   environment=dict(RECORDED_ENV, driver_version='590.1'))},
             'ENVIRONMENT_DIFFERS_FROM_LOCK:READING_EVIDENCE:accelerator.driver_version'),
            ({'document': evidence(candidate=side(json.loads(REAL_STUDY_RAW)['jobs'][0]['job'], OTHER),
                                   environment=dict(RECORDED_ENV, platform_release='6.8.0-1030-aws'))},
             'ENVIRONMENT_DIFFERS_FROM_LOCK:READING_EVIDENCE:runtime.kernel'),
            ({'raws': {'environment_lock': enc(lock_document(**{
                'accelerator.driver_version': common.ENVIRONMENT_UNESTABLISHED}))}},
             'ENVIRONMENT_ADMISSION_UNVERIFIED:READING_EVIDENCE:accelerator.driver_version'),
            ({'raws': {'environment_lock': enc(lock_document(**{
                'accelerator.driver_version': common.ENVIRONMENT_UNESTABLISHED}))}},
             'ENVIRONMENT_ADMISSION_UNVERIFIED:REFERENCE_TRAINING:accelerator.driver_version'),
            ({'record_changes': {'chronology': 'PRELAUNCH_ADMISSION'}},
             'ELIGIBILITY:NOT_THE_VALUE_THE_FROZEN_RULE_FIXES:chronology'),
            ({'record_changes': {'owner_direction_record': dict(common.OWNER_DIRECTION, commit='3' * 40)}},
             'ELIGIBILITY:NOT_THE_VALUE_THE_FROZEN_RULE_FIXES:owner_direction_record'),
            ({'record_changes': {'writer_blobs': dict(common.WRITER_BLOBS_AT_FREEZE, **{
                'prepare_unchanged_repro.py': '9' * 40})}},
             'ELIGIBILITY:NOT_THE_VALUE_THE_FROZEN_RULE_FIXES:writer_blobs'),
            ({'record_changes': {'numerical_environment_sha256': '9' * 64}},
             'ELIGIBILITY:NOT_THE_VALUE_THE_FROZEN_RULE_FIXES:numerical_environment_sha256'),
            ({'record_changes': {'eligibility_rule': {'commit': RULE_COMMIT, 'path': common.ELIGIBILITY_RULE_REL,
                                                      'sha256': '9' * 64}}},
             'ELIGIBILITY:ELIGIBILITY_RULE_IS_NOT_THE_RULE_THIS_READER_LOADED'),
            ({'fact_changes': {'rule': None}}, 'ELIGIBILITY:ELIGIBILITY_RULE_NOT_A_COMMITTED_BLOB'),
            ({'fact_changes': {'rule': {'commit': RULE_COMMIT, 'raw': RULE_RAW, 'anchored': True,
                                        'precedes_training_result': False}}},
             'ELIGIBILITY:ELIGIBILITY_RULE_NOT_COMMITTED_BEFORE_THE_U17_TRAINING_RESULT'),
            ({'fact_changes': {'rule': {'commit': RULE_COMMIT, 'raw': RULE_RAW, 'anchored': False,
                                        'precedes_training_result': True}}},
             'ELIGIBILITY:ELIGIBILITY_RULE_NOT_COMMITTED_BEFORE_THE_RECORD'),
            ({'fact_changes': {'lock_precedes_acceptance': False}},
             'ELIGIBILITY:ENVIRONMENT_LOCK_NOT_COMMITTED_BEFORE_THE_P1B_ACCEPTANCE'),
            ({'record_changes': {'runner_attestation': dict(ATTESTATION,
                                                             rule_on_launch_checkout_before_u17_launch=False)}},
             'ELIGIBILITY:RULE_WAS_NOT_ON_THE_LAUNCH_CHECKOUT_BEFORE_U17_LAUNCH'),
            ({'record_changes': {'runner_attestation': {'attester': 'x'}}}, 'ELIGIBILITY:RUNNER_ATTESTATION_FORM'),
            ({'history': dict(HISTORY_B, eligibility_follows_training_result=False)},
             'ELIGIBILITY_RECORD_IS_NOT_AFTER_THE_TRAINING_RESULT'),
        ]
        for options, reason in cases:
            record = self.read_b(**options)
            self.assertEqual(record['verdict'], INVALID, reason)
            self.assertIn(reason, record['invalid_reasons'], (reason, record['invalid_reasons']))
        receipts = eligibility_bundle()[1]['receipts']                      # a receipt committed AFTER the record
        receipts['review']['anchored'] = False
        record = self.read_b(fact_changes={'receipts': receipts})
        self.assertIn('ELIGIBILITY:RECEIPT_NOT_COMMITTED_BEFORE_THE_ELIGIBILITY_RECORD:review', record['invalid_reasons'])
        # Revision 5: the revision-4 lock (driver and kernel diagnostic) no longer admits anything.
        old = lock_document(comparison={
            'required_equal': [path for path in common.ENVIRONMENT_LOCK_LEAVES
                               if path not in ('runtime.kernel', 'accelerator.driver_version')],
            'diagnostic_only': [{'path': 'runtime.kernel', 'reason': 'Q-G default'},
                                {'path': 'accelerator.driver_version', 'reason': 'Q-G default'}]})
        record = self.read_b(raws={'environment_lock': enc(old)})
        self.assertEqual(record['verdict'], INVALID)
        self.assertIn('ELIGIBILITY:ENVIRONMENT_LOCK:LOCK_REQUIRED_EQUAL_LACKS:runtime.kernel,accelerator.driver_version',
                      record['invalid_reasons'])

    def test_this_reader_cannot_read_the_frozen_study_without_the_record(self):
        """As frozen, the study binds the revision-3 reader, so this revision TOOL-stops (no verdict) until an
        eligibility record binds it; a record binding another reader also stops."""
        frozen = {'study.json': REAL_STUDY_RAW}
        running = common.source_hashes()
        saved = reader.stop_unless
        reader.stop_unless = stop
        try:
            with self.assertRaisesRegex(Stopped, '^READER_IS_NOT_THE_ADMITTED_READER'):
                reader.admitted_reader_check(frozen.get, running)
            record, _ = eligibility_bundle({'reader': {'reader_sources_sha256': running,
                                                       'reader_source_sha256': common.reader_source_digest(running)}})
            reader.admitted_reader_check(frozen.get, running, enc(record))
            with self.assertRaisesRegex(Stopped, '^READER_IS_NOT_THE_READER_THE_ELIGIBILITY_RECORD_BINDS'):
                reader.admitted_reader_check(frozen.get, running, enc(eligibility_bundle()[0]))
        finally:
            reader.stop_unless = saved


if __name__ == '__main__':
    unittest.main()
