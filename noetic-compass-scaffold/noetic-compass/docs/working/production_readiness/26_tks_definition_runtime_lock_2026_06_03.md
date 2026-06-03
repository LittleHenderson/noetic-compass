# TKS Definition Runtime Lock - 2026-06-03

**Status: BUILT and route/probe-enforced.** Customer audit creation now fails
closed unless the packaged TKS definition source and the active probe-bundle
manifest agree on the locked owner-provided definition hash. Frontier/customer
probe specs must also declare that same `definition_sha256`; missing or different
definitions are rejected before work is scheduled.

This is the code-level answer to the failure mode where a future AI agent or
LLM misses the TODO and silently substitutes a fallback taxonomy.

## Locked Definition Source

Packaged app resource:

```text
api/resources/tks_owner_locked_definitions_20260603.json
```

Repo reference copy:

```text
docs/reference/tks_owner_locked_definitions_20260603.json
```

Locked SHA-256:

```text
a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0
```

The file contains the owner-provided TKS `A1-D10` 40 Element definitions and
TKS `1a-7d` 28 Foundation definitions supplied on 2026-06-03.

## Active Probe-Bundle Manifest

```text
api/resources/tks_definition_probe_bundle_manifest.v1.json
```

The manifest declares:

```text
definition_sha256: a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0
probe_status: definition_fixture_locked_no_trained_probe_claim
```

The `probe_status` is intentionally honest: the current manifest locks the
definition source and fixture identity; it does not claim a trained probe bundle
has been verified.

## Runtime Gate

Service:

```text
api/services/cas_harness_tks_definition_lock.py
```

Audit route enforcement:

```text
api/routes/cas_harness_audit.py
```

The route calls the lock before:

- `POST /api/cas-harness/audit/session`
- `POST /api/cas-harness/audit/session/{audit_id}/run`
- `POST /api/cas-harness/audit/distributed/session`

If the packaged definition file is missing, if its SHA-256 does not match the
locked hash, or if the active probe-bundle manifest declares a different
definition hash, the route returns HTTP 503 and refuses the audit.

## Customer Probe Spec Gate

Frontier-scale distributed audits can carry a caller-supplied probe spec. That
spec is now part of the same lock:

```json
"definition_sha256": "a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0"
```

`api/services/cas_harness_probe_compatibility.py` marks the probe
`PROBE_COMPATIBILITY_UNSUPPORTED` unless that value is present and equals the
locked TKS definition hash. The public route converts that into HTTP 422. This
closes the remaining bypass where the app had the right definitions but a
caller-supplied probe could omit which vocabulary it was trained/evaluated on.

## Tests

```text
pytest -q tests\test_tks_definition_lock.py tests\test_definition_locked_tks_fixture.py
10 passed

pytest -q tests\test_cas_harness_audit.py tests\test_cas_harness_distributed_audits.py
98 passed

pytest -q tests\test_cas_harness_probe_compatibility.py tests\test_tks_definition_lock.py tests\test_definition_locked_tks_fixture.py
34 passed
```

The lock tests prove:

- the packaged definitions match the hardcoded locked hash;
- the active manifest declares that same hash;
- a manifest with the wrong definition hash is rejected;
- a caller-supplied probe spec without the locked `definition_sha256` is rejected;
- a caller-supplied probe spec with a wrong `definition_sha256` is rejected;
- audit session creation refuses when the lock fails;
- distributed audit creation refuses when the lock fails;
- the fixture generator/loader still preserves `A1-D10` and `1a-7d`.

## Claim Boundary

This prevents wrong definitions from being used at audit creation or in a
customer-supplied probe spec. It does not prove that a trained production probe
exists yet. A future trained probe bundle must carry this same
`definition_sha256`, plus its own model/probe artifact hashes, before any
customer-facing audit can honestly rely on it.
