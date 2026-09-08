"""Render a bounded teaching-only guest bootstrap; rendering makes no AWS call.

Config and code are pinned before RunInstances. The later permit supplies the
observed instance identity and confirmed termination schedule. A permit's local
hash binds downloaded bytes, not an independent proof of who authorized them.
"""
import re
import shlex

ROOT = "/opt/cas-teaching"
WHEEL_SHA256 = "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee"


def render_bootstrap(*, bucket, job, source_sha256, driver_sha256, config_sha256, deadline_unix):
    if not re.fullmatch(r"cas-meta2-teaching-[0-9]{14}-[a-f0-9]{8}", job):
        raise ValueError("BOOTSTRAP_JOB")
    if bucket != job + "-807562639912":
        raise ValueError("BOOTSTRAP_BUCKET")
    if type(deadline_unix) is not int or deadline_unix <= 0:
        raise ValueError("BOOTSTRAP_DEADLINE")
    if not all(type(v) is str and re.fullmatch(r"[a-f0-9]{64}", v)
               for v in (source_sha256, driver_sha256, config_sha256)):
        raise ValueError("BOOTSTRAP_HASH")
    head = ["#!/bin/bash", "set -euo pipefail", "umask 077",
        "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_RETRY_MODE=standard AWS_PAGER=''",
        "export AWS_DEFAULT_REGION=us-west-2 CAS_META2_RUN_TEACHING_CYCLE=1",
        "DEADLINE=" + str(deadline_unix), "BUCKET=" + shlex.quote(bucket),
        "BASE=" + ROOT, "mkdir -p \"$BASE/bootstrap\"", "cd \"$BASE/bootstrap\"",
        "exec >bootstrap.log 2>&1",
        "# Absolute lifetime is set by the parent before RunInstances, not restarted at boot.",
        "NOW=$(date +%s)", "test \"$NOW\" -lt \"$DEADLINE\"",
        "( sleep $(( DEADLINE - NOW )); shutdown -h now ) >/dev/null 2>&1 &",
        "AWS_CALLS=0",
        "get_object() {",
        "  AWS_CALLS=$((AWS_CALLS + 1)); test \"$AWS_CALLS\" -le 126 || return 1",
        "  local left=$((DEADLINE - $(date +%s) - 120))",
        "  test \"$left\" -gt 0 || return 1",
        "  test \"$left\" -le 120 || left=120",
        "  timeout --signal=TERM --kill-after=5 \"$left\" aws s3api get-object --bucket \"$BUCKET\" --key \"$1\" \"$2\" --region us-west-2 --cli-connect-timeout 5 --cli-read-timeout 10",
        "}",
        "failed() {",
        "  code=$?; trap - EXIT",
        "  if test \"$code\" -ne 0; then",
        "    # Keep a bounded setup failure even when the teaching driver never starts.",
        "    tail -c 1048576 bootstrap.log >bootstrap_failure.log",
        "    timeout 20 aws s3api put-object --bucket \"$BUCKET\" --key results/bootstrap_failure.log --body bootstrap_failure.log --region us-west-2 --cli-connect-timeout 5 --cli-read-timeout 10 || true",
        "  fi",
        "  shutdown -h now || true",
        "  exit \"$code\"",
        "}", "trap failed EXIT",
        "command -v aws >/dev/null",
        "get_object input/source.zip source.zip",
        "echo '" + source_sha256 + "  source.zip' | sha256sum -c -",
        "get_object input/remote.py remote.py",
        "echo '" + driver_sha256 + "  remote.py' | sha256sum -c -",
        "get_object input/config.json config.json",
        "echo '" + config_sha256 + "  config.json' | sha256sum -c -",
        "# At most 64 polls. No workload retry and no release embedded in this script.",
        "PERMIT_READY=0",
        "for attempt in $(seq 1 64); do",
        "  if get_object input/permit.json permit.json; then PERMIT_READY=1; break; fi",
        "  sleep 2",
        "done",
        "test \"$PERMIT_READY\" -eq 1",
        "PY=''",
        "for p in python3.12 python3.11; do if command -v \"$p\" >/dev/null; then PY=\"$p\"; break; fi; done",
        "test -n \"$PY\"",
        "# Extract only the independently pinned wheel into bootstrap-only staging.",
        "\"$PY\" -I -B - <<'PYBOOT'",
        "import hashlib,json,pathlib,sys,zipfile",
        "root=pathlib.Path.cwd()",
        "config=json.loads((root/'config.json').read_bytes())",
        "permit=json.loads((root/'permit.json').read_bytes())",
        "assert permit['schema']=='cas-teaching-guest-permit/1'",
        "assert permit['config_sha256']==hashlib.sha256((root/'config.json').read_bytes()).hexdigest()",
        "assert permit['job']==config['job'] and permit['request_sha256']==config['request_sha256']",
        "assert permit['shutdown_schedule_confirmed'] is True and permit['automatic_retries']==0",
        "assert permit['deadline_unix']==config['deadline_unix']",
        "name='wheels/casformer_reference-0.1.0-py3-none-any.whl'",
        "with zipfile.ZipFile(root/'source.zip') as z:",
        "    matches=[i for i in z.infolist() if i.filename==name]",
        "    assert len(matches)==1 and 0<matches[0].file_size<=8*1024**2",
        "    raw=z.read(matches[0])",
        "assert hashlib.sha256(raw).hexdigest()=='" + WHEEL_SHA256 + "'",
        "with (root/pathlib.PurePosixPath(name).name).open('xb') as f: f.write(raw)",
        "PYBOOT",
        "INSTALL_DEADLINE=$(( $(date +%s) + 1200 ))",
        "bounded_install() {",
        "  local left=$((INSTALL_DEADLINE - $(date +%s)))",
        "  local totalleft=$((DEADLINE - $(date +%s) - 180))",
        "  test \"$left\" -le \"$totalleft\" || left=$totalleft",
        "  test \"$left\" -gt 0",
        "  timeout --signal=TERM --kill-after=10 \"$left\" \"$@\"",
        "}",
        "bounded_install \"$PY\" -I -B -m venv \"$BASE/venv\"",
        "VP=\"$BASE/venv/bin/python\"",
        "bounded_install \"$VP\" -I -B -m pip install --no-cache-dir --disable-pip-version-check --retries 0 --timeout 30 torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 --report torch_install.json",
        "bounded_install \"$VP\" -I -B -m pip install --no-cache-dir --disable-pip-version-check --retries 0 --timeout 30 --no-deps ./casformer_reference-0.1.0-py3-none-any.whl --report wheel_install.json",
        "bounded_install \"$VP\" -I -B -m pip install --no-cache-dir --disable-pip-version-check --retries 0 --timeout 30 numpy==2.2.6 --report dependency_install.json",
        "bounded_install \"$VP\" -I -B -m pip freeze --all >environment.txt",
        "# The config pin is independent. This permit hash only identifies the received bytes.",
        "PERMIT_SHA=$(sha256sum permit.json | cut -d ' ' -f 1)",
        "LEFT=$((DEADLINE - $(date +%s) - 60)); test \"$LEFT\" -gt 0",
        "timeout --signal=TERM --kill-after=10 \"$LEFT\" \"$PY\" -I -B remote.py --config \"$BASE/bootstrap/config.json\" --config-sha256 " + config_sha256 + " --permit \"$BASE/bootstrap/permit.json\" --permit-sha256 \"$PERMIT_SHA\" --root \"$BASE/job\" --python \"$VP\" --bootstrap-evidence \"$BASE/bootstrap\"",
        ""]
    output = "\n".join(head)
    if len(output.encode()) > 16384:
        raise ValueError("BOOTSTRAP_USERDATA_TOO_LARGE")
    return output
