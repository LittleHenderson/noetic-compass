#!/usr/bin/env bash
# Gate 1B on-instance bootstrap -- FROZEN (GATE 1A.2 section 4).
# Fail-closed everywhere; every value comes from the detached signed approval.
set -euo pipefail

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

aws s3 cp "$EXECUTION_APPROVAL_S3" /campaign/detached/execution_approval.json
aws s3 cp "$PREP_APPROVAL_S3" /campaign/detached/container_prep_approval.json
aws s3 cp "$PREP_RECEIPT_S3" /campaign/detached/container_prep_receipt.json

# stage the pinned model where exec/campaign_driver._load_frozen_model expects it
mkdir -p /campaign/model
aws s3 sync "$MODEL_S3" /campaign/model

# the watchdog runs as a SEPARATE process so termination never depends on the
# driver reaching its own finally block
python "$PKG/exec/watchdog_main.py" \
    --mode REAL \
    --heartbeat "/campaign/results/$CAMPAIGN_ID/heartbeat.json" \
    --evidence "/campaign/results/$CAMPAIGN_ID" &

exec python "$PKG/exec/launcher.py" \
    --mode REAL \
    --package-root "$PKG" \
    --campaign-id "$CAMPAIGN_ID" \
    --approval /campaign/detached/execution_approval.json \
    --prep-approval /campaign/detached/container_prep_approval.json \
    --prep-receipt /campaign/detached/container_prep_receipt.json \
    --evidence-root "/campaign/results/$CAMPAIGN_ID"
