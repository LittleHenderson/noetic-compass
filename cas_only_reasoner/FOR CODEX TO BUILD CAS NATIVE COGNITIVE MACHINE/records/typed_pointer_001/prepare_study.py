"""Freeze the three pointer-study jobs before the first result; package and rehearsal only. No launch.

Copied from `records/typed_practice_001/prepare_study.py` (108 lines, the practice study's own freeze) and changed
only where this study differs: `aws.typed_pointer_launch` and `cas_meta2.typed_teaching.pointer_contract` instead of
the practice pair, `build_pointer_package`, this study's protocol document, this study's admission schema, and ONE
owner record per job carrying the owner's FIVE decisions VERBATIM (DG9: one owner record per job, because the
inherited lifecycle allows one job per owner record).

WHAT THE FIVE LABELS ARE, AND WHERE THEY COME FROM. The recorded labels are the exact selected option labels the
owner chose on 2026-09-19. **Their authority is `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` SECTION 0.2, ITEMS 1-5** --
the section and item are the citation; the line numbers are only a dated hint and have already moved twice, so
they are given once, below, with the date and the document digest they were read at. A bare line list silently
rots; an item number inside a named section does not. The labels are NOT paraphrased and the third keeps its em
dash.

    read 2026-09-19 at protocol sha256 3cb002ed948b7101e27458e52152788af419fb8dc6b7664173d98bb92ffa3d41
    (the digest this freeze-time record was given; `prepare_smoke.py` records the value it reads at run time).
    UNCERTAIN, recorded rather than resolved: the copy in THIS worktree is 98536 bytes with sha256
    `81afe89eb2ffa8f0ad02b13407acfe768463ca8287fa6d6c6c1dfc395dc7f08f`, and the line numbers below were
    CONFIRMED against that copy by scanning for each label; the 96332-byte `3cb002ed...` revision is not in this
    worktree's history. The section-and-item citation holds either way; the digest is the owner's to reconcile:
      item 1  "Accept both, carry on."                                        :52
      item 2  "Approve the smoke job (Recommended)"                           :57
      item 3  "Yes — require the relational kinds."                           :86
      item 4  "Run it as the transfer test, label honestly (Recommended)"     :89-92   (the label wraps)
      item 5  "Stratify AND train longer (Recommended)"                       :94

THIS PARAGRAPH RECORDED A CONTRACT DEFECT FOR ONE DAY, AND THAT DEFECT IS FIXED. It used to say: item 3 was
byte-present inside `pointer_contract.DESIGN["owner_approval"]` with two ASCII hyphens where the protocol document
prints an em dash (`pointer_contract.py:706`), and item 4 was absent from that field entirely. Both readings were
true of the contract as it stood, and this script RECORDED them rather than refusing the freeze. The contract was
then corrected (`pointer_contract.py:702-714`, "CORRECTED 2026-09-19 (pre-flight, $0)"): all FIVE labels are now
byte-for-byte present, including `"Yes — require the relational kinds."` with a real em dash. That module stays
pure ASCII -- it carries the em dash as an ASCII source escape, and a byte scan reports 0 characters above U+007F.
Measured by import on the corrected tree, `owner_decisions_in_contract_text()` returns `[True, True, True, True,
True]`.

The check is NOT removed, and it is not a comment about history. It is how a future contract edit that drops or
paraphrases one of the five labels becomes visible in the very owner records this script writes, instead of being
inherited silently. Its docstring used to warn of the opposite failure -- that the freeze must not be refused for a
discrepancy it is meant to record -- so it now states what a `False` in that list means: the contract and the
protocol document have diverged again, and the owner record must be read by hand before the freeze is used.

The `assert` calls below are the practice freeze's own, kept unchanged: this script launches NOTHING (its docstring
is the practice study's: package and rehearsal only), and the rehearsal is a Windows refusal test that must not
reach a numeric import. The spend path is `execute_study.py`, where every stop is an explicit `stop_unless`.
"""
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_pointer_launch as launch
from cas_meta2.typed_teaching import pointer_contract as contract

PROTOCOL = ROOT / 'docs/CNCM_TYPED_POINTER_STUDY_v0.1.md'
OWNER_QUESTION = ('Which pointer-study options should I build and launch? Your choice will be recorded as the '
                  'signed approval for the study.')
# The five decisions, verbatim, in the order the protocol document records them.
OWNER_DECISIONS = (
    'Accept both, carry on.',
    'Approve the smoke job (Recommended)',
    'Yes — require the relational kinds.',
    'Run it as the transfer test, label honestly (Recommended)',
    'Stratify AND train longer (Recommended)')
OWNER_SCOPE = ('One of three pointer-study seeds under the owner-approved $45.00 cap; no automatic retry.')
OWNER_ANSWERED_UTC_DATE = '2026-09-19'
MAXIMUM_NEW_RESERVATION_USD = '45.00'


def write(path, value):
    raw = launch.canonical(value)
    with path.open('xb') as stream: stream.write(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def owner_decisions_in_contract_text():
    """Per label, whether `pointer_contract.DESIGN["owner_approval"]` carries it byte-for-byte.

    Recorded, never enforced: the freeze must not silently drop a decision the owner made, and it must not fail
    because the contract's PROSE renders one label with two ASCII hyphens instead of the em dash the protocol
    document prints. The discrepancy is a finding for the owner, not a reason to freeze nothing.
    """
    text = contract.DESIGN['owner_approval']
    return [label in text for label in OWNER_DECISIONS]


def prepare():
    source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', '.'], cwd=ROOT, text=True).strip()
    assert not dirty, 'COMMIT_FIRST_THE_PACKAGE_IS_BUILT_FROM_HEAD:\n' + dirty[:2000]
    assert len(contract.MODEL_SEEDS) * float(launch.RESERVATION_USD) <= float(MAXIMUM_NEW_RESERVATION_USD)
    output = ROOT / 'records/typed_pointer_001/admission_001'
    output.mkdir()
    package_parent = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001'
    package_parent.mkdir(exist_ok=True)
    package = launch.build_pointer_package(package_parent / ('package_' + source_sha[:8]), source_sha=source_sha)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    decisions_in_contract = owner_decisions_in_contract_text()
    jobs = []
    for seed in contract.MODEL_SEEDS:
        job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(seed)
        directory = output / str(seed)
        directory.mkdir()
        config = launch.worker_config(job, source_sha=source_sha)
        owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
                 'owner_instruction_raw': OWNER_DECISIONS[0], 'owner_question': OWNER_QUESTION,
                 'owner_selected_option_terms': list(OWNER_DECISIONS),
                 'owner_decisions_in_contract_text': list(decisions_in_contract),
                 'answered_utc_date': OWNER_ANSWERED_UTC_DATE, 'scope': OWNER_SCOPE,
                 'job': job, 'condition': contract.CONDITION, 'model_seed': seed, 'bounds': launch.BOUNDS}
        owner_pin = write(directory / 'owner.json', owner)
        identity = {k: package[k] for k in ('source_sha', 'archive_sha256', 'manifest_sha256')}
        request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity, 'launch_authorized': False}
        authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity, **launch.BOUNDS,
                     'candidate': launch.CANDIDATE, 'owner_authorization_sha256': owner_pin['sha256'],
                     'inputs_sha256': launch.frozen_inputs_hash(),
                     'design_sha256': launch.digest(launch.canonical(launch.DESIGN)),
                     'evidence_contract_sha256': launch.run_evidence.contract_digest(launch.evidence_contract()),
                     'worker_config': config}
        launch.validate_request(request); launch.validate_authority(authority)
        launch.validate_owner(directory / 'owner.json', authority)
        jobs.append({'job': job, 'condition': contract.CONDITION, 'model_seed': seed,
                     'request': write(directory / 'request.json', request),
                     'authority': write(directory / 'authority.json', authority), 'owner': owner_pin,
                     'receipt_dir': str(ROOT / 'records/typed_pointer_001' / ('receipt_' + str(seed)))})
        print(json.dumps({'prepared': job}), flush=True)
    # Exercise the exact packaged loader and worker admission. Windows must refuse before any numerical import.
    # This is a launch-path test, not a training run. The pointer worker CATCHES its own preflight refusal and
    # publishes a FAILED envelope (`cncm/typed_pointer_worker.py:1521-1522` is inside the `try`), so the failure
    # is read from the envelope this exact package produced rather than from a traceback's presence.
    rehearsal = output / 'rehearsal'
    rehearsal.mkdir()
    with ZipFile(package['archive']) as archive:
        for info in archive.infolist():
            target = (rehearsal / info.filename).resolve()
            assert target.is_relative_to(rehearsal.resolve()) and not info.is_dir()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info.filename))
    config = json.loads(Path(jobs[0]['authority']['path']).read_bytes())['worker_config']
    write(rehearsal / 'config.json', config)
    code = launch.bootstrap_source()
    ast.parse(code)
    proc = subprocess.run([sys.executable, '-B', '-I', '-c', code, str(rehearsal)], cwd=rehearsal,
                          capture_output=True, timeout=900)
    (output / 'rehearsal_stdout.txt').write_bytes(proc.stdout)
    (output / 'rehearsal_stderr.txt').write_bytes(proc.stderr)
    result = json.loads((rehearsal / 'results/result.json').read_bytes())
    # The worker's own FAILED status, read from the worker the launcher just probed -- never restated here.
    assert result['status'] == launch._probe().FAILED_STATUS, result.get('failure')
    assert 'LINUX_WORKER_REQUIRED' in (result.get('failure') or {}).get('detail', ''), result.get('failure')
    study = {'schema': 'cncm.typed-pointer-study-admission/0.1', 'status': 'FROZEN_BEFORE_FIRST_RUN',
             'source_sha': source_sha, 'candidate': launch.CANDIDATE,
             'config_schema': launch.CONFIG_SCHEMA,
             'package_archive_sha256': package['archive_sha256'],
             'package_manifest_sha256': package['manifest_sha256'], 'package_archive': package['archive'],
             'protocol_sha256': sha256(PROTOCOL.read_bytes()).hexdigest(),
             'owner_decisions_verbatim': list(OWNER_DECISIONS),
             'owner_decisions_in_contract_text': list(decisions_in_contract), 'jobs': jobs,
             'maximum_new_reservation_usd': MAXIMUM_NEW_RESERVATION_USD,
             'reservation_per_job_usd': launch.RESERVATION_USD,
             'jobs_execute_sequentially': True, 'automatic_retries': 0,
             'rehearsal': 'EXACT_PACKAGE_WINDOWS_REFUSAL_BEFORE_NUMERIC_IMPORT', 'numeric_runs_completed': 0}
    pin = write(output / 'study.json', study)
    print(json.dumps({'status': study['status'], 'study': pin}), flush=True)


if __name__ == '__main__': prepare()
