#!/bin/bash
set -euo pipefail
export AWS_DEFAULT_REGION=us-west-2
export HF_HOME=/workspace/hf-cache
export TRANSFORMERS_CACHE=/workspace/hf-cache
export PYTHONUNBUFFERED=1
BUCKET=cas-harness-runpod-92754088
PREFIX=bridge-control-20260822
LOG=/workspace/job.log
S3LOG=s3://$BUCKET/$PREFIX/logs/job.log
stage(){ echo "[$(date -u +%FT%TZ)] $1" | tee -a $LOG; aws s3 cp $LOG $S3LOG >/dev/null 2>&1 || true; }
trap 'stage "FAILED"; aws s3 cp $LOG $S3LOG >/dev/null 2>&1 || true; INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id); aws ec2 modify-instance-attribute --region us-west-2 --instance-id $INSTANCE_ID --disable-api-termination --value false >/dev/null 2>&1 || true; aws ec2 terminate-instances --region us-west-2 --instance-ids $INSTANCE_ID >/dev/null 2>&1 || true; exit 1' ERR
stage "boot started"
nvidia-smi 2>&1 | tee -a $LOG || stage "nvidia-smi failed"
stage "pip install"
python3 -m pip install --quiet --upgrade pip 2>&1 | tail -2
python3 -m pip install --quiet "torch==2.5.1" --index-url https://download.pytorch.org/whl/cu121 2>&1 | tail -2
python3 -m pip install --quiet "transformers==5.8.1" scikit-learn numpy 2>&1 | tail -2
stage "deps installed"
mkdir -p /workspace/run && cd /workspace/run
aws s3 cp s3://$BUCKET/$PREFIX/bundle.zip . >/dev/null 2>&1
unzip -q bundle.zip
stage "bundle unpacked"
REV=""
if [ -d "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" ]; then REV=$(ls "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" | head -1); fi
if [ -z "$REV" ]; then
  stage "downloading model 40GB"
  timeout 3600 python3 -c "import torch; from transformers import AutoModelForCausalLM, AutoTokenizer; m = AutoModelForCausalLM.from_pretrained('EleutherAI/gpt-neox-20b', torch_dtype=torch.float16, device_map='auto'); t = AutoTokenizer.from_pretrained('EleutherAI/gpt-neox-20b'); print('loaded params', m.num_parameters())"
  REV=$(ls "$HF_HOME/hub/models--EleutherAI--gpt-neox-20b/snapshots" | head -1)
fi
stage "model ready revision=$REV"
cd /workspace/run/scripts
timeout 5400 python3 run_bridge_control_20b.py --fixture /workspace/run/bridge_control/bridge_control_fixture_20260822.json --output /workspace/run/bridge_control_results_20260822.json --model-revision "$REV" 2>&1 | tee -a $LOG
stage "run complete"
aws s3 cp /workspace/run/bridge_control_results_20260822.json s3://$BUCKET/$PREFIX/results/bridge_control_results_20260822.json >/dev/null 2>&1
stage "results uploaded"
aws s3 cp $LOG $S3LOG >/dev/null 2>&1
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 modify-instance-attribute --region us-west-2 --instance-id $INSTANCE_ID --disable-api-termination --value false
aws ec2 terminate-instances --region us-west-2 --instance-ids $INSTANCE_ID
stage "termination requested"
