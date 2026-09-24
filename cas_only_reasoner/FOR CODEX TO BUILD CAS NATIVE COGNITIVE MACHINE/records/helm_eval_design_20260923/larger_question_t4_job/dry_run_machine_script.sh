#!/bin/bash
# HELM-LARGER-QUESTION-PATH-1 T4 checks on ONE throwaway g4dn.2xlarge (NVIDIA T4). Label CLAUDE_BUILT_CLAUDE_CHECKED.
# NO credentials on this machine: ONE download and THREE uploads (results, progress log, rows so far) through
# time-limited links. Forward passes only: no optimizer step, no checkpoint written, no training. It always ends by
# shutting down, and it is destroyed on shutdown (the launcher sets shutdown behaviour = terminate).
set -uo pipefail
trap '' PIPE
shutdown -h +123 "helm larger-question t4 hard limit" || true               # kill switch 0: OS power-off
LOG=/var/log/helm_lq_t4_job.log
exec > >(tee -a "$LOG") 2>&1
echo "JOB START $(date -u +%FT%TZ)"
( sleep 7200; kill -TERM $$ 2>/dev/null; sleep 120; shutdown -h now; echo "IN-INSTANCE TIMER FIRED" ) &   # kill switch 1

WORK=/root/helm_lq_t4
mkdir -p "$WORK/out"
cd "$WORK"
STATUS=setup
CHILD=
OUT_JSON="$WORK/out/larger_path_result.json"
ROWS="$OUT_JSON.rows.jsonl"
upload() { curl -sS --retry 3 --max-time 300 -X PUT --upload-file "$1" "$2" -o /dev/null -w "upload $(basename "$1") -> http %{http_code}\n" || true; }
finish() {                                                                                 # kill switch 2
  [ -n "$CHILD" ] && kill -TERM "$CHILD" 2>/dev/null && sleep 5
  echo "JOB FINISH $(date -u +%FT%TZ) status=$STATUS"
  echo "$STATUS" > "$WORK/out/STATUS"
  cp "$LOG" "$WORK/out/job.log" 2>/dev/null || true
  tar -czf "$WORK/results.tar.gz" -C "$WORK" out || true
  upload "$WORK/results.tar.gz" "https://DRY-RUN/helm-integration/larger-question-t4-20260924T053056Z/results.tar.gz"
  shutdown -h now
}
trap finish EXIT
trap 'STATUS="IN_INSTANCE_TIMER_TERM during $STATUS"; exit 143' TERM
( while true; do sleep 240; upload "$LOG" "https://DRY-RUN/helm-integration/larger-question-t4-20260924T053056Z/progress.log"; [ -f "$ROWS" ] && upload "$ROWS" "https://DRY-RUN/helm-integration/larger-question-t4-20260924T053056Z/rows_progress.jsonl"; done ) &

curl -fsS --retry 3 --max-time 900 -o bundle.tar.gz "https://DRY-RUN/helm-integration/larger-question-t4-20260924T053056Z/bundle.tar.gz" || { STATUS=bundle_download_failed; exit 1; }
echo "2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36  bundle.tar.gz" | sha256sum -c - || { STATUS=bundle_hash_mismatch; exit 1; }
mkdir pkg && tar -xzf bundle.tar.gz -C pkg || { STATUS=bundle_extract_failed; exit 1; }
cp pkg/identity.json "$WORK/out/identity.json"

export HOME=/root
curl -LsSf --retry 3 https://astral.sh/uv/install.sh | sh || { STATUS=uv_install_failed; exit 1; }
export PATH="/root/.local/bin:$PATH"
uv python install 3.14.7 || { STATUS=python_install_failed; exit 1; }
uv venv --python 3.14.7 "$WORK/venv" || { STATUS=venv_failed; exit 1; }
PY="$WORK/venv/bin/python"
uv pip install --python "$PY" "torch==2.11.0" --index-url https://download.pytorch.org/whl/cu128 || { STATUS=torch_install_failed; exit 1; }
uv pip install --python "$PY" "numpy==2.5.2" || { STATUS=numpy_install_failed; exit 1; }
W=pkg/research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist
uv pip install --python "$PY" --no-deps "$W/casformer_reference-0.1.0-py3-none-any.whl" "$W/cas_neural_cjt-0.2.0-py3-none-any.whl" || { STATUS=wheel_install_failed; exit 1; }
{ "$PY" --version; uname -a; nproc; free -m; nvidia-smi; echo "bundle_sha256=2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36";
  sha256sum "$W"/*.whl; uv pip freeze --python "$PY"; } > "$WORK/out/env.txt" 2>&1
cat "$WORK/out/env.txt"

# The run's environment (review V3: the T4 reference job also set the two thread counts).
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
export CAS_META2_RUN_TEACHING_CYCLE=1

# STAGE 0 (smoke, about a minute): torch build and GPU; the wheels; the script's own --list-inputs, and every listed
# input present in the bundle with its bytes and sha256. Any failure stops the job here, by name.
STATUS=stage0_smoke
cd "$WORK/pkg"
"$PY" -B research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py --list-inputs > "$WORK/out/stage0_list_inputs.json" 2> "$WORK/out/stage0_list_inputs.err" \
  || { STATUS=SMOKE_LIST_INPUTS_FAILED; exit 0; }
"$PY" -B - "$WORK/out/stage0_list_inputs.json" "$WORK/out/stage0_smoke.json" > "$WORK/out/stage0_smoke.log" 2>&1 <<'SMOKE'
import hashlib, importlib.metadata, importlib.util, json, pathlib, sys
listed = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
out, problems = {"schema": "claude.larger-question-t4-smoke/0.1"}, []
import torch
out["torch"], out["cuda_available"] = torch.__version__, torch.cuda.is_available()
if torch.__version__ != "2.11.0+cu128":
    problems.append("TORCH_VERSION:" + torch.__version__)
if torch.cuda.is_available():
    out["device_name"] = torch.cuda.get_device_name(0)
    out["cuda_sum"] = float(torch.ones(8, device="cuda").sum().item())
    if "T4" not in out["device_name"] or out["cuda_sum"] != 8.0:
        problems.append("GPU:" + out["device_name"])
else:
    problems.append("NO_CUDA")
for row in listed["required_inputs"]:
    path = pathlib.Path(row["path"])
    raw = path.read_bytes() if path.is_file() else None
    if raw is None or len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
        problems.append("INPUT:" + row["path"])
out["required_inputs_ok"] = len(listed["required_inputs"]) - sum(p.startswith("INPUT:") for p in problems)
out["source_tree_py_files"] = {t["path"]: len(list(pathlib.Path(t["path"]).rglob("*.py")))
                               for t in listed["required_source_trees"]}
problems += ["SOURCE_TREE:" + t for t, n in out["source_tree_py_files"].items() if n == 0]
problems += ["EVAL_PATHS:" + p for p in listed["eval_paths_files"] if not pathlib.Path(p).is_file()]
for module, want in listed["installed_wheel_modules"].items():
    try:
        version = importlib.metadata.version(want["distribution"])
    except importlib.metadata.PackageNotFoundError:
        version = None
    if importlib.util.find_spec(module) is None or version != want["version"]:
        problems.append("WHEEL:%s:%s" % (module, version))
out["problems"], out["pass"] = problems, not problems
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, sort_keys=True))
sys.exit(0 if not problems else 1)
SMOKE
S0=$?
cat "$WORK/out/stage0_smoke.log"
[ "$S0" -eq 0 ] || { STATUS=SMOKE_FAILED; exit 0; }

# STAGE 1 + 2, one process: the script's own timing preflight (stage 1: about 20 timed forward passes; it refuses
# with exit 5, PREFLIGHT_OVER_WALL_LIMIT, before any check if the projection is over its 3,600 s limit), then checks
# d, c, b, a (stage 2). Rows are written to $ROWS as each unit finishes. No retry.
STATUS=stage1_preflight_then_stage2_checks
START=$(date +%s)
"$PY" -B research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py --out "$OUT_JSON" > "$WORK/out/checks.log" 2>&1 &
CHILD=$!
wait "$CHILD"; CODE=$?
CHILD=
echo "checks exit=$CODE wall=$(( $(date +%s) - START ))s" | tee -a "$WORK/out/checks.log"
echo "$CODE" > "$WORK/out/CHECKS_EXIT_CODE"
tail -n 20 "$WORK/out/checks.log"
case "$CODE" in
  0) STATUS=done ;;
  1) STATUS=CHECKS_FAILED_OR_INCOMPLETE ;;
  2) STATUS=GPU_REQUIRED ;;
  3) STATUS=WALL_LIMIT_REACHED ;;
  4) STATUS=SETUP_REFUSED ;;
  5) STATUS=STAGE1_PREFLIGHT_OVER_WALL_LIMIT ;;
  *) STATUS="CHECKS_EXIT_$CODE" ;;
esac
exit 0
