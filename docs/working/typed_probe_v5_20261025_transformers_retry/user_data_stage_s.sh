#!/usr/bin/env bash
set -Eeuo pipefail
set +x
umask 077

REGION="us-west-2"
RUN_ID="typed-probe-v5-stage-s-transformers-retry-20261025"
BUCKET="cas-harness-runpod-92754088"
PREFIX="typed_probe_v5_20261025/${RUN_ID}"
SOURCE_PREFIX="${PREFIX}/input"
RUNNER_SHA256="413b309d101c132f8649e29e01d560f052611a371fee0cd1c57198166deec03e"
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

PYTHON="/opt/pytorch/bin/python"
TRANSFORMERS_VERSION="4.57.1"
TRANSFORMERS_INSTALL_TIMEOUT_SECONDS="240"
if [[ ! -x "${PYTHON}" ]]; then
  echo "Required PyTorch Python is absent: ${PYTHON}; refusing system-Python fallback."
  exit 20
fi
if ! TORCH_BEFORE="$("${PYTHON}" -W ignore -c 'import re, torch; m = re.match(r"^(\d+)\.(\d+)", torch.__version__); print(torch.__version__); raise SystemExit(0 if m and tuple(map(int, m.groups())) >= (2, 2) else 2)' 2>&1)"; then
  echo "The required PyTorch environment is unavailable or older than 2.2: ${TORCH_BEFORE}"
  exit 20
fi
echo "PyTorch environment passed: ${TORCH_BEFORE}"
if ! "${PYTHON}" -m pip --version; then
  echo "pip is unavailable in the required PyTorch environment."
  exit 21
fi
INSTALL_TRANSFORMERS=0
if ! IMPORT_INFO="$("${PYTHON}" -W ignore -c 'import torch, transformers; from transformers import AutoModelForCausalLM, AutoTokenizer; print("torch=" + torch.__version__ + "; transformers=" + transformers.__version__ + "; python=" + __import__("sys").version.split()[0])' 2>&1)"; then
  echo "Transformers is missing or unusable in ${PYTHON}; installing the frozen version ${TRANSFORMERS_VERSION}."
  INSTALL_TRANSFORMERS=1
elif [[ "${IMPORT_INFO}" != *"transformers=${TRANSFORMERS_VERSION};"* ]]; then
  echo "Transformers version is not the frozen version ${TRANSFORMERS_VERSION}: ${IMPORT_INFO}"
  INSTALL_TRANSFORMERS=1
fi
if [[ "${INSTALL_TRANSFORMERS}" == "1" ]]; then
  if ! timeout "${TRANSFORMERS_INSTALL_TIMEOUT_SECONDS}s" "${PYTHON}" -m pip install \
    --disable-pip-version-check --no-input --retries 2 --timeout 30 \
    --only-binary=:all: --upgrade-strategy only-if-needed \
    "transformers==${TRANSFORMERS_VERSION}"; then
    echo "Pinned Transformers installation failed or exceeded ${TRANSFORMERS_INSTALL_TIMEOUT_SECONDS} seconds."
    exit 22
  fi
  if ! IMPORT_INFO="$("${PYTHON}" -W ignore -c 'import torch, transformers; from transformers import AutoModelForCausalLM, AutoTokenizer; print("torch=" + torch.__version__ + "; transformers=" + transformers.__version__ + "; python=" + __import__("sys").version.split()[0])' 2>&1)"; then
    echo "PyTorch and Transformers verification failed after installation: ${IMPORT_INFO}"
    exit 23
  fi
fi
if [[ "${IMPORT_INFO}" != *"transformers=${TRANSFORMERS_VERSION};"* ]]; then
  echo "Unexpected Transformers version in the PyTorch environment: ${IMPORT_INFO}"
  exit 24
fi
TORCH_AFTER="$("${PYTHON}" -W ignore -c 'import torch; print(torch.__version__)')"
if [[ "${TORCH_AFTER}" != "${TORCH_BEFORE}" ]]; then
  echo "PyTorch changed during Transformers setup: before=${TORCH_BEFORE}; after=${TORCH_AFTER}"
  exit 25
fi
echo "PyTorch and Transformers verification passed: ${IMPORT_INFO}"
if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is not installed."
  exit 21
fi
"${PYTHON}" -m py_compile "${ROOT}/run_stage_s_v5.py"
CUDA_READY=0
CUDA_WAIT_STARTED="${SECONDS}"
attempt=0
while (( SECONDS - CUDA_WAIT_STARTED + 8 < 300 )); do
  attempt=$((attempt + 1))
  if CUDA_INFO="$(timeout 8 "${PYTHON}" -c 'import torch; ready = torch.cuda.is_available() and torch.cuda.device_count() > 0; gpu = torch.cuda.get_device_name(0) if ready else "none"; print("torch=" + torch.__version__ + "; cuda_build=" + str(torch.version.cuda) + "; cuda_available=" + str(torch.cuda.is_available()) + "; device_count=" + str(torch.cuda.device_count()) + "; gpu=" + gpu); raise SystemExit(0 if ready else 2)' 2>&1)"; then
    echo "CUDA and GPU check passed: ${CUDA_INFO}"
    CUDA_READY=1
    break
  else
    echo "CUDA and GPU check ${attempt} is not ready: ${CUDA_INFO}"
    if (( attempt % 6 == 0 )); then
      if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi -L || true
      else
        echo "nvidia-smi is not available yet."
      fi
    fi
    sleep 10
  fi
done
if [[ "${CUDA_READY}" -ne 1 ]]; then
  echo "CUDA and GPU did not become ready within the 300-second startup limit."
  exit 23
fi

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
