"""Fresh record identities using the unchanged 2x admission and launcher validators.

This orchestration file never launches, changes science, or writes a reservation.
Historical admission/receipt paths are read only. Source.zip must be built on AWS.
"""
from pathlib import Path
import importlib.util
import json
import subprocess
from decimal import Decimal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = 'a5fcf527b5f2c47a3a9b1f170977c55371845af0'
OLD_JOB = 'cas-meta2-tpntr-20260925151836-b981625f-m-20260918'
spec = importlib.util.spec_from_file_location('historical_admission_writer', ROOT / 'records/typed_pointer_001/admission_cm2x_001/prepare_cm2x_study.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
launch = base.launch
base.HERE = HERE
base.SEED_OUTPUT = HERE / 'seeds'
base.PARTIAL_OUTPUT = HERE / 'seeds.partial'
base.OWNER_PROBE = HERE / 'owner_probe.json'
base.RECEIPT_DIR = ROOT / 'records/typed_pointer_001/receipt_cm2x_rerun_20260926_20260918'
base.OWNER_DIRECTIVE = HERE / 'OWNER_REQUEST.md'
base.OWNER_DIRECTIVE_SHA256 = json.loads((HERE / 'owner_scope.json').read_bytes())['owner_request_sha256']
base.APPROVAL_CONTEXT = 'Owner live task instruction authorizes one new corrected 2x attempt from a5fcf527, after focused AWS tests and fresh finite admission.'
base.SCOPE = 'One fresh seed-20260918 20-pass g7.2xlarge job, constant LR0.003, fixed science and pass10/pass20 evaluations, mandatory midpoint state, zero automatic retries, verified cleanup. New attempt all-services cap USD20 includes prelaunch CPU validation. Historical failed attempt, reservations and original USD60 study unchanged.'
base.OWNER_SCHEMA_NOTE = 'Owner live message transcribed by Codex; not a signature. Distinct new attempt; no permission for another retry, CAS, 4x or 8x.'

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)

def check_source(source):
    if source != SOURCE:
        raise ValueError('EXACT_OWNER_SELECTED_SOURCE_REQUIRED')
    # Operational admission commits may follow source, but all source/input bytes
    # must still equal the exact tested and packaged commit.
    head = git('rev-parse', 'HEAD').decode().strip()
    rows = launch.frozen_inputs(source)
    for row in rows:
        raw = (ROOT / row['path']).read_bytes()
        if len(raw) != row['bytes'] or base.digest(raw) != row['sha256']:
            raise ValueError('WORKTREE_INPUT_CHANGED:' + row['path'])
    allowed = ('records/typed_pointer_001/admission_cm2x_rerun_20260926/',
               'records/typed_pointer_001/rerun_20260926_validation/',
               'research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_a5fcf527/')
    prefix = launch.shared.GIT_PREFIX
    changed = git('diff', '--name-only', SOURCE, '--', '.').decode().splitlines()
    unknown = git('ls-files', '--others', '--exclude-standard', '--', '.').decode().splitlines()
    for name in changed + unknown:
        relative = name.removeprefix(prefix)
        if not relative.startswith(allowed):
            raise ValueError('UNDECLARED_CHANGE:' + name)
    if base.RECEIPT_DIR.exists():
        raise ValueError('NEW_RECEIPT_ALREADY_EXISTS')
    return head

original_cost = base.cost_bound
def cost_bound():
    result = original_cost()
    forecast = json.loads((HERE / 'forecast.json').read_bytes())
    if forecast['guard_fit'] is not True:
        raise ValueError('RUNTIME_FORECAST_DOES_NOT_FIT')
    combined = Decimal(result['reservation_usd']) + Decimal('0.60') + Decimal('0.10') + Decimal(base.OTHER_SERVICES_ALLOWANCE_USD)
    if combined > Decimal(base.ALL_SERVICES_CAP_USD):
        raise ValueError('COMBINED_ATTEMPT_EXCEEDS_OWNER_CAP')
    result.update(expected_basis=forecast['basis'],
                  projected_worker_seconds=str(forecast['projected_worker_seconds']),
                  projected_instance_seconds=str(forecast['projected_instance_seconds']),
                  expected_cost_usd=str(forecast['expected_cost_usd']),
                  receipt_of_the_basis=str(HERE / 'forecast.json'),
                  prelaunch_validation_cap_usd='0.60',
                  package_only_build_cap_usd='0.10',
                  training_plus_other_subtotal_usd='19.30',
                  reservation_plus_allowance_usd=str(combined),
                  headroom_to_cap_usd=str(Decimal(base.ALL_SERVICES_CAP_USD) - combined),
                  total_new_attempt_reservations_and_allowances_usd=str(combined),
                  headroom_after_prerequisites_usd='0.00')
    return result

original_build = base.build
def build(source, package, job, *, owner_question):
    owner_raw, request, authority = original_build(source, package, job, owner_question=owner_question)
    owner = json.loads(owner_raw)
    owner.update(owner_instruction_raw='Proceed now with the corrected HELM critical-mass 2x attempt.',
                 answered_date='2026-09-26', answered_by='Owner live message; Codex transcription',
                 historical_failed_job=OLD_JOB, historical_failed_records_unchanged=True,
                 failed_reservation_not_reused=True, source_basis=SOURCE)
    owner_raw = base.canonical(owner)
    authority['owner_authorization_sha256'] = base.digest(owner_raw)
    base.validate_owner_record(owner_raw, authority)
    return owner_raw, request, authority

original_study = base.study_record
def study_record(*args, **kwargs):
    study = original_study(*args, **kwargs)
    study.update(historical_failed_job=OLD_JOB, historical_failed_records_unchanged=True,
                 source_basis=SOURCE, admission_kind='NEW_CORRECTED_ATTEMPT',
                 scientific_change='Only committed deadline routing; same seed/model/data/order/optimizer/LR/scoring and fixed pass10/pass20 evaluation.',
                 prelaunch_validation=json.loads((HERE / 'validation_acceptance.json').read_bytes()),
                 forecast_sha256=base.digest((HERE / 'forecast.json').read_bytes()),
                 source_ledger_gate_sha256=base.digest((HERE / 'source_ledger_gate.json').read_bytes()))
    return study

base.check_source = check_source
base.cost_bound = cost_bound
base.build = build
base.study_record = study_record

if __name__ == '__main__':
    accepted = json.loads((HERE / 'validation_acceptance.json').read_bytes())
    if accepted.get('source_commit') != SOURCE or accepted.get('tests_passed') != 41 or accepted.get('cleanup_complete') is not True or accepted.get('status') != 'PASS':
        raise ValueError('TERMINAL_AWS_VALIDATION_GATE_REQUIRED')
    raise SystemExit(base.main())
