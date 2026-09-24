"""Shared, launcher-free facts and checks for the switch-ON smoke writer, the seed writer and the runner.

WHY A SHARED MODULE. Three scripts in this folder must agree, byte for byte, on the same facts: where each output
goes, which untracked paths each writer may tolerate, the owner's words, the item-1 rule, the cost ceiling and the
stop rules. Retyping them three times is how they drift. This module holds them once.

IT IMPORTS NOTHING FROM THE LAUNCHER, torch or the network. The runner imports it without importing the launcher,
so the runner stays light on the operator's laptop. The two writers import the launcher themselves.

IT LIVES UNDER `records/`, NOT under `cncm/` or `cas_meta2/`, on purpose. `pointer_contract.input_inventory` globs
every `*.py` under those two trees, so a new file there would change the launcher's input inventory and its
`inputs_sha256`. Nothing here is in that inventory.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder, 2026-09-23). Transcribes the owner's words; it is not an
owner signature.
"""
import ast
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]          # the CNCM folder ("FOR CODEX TO BUILD CAS NATIVE ...")
GIT_PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
RECEIPTS = ROOT / 'records/typed_pointer_001'
PACKAGE_PARENT = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001'
LAUNCHER = ROOT / 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py'

# ---- the two admission output folders. Each writer writes ONE folder, first as `<name>.partial`, then renames it.
SEED_OUTPUT = HERE / 'seeds'           # seeds/<seed>/{owner,request,authority}.json, study.json, item1_reading.json
SMOKE_OUTPUT = HERE / 'smoke'          # smoke/<seed>/{owner,request,authority}.json, smoke.json, item1_reading.json
RUN_LOG = HERE / 'run_log.jsonl'       # written only by run_on_study.py --execute, append-only
SEEDS = (20260917, 20260918, 20260919)
SMOKE_SEED = 20260917
# The owner-required short test run WITH ablations, exactly as the coordinator specified it. It is the launcher's
# canonical form (sorted keys, no spaces), so the text on the command line is the text baked into the package.
SMOKE_LITERAL = ('{"ablations":true,"evaluations":[0,1],"interference":false,"passes":1,'
                 '"phase_a":["initial","pass_01","final"],"phase_b":false,"reloads":true,"replays":true,'
                 '"retention":false,"updates":8}')
# 51 artifact names + 3 envelope entries. Derived by hand from `expected_artifact_names` (40 for Helm 2.0's smoke,
# plus 5 ablation phases x 2 files, plus ablations.json) and checked by the smoke writer against the worker's own
# function before anything is written.
SMOKE_ARTIFACT_NAMES = 51
SMOKE_REQUIRED_COUNT = 54

# ---- item 1 (the order rule): training runs only after acceptance item 1 has passed.
ITEM1_PASS_VERDICT = 'OFF_PRESERVED_ON_T4'
ITEM1_COPY_NAME = 'item1_reading.json'
ITEM1_MAX_BYTES = 8 * 1024 * 1024

# ---- money. The owner approved "Up to $60 (Recommended)" for one test run plus 3 seeds.
RESERVATION_PER_JOB_USD = '15.00'
CEILING_USD = '60.00'                  # smoke $15.00 + 3 x $15.00
SEED_RESERVATIONS_USD = '45.00'
SPEND_STOP_USD = '30.00'               # "if actual spend passes $30 before the third seed, stop and report"
STOP_RULES = (
    'if the test run fails, no seed is launched;',
    'if any seed ends other than delivered, the next seed is not launched;',
    'if actual spend passes $30 before the third seed, stop and report.',
)
ONE_MACHINE_AT_A_TIME = True
AUTOMATIC_RETRIES = 0
# The launcher's bounds the writers expect. A writer refuses, rather than silently recording other numbers, if the
# launcher has moved (the training path the owner approved is Helm 2.0's g7.2xlarge path, one job per record).
EXPECTED_BOUNDS = {'training': True, 'jobs': 1, 'automatic_retries': 0, 'reservation_usd': RESERVATION_PER_JOB_USD,
                   'instance_type': 'g7.2xlarge', 'region': 'us-west-2'}

# ---- the owner's words, verbatim. Each is pinned by sha256 AND checked, at write time, against the committed
# owner record below (read with `git show`, never from a working-tree copy that could have been edited).
OWNER_RECORD_COMMIT = 'd6c9faa9e4b5f61730af127937776bad3fef18f4'
OWNER_RECORD_PATH = GIT_PREFIX + '_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DECISIONS_TAKEOVER_20260923.md'
OWNER_RECORD_BLOB = '35bbb67e48d3f07ee36c27e10cd800b51d274b1e'
OWNER_ANSWERED_DATE = '2026-09-23'
OWNER_INSTRUCTION_RAW = '3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL'
OWNER_MESSAGE_FULL_RAW = ('4. KEEP IT (G6E.XLARGE) 3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL '
                          '2. GO WITH YOUR RECOMMENDATION 6 AND 7 NODE 1. FOR RESCORER PICK WHICH EVER ONE '
                          'MAKES FOR A BETTER MODEL')
OWNER_BUDGET_QUESTION_RAW = (
    'Switch-ON training must run on the same AWS g7.2xlarge Helm 2.0 used (the training code refuses any other '
    'GPU). Expected real cost is about $24 total: a ~$1.50 short test run, then 3 seeds of about 3 hours each '
    '(~$7.50 each), one at a time. The code books a fixed $15 per job, so up to $60 is reserved. What spending '
    'limit do you approve?')
OWNER_BUDGET_ANSWER_RAW = 'Up to $60 (Recommended)'
OWNER_BUDGET_OPTION_RAW = ('Short test run + 3 seeds, one at a time. Expected ~$24. Stops if the test run or any '
                           'seed fails, and I stop and report if spend passes $30 before the third seed.')
OWNER_WORD_PINS = {
    'owner_instruction_raw': (OWNER_INSTRUCTION_RAW,
                              'a8c84d3c9fe8906b0f8c4a1aa8065648c2c341003ecc2065ec9e2854f73a0a6d'),
    'owner_message_full_raw': (OWNER_MESSAGE_FULL_RAW,
                               'f3a62b2e43112d0d120437948d47e7707152021ec8f49a3b742d4b0186372f58'),
    'owner_budget_question_raw': (OWNER_BUDGET_QUESTION_RAW,
                                  '37ab77f13f653acc13503536040318c956bcb2c7fd02950933518e6eb104c8ce'),
    'owner_budget_answer_raw': (OWNER_BUDGET_ANSWER_RAW,
                                '8893bc06769c0e9b8e0c0f0a5e26e9a6e81be099b3de3345a8592f04ae446606'),
    'owner_budget_option_raw': (OWNER_BUDGET_OPTION_RAW,
                                '0ecd0ed1acfa139f50c0c526b581afe6ed5d878c7f5ffe3671515b05d306aa24'),
}
LABEL = 'CLAUDE_BUILT_CLAUDE_CHECKED'
RUNNER = 'Claude coordinator (temporary takeover)'

# ---- the migration record the owner requires before launch (static, committed beside this file).
MIGRATION = HERE / 'MIGRATION_ON_SHAPES.json'
MIGRATION_SHA256 = 'dbdcda9c7b64a83d9f2bb8ee260bc1450427d8e9b62d52ecb03490330e87c207'
INVENTORY = ROOT / 'records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json'

# ---- members of the built source.zip that carry the switch default and the ablation table.
PACKAGED_LEARNER = 'research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py'
PACKAGED_WORKER = 'cncm/typed_pointer_worker.py'
ANALOGY_INIT_SEED = 20260923

# The paths under which a runner must see NO difference between the source commit and HEAD: every tree the
# launcher's input inventory and packaging read from, plus the launcher itself.
INVENTORY_TREES = ('cncm', 'research/CAS_META_2_COMPOSITION/cas_meta2', 'research/CAS_META_2_COMPOSITION/aws')


def make_stop(prefix):
    """An explicit stop, never an `assert` (which `python -O` removes)."""
    def stop_unless(condition, reason):
        if not condition:
            raise SystemExit(prefix + reason)
    return stop_unless


def digest(raw):
    return sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def partial_of(folder):
    return folder.with_name(folder.name + '.partial')


def seed_package_dir(source_sha):
    return PACKAGE_PARENT / ('package_' + source_sha[:8])


def smoke_package_dir(source_sha):
    return PACKAGE_PARENT / ('package_on_smoke_' + source_sha[:8])


def seed_receipt_dir(seed):
    return RECEIPTS / ('receipt_analogy_on_' + str(seed))


def smoke_receipt_dir(seed=SMOKE_SEED):
    return RECEIPTS / ('receipt_analogy_on_smoke_' + str(seed))


def tolerated_prefixes(source_sha):
    """Repository-relative prefixes of the ONLY untracked paths either writer tolerates at HEAD == source.

    Each writer tolerates its own package, the other writer's package and the other writer's admission folder. Its
    own admission folder must not exist at all, which the writer refuses separately. A `.partial` folder is never
    tolerated (`seeds/` does not prefix `seeds.partial/`).
    """
    folders = (seed_package_dir(source_sha), smoke_package_dir(source_sha), SEED_OUTPUT, SMOKE_OUTPUT)
    return tuple(GIT_PREFIX + folder.relative_to(ROOT).as_posix() + '/' for folder in folders)


def dirty_paths(source_sha, stop):
    """Every changed or untracked path under ROOT, except UNTRACKED files under `tolerated_prefixes`."""
    prefix = git('rev-parse', '--show-prefix').decode('utf-8').strip()
    stop(prefix == GIT_PREFIX, 'GIT_PREFIX:' + prefix)
    allowed = tolerated_prefixes(source_sha)
    fields = git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', '.').split(b'\0')
    dirty, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        code, path = entry[:2].decode('ascii'), entry[3:].decode('utf-8')
        if 'R' in code or 'C' in code:
            index += 1                      # a rename or copy carries its source path as the next field
        if code == '??' and path.startswith(allowed):
            continue
        dirty.append(code + ' ' + path)
    return dirty


def refuse_partials(stop):
    """A `.partial` folder means an earlier write stopped half-way. A person must look at it; nothing deletes it."""
    for folder in (SEED_OUTPUT, SMOKE_OUTPUT):
        stop(not partial_of(folder).exists(), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND:' + str(partial_of(folder)))


def check_head(source_sha, stop):
    head = git('rev-parse', 'HEAD').decode('ascii').strip()
    stop(head == source_sha, 'SOURCE_SHA_IS_NOT_HEAD:' + head)


def normalised_owner_record():
    """The committed owner record's text with its line breaks (and blockquote markers) turned into spaces."""
    blob = git('rev-parse', OWNER_RECORD_COMMIT + ':' + OWNER_RECORD_PATH).decode('ascii').strip()
    raw = git('show', OWNER_RECORD_COMMIT + ':' + OWNER_RECORD_PATH)
    return blob, raw, raw.decode('utf-8').replace('\n> ', ' ').replace('\n', ' ')


def verify_owner_words(stop):
    """Every quoted owner string matches its pin AND occurs exactly once, verbatim, in the committed owner record."""
    for name, (text, pinned) in OWNER_WORD_PINS.items():
        stop(digest(text.encode('utf-8')) == pinned, 'OWNER_WORDS_EDITED:' + name)
    stop(OWNER_INSTRUCTION_RAW in OWNER_MESSAGE_FULL_RAW, 'OWNER_ITEM_3_NOT_IN_FULL_MESSAGE')
    try:
        blob, raw, text = normalised_owner_record()
    except subprocess.CalledProcessError:
        stop(False, 'OWNER_RECORD_OBJECT_MISSING:git fetch origin research/helm-integration-20260923 (do not check '
                    'it out), then re-run')
    stop(blob == OWNER_RECORD_BLOB, 'OWNER_RECORD_BLOB:' + blob)
    for name, (words, _) in OWNER_WORD_PINS.items():
        if name == 'owner_instruction_raw':
            continue                        # item 3 is inside the full message; its own count is not 1 by design
        stop(text.count(words) == 1, 'OWNER_WORDS_NOT_IN_OWNER_RECORD:' + name)
    for rule in STOP_RULES:
        stop(text.count(rule) == 1, 'STOP_RULE_NOT_IN_OWNER_RECORD:' + rule)
    return {'commit': OWNER_RECORD_COMMIT, 'path': OWNER_RECORD_PATH, 'blob': blob, 'sha256': digest(raw),
            'bytes': len(raw), 'section': 'section 3 and its addendum "the spending limit for switch-ON training"'}


def owner_budget_fields(owner_record):
    """The budget facts every record carries, in one shape."""
    return {'owner_budget_question_raw': OWNER_BUDGET_QUESTION_RAW,
            'owner_budget_answer_raw': OWNER_BUDGET_ANSWER_RAW,
            'owner_budget_option_raw': OWNER_BUDGET_OPTION_RAW,
            'owner_record': owner_record,
            'ceiling_usd': CEILING_USD,
            'ceiling_basis': ('one reduced-schedule test run (the smoke) $15.00 + 3 seed jobs x $15.00, each the '
                              "launcher's fixed reservation; g7.2xlarge, us-west-2"),
            'smoke_reservation_usd': RESERVATION_PER_JOB_USD,
            'seed_reservations_usd': SEED_RESERVATIONS_USD,
            'reservation_per_job_usd': RESERVATION_PER_JOB_USD,
            'one_machine_at_a_time': ONE_MACHINE_AT_A_TIME,
            'automatic_retries': AUTOMATIC_RETRIES,
            'stop_rules': list(STOP_RULES),
            'spend_stop_usd': SPEND_STOP_USD,
            'stop_rules_enforced_by': 'records/typed_pointer_001/admission_analogy_on_001/run_on_study.py'}


def check_budget(reservation_usd, stop):
    stop(reservation_usd == RESERVATION_PER_JOB_USD, 'RESERVATION_CHANGED:' + str(reservation_usd))
    stop(Decimal(reservation_usd) * (1 + len(SEEDS)) == Decimal(CEILING_USD), 'CEILING_ARITHMETIC')
    stop(Decimal(reservation_usd) * len(SEEDS) == Decimal(SEED_RESERVATIONS_USD), 'SEED_RESERVATION_ARITHMETIC')


def check_switch_on_source(launch, contract, pointer_learner, stop):
    """That this checkout really is the switch-ON design with the ablation fix, on the approved training path.

    The three modules are passed in by the writer, so this file itself never imports the launcher.
    """
    import inspect
    default = inspect.signature(pointer_learner._build_container).parameters['analogy_focus_comparison'].default
    stop(default is True, 'SWITCH_DEFAULT_IS_NOT_ON')
    stop(pointer_learner.ANALOGY_INIT_SEED == ANALOGY_INIT_SEED, 'ANALOGY_INIT_SEED_CHANGED')
    worker = launch._probe()
    heads = dict(worker.ABLATION_COMPONENTS).get('heads', ())
    stop('analogy_head.' in heads, 'ABLATION_HEADS_ROW_LACKS_ANALOGY_HEAD')
    stop(tuple(contract.MODEL_SEEDS) == SEEDS and SMOKE_SEED in SEEDS, 'MODEL_SEEDS_CHANGED')
    stop(all(launch.BOUNDS.get(key) == value for key, value in EXPECTED_BOUNDS.items())
         and launch.RESERVATION_USD == launch.BOUNDS['reservation_usd'], 'BOUNDS_CHANGED')
    check_budget(launch.RESERVATION_USD, stop)
    return worker, {'analogy_focus_comparison_default': default, 'analogy_init_seed': ANALOGY_INIT_SEED,
                    'ablation_heads_row': list(heads), 'model_variant': pointer_learner.MODEL_VARIANT,
                    'checkpoint_schema': pointer_learner.CHECKPOINT_SCHEMA}


def read_item1(path, expected_sha256, stop):
    """Acceptance item 1 must have passed before any training job is admitted (owner record, section 3, 'Order').

    Returns `(record, raw)`. The raw bytes are copied into the admission folder, so the evidence travels with it.
    """
    stop(type(expected_sha256) is str and len(expected_sha256) == 64
         and all(ch in '0123456789abcdef' for ch in expected_sha256), 'ITEM1_SHA256_FORM')
    stop(type(path) is str and Path(path).is_file(), 'ITEM1_READING_FILE_MISSING:' + str(path))
    source = Path(path).resolve(strict=True)
    stop(source.stat().st_size <= ITEM1_MAX_BYTES, 'ITEM1_READING_FILE_TOO_LARGE')
    raw = source.read_bytes()
    stop(digest(raw) == expected_sha256, 'ITEM1_READING_SHA256:' + digest(raw))
    # The copy is committed under `text eol=lf`; a CR byte would be rewritten on commit and break this pin.
    stop(b'\r' not in raw, 'ITEM1_READING_HAS_CR_BYTES')
    reading = json.loads(raw)
    stop(type(reading) is dict, 'ITEM1_READING_NOT_AN_OBJECT')
    verdict = reading.get('item1_verdict')
    stop(verdict == ITEM1_PASS_VERDICT, 'ITEM1_NOT_PASSED:' + repr(verdict))
    return {'source_path': str(source), 'sha256': expected_sha256, 'bytes': len(raw), 'item1_verdict': verdict,
            'copied_to': ITEM1_COPY_NAME,
            'expected_origin': ('records/helm_eval_design_20260923/analogy_repair_t4_job/RESULTS_READING.json on '
                                'branch research/helm-integration-20260923 (supplied by the coordinator)')}, raw


def verify_migration(stop):
    """The committed migration record: its pin, and its counts re-derived from the tensor inventory it cites."""
    raw = MIGRATION.read_bytes()
    stop(digest(raw) == MIGRATION_SHA256, 'MIGRATION_RECORD_SHA256:' + digest(raw))
    record = json.loads(raw)
    inventory_raw = INVENTORY.read_bytes()
    stop(digest(inventory_raw) == record['source_inventory']['sha256'], 'MIGRATION_INVENTORY_SHA256')
    rows = json.loads(inventory_raw)['rows']
    head = [row for row in rows if row['name'].startswith('analogy_head.')]
    shared = [row for row in rows if not row['name'].startswith('analogy_head.')]
    stop(len(rows) == record['switch_on']['state_dict_keys'] == 53
         and sum(row['elements'] for row in rows) == record['switch_on']['parameters'] == 203424,
         'MIGRATION_ON_SHAPES')
    stop(len(shared) == record['switch_off']['state_dict_keys'] == 48
         and sum(row['elements'] for row in shared) == record['switch_off']['parameters'] == 174303,
         'MIGRATION_OFF_SHAPES')
    stop([{key: row[key] for key in ('name', 'shape', 'elements')} for row in head] == record['analogy_head_tensors']
         and len(head) == 5, 'MIGRATION_ANALOGY_HEAD_TENSORS')
    stop([item['model_seed'] for item in record['matched_starts']['per_seed']] == list(SEEDS), 'MIGRATION_SEEDS')
    return {'path': str(MIGRATION), 'bytes': len(raw), 'sha256': MIGRATION_SHA256,
            'state_dict_keys_on': 53, 'parameters_on': 203424, 'state_dict_keys_off': 48, 'parameters_off': 174303,
            'helm2_initial_pt_sha256': {str(item['model_seed']): item['helm2_initial_pt_sha256']
                                        for item in record['matched_starts']['per_seed']}}


def packaged_switch_facts(archive, stop):
    """Read the SHIPPED bytes, not this process's imports: the switch default and the ablation `heads` row.

    Parsed with `ast` only. Nothing from the archive is executed.
    """
    with ZipFile(archive) as bundle:
        learner = bundle.read(PACKAGED_LEARNER)
        worker = bundle.read(PACKAGED_WORKER)
    tree = ast.parse(learner.decode('utf-8'))
    seeds = [node.value.value for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1
             and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'ANALOGY_INIT_SEED'
             and isinstance(node.value, ast.Constant)]
    stop(seeds == [ANALOGY_INIT_SEED], 'PACKAGED_ANALOGY_INIT_SEED:' + repr(seeds))
    builders = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_build_container']
    stop(len(builders) == 1, 'PACKAGED_BUILD_CONTAINER')
    arguments = builders[0].args
    defaults = {arg.arg: default for arg, default in zip(arguments.kwonlyargs, arguments.kw_defaults)}
    switch = defaults.get('analogy_focus_comparison')
    stop(isinstance(switch, ast.Constant) and switch.value is True, 'PACKAGED_SWITCH_DEFAULT_IS_NOT_ON')
    seed_default = defaults.get('analogy_seed')
    stop(isinstance(seed_default, ast.Name) and seed_default.id == 'ANALOGY_INIT_SEED', 'PACKAGED_SEED_DEFAULT')
    table = [node.value for node in ast.parse(worker.decode('utf-8')).body if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id == 'ABLATION_COMPONENTS']
    stop(len(table) == 1, 'PACKAGED_ABLATION_TABLE')
    heads = dict(ast.literal_eval(table[0])).get('heads', ())
    stop('analogy_head.' in heads, 'PACKAGED_HEADS_ROW_LACKS_ANALOGY_HEAD')
    return {'packaged_switch_default': True, 'packaged_analogy_init_seed': ANALOGY_INIT_SEED,
            'packaged_heads_row': list(heads), 'packaged_learner_sha256': digest(learner),
            'packaged_worker_sha256': digest(worker)}


PACKAGE_RECEIPT_SCHEMA = 'cncm.typed-pointer-package-receipt/0.1'
REDUCED_SCHEDULE_ENV_BYTES = b'CNCM_POINTER_REDUCED_SCHEDULE'


def verify_package(launch, directory, source_sha, stop, *, smoke):
    """The built package, byte for byte, as the launcher will find and ship it. `launch` is passed in.

    `smoke=True`: the shipped worker must carry the reduced-schedule line exactly once. `smoke=False`: never.
    A package folder without both files is a build that stopped half-way; a person must look at it.
    """
    receipt_path, archive = directory / 'receipt.json', directory / 'source.zip'
    stop(receipt_path.is_file() and archive.is_file(), 'PACKAGE_INCOMPLETE_INSPECT_BY_HAND:' + str(directory))
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    stop(receipt.get('schema') == PACKAGE_RECEIPT_SCHEMA and receipt.get('status') == 'SOURCE_ONLY_NO_LAUNCH'
         and receipt.get('source_sha') == source_sha, 'PACKAGE_RECEIPT')
    raw = archive.read_bytes()
    stop(digest(raw) == receipt['archive_sha256'] and len(raw) == receipt['archive_bytes'], 'PACKAGE_ARCHIVE_BYTES')
    # The launcher finds the archive through the receipt's own `archive` path (`_locate_archive`), so that path
    # must be this very file in this checkout, and the launcher's own search must return it.
    stop(Path(receipt['archive']).resolve() == archive.resolve(), 'PACKAGE_ARCHIVE_PATH')
    stop(launch.lifecycle._locate_archive(receipt['archive_sha256']).resolve() == archive.resolve(),
         'LAUNCHER_CANNOT_LOCATE_THIS_ARCHIVE')
    with ZipFile(archive) as bundle:
        manifest_raw = bundle.read(launch.shared.MANIFEST_NAME)
        worker_member = bundle.read(launch.WORKER_NAME)
    stop(digest(manifest_raw) == receipt['manifest_sha256'], 'PACKAGE_MANIFEST_BYTES')
    manifest = json.loads(manifest_raw)
    stop(launch.canonical(manifest) == launch.canonical(receipt['manifest']), 'PACKAGE_RECEIPT_MANIFEST')
    stop(manifest['inputs_sha256'] == launch.frozen_inputs_hash(source_sha), 'PACKAGE_INPUTS_NOT_THIS_SOURCE')
    stop({key: manifest['frozen_budget'].get(key) for key in launch.BOUNDS} == launch.BOUNDS, 'PACKAGE_BOUNDS')
    # `build_pointer_package` always pre-declares the REGISTERED contract here, for a smoke package too (Helm 2.0's
    # delivered smoke had the same). A smoke's own reduced contract is bound in its authority instead.
    registered = launch.run_evidence.contract_digest(launch.evidence_contract())
    stop(manifest['transport']['predeclared_contract_sha256'] == registered, 'PACKAGE_EVIDENCE_CONTRACT')
    count = worker_member.count(REDUCED_SCHEDULE_ENV_BYTES)
    stop(count == (1 if smoke else 0), 'PACKAGE_REDUCED_SCHEDULE_LINE_COUNT:%d' % count)
    return {'source_sha': source_sha, 'archive': str(archive), 'archive_sha256': receipt['archive_sha256'],
            'archive_bytes': receipt['archive_bytes'], 'manifest_sha256': receipt['manifest_sha256'],
            'receipt_sha256': digest(receipt_raw), 'inputs_sha256': manifest['inputs_sha256'],
            'package_predeclared_contract_sha256': registered,
            'shipped_worker_member_sha256': digest(worker_member), **packaged_switch_facts(archive, stop)}


def other_package_inputs(directory):
    """`inputs_sha256` of another built package, or `None` if it is not built yet. Read from its own receipt."""
    receipt = directory / 'receipt.json'
    if not receipt.exists():
        return None
    return json.loads(receipt.read_bytes())['manifest']['inputs_sha256']


def other_job_names(record_path):
    """The job names another writer froze, so two writers can never pick the same job name (same bucket)."""
    if not record_path.exists():
        return []
    return [job['job'] for job in json.loads(record_path.read_bytes())['jobs']]


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def write_folder_atomically(final, entries, recheck, stop):
    """Write every file into `<final>.partial`, read it all back, re-run `recheck`, then rename into place.

    `entries` is a list of `(final_path, raw)`; every `final_path` lies inside `final`. `recheck(locate)` re-runs the
    caller's validators, where `locate(final_path)` gives the file's current (partial) path. If anything fails, the
    `.partial` folder stays for a person to inspect, and every later run refuses until it is dealt with by hand.
    """
    partial = partial_of(final)
    stop(not final.exists(), 'TARGET_EXISTS_NO_OVERWRITE:' + str(final))
    stop(not partial.exists(), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND:' + str(partial))
    relative = []
    for path, raw in entries:
        stop(path.is_relative_to(final) and type(raw) is bytes, 'ENTRY_OUTSIDE_TARGET:' + str(path))
        relative.append((path.relative_to(final), raw))
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
