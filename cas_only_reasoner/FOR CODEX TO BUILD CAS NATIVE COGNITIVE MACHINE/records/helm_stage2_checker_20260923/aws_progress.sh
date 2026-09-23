set -eu
cd /opt/helm-stage2
free -m
ps -eo pid,etime,pcpu,rss,args | grep -E 'pytest|verify_stage2|pip install' | grep -v grep || true
for f in run001/records/helm_stage2_checker_20260923/run_status.json run001/records/helm_stage2_checker_20260923/builder_tests.txt run001/records/helm_stage2_checker_20260923/performance.log run001/records/helm_stage2_checker_20260923/compatibility.log; do
 if [ -f "$f" ]; then printf '\n%s\n' "$f"; tail -3 "$f"; fi
done
