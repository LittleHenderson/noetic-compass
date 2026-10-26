#!/usr/bin/env bash
set -Eeuo pipefail
set +x
umask 077

REGION="us-west-2"
RUN_ID="typed-probe-v5-stage-s-retry1-20261025-0400z"
BUCKET="cas-harness-runpod-92754088"
PREFIX="typed_probe_v5_20261025/${RUN_ID}"
SOURCE_PREFIX="${PREFIX}/input"
RUNNER_SHA256="b44bcbbd9ee9a41252e72bc9f1c9efef3fee6de07a701ad743c26399dd010268"
ROOT="/opt/typed-probe-v5-stage-s"
WORK="${ROOT}/work"
LOG="/var/log/typed-probe-v5-stage-s.log"
INSTANCE_ID=""

mkdir -p "${ROOT}" "${WORK}"
exec >>"${LOG}" 2>&1

finish() {
  rc=$?
  trap - EXIT
  set +e
  printf 'exit_code=%s\nfinished_at_utc=%s\n' "${rc}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >"${WORK}/instance_exit_status.txt"
  aws s3 cp "${LOG}" "s3://${BUCKET}/${PREFIX}/output/logs/instance-bootstrap.log" \
    --region "${REGION}" --sse AES256 >/dev/null 2>&1
  aws s3 cp "${WORK}/instance_exit_status.txt" \
    "s3://${BUCKET}/${PREFIX}/output/logs/instance_exit_status.txt" \
    --region "${REGION}" --sse AES256 >/dev/null 2>&1
  if [[ -n "${INSTANCE_ID}" ]]; then
    aws ec2 terminate-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}" \
      >/dev/null 2>&1
  fi
  exit "${rc}"
}
trap finish EXIT

TOKEN="$(curl --fail --silent --show-error -X PUT \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
  http://169.254.169.254/latest/api/token)"
INSTANCE_ID="$(curl --fail --silent --show-error \
  -H "X-aws-ec2-metadata-token: ${TOKEN}" \
  http://169.254.169.254/latest/meta-data/instance-id)"
unset TOKEN

export AWS_REGION="${REGION}"
export STAGE_S_BUCKET="${BUCKET}"
export STAGE_S_PREFIX="${PREFIX}"
export STAGE_S_RUN_ID="${RUN_ID}"
export STAGE_S_INSTANCE_ID="${INSTANCE_ID}"
export STAGE_S_WORKDIR="${WORK}"
export STAGE_S_BANK="${ROOT}/candidate_bank_v4_120_20260610.jsonl"
export STAGE_S_RUBRIC="${ROOT}/typed_probe_v5_judge_rubric_20261025.txt"
export HF_HOME="${ROOT}/hf-cache"
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
ulimit -c 0

aws s3 cp "s3://${BUCKET}/${SOURCE_PREFIX}/run_stage_s_v5.py" \
  "${ROOT}/run_stage_s_v5.py" --region "${REGION}"
aws s3 cp "s3://${BUCKET}/${SOURCE_PREFIX}/candidate_bank_v4_120_20260610.jsonl" \
  "${STAGE_S_BANK}" --region "${REGION}"
aws s3 cp "s3://${BUCKET}/${SOURCE_PREFIX}/typed_probe_v5_judge_rubric_20261025.txt" \
  "${STAGE_S_RUBRIC}" --region "${REGION}"
aws s3 cp "s3://${BUCKET}/${SOURCE_PREFIX}/typed_probe_gate_prereg_v5_safe_handling_20261025.md" \
  "${ROOT}/typed_probe_gate_prereg_v5_safe_handling_20261025.md" --region "${REGION}"
aws s3 cp "s3://${BUCKET}/${SOURCE_PREFIX}/typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md" \
  "${ROOT}/typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md" \
  --region "${REGION}"

test "$(sha256sum "${STAGE_S_BANK}" | awk '{print $1}')" = \
  "4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f"
test "$(sha256sum "${STAGE_S_RUBRIC}" | awk '{print $1}')" = \
  "e176676df7cd4d1593288daf9a793e0c75a1a81cdc9d9c40980c4d1eb02307fd"
test "$(sha256sum "${ROOT}/typed_probe_gate_prereg_v5_safe_handling_20261025.md" | awk '{print $1}')" = \
  "c3049fbf65565cf062fdddafd91200b96a2c7fbbd3eed7daaeb513900b5e7132"
test "$(sha256sum "${ROOT}/typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md" | awk '{print $1}')" = \
  "7d259447e5e5bfc8e650694bba25cb99ee0d76760e76665c3d81eea9ffcc22fe"
test "$(sha256sum "${ROOT}/run_stage_s_v5.py" | awk '{print $1}')" = "${RUNNER_SHA256}"

PYTHON=""
for candidate in /opt/pytorch/bin/python /opt/pytorch/bin/python3 /opt/conda/bin/python3 /usr/bin/python3; do
  if [[ ! -x "${candidate}" ]]; then
    echo "Python candidate is absent: ${candidate}"
    continue
  fi
  if "${candidate}" -c \
    'import torch, transformers; assert torch.cuda.is_available()' >/dev/null 2>&1; then
    PYTHON="${candidate}"
    break
  else
    echo "Python candidate failed the PyTorch, Transformers, or CUDA check: ${candidate}"
  fi
done
if [[ -z "${PYTHON}" ]]; then
  echo "No installed Python environment has PyTorch, Transformers, and CUDA."
  exit 20
fi
if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is not installed."
  exit 21
fi
"${PYTHON}" -m py_compile "${ROOT}/run_stage_s_v5.py"

API_KEY="$(aws ssm get-parameter --region "${REGION}" \
  --name "/cas-harness/typed-probe-v5/anthropic-api-key" \
  --with-decryption --query 'Parameter.Value' --output text)"
if [[ -z "${API_KEY}" || "${API_KEY}" == "None" ]]; then
  echo "Encrypted Anthropic key parameter is unavailable."
  exit 22
fi
export ANTHROPIC_API_KEY="${API_KEY}"
unset API_KEY

echo "Starting authorized Stage S on AWS instance ${INSTANCE_ID}."
echo "Local model fallback is disabled. The runner has an 80-minute runtime guard."
"${PYTHON}" "${ROOT}/run_stage_s_v5.py"
