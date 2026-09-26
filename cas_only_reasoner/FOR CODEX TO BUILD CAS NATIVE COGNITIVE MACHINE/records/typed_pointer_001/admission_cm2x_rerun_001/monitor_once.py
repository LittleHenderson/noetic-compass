"""Run the frozen HELM command once and keep the public heartbeat current."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

COORD = Path('D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination')
SOURCE = 'c45f775f225dd06cc20cdf313f0a0398486e0d61'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    study_path = Path(sys.argv[1]).resolve()
    study_raw = study_path.read_bytes()
    if len(sys.argv) != 3 or hashlib.sha256(study_raw).hexdigest() != sys.argv[2]:
        raise ValueError('EXACT_FROZEN_STUDY_HASH_REQUIRED')
    study = json.loads(study_raw)
    if study['source_sha'] != SOURCE or study['model_seed'] != 20260918:
        raise ValueError('FROZEN_STUDY_IDENTITY')
    job = study['job_record']
    receipt = Path(job['receipt_dir'])
    marker = COORD / (study['job'] + '.operator_attempt.json')
    record = {'utc': now(), 'source_sha': SOURCE, 'job': study['job'],
              'study': str(study_path), 'study_sha256': hashlib.sha256(study_path.read_bytes()).hexdigest(),
              'monitor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'receipt_dir': str(receipt), 'automatic_retries': 0}
    with marker.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
    command = [sys.executable, *job['launch_command'][1:], *job['launch_argv']]
    log = COORD / (study['job'] + '.operator.log')
    def heartbeat(status, returncode=None):
        observed = [name for name in ('intent.json', 'preflight.json', 'reservation.json',
                    'launch.json', 'failure.json', 'result.json') if (receipt / name).is_file()]
        cleanup_confirmed = False
        if 'result.json' in observed:
            try:
                cleanup_confirmed = json.loads((receipt / 'result.json').read_bytes()).get('cleanup', {}).get('complete') is True
            except (ValueError, OSError):
                pass
        row = {'utc': now(), 'agent': 'codex', 'status': status,
               'current_task': 'HELM fresh 20-pass 2x job ' + study['job'],
               'work_done_since_last_heartbeat': {'receipt_files_present': observed, 'operator_exit_code': returncode},
               'blocker': 'Inspect final receipt and cleanup' if returncode not in (None, 0) else None,
               'next_action': 'Collect readout and confirm cleanup before any extension' if returncode is not None else 'Observe this single frozen job; do not resubmit',
               'relevant_commit_or_file': str(receipt),
               'paid_cloud_work_active': False if cleanup_confirmed else ('reservation.json' in observed),
               'cloud_state_note': 'Conservative until cleanup is confirmed. Reservation alone does not prove an instance is running; verify launch/provider state.'}
        with (COORD / 'codex_heartbeat.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row) + '\n')
        (COORD / 'HELM_RERUN_ACTIVE_OPERATOR_20260926.json').write_text(json.dumps({**record,
            'receipt_files_present': observed, 'operator_log': str(log), 'updated_utc': now(),
            'exit_code': returncode}, indent=2) + '\n', encoding='utf-8')
    heartbeat('START')
    with log.open('xb') as stream:
        process = subprocess.Popen(command, cwd=study['source_checkout'], stdout=stream, stderr=subprocess.STDOUT)
        print(json.dumps({'job': study['job'], 'child_pid': process.pid, 'operator_log': str(log)}), flush=True)
        last = time.monotonic()
        while process.poll() is None:
            time.sleep(5)
            if time.monotonic() - last >= 90:
                heartbeat('PROGRESS')
                last = time.monotonic()
        heartbeat('END', process.returncode)
        print(json.dumps({'job': study['job'], 'returncode': process.returncode, 'receipt_dir': str(receipt)}), flush=True)
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
