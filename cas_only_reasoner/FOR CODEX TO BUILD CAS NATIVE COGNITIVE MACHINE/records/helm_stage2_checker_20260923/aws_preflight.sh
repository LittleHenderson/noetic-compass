set -eu
cat /opt/helm-stage2/startup-status
python3 --version
aws --version
free -m
systemctl list-timers --all --no-pager | head -12
