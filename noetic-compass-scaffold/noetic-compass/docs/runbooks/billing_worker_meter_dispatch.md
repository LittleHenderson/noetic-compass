# Trusted worker metering and Stripe dispatch

This runbook describes the dark-by-default implementation. It does not prove a
live Stripe invoice, authorize a charge, or close customer-production billing
`ACCEPT`. Keep both effect switches `false` until the hosted canary and provider
readback are reviewed.

## Safety model

- The live worker is the odometer. It measures only a real CUDA-resident model
  interval, synchronizes the device at both boundaries, and signs a canonical
  receipt.
- The receipt is the tamper-evident trip slip. Its HMAC binds the tenant,
  billing account, logical run attempt, worker, RunPod/provider identity, model,
  accelerator count and milliseconds, time window, issuance time, and nonce.
- The billing outbox is the dispatch tray. It globally binds both the receipt
  digest and semantic measurement identity, so an exact replay is idempotent and
  a newly signed duplicate window is refused.
- Before reservation, a sealed `pending` row must still match the active store
  and provider contract: livemode, meter name and version, usage price, and
  currency. A restart under changed configuration leaves the row untouched for
  review, with no reservation and no provider contact.
- `delivery_uncertain` is the quarantine shelf. The dispatcher writes that state
  before contacting Stripe. A timeout, cancellation, crash, invalid response, or
  acknowledgement-write failure never returns the row to `pending`.
- The Stripe Meter Event `identifier` is deterministic and is also supplied as
  the HTTP idempotency key. The adapter sets per-request
  `max_network_retries=0`; there is one provider call for one durable
  reservation. Bounded retries apply only to candidate reads before any provider
  dispatch.

## API configuration

The legacy lane declares provider slots in repository-root `render.yaml`, but
those slots do not configure the isolated customer service. The customer
Blueprint currently pins `NC_BILLING_PROVIDER=null` and deliberately declares
no Stripe slots. Customer billing therefore remains `OPEN`; a future protected
`render.customer.yaml` change must add the exact customer-only provider slots
and pass its own deployment/readback gates before dispatch can be considered.
Keep these switches dark during setup:

```text
NC_BILLING_WORKER_MEASUREMENT_ENABLED=false
NC_BILLING_USAGE_DISPATCH_ENABLED=false
```

Set a cryptographically generated, dedicated HMAC key (at least 32 bytes) and
stable source bindings on the API:

```text
NC_BILLING_WORKER_RECEIPT_HMAC_KEY=<dedicated secret>
NC_BILLING_WORKER_RECEIPT_KEY_ID=<rotation id>
NC_BILLING_WORKER_RECEIPT_ISSUER=<issuer id>
NC_BILLING_WORKER_PROVIDER_ID=<provider/resource id>
NC_BILLING_WORKER_ID=<worker id>
NC_BILLING_WORKER_RECEIPT_MAX_AGE_SECONDS=300
```

The receipt key must not equal the JWT, worker service token, Stripe secret,
webhook secret, provider-reference key, database password, WORM attestation key,
or another authority secret.

## RunPod worker configuration

Set the same source bindings and the same receipt key in the private worker
environment. Do not put them in Git, logs, evidence packets, or chat.

```text
CAS_BILLING_WORKER_RECEIPT_HMAC_KEY=<same dedicated secret>
CAS_BILLING_WORKER_RECEIPT_KEY_ID=<same rotation id>
CAS_BILLING_WORKER_RECEIPT_ISSUER=<same issuer id>
CAS_BILLING_WORKER_PROVIDER_ID=<same provider/resource id>
CAS_BILLING_WORKER_ID=<same worker id>
```

A billing context presented to a demo, CPU-only, unsigned, differently sourced,
or stale worker request fails with HTTP 503. It never falls back to an estimate.

## Dispatcher configuration

These bounds have safe checked-in defaults:

```text
NC_BILLING_USAGE_DISPATCH_INTERVAL_SECONDS=5
NC_BILLING_USAGE_DISPATCH_BATCH_SIZE=25
NC_BILLING_USAGE_DISPATCH_PREFLIGHT_RETRIES=3
```

`NC_BILLING_USAGE_DISPATCH_ENABLED=true` additionally requires accounts,
quotas, Stripe entitlements, reconciliation, trusted worker measurement, the
pinned Stripe SDK/API contract, and all provider configuration to validate at
startup. The dispatcher has no public submit route.

## Enablement order

1. Deploy both code artifacts with measurement and dispatch still `false`.
2. Install matching receipt secrets and exact worker/provider identities.
3. Prove a real CUDA run returns a fresh receipt and creates one `pending`
   outbox row with exact tenant/account/run/worker/provider/model/time binding.
4. Prove exact replay is idempotent and a differently signed duplicate window
   fails closed.
5. In Stripe test mode, enable measurement first, then dispatch. Prove one Meter
   Event, one request receipt, exact quantity readback, and no second call after
   a simulated timeout/restart.
6. Disable the test-mode switches, review evidence, then separately decide the
   live-mode rollout. A live invoice and paid receipt remain required for the
   final accounts/billing `ACCEPT` gate.

Never manually reset a `delivery_uncertain` row to `pending`. Stripe Meter Event
v1 has no exact retrieval endpoint for that event, so an uncertain row requires
provider/invoice reconciliation and human financial review.

Never change the active meter, price, currency, or livemode expecting existing
`pending` rows to migrate automatically. They fail closed and require an
explicit financial review or migration decision.
