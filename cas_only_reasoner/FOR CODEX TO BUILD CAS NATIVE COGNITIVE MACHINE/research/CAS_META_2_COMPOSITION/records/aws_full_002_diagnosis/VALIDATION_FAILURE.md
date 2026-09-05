# First diagnosis receipt is invalid

Post-write validation found that the receipt's self-digest does not survive a
JSON load/save round trip. Numeric histogram keys sort numerically in memory but
become strings in stored JSON. This changed their canonical ordering.

The data counts matched the earlier independent diagnosis. The error concerns
the diagnosis receipt's own serialization, not the inspected AWS evidence.
The original output is preserved and must not be treated as a valid receipt.

The corrected run is in the sibling `aws_full_002_diagnosis_v2` directory.
