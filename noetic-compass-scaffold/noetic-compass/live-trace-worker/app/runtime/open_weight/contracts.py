"""Closed status vocabulary for the local open-weight engineering boundary."""

CAPTURE_SCHEMA = "cas_open_weight_trajectory_capture.v1"
CAPTURE_STATUS = "REAL_MODEL_FORWARD_ENGINEERING_CAPTURE_COMPLETED"
PACKET_ELIGIBILITY = "NOT_PACKET_ELIGIBLE"
SCIENTIFIC_STATUS = "NOT_A_SCIENTIFIC_EXPERIMENT_RESULT"
TENSOR_SCHEMA = "cas_open_weight_trajectory_tensors.v1"
RECEIPT_SCHEMA = "cas_open_weight_trajectory_receipt.v1"

OBSERVATION_CLAIM_BOUNDARY = (
    "This receipt proves a local byte-attested engineering capture only. "
    "It does not prove a detector, causal hypothesis, safety property, "
    "external custody, independent replication, or Evidence Packet."
)
RECEIPT_CLAIM_BOUNDARY = (
    "Create-once local integrity receipt. The self-hash is not a signature "
    "or external timestamp and does not establish scientific correctness."
)
ADAPTER_BINDING_STATUS = (
    "EXACT_SOURCE_SNAPSHOT_PLAN_SCHEMA_IDENTITY_AND_HOOK_PATHS_VERIFIED"
)
ADAPTER_CLAIM_BOUNDARY = (
    "Executable hook binding only. It is not scientific validation, "
    "detector evidence, or execution authority."
)
