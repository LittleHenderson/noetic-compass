#!/usr/bin/env bash
# Gate 1B on-instance bootstrap -- FROZEN (GATE 1A.2 section 4).
# Fail-closed everywhere; every value comes from the detached signed approval.
set -euo pipefail

# REQUIRED before the first CUDA GEMM for torch.use_deterministic_algorithms(True)
# (audit fix); belt-and-suspenders with the Dockerfile ENV
export CUBLAS_WORKSPACE_CONFIG="${CUBLAS_WORKSPACE_CONFIG:-:4096:8}"

: "${CAMPAIGN_REPO_URL:?}"          # set by the launch configuration
: "${CAMPAIGN_COMMIT:?}"            # the exact approved commit
: "${CAMPAIGN_ID:?}"
: "${EXECUTION_APPROVAL_S3:?}"      # detached approval location (owner-controlled)
: "${PREP_RECEIPT_S3:?}"

git clone --no-checkout "$CAMPAIGN_REPO_URL" /campaign/repo
cd /campaign/repo
git checkout --detach "$CAMPAIGN_COMMIT"

PKG=cas_only_reasoner/cjt_gate1a_static_neural_v1
python "$PKG/tools/generate_construction_gold.py" --check
python "$PKG/tools/build_manifests.py" --check
python "$PKG/tools/test_byte_domain.py" --skip-fresh-clone

: "${PREP_APPROVAL_S3:?}"           # detached prep approval (owner-controlled)
: "${MODEL_S3:?}"                   # pinned model artifacts (staged by prep)
: "${S7_TABLE_S3:?}"                # the alternative-taxonomy table (built by prep)
: "${AWS_REGION:?}"

# staging uses the PINNED boto3 (not an `aws` CLI the image does not install):
# downloads approvals, prep receipt, exact model/tokenizer set, and the S7 table,
# verifying every declared digest and creating no unregistered file
python "$PKG/exec/stage_main.py" \
    --region "$AWS_REGION" \
    --execution-approval-s3 "$EXECUTION_APPROVAL_S3" \
    --prep-approval-s3 "$PREP_APPROVAL_S3" \
    --prep-receipt-s3 "$PREP_RECEIPT_S3" \
    --model-s3 "$MODEL_S3" \
    --s7-table-s3 "$S7_TABLE_S3" \
    --detached-dir /campaign/detached \
    --package-root "$PKG"

# the watchdog runs as a SEPARATE process so termination never depends on the
# driver reaching its own finally block. It reads the SIGNED per-job cap from
# watchdog_config.json (written by the driver after approval verification) and
# will not terminate before the first heartbeat during the startup grace.
python "$PKG/exec/watchdog_main.py" \
    --mode REAL \
    --heartbeat "/campaign/results/$CAMPAIGN_ID/heartbeat.json" \
    --evidence "/campaign/results/$CAMPAIGN_ID" \
    --config "/campaign/results/$CAMPAIGN_ID/watchdog_config.json" \
    --startup-grace-seconds 900 &

exec python "$PKG/exec/launcher.py" \
    --mode REAL \
    --package-root "$PKG" \
    --campaign-id "$CAMPAIGN_ID" \
    --approval /campaign/detached/execution_approval.json \
    --prep-approval /campaign/detached/container_prep_approval.json \
    --prep-receipt /campaign/detached/container_prep_receipt.json \
    --evidence-root "/campaign/results/$CAMPAIGN_ID"
