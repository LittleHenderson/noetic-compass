set -eu
cd /opt/helm-stage2
aws s3 cp s3://cas-helm-checker-20260923-807562639912-9eeab1e7/job/input_bundle.tar.gz input_bundle.tar.gz --only-show-errors
printf '%s  %s\n' a9ef9062801fd6657f6c39be2a9dac3ac7f464e14c17a96d1265fff67d1d8d05 input_bundle.tar.gz | sha256sum -c -
mkdir run001
tar -xzf input_bundle.tar.gz -C run001
python3 -m venv /opt/helm-stage2/venv
timeout 180 /opt/helm-stage2/venv/bin/pip install --disable-pip-version-check pytest==8.4.2 > pip-install.log 2>&1
cat > run001/run_checks.sh <<'SH'
set -u
cd /opt/helm-stage2/run001
export PYTHONPATH="$PWD/research/CAS_META_2_COMPOSITION"
export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
P=/opt/helm-stage2/venv/bin/python
R=records/helm_stage2_checker_20260923
$P -B -c "import sys;sys.path.insert(0,'$R');from verify_stage2 import verify_inputs;print('INPUTS_VERIFIED',len(verify_inputs()['files']))" > "$R/input_verification.log" 2>&1 || exit 9
timeout 1800 $P -B -m pytest -q research/CAS_META_2_COMPOSITION/tests/test_stage2_checker.py research/CAS_META_2_COMPOSITION/tests/test_typed_teaching_checker.py --junitxml="$R/builder_tests.xml" > "$R/builder_tests.txt" 2>&1
unit=$?
printf '{"unit_exit":%s}\n' "$unit" > "$R/run_status.json"
if [ "$unit" -eq 0 ]; then
 timeout 600 $P -B "$R/verify_stage2.py" benchmark > "$R/performance.log" 2>&1
 bench=$?
 printf '{"unit_exit":%s,"benchmark_exit":%s}\n' "$unit" "$bench" > "$R/run_status.json"
 aws s3 cp "$R/run_status.json" s3://cas-helm-checker-20260923-807562639912-9eeab1e7/job/run001-progress.json --only-show-errors
 timeout 3600 $P -B "$R/verify_stage2.py" compatibility > "$R/compatibility.log" 2>&1
 compat=$?
 printf '{"unit_exit":%s,"benchmark_exit":%s,"compatibility_exit":%s}\n' "$unit" "$bench" "$compat" > "$R/run_status.json"
fi
cat "$R/run_status.json"
SH
set +e
systemd-run --unit=helm-stage2-run001 --wait --pipe -p MemoryMax=4G -p CPUQuota=100% /bin/bash /opt/helm-stage2/run001/run_checks.sh
code=$?
set -e
cp run001/INPUT_MANIFEST.json run001/records/helm_stage2_checker_20260923/INPUT_MANIFEST.json
cp pip-install.log run001/records/helm_stage2_checker_20260923/pip-install.log
tar -czf run001-results.tar.gz -C run001 records/helm_stage2_checker_20260923
aws s3 cp run001-results.tar.gz s3://cas-helm-checker-20260923-807562639912-9eeab1e7/job/run001-results.tar.gz --only-show-errors
printf 'worker_exit=%s\n' "$code"
exit "$code"

