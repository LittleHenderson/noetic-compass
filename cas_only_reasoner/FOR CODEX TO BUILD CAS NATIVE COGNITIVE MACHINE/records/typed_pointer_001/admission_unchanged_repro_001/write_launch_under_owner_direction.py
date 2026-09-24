"""Freeze the unchanged-arm job (seed 20260917 of 20208c92) under the owner's 2026-09-24 direction. Records only.

MF-1 (BLOCKER). `prepare_unchanged_repro.py --write` refuses today: EXECUTION_ADMISSION.json is NOT_READY and pinned
policy files moved at their branch tips. The owner's 2026-09-24 direction ("launch today ... 3 repaired runs plus the
old-Helm re-run, inside my $60 limit, with the existing stop rules") replaces that approval gate for the launch.
This file imports prepare_unchanged_repro.py and repro_common.py and edits neither. It runs their checks in order:
existing-folder refusals, the tree and untracked rules, the policy gate (tips report-only), owner authorization (must
be STANDING_PROJECT_AUTHORIZATION), Helm 2.0's seed-17 records, the committed package byte for byte, the launcher's
three validators, and equality with Helm 2.0's request and authority except the job name. It records the execution
admission as it is (NOT_READY, with the gate's reasons). It never edits EXECUTION_ADMISSION.json, writes no approval
word, and leaves the reader, its rule and its digest untouched.

WRITES frozen/20260917/{owner,request,authority}.json and frozen/study.json through frozen.partial/, read back and
re-validated before the rename. Commit frozen/ by explicit path and push BEFORE the launch (MF-2).

USAGE, from this worktree's CNCM folder, after this file is committed (untracked files are refused):
    python -B records/typed_pointer_001/admission_unchanged_repro_001/write_launch_under_owner_direction.py
No torch, no AWS call. It imports the launcher (pure Python) and stats the ledger path; it never opens the ledger.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. It transcribes the owner's words; it is not an owner signature.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import prepare_unchanged_repro as prep  # noqa: E402
import repro_common as common  # noqa: E402

stop_unless = common.make_stop('UNCHANGED_REPRO_OWNER_DIRECTION_STOPPED:')
LAUNCH_BASIS = 'OWNER_DIRECTION_20260924'
SELF_REL = common.HERE_REL + '/write_launch_under_owner_direction.py'
OWNER_WORDS = {   # verbatim; item 2's line breaks joined by single spaces; each pinned by sha256
    'owner_direction_20260924_item2': (
        '2. HELM MAIN TRAINING (HELM-REPAIR-CONTROLLED-1): launch today. - Settle the 6 held items now. For each item, '
        'write one line: MUST-FIX-BEFORE-LAUNCH or RECORD-AND-CONTINUE. The default is RECORD-AND-CONTINUE. - Fix only '
        'the MUST-FIX items, then launch: 3 repaired runs plus the old-Helm re-run, inside my $60 limit, with the '
        'existing stop rules. - Do not pre-solve the backup plan. If the backup is needed and would go over $60, stop '
        'at that point and ask me then.', 'baa24028a187d9226116a6ee48eb93c9cd86d363bafa0d6153a217a3d7a0432e'),
    'owner_launch_yes_20260924': (
        'YES to launching the side-by-side training of the repaired Helm. You approved up to $60.',
        'a19e79abe5629503c2d5db8b99f3692c73102c505982ce15ecb1cd28881b4e2b'),
}
BEFORE_LAUNCH = [
    'MF-2: frozen/ committed by explicit path and pushed; git status clean; HEAD equals the remote branch tip',
    'MF-3: measured spend so far (full, including the $7.36 prior) + $15.00 <= $60.00, checked by hand; else stop',
    'one GPU machine at a time; no automatic retry; never --reduced-schedule']


def policy_gate():
    """The report-only gate. If the fetch fails, the local remote-tracking refs are used, and the record says so."""
    try:
        return prep.gates(fetch=True, require_admitted=False), True
    except SystemExit as error:
        stop_unless(str(error).startswith('UNCHANGED_REPRO_ADMISSION_STOPPED:POLICY_TIP_NOT_FETCHED'), str(error)[:600])
        return prep.gates(fetch=False, require_admitted=False), False


def main():
    for name, (words, pinned) in OWNER_WORDS.items():
        stop_unless(sha256(words.encode('ascii')).hexdigest() == pinned, 'OWNER_WORDS_EDITED:' + name)
    prep.refuse_existing()
    head = prep.check_repository()
    gate, fetched = policy_gate()
    owner = gate['owner_authorization']
    stop_unless(owner['state'] == common.OWNER_AUTHORIZED, 'OWNER_AUTHORIZATION:' + '|'.join(owner['reasons'])[:800])
    helm2 = prep.helm2_records()
    launch = prep.load_launcher()
    prep.check_launcher(launch)
    package = prep.verify_package(launch)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    files, job, bindings = prep.build(launch, stamp=stamp, gate=gate, package=package, helm2=helm2)
    stop_unless(bindings == common.HELM2_BINDINGS, 'BINDINGS_DIFFER_FROM_HELM2')
    argv = job['launch_argv']
    stop_unless('--reduced-schedule' not in argv and argv[argv.index('--receipt-dir') + 1] == str(common.RECEIPT_DIR),
                'LAUNCH_ARGV_FORM')
    admission = gate['execution_admission']
    study = prep.study_record(launch, head=head, gate=gate, package=package, job=job, bindings=bindings)
    superseded = {key: study[key] for key in ('before_launch_required', 'check_before_launch')}
    study.update({
        'launch_basis': LAUNCH_BASIS,
        'owner_words_launch_basis': {name: {'raw': words, 'sha256': pinned} for name, (words, pinned) in OWNER_WORDS.items()},
        'owner_direction_record': ('_handoffs/HELM_NEXT_PHASE_20260923/OWNER_STOP_POLISHING_20260924.md on '
                                   'research/helm-integration-20260923'),
        'execution_admission_at_freeze': {key: admission[key] for key in ('state', 'recorded_state', 'reasons',
                                                                          'record_sha256')},
        'policy_tip_fetched_at_freeze': fetched,
        'before_launch_required': BEFORE_LAUNCH,
        'check_before_launch': 'NOT prepare_unchanged_repro.py --check (it requires ADMITTED); the MF-2 and MF-3 checks',
        'writer_default_before_launch_superseded_by_owner_direction': superseded,
        'writer': SELF_REL, 'writer_blob_at_head': common.blob_id('HEAD', SELF_REL),
        'reading_needs_first': ('before anyone opens the result: a disclosed amendment to the reader admission check '
                                'only; decide() unchanged; EXECUTION_ADMISSION.json never flipped afterwards')})
    study_raw = launch.canonical(study)
    files.append((common.OUTPUT / 'study.json', study_raw))
    launch.validate_ledger_path(launch.CANONICAL_LEDGER)       # a stat only; the ledger is never opened here

    def recheck(locate):
        """The launcher's own validators, Helm 2.0 equality and argv equality, on the bytes in frozen.partial/."""
        pins = {name: common.pin(Path(job[name]['path']), locate(job[name]['path']).read_bytes())
                for name in ('owner', 'request', 'authority')}
        stop_unless(all(pins[name] == job[name] for name in pins), 'WRITTEN_PINS')
        request = json.loads(locate(job['request']['path']).read_bytes())
        authority = json.loads(locate(job['authority']['path']).read_bytes())
        prep.validate(launch, request, authority, locate(job['owner']['path']))
        prep.compare_with_helm2(launch, request, authority, helm2)
        expected = common.launch_argv(launcher=common.ROOT / common.LAUNCHER_REL, request=pins['request'],
                                      authority=pins['authority'], owner=pins['owner'],
                                      receipt_dir=common.RECEIPT_DIR, ledger=launch.CANONICAL_LEDGER)
        written = json.loads(locate(common.OUTPUT / 'study.json').read_bytes())
        stop_unless(written['jobs'][0]['launch_argv'] == argv == expected, 'LAUNCH_ARGV_EQUALITY')

    written = common.write_folder_atomically(common.OUTPUT, files, recheck, stop_unless)
    print(json.dumps({'status': 'FROZEN_BEFORE_FIRST_RUN', 'launch_basis': LAUNCH_BASIS, 'job': job['job'],
                      'execution_admission_at_freeze': admission['state'], 'written': written,
                      'study_json_sha256': common.digest(study_raw), 'launch_cwd': str(common.ROOT),
                      'launch_argv': argv, 'next': 'commit frozen/ by explicit path and push (MF-2), then MF-3'},
                     sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
