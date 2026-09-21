# Schema scope
These are proposed CAS Expression Lab envelopes, not existing Helm APIs. Both schema files use JSON Schema draft 2020-12. They establish structural validation only. Fable must implement semantic checks, exact visibility rules, and operation-specific schemas before acceptance.

The complete behavior-pair record is a dataset/custodian artifact. Only `model_input` may reach the predictor, with its nested fields audited for answer leakage. Schema conformity does not establish that an arbitrary context field is safe. Source hashes, split names, target receipts, and structure-family identifiers are not model features by default.

Input/output schemas in an operation contract must be reviewed independently; a permissive schema cannot replace semantics. Unsupported or parameterized operations must be classified before data generation. Validation code must not download external schema URLs at run time.
