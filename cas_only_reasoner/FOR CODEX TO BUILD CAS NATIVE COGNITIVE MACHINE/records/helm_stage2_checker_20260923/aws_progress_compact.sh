set -eu
cd /opt/helm-stage2/run001
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('records/helm_stage2_checker_20260923/compatibility.json')
if p.exists():
 d=json.loads(p.read_bytes())
 print(json.dumps({k:d.get(k) for k in ['status','target_records','slot_plans','predictions','unique_check_inputs','reused_identical_check_inputs','elapsed_seconds','target_mismatches','witness_mismatches','slot_mismatches','check_mismatches']}))
PY
