#!/bin/bash
# c41 worker: SCORE_SCRIBE_L4_SEALED_98 on one t3.medium (Amazon Linux 2023). Runs as root via SSM.
# Fetch input.zip, check sha256, install CPU-only torch in a venv, unpack, run the plan's command, upload a
# deliverable zip (counts-only receipt + logs) and a terminal record. Never prints sealed row text.
set -uo pipefail
export AWS_DEFAULT_REGION=us-west-2 AWS_PAGER= PYTHONDONTWRITEBYTECODE=1 HOME=/root
B='__BUCKET__'; P='__PREFIX__'; J='__JOB__'; I='__INSTANCE__'; PS='__PAYLOAD_SHA__'
R=/opt/c41; O=$R/out
mkdir -p "$O"; cd "$R"
STATUS=STARTED
log() { echo "$(date -u +%FT%TZ) $*" >> "$O/worker.log"; }
prog() {
  printf '{"job":"%s","instance":"%s","payload_sha256":"%s","phase":"%s","utc":"%s"}\n' "$J" "$I" "$PS" "$1" "$(date -u +%FT%TZ)" > "$R/progress.json"
  aws s3api put-object --bucket "$B" --key "${P}progress.json" --body "$R/progress.json" > /dev/null 2>> "$O/worker.log" || true
  log "PHASE $1"
}
finish() {
  local st="$1"
  local sx; sx=$(cat "$O/score.exit.txt" 2>/dev/null || echo none)
  { uname -a; nproc; free -m; df -h /; cat /etc/os-release; } > "$O/host_info.txt" 2>&1
  ( cd "$O" && sha256sum $(ls | grep -v '^SHA256SUMS.txt$') > SHA256SUMS.txt )
  python3 -I -c "import zipfile,os; z=zipfile.ZipFile('/opt/c41/deliverable.zip','w',zipfile.ZIP_DEFLATED); [z.write(os.path.join('/opt/c41/out',n),'c41_out/'+n) for n in sorted(os.listdir('/opt/c41/out'))]; z.close()"
  local ds; ds=$(sha256sum "$R/deliverable.zip" | cut -d' ' -f1)
  local dl; dl=$(stat -c %s "$R/deliverable.zip")
  aws s3api put-object --bucket "$B" --key "${P}pointer-saturation-deliverable.zip" --body "$R/deliverable.zip" --metadata "sha256=$ds,length=$dl" > /dev/null 2>> "$R/upload_err.log"
  local up=$?
  printf '{"job":"%s","instance":"%s","payload_sha256":"%s","status":"%s","score_exit":"%s","deliverable_sha256":"%s","deliverable_bytes":%s,"deliverable_upload_rc":%s,"utc":"%s"}\n' "$J" "$I" "$PS" "$st" "$sx" "$ds" "$dl" "$up" "$(date -u +%FT%TZ)" > "$R/transport-result.json"
  aws s3api put-object --bucket "$B" --key "${P}transport-result.json" --body "$R/transport-result.json" > /dev/null 2>> "$R/upload_err.log"
  prog "DONE_$st"
  cat "$R/transport-result.json"
  exit 0
}
prog BOOT
aws s3api get-object --bucket "$B" --key "${P}input.zip" "$R/input.zip" > /dev/null 2>> "$O/worker.log" || finish PLUMBING_FAIL_INPUT_GET
echo "$PS  $R/input.zip" | sha256sum -c - >> "$O/worker.log" 2>&1 || finish PLUMBING_FAIL_INPUT_SHA
prog INSTALL_PYTHON
PY=""
for v in 3.12 3.11; do
  if dnf install -y -q "python$v" "python$v-pip" >> "$O/install.log" 2>&1; then PY="python$v"; break; fi
done
[ -n "$PY" ] || PY=python3
log "PYTHON $PY $($PY --version 2>&1)"
$PY -m venv "$R/venv" >> "$O/install.log" 2>&1 || finish PLUMBING_FAIL_VENV
prog INSTALL_TORCH_CPU
"$R/venv/bin/pip" install --no-cache-dir --disable-pip-version-check torch --index-url https://download.pytorch.org/whl/cpu > "$O/pip_install.log" 2>&1 || finish PLUMBING_FAIL_TORCH_INSTALL
"$R/venv/bin/pip" freeze > "$O/pip_freeze.txt" 2>&1
prog UNPACK
"$R/venv/bin/python" -I -c "import zipfile; zipfile.ZipFile('/opt/c41/input.zip').extractall('/opt/c41/w')" >> "$O/worker.log" 2>&1 || finish PLUMBING_FAIL_UNPACK
"$R/venv/bin/python" -I -c "
import hashlib, json, pathlib
w = pathlib.Path('/opt/c41/w'); m = json.loads((w / 'PAYLOAD_MANIFEST.json').read_bytes())
bad = [k for k, v in m['members'].items() if hashlib.sha256((w / k).read_bytes()).hexdigest() != v]
print('MANIFEST_MEMBERS', len(m['members']), 'BAD', len(bad)); raise SystemExit(1 if bad else 0)
" >> "$O/worker.log" 2>&1 || finish PLUMBING_FAIL_MANIFEST
prog SCORE
cd "$R/w"
PYTHONPATH="$R/w/lacunarity_machine_v1" "$R/venv/bin/python" -X utf8 -B score_scribe_l4.py --weights scribe_l4_weights.pt --vocab scribe_vocab.json \
  --scribe-src ./scribe_src --lang-v3 ./language_v3 --bridge ./bridge_root --sealed real_heldout_unparseables_98.jsonl \
  --approval OWNER_APPROVAL_SCORE_SCRIBE_L4.md --out "$O/SCRIBE_L4_SEALED_98_RECEIPT.json" > "$O/score.stdout.log" 2> "$O/score.stderr.log"
echo $? > "$O/score.exit.txt"
cd "$R"
if [ "$(cat "$O/score.exit.txt")" = "0" ] && [ -s "$O/SCRIBE_L4_SEALED_98_RECEIPT.json" ]; then finish SCORED; else finish SCORE_FAILED; fi
