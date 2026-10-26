"""Build the CPU-only pre-check controller folder for Option B job b1 (operator decision D7).

The folder is derived from controller_cas_probe_c02, the CPU probe that was reviewed and ran on
2026-10-04. Bytes and text only: no AWS call, no project code is imported, compiled or run here.
Every text change is an exact-count replacement, so any surprise stops the build. The target
folder must not exist. This script copies itself and its config into the new folder at the end.

What the pre-check job does on AWS (one m6i.xlarge CPU host, no GPU, no model B weights):
unpack the same source.zip the GPU job gets, build the same pinned environment, place ONLY the six
small tokenizer and config files of model B, run 'runner_b1.py selftest --mode precheck' once, and
return its output. Limits: 0.50 USD, 45 minutes, one attempt, the host shuts itself down.

Review round 1 (plan section 19.1). A pre-check that does not pass may be followed by another
pre-check job, by the plan's own rule. So the config names the job:
  "attempt": 1 to 4   each job has its own job id, folder, lease and claim; the number is the suffix
                      (a development test: 1 or 2)
  "kind":             SEALED_PACKAGE     the package of seal step 6 (or of the last repair line 6R)
                      REHEARSAL          after seal step 5 and before seal step 6, on a scratch seal
                      DEVELOPMENT_TEST   made-up data before seal step 1; outside the seal chain;
                                         not one of the 4 jobs; at most 2 such jobs
The seal file decides which kind a package is. The config must say the same, or the build stops.
Only a SEALED_PACKAGE job returns values for seal step 7.

Amendment A10 (2026-10-05). The development test is ordered, not only allowed: one job, at most two,
each with the limits of a pre-check job (0.50 USD, 45 minutes, one attempt). It is authorised by the
operator's decision under the owner's approval record OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json.
Its package holds made-up data only and is built by optionb/dry/build_dev_package.py. Its output is
never evidence about roles. Its result is never written to a seal file.

Amendment A5 (2026-10-05). A tool-repair line can stand only after seal line 1 and before the line
3C. This script stops if the real seal file holds one anywhere else.

Usage:
  python -B derive_precheck_job.py --check-text-only      reads the base files, writes nothing
  python -B derive_precheck_job.py PRECHECK_CONFIG.json   builds the folder (laptop, a few MB of memory)

This script does not write ALLOCATION.json, CONTROLLER_REVIEW.json, INDEPENDENT_STATIC_REVIEW.json,
the lease or the claim. Those records grant authority. The operator writes them after the review.
"""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
BASE = OP / 'controller_cas_probe_c02'
CAS = Path(r'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CASALESCENCE_NOETICS_v0_1')
PLAN = CAS / 'optionb' / 'PLAN_CONSTANTS.json'
SEAL = CAS / 'optionb' / 'SEAL_OPTIONB.jsonl'
POINTER = Path(r'C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json')
# Amendment A10: the standing approval record under which the operator orders the development test.
# REAL: the sha256 was taken from the file on 2026-10-05.
OWNER_APPROVAL = CAS / 'OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json'
OWNER_APPROVAL_SHA = 'd1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325'

# ---- identities of the base (probe c02). REAL: read from its files on 2026-10-05. ----
BASE_PINS_SHA = '5e7d11c59c4661a7cf69567884eecf1bf2bf8ad01008c01f31328ffad1007d27'
OLD_JOB = 'cas-small-v02-software-probe-20261004-c02'
OLD_PREVIOUS_JOB = 'helm-claude-tests-only-20261004-c01'
OLD_PREVIOUS_FOLDER = 'controller_claude_tests_c01'
OLD_PREVIOUS_CLEANUP_FILE = 'aws-claude-tests-c01-independent-cleanup.json'
OLD_PREVIOUS_CLEANUP_SHA = '6efee0d7e6940113529b1eac0eda685f7dd088a7c692c515fce9fd89ab105d81'
OLD_PREVIOUS_RESOURCES = "previous['instance']=='i-07cb2598bb2cd7dd9' and previous['all_job_volumes']==['vol-0301e3b4af24e3f69']"
OLD_ARCHIVE = 'c58a6da0623719c387e513019785bc65192dc2e7a047f708345be4896a4e3055'
OLD_MANIFEST = 'df821cf46c2c977781bade4bce677fe2d7cd29a75f039755930e653a9df811e8'
OLD_STEM = 'aws-cas-probe-c02'
OLD_PAYLOAD = 'cas-probe-c02-payload.zip'
OLD_PURPOSE = ("'purpose':'Tests-only probe: /opt/pytorch package inventory, isolated pinned overlay per package "
               "FUTURE_COMMANDS, CASalescence small v0.2 28 software tests once; no model, no experiment'")
OLD_PROJECT_FILES = ("    project_files = ('src/casalescence_pilot/small_host.py', 'tools/run_small_tests_once.py',\n"
                     "                     'contracts/software-test-roster.json', 'contracts/requirements.small-linux.txt',\n"
                     "                     'BUNDLE_MANIFEST.json')\n")

# ---- identities and limits of the new job ----
# Review round 1 (plan section 19.1): each pre-check job has its own job id, folder, lease and claim, with the attempt
# number as suffix. name_the_job() sets these six names. Nothing below uses them before it has run.
JOBS_MAX = 4
# Amendment A10: at most 2 development tests (PLAN_CONSTANTS.json, aws.development_test_job.jobs_max).
DEV_JOBS_MAX = 2
SERIES_MAX = {'p': JOBS_MAX, 'd': DEV_JOBS_MAX}
KINDS = ('SEALED_PACKAGE', 'REHEARSAL', 'DEVELOPMENT_TEST')
# (job id, file stem, lease and claim prefix, folder). p = one of the 4 pre-check jobs. d = a test on made-up data
# before seal step 1, which is not one of the 4 jobs.
NAME_FORMS = {'p': ('cas-optionb-b1-precheck-p%d', 'aws-cas-optionb-precheck-p%d', 'CAS_OPTIONB_PRECHECK_P%d',
                    'controller_cas_optionb_precheck_p%d'),
              'd': ('cas-optionb-b1-devtest-d%d', 'aws-cas-optionb-devtest-d%d', 'CAS_OPTIONB_DEVTEST_D%d',
                    'controller_cas_optionb_devtest_d%d')}
JOB = STEM = PAYLOAD_NAME = LEASE = CLAIM = NEW = None


def claim_name(series, attempt):
    return NAME_FORMS[series][2] % attempt + '_SINGLE_LAUNCH_CLAIM.json'


def name_the_job(kind, attempt):
    """Set the six names of one job. Returns the series letter: 'p' or 'd'."""
    global JOB, STEM, PAYLOAD_NAME, LEASE, CLAIM, NEW
    assert kind in KINDS, ('KIND_MUST_BE_ONE_OF', KINDS, kind)
    series = 'd' if kind == 'DEVELOPMENT_TEST' else 'p'
    # 1 to 4 for a pre-check job; 1 or 2 for a development test (amendment A10).
    assert type(attempt) is int and 1 <= attempt <= SERIES_MAX[series], (
        'ATTEMPT_MUST_BE_A_WHOLE_NUMBER_FROM_1_TO_%d_FOR_THIS_KIND' % SERIES_MAX[series], kind, attempt)
    job, stem, prefix, folder = (form % attempt for form in NAME_FORMS[series])
    JOB, STEM, NEW = job, stem, OP / folder
    PAYLOAD_NAME = stem[len('aws-'):] + '-payload.zip'
    LEASE, CLAIM = prefix + '_TRANSPORT_LEASE.json', claim_name(series, attempt)
    return series


SUPERVISOR = 'precheck_supervisor.py'
CAP_USD = 0.50
HOST_MINUTES, FORCE_MINUTES, WORK_MINUTES = 45, 40, 35
WORKLOAD_SECONDS = 2100
MINIMUM_ADMISSION_SECONDS = 1500
STAGE_MAXIMUM_SECONDS = {'runtime_preflight': 300, 'opt_pytorch_inventory': 60, 'overlay_install': 600,
                         'import_smoke': 180, 'selftest': 900}
# Upper estimate at the admitted maximum: 45 minutes at the 0.20 USD per hour bound, the unchanged allowances of
# service_prices.py, 8 billable storage days and the unchanged 0.15 USD contingency.
UPPER_COMPONENTS = {'compute_45min_at_0_20_per_hour': 0.15, 'root_storage': 0.03, 'public_ipv4': 0.01,
                    'bounded_transfer_and_requests': 0.15,
                    'retention_storage_8_days_at_0_023_per_gb_month': 0.003285714286, 'contingency': 0.15,
                    'sum_upper': 0.493285714286}
REQUIREMENTS_SHA = '6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7'
# Review round 1: tools/verdict.py is a package file (FILE_FORMATS.md section 14). The analysis program needs it for
# three views the plan says are always printed, and the self-test must run their code before the GPU attempt.
PROJECT_FILES = ('job/runner_b1.py', 'job/scorer_v0_1_1.py', 'job/gate_b1.py', 'job/analysis_b1.py',
                 'job/scorer_examples_v0_1_1.json', 'prompts/prompt_parts_practice.json',
                 'prompts/prompt_parts_final.json', 'keys_practice/keys_practice.json',
                 'keys_practice/task_meta_practice.json', 'keys_final/keys_final.json',
                 'keys_final/task_meta_final.json', 'PLAN_CONSTANTS.json', 'SEAL_OPTIONB.jsonl', 'tools/verdict.py',
                 'contracts/requirements.small-linux.txt', 'BUNDLE_MANIFEST.json')
PURPOSE = ('Option B pre-check (decision D7): /opt/pytorch package inventory, isolated pinned overlay, then '
           'runner_b1.py selftest --mode precheck once with the tokenizer only; no model B weights, no model call, '
           'no experiment')
TOKEN_ARCHIVE = '@@SOURCE_ARCHIVE_SHA256@@'
TOKEN_MANIFEST = '@@BUNDLE_MANIFEST_SHA256@@'
TOKEN_JOB = '@@JOB@@'
TOKEN_KIND = '@@PRECHECK_KIND@@'
PROGRAM_LINES = ('6_PROGRAMS', '6R_PROGRAMS_REPAIRED')
# Amendment A5: the tool-repair line, and the line that closes its window.
TOOL_REPAIR, FINAL_LINE = 'TR_TOOLS_REPAIRED', '3C_FINAL_QUESTIONS_AND_KEYS'


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def text(path):
    """Exact UTF-8 text of an LF-only file. No newline translation."""
    value = Path(path).read_bytes().decode('utf-8')
    assert '\r' not in value, ('CARRIAGE_RETURN_IN_SOURCE', str(path))
    return value


def rep(value, old, new, count, label):
    found = value.count(old)
    if found != count:
        raise SystemExit('REPLACE_COUNT %s: expected %d found %d' % (label, count, found))
    return value.replace(old, new)


def apply(value, edits, name):
    for old, new, count, label in edits:
        value = rep(value, old, new, count, name + ':' + label)
    return value


def write_lf(path, value):
    assert '\r' not in value, path
    with open(path, 'x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


# ---------------- the edit tables: (old text, new text, exact count, label) ----------------

def control_edits(v):
    combined = round(v['existing'] + CAP_USD, 2)
    return [
        ("\nJOB='" + OLD_JOB + "'", "\nJOB='" + JOB + "'", 1, 'job'),
        ("PREVIOUS_JOB='" + OLD_PREVIOUS_JOB + "'", "PREVIOUS_JOB='" + v['previous_job'] + "'", 1, 'previous job'),
        ('EXISTING_ALLOCATION_USD=78.96', 'EXISTING_ALLOCATION_USD=' + repr(v['existing']), 1, 'existing allocation'),
        ("PREVIOUS_WORK=PACKAGE.parent/'" + OLD_PREVIOUS_FOLDER + "'",
         "PREVIOUS_WORK=PACKAGE.parent/'" + v['previous_folder'] + "'", 1, 'previous work'),
        ("PREVIOUS_CLEANUP_SHA256='" + OLD_PREVIOUS_CLEANUP_SHA + "'",
         "PREVIOUS_CLEANUP_SHA256='" + v['previous_cleanup_sha'] + "'", 1, 'previous cleanup pin'),
        # Own-job file stem first, so the previous-job cleanup file name inserted next is not touched.
        (OLD_STEM + '-', STEM + '-', 18, 'file stem'),
        ("'" + OLD_PREVIOUS_CLEANUP_FILE + "'", "'" + v['previous_cleanup_file'] + "'", 1, 'previous cleanup file'),
        (OLD_PAYLOAD, PAYLOAD_NAME, 4, 'payload name'),
        ('CAS_PROBE_C02_TRANSPORT_LEASE.json', LEASE, 1, 'lease'),
        ('CAS_PROBE_C02_SINGLE_LAUNCH_CLAIM.json', CLAIM, 1, 'claim'),
        (OLD_MANIFEST, v['manifest'], 9, 'source freeze = sha256 of BUNDLE_MANIFEST.json'),
        (OLD_ARCHIVE, v['archive'], 8, 'archive = sha256 of source.zip'),
        ("authority.get('combined_existing_allocation_usd')==78.96 and authority.get('combined_allocation_usd')==79.96",
         "authority.get('combined_existing_allocation_usd')==%r and authority.get('combined_allocation_usd')==%r"
         % (v['existing'], combined), 1, 'ledger numbers'),
        (OLD_PREVIOUS_RESOURCES,
         "previous['instance']=='" + v['previous_instance'] + "' and previous['all_job_volumes']=="
         + repr(v['previous_volumes']), 1, 'previous resources'),
        (OLD_PURPOSE, "'purpose':" + repr(PURPOSE), 1, 'purpose'),
        # ---- money: 1.00 USD becomes 0.50 USD ----
        ('PROPOSED_CAP_USD=1.00', 'PROPOSED_CAP_USD=0.50', 1, 'cap'),
        # ---- time: 60 / 55 / 50 minutes become 45 / 40 / 35 minutes ----
        ("policy['maximum_host_minutes']==60 and policy['maximum_workload_seconds']==3000",
         "policy['maximum_host_minutes']==%d and policy['maximum_workload_seconds']==%d"
         % (HOST_MINUTES, WORKLOAD_SECONDS), 1, 'policy host and work window'),
        ("policy['work_cutoff_minutes']==50 and policy['force_cutoff_minutes']==55",
         "policy['work_cutoff_minutes']==%d and policy['force_cutoff_minutes']==%d" % (WORK_MINUTES, FORCE_MINUTES),
         1, 'policy cutoffs'),
        ("components={'compute_60min':rates[0],", "components={'compute_45min':rates[0]*0.75,", 1, 'compute estimate'),
        ('cut=started+datetime.timedelta(minutes=55)', 'cut=started+datetime.timedelta(minutes=%d)' % FORCE_MINUTES,
         1, 'force cutoff'),
        ('work_cut=started+datetime.timedelta(minutes=50)',
         'work_cut=started+datetime.timedelta(minutes=%d)' % WORK_MINUTES, 1, 'work cutoff'),
        ("'hard_deadline_utc':(started+datetime.timedelta(minutes=60)).isoformat()",
         "'hard_deadline_utc':(started+datetime.timedelta(minutes=%d)).isoformat()" % HOST_MINUTES, 1, 'hard deadline'),
        ('API_FORCE_CUTOFF_REMAINS_EXACT_55_MINUTES', 'API_FORCE_CUTOFF_REMAINS_EXACT_%d_MINUTES' % FORCE_MINUTES,
         1, 'force cutoff wording'),
        ("'maximum_workload_seconds':3000,", "'maximum_workload_seconds':%d," % WORKLOAD_SECONDS, 1, 'intent work window'),
        ('(work_cut-now()).total_seconds()<2400', '(work_cut-now()).total_seconds()<%d' % MINIMUM_ADMISSION_SECONDS,
         2, 'minimum dispatch window'),
        ('INSUFFICIENT_2400_SECOND_WORK_WINDOW', 'INSUFFICIENT_%d_SECOND_WORK_WINDOW' % MINIMUM_ADMISSION_SECONDS,
         1, 'minimum dispatch window wording'),
    ]


CONTROL_STALE = (OLD_JOB, OLD_ARCHIVE, OLD_MANIFEST, 'cas-probe-c02', 'CAS_PROBE_C02', '78.96', '79.96', '3000', '2400',
                 'minutes=55', 'minutes=50', 'minutes=60', 'compute_60min', 'PROPOSED_CAP_USD=1.00', 'software')


def worker_edits(v):
    return [
        (OLD_JOB, JOB, 10, 'job'),
        (OLD_MANIFEST, v['manifest'], 8, 'source freeze'),
        (OLD_ARCHIVE, v['archive'], 4, 'archive'),
        ("assert receipt['status'] in ('PROBE_COMPLETE_SOFTWARE28_PASS','PROBE_COMPLETE_WITH_FINDINGS')",
         "assert receipt['status'] in ('PRECHECK_COMPLETE_SELFTEST_PASS','PRECHECK_COMPLETE_WITH_FINDINGS')", 1, 'status'),
        ("assert [s['name'] for s in receipt['suites']]==['opt_pytorch_inventory','overlay_install','import_smoke','software28']",
         "assert [s['name'] for s in receipt['suites']]==['opt_pytorch_inventory','overlay_install','import_smoke','selftest']",
         1, 'stage names'),
        ("if receipt['status']=='PROBE_COMPLETE_SOFTWARE28_PASS':",
         "if receipt['status']=='PRECHECK_COMPLETE_SELFTEST_PASS':", 1, 'pass branch'),
        (" assert (test['tests_run'],test['failures'],test['errors'],test['skipped'])==(28,0,0,0)\n",
         " assert test['selftest_status']=='SELFTEST_PASS' and test['selftest_mode']=='precheck' and test['bound_hashes_match_files'] is True\n",
         1, 'pass branch stage check'),
        # ---- time: the 3000 second window becomes 2100 seconds; the least admitted window 2400 becomes 1500 ----
        ('work cutoff 3000 seconds after launch', 'work cutoff %d seconds after launch' % WORKLOAD_SECONDS, 1, 'comment 1'),
        ('Admit at least 2400 seconds remaining', 'Admit at least %d seconds remaining' % MINIMUM_ADMISSION_SECONDS,
         1, 'comment 2'),
        ('a fresh 3000-second allowance. The 50-to-55-minute finalization reserve',
         'a fresh %d-second allowance. The %d-to-%d-minute finalization reserve'
         % (WORKLOAD_SECONDS, WORK_MINUTES, FORCE_MINUTES), 1, 'comment 3'),
        ('the controller owns the60minute hard cap', 'the controller owns the %d minute hard cap' % HOST_MINUTES,
         1, 'comment 4'),
        ('if [ "$remaining" -lt 2400 ]; then phase INSUFFICIENT_SHARED_WINDOW; exit 4; fi',
         'if [ "$remaining" -lt %d ]; then phase INSUFFICIENT_SHARED_WINDOW; exit 4; fi' % MINIMUM_ADMISSION_SECONDS,
         1, 'least admitted window'),
        ('if [ "$remaining" -gt 3000 ]; then remaining=3000; fi',
         'if [ "$remaining" -gt %d ]; then remaining=%d; fi' % (WORKLOAD_SECONDS, WORKLOAD_SECONDS), 1, 'window cap'),
    ]


WORKER_STALE = (OLD_JOB, OLD_ARCHIVE, OLD_MANIFEST, '3000', '2400', '60minute', '50-to-55', 'software28',
                'PROBE_COMPLETE', 'c02')


def preflight_edits(v):
    new_files = ('    project_files = (' + ',\n                     '.join(repr(name) for name in PROJECT_FILES) + ')\n')
    return [
        (OLD_JOB, JOB, 1, 'job'),
        (OLD_PROJECT_FILES, new_files, 1, 'project files'),
        (OLD_MANIFEST, v['manifest'], 1, 'bundle manifest'),
    ]


def entry_edits(v):
    return [('execution/cas_probe_supervisor.py', 'execution/' + SUPERVISOR, 1, 'supervisor')]


def cleanup_edits(v):
    return [
        (OLD_JOB, JOB, 1, 'job'),
        (OLD_STEM, STEM, 6, 'file stem'),
        (OLD_PAYLOAD, PAYLOAD_NAME, 1, 'payload'),
        (OLD_MANIFEST, v['manifest'], 1, 'source freeze'),
    ]


def supervisor_edits(v):
    return [(TOKEN_ARCHIVE, v['archive'], 1, 'archive'), (TOKEN_MANIFEST, v['manifest'], 1, 'manifest'),
            (TOKEN_JOB, JOB, 1, 'job'), (TOKEN_KIND, v['kind'], 1, 'kind')]


# Made-up values with no digits that could look like an old number. The stale-text checks run on these, so a
# real hash that happens to hold '3000' can never stop a build by accident.
MADE_UP = {'existing': 87.36, 'previous_job': 'made-up-previous-job', 'previous_folder': 'made_up_folder',
           'previous_cleanup_file': 'aws-made-up-independent-cleanup.json', 'previous_cleanup_sha': 'a' * 64,
           'previous_instance': 'i-abcdefabcdefabcde', 'previous_volumes': ['vol-abcdefabcdefabcde'],
           'archive': 'b' * 64, 'manifest': 'c' * 64, 'kind': 'SEALED_PACKAGE'}


def derive_texts(v, stale_checks):
    """All derived program texts, from the base bytes and the supervisor beside this script. Writes nothing."""
    out = {}
    out['aws_control.py'] = apply(text(BASE / 'aws_control.py'), control_edits(v), 'aws_control.py')
    assert out['aws_control.py'].count("\nJOB='" + JOB + "'") == 1 and out['aws_control.py'].count(STEM + '-') == 18
    out['worker.sh'] = apply(text(BASE / 'worker.sh'), worker_edits(v), 'worker.sh')
    assert out['worker.sh'].count(JOB) == 10
    out['runtime_preflight.py'] = apply(text(BASE / 'runtime_preflight.py'), preflight_edits(v), 'runtime_preflight.py')
    assert "('torch', 'numpy', 'jsonschema')" in out['runtime_preflight.py']
    out['shared_entry.py'] = apply(text(BASE / 'shared_entry.py'), entry_edits(v), 'shared_entry.py')
    out['independent_cleanup.py'] = apply(text(BASE / 'independent_cleanup.py'), cleanup_edits(v), 'independent_cleanup.py')
    if stale_checks:
        for stale in CONTROL_STALE:
            assert stale not in out['aws_control.py'], ('STALE_IN_CONTROL', stale)
        for stale in WORKER_STALE:
            assert stale not in out['worker.sh'], ('STALE_IN_WORKER', stale)
        assert OLD_JOB not in out['runtime_preflight.py'] and 'small_host' not in out['runtime_preflight.py']
        for stale in (OLD_JOB, 'cas-probe-c02', OLD_MANIFEST, 'c02'):
            assert stale not in out['independent_cleanup.py'], ('STALE_IN_CLEANUP', stale)
    supervisor = text(HERE / SUPERVISOR)
    assert supervisor.count("\nJOB = '" + TOKEN_JOB + "'\n") == 1 and OLD_JOB not in supervisor
    assert supervisor.count("\nPRECHECK_KIND = '" + TOKEN_KIND + "'\n") == 1
    assert 'MAXIMUM_WORKLOAD_SECONDS = %d\n' % WORKLOAD_SECONDS in supervisor
    assert "'overlay_install': %d, 'import_smoke': %d, 'selftest': %d}" % (
        STAGE_MAXIMUM_SECONDS['overlay_install'], STAGE_MAXIMUM_SECONDS['import_smoke'],
        STAGE_MAXIMUM_SECONDS['selftest']) in supervisor
    out[SUPERVISOR] = apply(supervisor, supervisor_edits(v), SUPERVISOR)
    assert '@@' not in out[SUPERVISOR] and out[SUPERVISOR].count("\nJOB = '" + JOB + "'\n") == 1
    return out


def runner_flags(supervisor_text):
    """Every word of SELFTEST_ARGV that starts with '--', read from the supervisor text. Text only."""
    start = supervisor_text.index('SELFTEST_ARGV = (')
    block = supervisor_text[start:supervisor_text.index(')', start)]
    flags = [part.strip(" '\n") for part in block.split(',') if part.strip(" '\n").startswith('--')]
    assert flags and 'selftest' in block and 'precheck' in block, 'SELFTEST_ARGV_NOT_READABLE'
    return flags


def check_text_only():
    """Apply every edit table to the base files with made-up values. Proves the counts. Writes nothing."""
    pins = json.loads((BASE / 'CONTROLLER_SOURCE_PINS.json').read_bytes())
    assert sha(BASE / 'CONTROLLER_SOURCE_PINS.json') == BASE_PINS_SHA, 'BASE_PINS_CHANGED'
    for name in ('aws_control.py', 'worker.sh', 'bounded_s3.py', 'runtime_preflight.py', 'service_prices.py',
                 'independent_cleanup.py', 'COST_POLICY.json', 'STORAGE_ADMISSION.json', 'shared_entry.py'):
        assert sha(BASE / name) == pins['files'][name]['sha256'], ('BASE_FILE_NOT_AS_REVIEWED', name)
    # Every job name this script can give: the 4 pre-check jobs (both kinds) and the 2 development tests.
    checked = {}
    for kind in KINDS:
        for attempt in range(1, SERIES_MAX['d' if kind == 'DEVELOPMENT_TEST' else 'p'] + 1):
            name_the_job(kind, attempt)
            texts = derive_texts(dict(MADE_UP, kind=kind), True)
            policy = derive_policy(MADE_UP)
            checked[JOB] = sum(len(value.encode('utf-8')) for value in texts.values())
    flags = runner_flags(text(HERE / SUPERVISOR))
    print(json.dumps({'status': 'TEXT_CHECK_PASS', 'wrote': 'nothing', 'job_names_checked': sorted(checked),
                      'derived_bytes_last_job': {name: len(value.encode('utf-8')) for name, value in sorted(texts.items())},
                      'policy_upper_usd': policy['all_services_upper_usd'], 'runner_flags_to_find': flags}, indent=1))


def derive_policy(v):
    policy_text = text(BASE / 'COST_POLICY.json')
    policy = json.loads(policy_text)
    assert json.dumps(policy, indent=2) + '\n' == policy_text, 'BASE_COST_POLICY_NOT_ROUND_TRIP_STABLE'
    assert policy['status'] == 'TESTS_ONLY_OWNER_APPROVED_ONE_ATTEMPT' and policy['maximum_all_services_usd'] == 1.0
    assert policy['maximum_host_minutes'] == 60 and policy['all_services_upper_usd'] == 0.543285714286
    assert policy['tests_only'] is True and policy['scientific_stages'] == 0 and policy['optimizer_updates'] == 0
    combined = round(v['existing'] + CAP_USD, 2)
    assert abs(sum(value for key, value in UPPER_COMPONENTS.items() if key != 'sum_upper')
               - UPPER_COMPONENTS['sum_upper']) < 1e-12 and UPPER_COMPONENTS['sum_upper'] <= CAP_USD
    policy.update(
        job=JOB, maximum_all_services_usd=CAP_USD, proposed_allocation_usd=CAP_USD, new_allocation_usd=CAP_USD,
        combined_existing_allocation_usd=v['existing'], combined_allocation_usd=combined,
        prospective_combined_allocation_usd=combined,
        maximum_host_minutes=HOST_MINUTES, maximum_workload_seconds=WORKLOAD_SECONDS,
        minimum_worker_admission_seconds=MINIMUM_ADMISSION_SECONDS, work_cutoff_minutes=WORK_MINUTES,
        force_cutoff_minutes=FORCE_MINUTES, stage_maximum_seconds=dict(STAGE_MAXIMUM_SECONDS),
        all_services_upper_usd=UPPER_COMPONENTS['sum_upper'],
        current_components_at_admitted_maximum=dict(UPPER_COMPONENTS),
        deadline_contract='One launch-derived %d second window includes bootstrap, preflight and four stages, each run '
                          'once: /opt/pytorch package inventory, isolated overlay install, import smoke, and the '
                          'runner self-test in precheck mode (tokenizer only). No model B weights, no model call, no '
                          'retry or second host. Finalization 300 seconds, force %d min, host %d min.'
                          % (WORKLOAD_SECONDS, FORCE_MINUTES, HOST_MINUTES),
        throughput_evidence='Stages 1 to 3 took about 200 seconds in probe c02 on 2026-10-04 (measured). '
                            'The self-test time is not measured.',
        cost_proof_limits='Conditional finite upper estimate, not an exact bill. Ledger basis: owner-ordered '
                          'reconciliation chain (AWS_COMBINED_ALLOCATION_CURRENT.json).')
    return policy


def main():
    if sys.argv[1:] == ['--check-text-only']:
        return check_text_only()
    assert len(sys.argv) == 2, 'USAGE: derive_precheck_job.py PRECHECK_CONFIG.json | --check-text-only'
    config_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    kind, attempt = cfg['kind'], cfg['attempt']
    series = name_the_job(kind, attempt)
    assert not NEW.exists(), 'TARGET_FOLDER_EXISTS'
    assert not (OP / LEASE).exists() and not (OP / CLAIM).exists(), 'LEASE_OR_CLAIM_ALREADY_EXISTS'
    # Every job that was launched counts toward the 4 (plan section 19.1), or toward the 2 development tests
    # (amendment A10). A launch leaves its claim file behind.
    # So a number is used only when every lower number of its series was launched, and no number is used twice.
    for earlier in range(1, attempt):
        assert (OP / claim_name(series, earlier)).exists(), ('A_LOWER_ATTEMPT_NUMBER_WAS_NEVER_LAUNCHED_USE_IT_FIRST', earlier)

    # ---------------- the base: the reviewed, run bytes of probe c02 ----------------
    pins = json.loads((BASE / 'CONTROLLER_SOURCE_PINS.json').read_bytes())
    assert sha(BASE / 'CONTROLLER_SOURCE_PINS.json') == BASE_PINS_SHA, 'BASE_PINS_CHANGED'
    for name in ('aws_control.py', 'worker.sh', 'bounded_s3.py', 'runtime_preflight.py', 'service_prices.py',
                 'independent_cleanup.py', 'COST_POLICY.json', 'STORAGE_ADMISSION.json', 'shared_entry.py'):
        assert sha(BASE / name) == pins['files'][name]['sha256'], ('BASE_FILE_NOT_AS_REVIEWED', name)

    # ---------------- the previous job on the shared four-key slot, and the ledger ----------------
    prev = cfg['previous']
    assert len(prev['volumes']) == 1 and "'" not in prev['folder'] + prev['job'] + prev['cleanup_file']
    previous_path = OP / prev['folder'] / prev['cleanup_file']
    previous_sha = sha(previous_path)
    assert previous_sha == prev['cleanup_sha256'], ('PREVIOUS_CLEANUP_HASH_DIFFERS_STOP', previous_sha)
    previous = json.loads(previous_path.read_bytes())
    assert previous['job'] == prev['job'] and previous['client_token'] == prev['job'] + '-2b'
    assert previous['status'] == 'VERIFIED' and previous['instance'] == prev['instance']
    assert previous['all_job_volumes'] == prev['volumes']
    assert all(previous[key] is True for key in ('cleanup_verified', 'compute_cleanup_verified',
                                                 'local_preservation_verified', 'prefix_cleanup_verified'))
    pointer = json.loads(POINTER.read_bytes())
    existing = cfg['existing_allocation_usd']
    assert pointer['combined_allocation_usd'] == existing, ('LEDGER_POINTER_DIFFERS_FROM_CONFIG', pointer['combined_allocation_usd'])
    assert pointer.get('last_jobs') == [prev['job']], ('PREVIOUS_JOB_IS_NOT_THE_LAST_JOB_ON_THE_LEDGER', pointer.get('last_jobs'))
    assert round(existing + CAP_USD, 2) <= pointer['ceiling_usd'], 'CEILING'

    # ---------------- the sealed plan constants: which model files the pre-check may hold ----------------
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    limits = plan['aws']['precheck_job']
    assert (limits['jobs_max'] == JOBS_MAX and round(float(limits['cap_usd_proposed']) * 100) == round(CAP_USD * 100)
            and limits['hard_time_limit_minutes_proposed'] == HOST_MINUTES), 'THIS_KIT_AND_THE_PLAN_DISAGREE_ON_THE_PRECHECK_LIMITS'
    # Amendment A10: the development test has its own block in the plan. Same cap and time, at most 2 jobs,
    # and it never counts toward the 4 pre-check jobs.
    dev = plan['aws']['development_test_job']
    assert (dev['kind'] == 'DEVELOPMENT_TEST' and dev['jobs_max'] == DEV_JOBS_MAX
            and round(float(dev['cap_usd']) * 100) == round(CAP_USD * 100)
            and dev['hard_time_limit_minutes'] == HOST_MINUTES
            and dev['counts_toward_the_4_precheck_jobs'] is False), 'THIS_KIT_AND_THE_PLAN_DISAGREE_ON_THE_DEVELOPMENT_TEST_LIMITS'
    if kind == 'DEVELOPMENT_TEST':
        # The draft of ALLOCATION.json below names this record with its sha256. So the file must be the pinned one.
        assert sha(OWNER_APPROVAL) == OWNER_APPROVAL_SHA, 'OWNER_APPROVAL_RECORD_IS_NOT_THE_PINNED_ONE'
    model = plan['model_b']
    snapshot = model['snapshot_path_in_payload']
    small = list(model['precheck_files'])
    assert len(small) == 6 and 'model.safetensors' not in small and all(name in model['files'] for name in small)
    assert sum(model['files'][name]['bytes'] for name in small) == model['precheck_files_total_bytes']
    supervisor_text = text(HERE / SUPERVISOR)
    assert ("MODEL_SNAPSHOT = '" + snapshot + "'\n") in supervisor_text, 'SUPERVISOR_MODEL_PATH_DIFFERS_FROM_PLAN'

    # ---------------- the source archive: the same source.zip the GPU job gets, byte for byte ----------------
    source_zip = Path(cfg['source_zip'])
    archive = sha(source_zip)
    assert archive == cfg['source_zip_sha256'], ('SOURCE_ZIP_HASH_DIFFERS_FROM_CONFIG', archive)
    with zipfile.ZipFile(source_zip) as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        # The GPU guest's caps for source.zip (design: 8 MiB unpacked and 400 files).
        assert len(set(names)) == len(names) and len(names) <= 400, 'SOURCE_ZIP_MEMBERS'
        assert sum(info.file_size for info in infos) <= 8 * 1024 * 1024, 'SOURCE_ZIP_ABOVE_THE_GUEST_CAP_OF_8_MIB_UNPACKED'
        assert source.testzip() is None
        for name in PROJECT_FILES:
            assert name in names, ('SOURCE_ZIP_LACKS', name)
        manifest_raw = source.read('BUNDLE_MANIFEST.json')
        manifest = sha_bytes(manifest_raw)
        assert sha_bytes(source.read('contracts/requirements.small-linux.txt')) == REQUIREMENTS_SHA, 'REQUIREMENTS_FILE_CHANGED'
        assert sha_bytes(source.read('PLAN_CONSTANTS.json')) == sha(PLAN), 'PACKAGE_PLAN_CONSTANTS_DIFFER_FROM_THE_LAPTOP_COPY'
        runner_text = source.read('job/runner_b1.py').decode('utf-8')
        for flag in runner_flags(supervisor_text):
            assert flag in runner_text, ('RUNNER_DOES_NOT_KNOW_THIS_FLAG_FIX_SELFTEST_ARGV', flag)
        assert 'selftest' in runner_text and 'precheck' in runner_text
        source_members = {info.filename: source.read(info) for info in infos
                          if not info.is_dir()}
        assert len(source_members) == len(infos), 'SOURCE_ZIP_HOLDS_A_DIRECTORY_ENTRY'
        for info in infos:
            assert (info.external_attr >> 16) & 0o170000 != 0o120000, ('SYMLINK_IN_SOURCE_ZIP', info.filename)
        assert sha_bytes(source_members['tools/verdict.py']) == plan['sources']['verdict_program']['sha256'], 'PACKAGE_VERDICT_PROGRAM_IS_NOT_THE_PINNED_ONE'

    # ---------------- which kind of job this is: the seal file decides, not the operator (plan section 19.1) ----------------
    seal_copy = source_members['SEAL_OPTIONB.jsonl']
    assert seal_copy.endswith(b'\n') and b'\r' not in seal_copy, 'PACKAGE_SEAL_COPY_LINE_ENDS'
    copy_steps = [json.loads(line.decode('utf-8'))['step'] for line in seal_copy[:-1].split(b'\n')]
    assert copy_steps[-1] in PROGRAM_LINES, ('PACKAGE_SEAL_COPY_DOES_NOT_END_WITH_A_PROGRAM_LINE', copy_steps[-1])
    if not SEAL.exists():
        # Before seal step 1 there is no seal file. Only a test on made-up data can run then.
        found_kind = 'DEVELOPMENT_TEST'
    else:
        seal_raw = SEAL.read_bytes()
        assert seal_raw.endswith(b'\n') and b'\r' not in seal_raw, 'SEAL_FILE_LINE_ENDS'
        real_steps = [json.loads(line.decode('utf-8'))['step'] for line in seal_raw[:-1].split(b'\n')]
        # Amendment A5: a tool repair is allowed only while no final question exists. So a tool-repair line
        # stands after line 1 and before the line 3C. One that stands elsewhere stops the build.
        final = real_steps.index(FINAL_LINE) if FINAL_LINE in real_steps else len(real_steps)
        assert all(0 < index < final for index, step in enumerate(real_steps) if step == TOOL_REPAIR), \
            'SEAL_FILE_HOLDS_A_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW'
        if seal_raw.startswith(seal_copy):
            # The package holds the real seal up to its last program line: step 6, or the last repair line 6R.
            assert not [step for step in real_steps[len(copy_steps):] if step in PROGRAM_LINES], 'PACKAGE_IS_OLDER_THAN_THE_LAST_PROGRAM_REPAIR'
            assert '7_PRECHECK' not in real_steps, 'SEAL_STEP_7_IS_WRITTEN_NO_FURTHER_PRECHECK'
            found_kind = 'SEALED_PACKAGE'
        else:
            # Rehearsal: the real seal ends with step 5. (Amendment A5: no repair line can follow step 5 there.)
            # The package holds it plus one line: the step 6 line that 'tools/ob_seal.py step 6 --dry-run' printed.
            assert (seal_copy.startswith(seal_raw) and len(copy_steps) == len(real_steps) + 1
                    and copy_steps[-1] == '6_PROGRAMS' and real_steps[-1] == '5_PROMPT_PARTS_AND_REMOVAL_LOG'), \
                'PACKAGE_SEAL_COPY_FITS_NEITHER_THE_SEAL_FILE_NOR_A_REHEARSAL'
            found_kind = 'REHEARSAL'
    assert kind == found_kind, ('CONFIG_KIND_DIFFERS_FROM_WHAT_THE_SEAL_FILE_SHOWS', kind, found_kind)

    v = {'existing': existing, 'previous_job': prev['job'], 'previous_folder': prev['folder'],
         'previous_cleanup_file': prev['cleanup_file'], 'previous_cleanup_sha': previous_sha,
         'previous_instance': prev['instance'], 'previous_volumes': list(prev['volumes']),
         'archive': archive, 'manifest': manifest, 'kind': kind}
    derive_texts(MADE_UP, True)
    texts = derive_texts(v, False)
    policy = derive_policy(v)

    # ---------------- the six small model B files, read from an existing sealed input archive ----------------
    tokenizer_files = {}
    with zipfile.ZipFile(cfg['tokenizer_source_zip']) as models:
        for name in small:
            raw = models.read(snapshot + '/' + name)
            pin = model['files'][name]
            assert len(raw) == pin['bytes'] and sha_bytes(raw) == pin['sha256'], ('MODEL_FILE_PIN', name)
            tokenizer_files[snapshot + '/' + name] = raw

    # ---------------- write the folder ----------------
    NEW.mkdir()
    for name in ('bounded_s3.py', 'service_prices.py'):
        shutil.copyfile(BASE / name, NEW / name)
        assert sha(NEW / name) == pins['files'][name]['sha256']
    for name, value in texts.items():
        write_lf(NEW / name, value)
    write_lf(NEW / 'COST_POLICY.json', json.dumps(policy, indent=2) + '\n')
    storage_text = text(BASE / 'STORAGE_ADMISSION.json')
    storage = json.loads(storage_text)
    assert json.dumps(storage, indent=2) + '\n' == storage_text, 'BASE_STORAGE_ADMISSION_NOT_ROUND_TRIP_STABLE'
    assert storage['job'] == OLD_JOB and storage['previous_job'] == OLD_PREVIOUS_JOB
    storage.update(job=JOB, previous_job=prev['job'])
    write_lf(NEW / 'STORAGE_ADMISSION.json', json.dumps(storage, indent=2) + '\n')

    # ---------------- payload ----------------
    members = {}
    payload_path = NEW / PAYLOAD_NAME
    fixed = (2026, 10, 5, 0, 0, 0)
    with zipfile.ZipFile(payload_path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        def add(name, raw):
            assert name not in members and not name.startswith('/') and '..' not in name.split('/') and ':' not in name and chr(92) not in name
            parts = PurePosixPath(name).parts
            assert '__pycache__' not in parts and PurePosixPath(name).suffix not in ('.pyc', '.pyo', '.so', '.pth'), name
            info = zipfile.ZipInfo(name, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, raw)
            members[name] = {'sha256': sha_bytes(raw), 'bytes': len(raw)}
        for name in sorted(source_members):
            add('sources/cas/' + name, source_members[name])
        for name in sorted(tokenizer_files):
            add(name, tokenizer_files[name])
        for name in (SUPERVISOR, 'runtime_preflight.py', 'shared_entry.py'):
            add('execution/' + name, (NEW / name).read_bytes())
        assert not [name for name in members if name.endswith('model.safetensors')], 'MODEL_WEIGHTS_MUST_NOT_BE_IN_THE_PRECHECK_PAYLOAD'
        inventory = {'schema': 'helm.native-semantic.payload-inventory/1', 'job': JOB,
                     'sources': {'cas': {'archive_sha256': archive, 'source_freeze_sha256': manifest,
                                         'members': len(source_members)}},
                     'model_files': {'snapshot': snapshot, 'names': small, 'weights_included': False},
                     'members': members}
        raw_inventory = (json.dumps(inventory, indent=1, sort_keys=True) + '\n').encode('utf-8')
        info = zipfile.ZipInfo('payload_inventory.json', date_time=fixed)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        out.writestr(info, raw_inventory)
    with open(NEW / 'payload_inventory.json', 'xb') as stream:
        stream.write(raw_inventory)
    size = payload_path.stat().st_size
    assert size <= 64 * 1024 * 1024, size
    with zipfile.ZipFile(payload_path) as check:
        assert check.testzip() is None
        expanded = sum(item.file_size for item in check.infolist())
        assert expanded <= 128 * 1024 * 1024, expanded
        names = check.namelist()
        assert len(names) == len(set(names)) == len(members) + 1
        # The controller's exact-closure rule, and byte identity of every source member with the sealed archive.
        assert {name: sha_bytes(check.read(name)) for name in names} == {
            **{name: pin['sha256'] for name, pin in members.items()}, 'payload_inventory.json': sha(NEW / 'payload_inventory.json')}
        for name, raw in source_members.items():
            assert check.read('sources/cas/' + name) == raw, name
        # runtime_preflight rule: code files on the host are exactly the .py payload members.
        assert not [name for name in names if PurePosixPath(name).suffix in ('.so', '.pth', '.pyc', '.pyo')]

    # ---------------- pins ----------------
    pinned = ('aws_control.py', 'worker.sh', 'bounded_s3.py', 'runtime_preflight.py', 'service_prices.py',
              'independent_cleanup.py', 'COST_POLICY.json', 'STORAGE_ADMISSION.json', SUPERVISOR,
              'shared_entry.py', PAYLOAD_NAME, 'payload_inventory.json')
    new_pins = {'job': JOB, 'source_freeze_sha256': manifest, 'arm_b_source_freeze_sha256': manifest,
                'archive_sha256': archive, 'arm_b_archive_sha256': archive,
                'identity_mapping': 'One source only: the Option B source.zip. source_freeze_sha256 = sha256 of its '
                                    'BUNDLE_MANIFEST.json; archive_sha256 = sha256 of source.zip. The arm_b fields are a '
                                    'legacy second-source slot of this controller family; both carry the same two values.',
                'files': {name: {'sha256': sha(NEW / name), 'bytes': (NEW / name).stat().st_size} for name in pinned}}
    write_lf(NEW / 'CONTROLLER_SOURCE_PINS.json', json.dumps(new_pins, indent=2) + '\n')
    payload_sha, pins_sha = sha(payload_path), sha(NEW / 'CONTROLLER_SOURCE_PINS.json')
    counts = series == 'p'
    write_lf(NEW / 'PACKAGING_RECEIPT.json', json.dumps({
        'job': JOB, 'kind': kind, 'attempt': attempt, 'attempts_max_for_this_kind': SERIES_MAX[series],
        'counts_toward_the_4_precheck_jobs': counts,
        'payload_sha256': payload_sha, 'payload_bytes': size, 'members': len(members) + 1,
        'expanded_bytes': expanded, 'source_archive_sha256': archive, 'bundle_manifest_sha256': manifest,
        'model_weights_in_payload': False, 'source_execution': 'NONE', 'upload': 'NONE',
        'built_from': 'controller_cas_probe_c02 (reviewed, run on 2026-10-04 as probe c02)',
        'builder': 'derive_precheck_job.py; bytes and text only'}, indent=2) + '\n')

    # ---------------- values for the records the operator writes after the review ----------------
    combined = round(existing + CAP_USD, 2)
    # The authority text of ALLOCATION.json. For a development test amendment A10 fixes it. For the other kinds the
    # operator writes it after the review.
    authority_text = '<<the owner approval record, its sha256, and the limits in words>>'
    if kind == 'DEVELOPMENT_TEST':
        authority_text = ('Amendment A10: operator decision of 2026-10-05 under the owner approval record %s sha256 %s '
                          '(spend only inside unreserved funds, with a stated cap and automatic shutdown on every job). '
                          'Development test d%d of at most %d: one CPU host, USD %.2f cap, %d minutes, single attempt, no retry. '
                          'Made-up data only. The runner self-test only. Never evidence about roles.'
                          % (OWNER_APPROVAL.name, OWNER_APPROVAL_SHA, attempt, DEV_JOBS_MAX, CAP_USD, HOST_MINUTES))
    values = {
        'job': JOB, 'folder': str(NEW), 'status': 'BUILT_NOT_REVIEWED_NOT_LAUNCHED. This file grants no authority.',
        'kind': kind, 'attempt': attempt, 'attempts_max_for_this_kind': SERIES_MAX[series],
        'counts_toward_the_4_precheck_jobs': counts,
        'result_may_be_written_to_seal_step_7': kind == 'SEALED_PACKAGE',
        'kind_note': {'SEALED_PACKAGE': 'The package of seal step 6, or of the last repair line 6R. A pass gives the values of seal step 7.',
                      'REHEARSAL': 'Plan section 19.1: after seal step 5 and before seal step 6, on a scratch seal. One of the 4 jobs. '
                                   'Its result is never written to the real seal file.',
                      'DEVELOPMENT_TEST': 'Plan section 19.1, amendment A10: made-up data before seal step 1, outside the seal chain. '
                                          'Ordered. At most 2 such jobs (d1, d2). Not one of the 4 pre-check jobs. Authorised by the '
                                          "operator's decision under the owner's approval record " + OWNER_APPROVAL.name + '. Its output '
                                          'is never evidence about roles. Its result is never written to a seal file.'}[kind],
        'payload_sha256': payload_sha, 'payload_bytes': size, 'pins_sha256': pins_sha,
        'source_zip': str(source_zip), 'archive_sha256': archive, 'source_freeze_sha256': manifest,
        'previous_job': prev['job'], 'previous_cleanup_sha256': previous_sha,
        'limits': {'cap_usd': CAP_USD, 'host_minutes': HOST_MINUTES, 'force_minutes': FORCE_MINUTES,
                   'work_minutes': WORK_MINUTES, 'all_services_upper_usd': policy['all_services_upper_usd']},
        'limits_in_the_plan': plan['aws']['development_test_job' if series == 'd' else 'precheck_job'],
        'write_order': ['INDEPENDENT_STATIC_REVIEW.json', 'CONTROLLER_REVIEW.json', 'ALLOCATION.json', LEASE],
        'must_not_exist_before_launch': [str(OP / CLAIM), STEM + '-control.json', STEM + '-launch-intent.json'],
        'drafts_not_authority': {
            'INDEPENDENT_STATIC_REVIEW.json': {'accepted': '<<true only after the review accepts>>', 'job': JOB,
                                               'source_pins_sha256': pins_sha, 'payload_sha256': payload_sha},
            'CONTROLLER_REVIEW.json': {
                'job': JOB, 'payload_sha256': payload_sha, 'approved_source_review': True,
                'tests_only_owner_approved': True, 'source_pins_sha256': pins_sha,
                'arm_b_source_freeze_sha256': manifest, 'arm_b_archive_sha256': archive,
                'independent_review_receipt_sha256': '<<sha256 of INDEPENDENT_STATIC_REVIEW.json as finally written>>',
                'archive_sha256': archive, 'source_freeze_sha256': manifest},
            'ALLOCATION.json': {
                'job': JOB, 'launch_authorized': True, 'approved_for_single_launch': True, 'tests_only_scope': True,
                'new_allocation_usd': CAP_USD, 'maximum_all_services_usd': CAP_USD,
                'combined_existing_allocation_usd': existing, 'combined_allocation_usd': combined,
                'authority_record': authority_text,
                'owner_transfer_record': '<<one non-empty text; the lease must carry the same text>>',
                'storage_reuse_adopted': True, 'read_only_readiness_authorized': True,
                'source_archives': {'cas': {'path': str(source_zip), 'archive_sha256': archive,
                                            'source_freeze_sha256': manifest}}},
            LEASE: {
                'status': 'EXCLUSIVELY_HELD', 'job': JOB, 'bucket': storage['bucket'], 'prefix': storage['prefix'],
                'owner_transfer_record': '<<identical to ALLOCATION.json>>', 'no_other_launcher': True,
                'prior_cleanup_sha256': previous_sha, 'payload_sha256': payload_sha,
                'arm_b_source_freeze_sha256': manifest, 'source_freeze_sha256': manifest}}}
    write_lf(NEW / 'PRECHECK_ADMISSION_VALUES.json', json.dumps(values, indent=1) + '\n')
    for name in ('ALLOCATION.json', 'CONTROLLER_REVIEW.json', 'INDEPENDENT_STATIC_REVIEW.json'):
        assert not (NEW / name).exists(), name
    shutil.copyfile(Path(__file__), NEW / 'derive_precheck_job.py')
    shutil.copyfile(config_path, NEW / 'PRECHECK_CONFIG.json')
    print(json.dumps({'folder': str(NEW), 'payload_sha256': payload_sha, 'payload_bytes': size,
                      'members': len(members) + 1, 'pins_sha256': pins_sha, 'archive_sha256': archive,
                      'source_freeze_sha256': manifest, 'previous_cleanup_sha256': previous_sha}, indent=1))


if __name__ == '__main__':
    main()
