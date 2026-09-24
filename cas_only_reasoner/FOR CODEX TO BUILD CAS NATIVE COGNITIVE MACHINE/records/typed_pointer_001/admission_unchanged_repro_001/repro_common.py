"""Shared, launcher-free facts and checks for the unchanged-arm reproduction (HELM-REPAIR-CONTROLLED-1, option C).

WHAT THIS FOLDER DOES. It freezes ONE AWS job, and later reads its result:
  * the job: seed 20260917 of the historical Helm 2.0 source 20208c92, full registered 10-pass schedule, trained by
    the same launcher (`aws/typed_pointer_launch.py`) on g7.2xlarge, from the same committed package;
  * the reading: `REPRODUCES` iff the new run's `final.pt` sha256 equals the Helm 2.0 receipt's `final.pt` sha256,
    else `DOES_NOT_REPRODUCE` (plan section 4a), or `INCOMPLETE` when the new run did not deliver.

THIS MODULE IMPORTS NOTHING FROM THE LAUNCHER, torch or the network. The reader and the tests import it without
importing the launcher. `prepare_unchanged_repro.py` imports the launcher itself, lazily.

IT LIVES UNDER `records/`, NOT under `cncm/` or `cas_meta2/`, on purpose: `pointer_contract.input_inventory` globs
`*.py` under those trees, so a new file there would change the launcher's input inventory and `inputs_sha256`.

EVERY PIN BELOW WAS READ FROM GIT on 2026-09-23 by the builder, with `git rev-parse <commit>:<path>` and `git show`:
  * the package: commit 3da10d84 ("Freeze the corrected Helm 2.0 study at 20208c92"), a direct child of 20208c92;
  * Helm 2.0's own seed-17 admission records: the same commit, `records/typed_pointer_001/admission_001/20260917/`;
  * the comparison target: commit c8d5c430, `records/typed_pointer_001/receipt_20260917/` (the delivered Helm 2.0 run,
    job cas-meta2-tpntr-20260920210258-20208c92-m-20260917). The same blobs are at the tips of
    `claude/helm-builder-continuation-20260923` (cc68d8b3) and `research/helm-integration-20260923` (197caa32);
  * the plan: commit 197caa32, `_handoffs/HELM_NEXT_PHASE_20260923/PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md`.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder while Codex is away, 2026-09-23). It transcribes the
owner's words; it is not an owner signature.
"""
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]          # the CNCM folder ("FOR CODEX TO BUILD CAS NATIVE ...")
GIT_PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
HERE_REL = 'records/typed_pointer_001/admission_unchanged_repro_001'
LABEL = 'CLAUDE_BUILT_CLAUDE_CHECKED'
RUNNER = 'Claude builder (temporary takeover while Codex is away)'

# ---- the source and the one job.
SOURCE_SHA = '20208c923d41c24614504d4ecc2b289ecb66eda8'
MODEL_SEED = 20260917
JOB_KIND = 'UNCHANGED_ARM_REPRODUCTION'
LAUNCHER_REL = 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py'

# ---- the committed package, restored into this branch blob-identical (commit d5a7b630 on this branch).
PACKAGE_COMMIT = '3da10d84652988190f66e3c239ee5cdeee8cc9dc'
PACKAGE_REL = 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_20208c92'
PACKAGE_BLOBS = {'receipt.json': '597e9a2fe3acd7a0e01d019bcd62728d5e8431f1',
                 'source.zip': '5020103650864d7d6cd6b9dd3b8e60d4d5e9e279'}
ARCHIVE_SHA256 = 'c42370c4941384c852feda33303dd70a01e956d28953cf07dd1b981220f31ed8'
ARCHIVE_BYTES = 5977155
MANIFEST_SHA256 = '333381ace5c4e37ff4c7fba7338bced0a4495f0cee7a43432bc3f2cc35923d40'
MEMBER_COUNT = 270
PACKAGE_RECEIPT_SCHEMA = 'cncm.typed-pointer-package-receipt/0.1'

# ---- Helm 2.0's own seed-17 admission (same commit as the package). The new records must match it except the job.
HELM2_ADMISSION_REL = 'records/typed_pointer_001/admission_001/20260917'
HELM2_ADMISSION_BLOBS = {'request.json': 'd8c0b6574c85edc07927c7f232dac2b398432f0e',
                         'authority.json': '8017fec08f350ac802ec6ea437555da79c4711f0',
                         'owner.json': '4fc0ef3198bfeadb1e2c846181c01f8352cdbb6a'}
HELM2_JOB = 'cas-meta2-tpntr-20260920210258-20208c92-m-20260917'
HELM2_STAMP = '20260920210258'
HELM2_BINDINGS = {'inputs_sha256': '442ae914e563fcf0bbb49d9c6d6746b0bea2b4ef7390542b135a33864a494150',
                  'design_sha256': '7d57b52bd7055dd63e8c6ed293a885b06651406e521d24c2116ef8ca84826ec6',
                  'evidence_contract_sha256': '1a0f87415314ef1f324a01237ecacbe023d84bf83735d527a5bce89f42c6a490'}
HELM2_CONDITION = 'MIXED_SAME_ITEMS'
# The launcher's frozen bounds exactly as Helm 2.0's owner record carries them. A moved launcher is refused.
EXPECTED_BOUNDS = {'automatic_retries': 0, 'instance_seconds_max': 14400, 'instance_type': 'g7.2xlarge', 'jobs': 1,
                   'max_wall_seconds': 12600, 'optimizer_updates_max': 1488, 'region': 'us-west-2',
                   'reservation_usd': '15.00', 'training': True}

# ---- the comparison target: the delivered Helm 2.0 seed-17 receipt.
REFERENCE_COMMIT = 'c8d5c430eec23a8fadd98bbcd045fecf03d86239'
REFERENCE_RECEIPT_REL = 'records/typed_pointer_001/receipt_20260917'
REFERENCE_FINAL_PT_SHA256 = 'c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb'
REFERENCE_FINAL_PT_BYTES = 3670007
# The three committed JSON records that state the final.pt sha256, relative to the receipt folder, and their blobs.
FINAL_PT_RECORDS = ('collected/results/artifacts/manifest.json',          # the worker's own artifact manifest
                    'collected_inventory.json',                            # the launcher's inventory of the S3 copy
                    'collected/results/artifacts/final_checkpoint.json')   # the worker's checkpoint pin
REFERENCE_BLOBS = {'collected/results/artifacts/manifest.json': 'd98b25aa6b8022da9ad7f1b2c90c8799ea5b5827',
                   'collected_inventory.json': '25a2277b00c84613b33414de1c70c4cb96ee1ba7',
                   'collected/results/artifacts/final_checkpoint.json': '123f14c8ce64b99268702a64f3d9ef20235fa196',
                   'collected/input/source.zip': PACKAGE_BLOBS['source.zip']}
FINAL_PT_WEIGHTS = 'collected/results/artifacts/final.pt'   # read ONLY when no record states a sha256

# ---- the owner-approved plan.
PLAN_COMMIT = '197caa322d20ae6830928b20c5b16933e93cd00d'
PLAN_REL = '_handoffs/HELM_NEXT_PHASE_20260923/PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md'
PLAN_BLOB = '67163714b6f86f5d0e9dd6925a0a7a276c26ff01'
PLAN_SHA256 = '916cd9e4a8252cdfa44e79596f40d681335331528667ff15e9db3bd4e1046ada'
PLAN_FETCH = ('git fetch origin research/helm-integration-20260923:'
              'refs/remotes/origin/research/helm-integration-20260923')
OWNER_ANSWERED_DATE = '2026-09-24'     # the plan's own date for both answers (sections 0 and 4a)

# The owner's own words, verbatim (inside the plan's quotation marks), each pinned by sha256.
OWNER_WORDS = {
    'owner_launch_approval_raw': (
        'YES to launching the side-by-side training of the repaired Helm. You approved up to $60. AND Run the '
        'access-restriction commands Claude handed to lock down the secret test files.',
        'e8ff2dd0b12f80fe70b8e4d84da1b8ca2b6738d739b5e3efafb80e0220c5234f'),
    'owner_option_delegation_raw': (
        'WHICH EVER IS BEST FOR THE OVER ALL MODEL/PROJECT:   A: reuse the old runs, about $22.50; C, recommended: '
        're-run one seed to prove the old runs reproduce exactly, then reuse them, about $30; B: re-run all three, '
        'about $45.',
        '2b2e7dd0882c2d663eace45b448094188120a7df50b97ed6ee4c52587e469128'),
}
# The plan's own text (the coordinator's application of those words, NOT owner words), verbatim, each pinned.
PLAN_WORDS = {
    'plan_option_c_applied': (
        '**Applied as option C, with a pre-set fallback to B.** The Claude coordinator chose it under this '
        'delegation; this is not an owner signature.',
        'e9694176fcb48cbe4c4bf46584b58436e1fc879170cf21f723395973aa932921'),
    'plan_option_c_row': (
        "| **C (recommended)** | Re-run `20208c92` for **one** seed (20260917) first, and require its final "
        "checkpoint to equal the Helm 2.0 receipt's bit for bit. If it does, reuse the other two receipts; if not, "
        "fall back to B | 4 | about $30 | 4 x $15 | proves the old runs are a fair control, at one extra job |",
        '2d5b7842afc160a5d3fc00afa4cb427dd063288536f02b040b67ea531f1ca1a0'),
    'plan_test_seed': (
        '- Seed 20260917 of `20208c92`, trained by the same launcher on g7.2xlarge.',
        '5f6564e18f934bcfa87b343645706df186fa22b144f4432a2317e906c95f8bd3'),
    'plan_test_reproduces': (
        "- **`REPRODUCES`** iff the sha256 of its `final.pt` equals the Helm 2.0 receipt's `final.pt` sha256.",
        '85198e7fca0455cc4a1abb48b499e7029b15bd9fb4995c2064f14b6fd15de5c1'),
    'plan_test_does_not_reproduce': (
        '- Anything else reads **`DOES_NOT_REPRODUCE`** and triggers B: seeds 20260918 and 20260919 of `20208c92` '
        'are re-run too.',
        'b15552f258ef02c67a671bb1e5824b521250fbd0f16f72501275b33a17af2138'),
    'plan_test_by_program': (
        '- The reading is made by a program, before any TEST cell of HSET-2 is read.',
        '5de7c40e84f92b90555ca029c08890941a62f0ee589c0a1b5c3056d39edb7b60'),
    'plan_job_order_item_3': (
        '3. the unchanged reproduction seed 20260917 of `20208c92`, once its admission writer is built and reviewed;',
        '07307c53d57c7e7c3d20b14e2be3660c0e1d6db31a19c963b9c1225ac455da66'),
    'plan_job_order_item_4': (
        '4. if it reads `DOES_NOT_REPRODUCE`, unchanged seeds 20260918 and 20260919.',
        '6cbafcbd981ad9ffa09baf73f0169152a6d51d89e0e0288271d8012bc0237390'),
    'plan_ceiling': (
        '**Ceiling: $60.00 of actual AWS spend** for the whole comparison: every smoke attempt and every training job.',
        '64a10ef27c750c6ca4f83c6dd11e91af3b6362da6f707ccee8e4a8f42ed556a1'),
    'plan_before_each_job': (
        '**Before each job:** measured spend so far + $15.00 (the per-job bound) must be at most $60.00, or the run '
        'stops and is reported.',
        '8cc9626d35f6b8c8d71ef73c6a5f53a085c7d040da96da1e218e64c5ff9536e4'),
    'plan_earlier_stop': (
        "**The owner's earlier stop stays:** if spend passes $30 before the third training job, stop and report.",
        'd1c267ddd28835f7240b681ba022c47b635aad6bb1ff04f73798f05672975a61'),
    'plan_stop_not_delivered': (
        '- If any job ends other than delivered, the next job is not launched.',
        'ec33795327cc0c9bd877eced493a4b55b103c3318c1e3dc39fb7dba65a056dbb'),
    'plan_access_commands': (
        "**Access commands.** Not run by Claude: changing folder permissions is a security setting, which Claude's "
        "rules forbid even at the owner's request. The owner has the exact commands.",
        '1192676dd3618602ef25e719f0e71c30dea9151afba79571547da46ec434861a'),
}

# ---- outputs. The writer writes ONE folder (`frozen/`, via `frozen.partial/`); the reader may write ONE file.
OUTPUT = HERE / 'frozen'
READING = HERE / 'reproduction_reading.json'
RECEIPT_REL = 'records/typed_pointer_001/receipt_unchanged_repro_20260917'
RECEIPT_DIR = ROOT / RECEIPT_REL

# ---- the tree rule. Relative to ROOT. HEAD may differ from SOURCE_SHA ONLY by ADDED files under these prefixes.
ALLOWED_ADDED_PREFIXES = (HERE_REL + '/', PACKAGE_REL + '/')
# Every tree the launcher's input inventory and packaging read from. Any difference here is refused by name.
INVENTORY_TREES = ('cncm/', 'research/CAS_META_2_COMPOSITION/cas_meta2/', 'research/CAS_META_2_COMPOSITION/aws/',
                   'research/CAS_META_2_COMPOSITION/requirements-gpu.txt', 'records/typed_course_001/',
                   'records/typed_interface_001/', 'records/typed_matched_001/', 'records/typed_practice_001/',
                   'research/CAS_CJT_TRANSFORMER_v0_2/')
# ---- the untracked rule: only this folder's own outputs may be untracked (a `.partial` folder never is).
TOLERATED_UNTRACKED = (HERE_REL + '/frozen/', HERE_REL + '/reproduction_reading.json')


def make_stop(prefix):
    """An explicit stop, never an `assert` (which `python -O` removes)."""
    def stop_unless(condition, reason):
        if not condition:
            raise SystemExit(prefix + reason)
    return stop_unless


def digest(raw):
    return sha256(raw).hexdigest()


def git_object_id(raw):
    """Git's own blob id for these bytes (SHA-1 over `blob <len>\\0<content>`)."""
    return sha1(b'blob %d\0' % len(raw) + raw).hexdigest()


def is_hex(value, length):
    return type(value) is str and len(value) == length and all(ch in '0123456789abcdef' for ch in value)


def git(*args, cwd=None):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=str(cwd or ROOT), check=True,
                          capture_output=True, timeout=120).stdout


def git_ok(*args, cwd=None):
    """True when the git command exits 0 (yes/no questions such as `merge-base --is-ancestor`)."""
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=str(cwd or ROOT), capture_output=True,
                          timeout=120).returncode == 0


def repo_path(relative):
    """A ROOT-relative path as git names it from the repository root."""
    return GIT_PREFIX + relative


def has_object(commit, relative):
    return git_ok('cat-file', '-e', commit + ':' + repo_path(relative))


def blob_id(commit, relative):
    return git('rev-parse', commit + ':' + repo_path(relative)).decode('ascii').strip()


def show(commit, relative):
    return git('show', commit + ':' + repo_path(relative))


# ---------------------------------------------------------------------------------------------------------------------
# Quotes.
# ---------------------------------------------------------------------------------------------------------------------
def normalise(text):
    """The plan's text with each line break (and the next line's leading spaces) turned into ONE space.

    Spaces INSIDE a line are kept exactly: the owner's option answer carries three spaces after
    "MODEL/PROJECT:", and that is part of the verbatim quote.
    """
    return re.sub(r'\n[ \t]*', ' ', text)


def check_quotes(text, stop):
    """Every pinned quote matches its sha256 AND occurs exactly once, verbatim, in the normalised plan text."""
    for group in (OWNER_WORDS, PLAN_WORDS):
        for name, (words, pinned) in group.items():
            stop(digest(words.encode('utf-8')) == pinned, 'QUOTE_EDITED:' + name)
            stop(text.count(words) == 1, 'QUOTE_NOT_EXACTLY_ONCE_IN_PLAN:' + name)
    return True


def read_plan(stop):
    """The plan, read with `git show <PLAN_COMMIT>:<PLAN_REL>` (never a working-tree copy), blob and sha256 pinned."""
    try:
        blob = blob_id(PLAN_COMMIT, PLAN_REL)
        raw = show(PLAN_COMMIT, PLAN_REL)
    except subprocess.CalledProcessError:
        stop(False, 'PLAN_OBJECT_MISSING:run `' + PLAN_FETCH + '` (do not check it out), then re-run')
    stop(blob == PLAN_BLOB, 'PLAN_BLOB:' + blob)
    stop(digest(raw) == PLAN_SHA256, 'PLAN_SHA256:' + digest(raw))
    check_quotes(normalise(raw.decode('utf-8')), stop)
    return {'commit': PLAN_COMMIT, 'path': GIT_PREFIX + PLAN_REL, 'blob': blob, 'sha256': digest(raw),
            'bytes': len(raw), 'read_with': 'git show <commit>:<path>',
            'sections': 'section 0 (launch approval), section 4a (option C and the reproduction test), section 6'}


def quotes_record():
    """The quotes as they go into the records: text only (the pins stay in this module)."""
    return ({name: words for name, (words, _) in OWNER_WORDS.items()},
            {name: words for name, (words, _) in PLAN_WORDS.items()})


# ---------------------------------------------------------------------------------------------------------------------
# The tree rule and the untracked rule (pure functions over git's -z output, so they can be tested without git).
# ---------------------------------------------------------------------------------------------------------------------
def parse_name_status_z(raw):
    """`git diff --name-status -z --no-renames` output -> [(status, repo-relative path)]."""
    fields = [field for field in raw.split(b'\0')]
    if fields and fields[-1] == b'':
        fields.pop()
    if len(fields) % 2:
        raise ValueError('NAME_STATUS_FIELDS_ODD')
    return [(fields[i].decode('ascii'), fields[i + 1].decode('utf-8')) for i in range(0, len(fields), 2)]


def tree_violations(entries):
    """Every difference between SOURCE_SHA and HEAD that is not an ADDED file under an allowed prefix.

    A path under an inventory tree is reported as INVENTORY even when it was only added: a new `*.py` under `cncm/`
    or `cas_meta2/` changes the launcher's input inventory, so it is exactly what must not happen.
    """
    allowed = tuple(GIT_PREFIX + prefix for prefix in ALLOWED_ADDED_PREFIXES)
    inventory = tuple(GIT_PREFIX + prefix for prefix in INVENTORY_TREES)
    violations = []
    for status, path in entries:
        if path.startswith(inventory):
            violations.append('INVENTORY:' + status + ':' + path)
        elif status != 'A' or not path.startswith(allowed):
            violations.append('OUTSIDE_THIS_ADMISSION:' + status + ':' + path)
    return violations


def parse_status_z(raw):
    """`git status --porcelain=v1 -z` output -> [(two-letter code, repo-relative path)].

    A rename or copy entry carries its source path as the NEXT field, which is consumed here.
    """
    fields = raw.split(b'\0')
    entries, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        code, path = entry[:2].decode('ascii'), entry[3:].decode('utf-8')
        if 'R' in code or 'C' in code:
            index += 1
        entries.append((code, path))
    return entries


def status_violations(entries):
    """Everything git status reports, except UNTRACKED files that are this folder's own outputs."""
    tolerated = tuple(GIT_PREFIX + prefix for prefix in TOLERATED_UNTRACKED)
    return [code + ' ' + path for code, path in entries if not (code == '??' and path.startswith(tolerated))]


# ---------------------------------------------------------------------------------------------------------------------
# Record builders (pure: the launcher's constants are passed in).
# ---------------------------------------------------------------------------------------------------------------------
def job_name(stamp):
    return 'cas-meta2-tpntr-' + stamp + '-' + SOURCE_SHA[:8] + '-m-' + str(MODEL_SEED)


def check_stamp(stamp, stop):
    stop(type(stamp) is str and re.fullmatch(r'\d{14}', stamp) is not None, 'STAMP_FORM')
    stop(stamp != HELM2_STAMP and job_name(stamp) != HELM2_JOB, 'STAMP_IS_HELM2_S_OWN_STAMP_A_NEW_JOB_IS_REQUIRED')
    return job_name(stamp)


def owner_record(*, schema, candidate, job, condition, bounds, plan):
    """The owner record for the one job. The launcher reads schema, candidate, owner_instruction_raw, job, bounds."""
    owner_words, plan_words = quotes_record()
    return {'schema': schema, 'candidate': candidate,
            'owner_instruction_raw': owner_words['owner_launch_approval_raw'],
            'owner_words_verbatim': owner_words, 'plan_text_verbatim': plan_words, 'plan_record': plan,
            'owner_answered_date': OWNER_ANSWERED_DATE,
            'option_c_chosen_by': ('the Claude coordinator, under the owner\'s delegation quoted in '
                                   'owner_option_delegation_raw (plan section 4a); this is not an owner signature'),
            'transcribed_by_agent': True, 'is_owner_signature': False, 'label': LABEL, 'runner': RUNNER,
            'job': job, 'job_kind': JOB_KIND, 'condition': condition, 'model_seed': MODEL_SEED,
            'source_sha': SOURCE_SHA, 'reproduces_job': HELM2_JOB,
            'comparison_target': reference_pointer(),
            'scope': ('ONE job: seed 20260917 of source 20208c92, the full registered 10-pass schedule, the committed '
                      'package_20208c92, one machine, no automatic retry. Launched only after the three repaired '
                      'seeds, after this writer is reviewed, and only if measured spend so far + $15.00 <= $60.00.'),
            'bounds': bounds}


def reference_pointer():
    return {'final_pt_sha256': REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': REFERENCE_FINAL_PT_BYTES,
            'commit': REFERENCE_COMMIT, 'receipt': GIT_PREFIX + REFERENCE_RECEIPT_REL,
            'records': {name: {'path': GIT_PREFIX + REFERENCE_RECEIPT_REL + '/' + name, 'blob': REFERENCE_BLOBS[name]}
                        for name in FINAL_PT_RECORDS}}


def launch_argv(*, launcher, request, authority, owner, receipt_dir, ledger):
    """The exact argv, in `execute_study.py`'s order. No `--reduced-schedule`: this is the full registered run."""
    return ['python', '-B', str(launcher), '--execute',
            '--request', request['path'], '--request-sha256', request['sha256'],
            '--authority', authority['path'], '--authority-sha256', authority['sha256'],
            '--owner-authorization', owner['path'], '--receipt-dir', str(receipt_dir),
            '--ledger-path', str(ledger)]


def config_equal_except_job(new_text, old_text, new_job, old_job):
    """True when the two canonical worker configs are the same text once the job name is swapped.

    The job name appears exactly twice in the config (`job` and `bucket`, which is the job plus the account); it is
    checked to appear the same number of times on both sides, so the swap cannot hide a second difference.
    """
    if new_job == old_job or new_text.count(new_job) != old_text.count(old_job) or new_text.count(new_job) != 2:
        return False
    return new_text.replace(new_job, old_job) == old_text


# ---------------------------------------------------------------------------------------------------------------------
# Writing.
# ---------------------------------------------------------------------------------------------------------------------
def partial_of(folder):
    return folder.with_name(folder.name + '.partial')


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def write_folder_atomically(final, entries, recheck, stop):
    """Write every file into `<final>.partial`, read it all back, re-run `recheck`, then rename into place.

    `entries` is a list of `(final_path, raw)` inside `final`. `recheck(locate)` re-runs the caller's validators, where
    `locate(final_path)` gives the file's current (partial) path. If anything fails, the `.partial` folder stays for a
    person to inspect, and every later run refuses until it is dealt with by hand. Nothing here deletes anything.
    """
    partial = partial_of(final)
    stop(not final.exists(), 'TARGET_EXISTS_NO_OVERWRITE:' + str(final))
    stop(not partial.exists(), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND:' + str(partial))
    relative = []
    for path, raw in entries:
        stop(Path(path).is_relative_to(final) and type(raw) is bytes, 'ENTRY_OUTSIDE_TARGET:' + str(path))
        stop(b'\r' not in raw, 'ENTRY_HAS_CR_BYTES:' + str(path))      # committed under `text eol=lf`
        relative.append((Path(path).relative_to(final), raw))
    stop(len({item for item, _ in relative}) == len(relative), 'ENTRY_DUPLICATED')
    partial.mkdir()
    for item, raw in relative:
        target = partial / item
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    present = sorted(path.relative_to(partial).as_posix() for path in partial.rglob('*') if path.is_file())
    stop(present == sorted(item.as_posix() for item, _ in relative), 'PARTIAL_FILE_SET')
    for item, raw in relative:
        stop((partial / item).read_bytes() == raw, 'WRITTEN_BYTES:' + item.as_posix())
    recheck(lambda path: partial / Path(path).relative_to(final))
    os.rename(partial, final)
    for item, raw in relative:
        stop((final / item).read_bytes() == raw, 'RENAMED_BYTES:' + item.as_posix())
    return [pin(final / item, raw) for item, raw in relative]


def canonical(value):
    """The launcher's canonical JSON form (`graph_training_curriculum_launch.canonical`), for launcher-free code."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('utf-8')
