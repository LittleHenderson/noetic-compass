#!/bin/bash
set -uo pipefail
export AWS_DEFAULT_REGION=us-west-2
export HF_HOME=/workspace/hf-cache
export TRANSFORMERS_CACHE=/workspace/hf-cache
export PYTHONUNBUFFERED=1
BUCKET=cas-harness-runpod-92754088
PREFIX=bridge-control-20260822
LOG=/workspace/job.log
S3LOG=s3://$BUCKET/$PREFIX/logs/job.log
mkdir -p /workspace
s3cp_retry(){ for i in 1 2 3 4 5 6; do if aws s3 cp "$1" "$2" >/dev/null 2>&1; then return 0; fi; sleep 20; done; return 1; }
stage(){ echo "[$(date -u +%FT%TZ)] $1" | tee -a $LOG; s3cp_retry $LOG $S3LOG || true; }
fail(){ stage "FAILED: $1"; INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id); s3cp_retry $LOG $S3LOG || true; aws ec2 modify-instance-attribute --region us-west-2 --instance-id $INSTANCE_ID --disable-api-termination --value false >/dev/null 2>&1 || true; aws ec2 terminate-instances --region us-west-2 --instance-ids $INSTANCE_ID >/dev/null 2>&1 || true; sleep 60; exit 1; }
stage "boot started (waiting for role creds)"
OK=0
for i in $(seq 1 20); do if aws sts get-caller-identity >/dev/null 2>&1; then OK=1; break; fi; sleep 15; done
if [ "$OK" != "1" ]; then fail "no role creds after 5min"; fi
stage "creds ok"
nvidia-smi 2>&1 | tee -a $LOG || stage "nvidia-smi warn"
stage "venv setup"
python3 -m venv /workspace/venv || fail "venv"
/workspace/venv/bin/pip install --quiet --upgrade pip 2>&1 | tail -2 || fail "pip upgrade"
stage "installing torch (2.5GB)"
/workspace/venv/bin/pip install --quiet "torch==2.5.1" --index-url https://download.pytorch.org/whl/cu121 2>&1 | tail -2 || fail "torch install"
/workspace/venv/bin/pip install --quiet "transformers==5.8.1" scikit-learn numpy 2>&1 | tail -2 || fail "deps install"
stage "deps installed"
mkdir -p /workspace/run && cd /workspace/run
s3cp_retry s3://$BUCKET/$PREFIX/bundle.zip bundle.zip || fail "bundle download"
unzip -q bundle.zip
stage "bundle unpacked"
REV=""
if [ -d "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" ]; then REV=$(ls "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" | head -1); fi
if [ -z "$REV" ]; then
  stage "downloading model 40GB"
  timeout 3600 /workspace/venv/bin/python -c "import torch; from transformers import AutoModelForCausalLM, AutoTokenizer; m = AutoModelForCausalLM.from_pretrained('EleutherAI/gpt-neox-20b', torch_dtype=torch.float16, device_map='auto'); t = AutoTokenizer.from_pretrained('EleutherAI/gpt-neox-20b'); print('loaded params', m.num_parameters())" || fail "model download"
  REV=$(ls "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" | head -1)
fi
stage "model ready revision=$REV"
cd /workspace/run/scripts
timeout 5400 /workspace/venv/bin/python run_bridge_control_20b.py --fixture /workspace/run/bridge_control/bridge_control_fixture_20260822.json --output /workspace/run/bridge_control_results_20260822.json --model-revision "$REV" 2>&1 | tee -a $LOG || fail "runner"
stage "run complete"
s3cp_retry /workspace/run/bridge_control_results_20260822.json s3://$BUCKET/$PREFIX/results/bridge_control_results_20260822.json || fail "results upload"
stage "results uploaded"
s3cp_retry $LOG $S3LOG
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 modify-instance-attribute --region us-west-2 --instance-id $INSTANCE_ID --disable-api-termination --value false
aws ec2 terminate-instances --region us-west-2 --instance-ids $INSTANCE_ID
stage "termination requested"
