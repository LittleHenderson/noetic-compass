# 11 — Multi-Host State Substrate

**Workstream:** 11 (state-substrate extension) · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the durable run/worker/tenant ledger (`api/services/production/state_substrate/`) — taking the
`StateStore` Protocol from *durable-on-one-host* (SQLite) to *durable-across-hosts* (Postgres / Redis) **behind the
identical interface**.

> Scope boundary up front: this workstream does **not** redefine the `StateStore` Protocol — that interface is
> **locked** (`interface.py`) and its semantics are pinned by `run_state_store_contract` (`conformance.py`). 11 owns
> exactly one thing: *how a multi-host backend realizes the SAME guarantees when N API hosts share one store, and the
> distributed-systems hazards that appear only once state is shared.* Code written against the Protocol does not change.
> When in doubt: workstream 10 migrates the live global dicts onto the substrate; 04 builds a durable *queue* on top of
> the same kind of backend; 11 is the answer to "what does the durable layer **underneath** all of them actually have to
> be, across hosts, without lying about it?"

---

## 1. Current state / where the ladder stops

The substrate already ships a real, tested durability ladder. `interface.py` frames it explicitly:
**in-memory (non-durable) → SQLite (durable, single host) → Postgres/Redis (durable, multi-host)**. The same
`StateStore` Protocol — `put`/`get`/`list`/`delete` with optimistic-concurrency `expected_version`, and
`acquire_lease`/`renew_lease`/`release_lease`/`get_lease` single-holder expiring leases — is implemented at every rung.

### 1.1 The Protocol semantics are already pinned

`run_state_store_contract(make_store)` (`conformance.py:41-56`) is an *executable specification*, not a docstring. It
exercises, against any backend factory:

- **record round-trip + the version-0→1 promotion** (`_records_roundtrip` `:58-93`): a freshly built record is
  `version == 0`; the first `put(expected_version=0)` promotes it to `1`; `created_at` is immutable across updates;
  `updated_at` moves forward; the traceability envelope (`source`, `trace_id`, `parent_ids`) survives the round-trip;
  `list` returns the latest version in a stable order.
- **fail-closed tenant scoping** (`_tenant_scoping_fails_closed` `:96-130`): same `record_id` under two tenants are two
  independent rows; a cross-tenant `get` returns `None` (indistinguishable from absent — tenant C must not even learn the
  row exists); `list` is tenant-scoped; a cross-tenant `delete` raises `TenantScopeViolation` (loud on mutate, silent on
  read).
- **optimistic concurrency** (`_optimistic_concurrency` `:133-166`): re-creating an existing record at
  `expected_version=0` is a `VersionConflict`; two readers on version 1 race, **first writer wins**, the loser gets a
  `VersionConflict` whose `.actual` tells it the version to rebase onto.
- **version-checked delete** (`_delete_semantics` `:169-189`): wrong version → `VersionConflict`, row survives; correct
  version → gone.
- **the full lease lifecycle** (`_lease_single_holder`/`_lease_expiry`/`_lease_renew_release` `:192-274`): single live
  holder; a second holder gets `LeaseHeld`; same-holder re-acquire is idempotent and **mints a fresh token**; expiry is
  decided by injected `now` (`>=`); an expired lease reads as absent and is claimable by anyone; `renew` preserves the
  token but raises `LeaseExpired` once lapsed and `UnknownLease` for a token never issued; `release` frees the resource
  and is an idempotent no-op on a second call.

Both `InMemoryStateStore` and the SQLite backend (per `__init__.py:28-34`, SQLite proves survival across a close/reopen
of the same file) pass this *same* suite. **That is the whole leverage of this workstream:** the behaviour is already
nailed down by tests. Multi-host is not "design new semantics" — it is "preserve these *exact* semantics when N hosts
share one store, and earn no durability/mutual-exclusion claim a backend cannot actually keep."

### 1.2 Where the ladder stops: SQLite is one file on one host

SQLite is genuinely durable (WAL + fsync) — but a SQLite database is **a file on one host's filesystem**. Two API hosts
run two processes against two *different* files. Concretely:

- Host A's `put` writes a run record into `/data/host-a/substrate.db`. Host B's `get` for the same
  `(tenant_id, kind, record_id)` reads `/data/host-b/substrate.db` and returns `None`. **Host B cannot see Host A's
  records.** There is no shared row.
- Host A's `acquire_lease("t", "shard-7", holder="worker-a", ...)` writes a lease row into Host A's file. Host B's
  `acquire_lease("t", "shard-7", holder="worker-b", ...)` consults Host B's file, finds no live holder, and **succeeds.**
  Both hosts now believe they hold the *same* lease. The single-holder guarantee the contract pins
  (`_lease_single_holder` `:192-222`) holds *within* one file and is silently void *across* files.

SQLite-on-a-shared-network-filesystem (NFS/EFS) is **not** a fix: SQLite's locking is explicitly documented as unreliable
over network filesystems, and `appendfsync`-style durability assumptions break when the filesystem lies about fsync. The
honest statement is: **SQLite is the correct top of the *single-host* ladder, and the wrong tool the instant a second host
appears.** Multi-host needs a backend whose single source of truth is reachable by every host — a database server
(Postgres) or a shared in-memory store (Redis), not a file.

### 1.3 Honest one-line summary

> Today the substrate is durable on **one** host: in-memory and SQLite both pass `run_state_store_contract`, so the
> Protocol semantics (version checks, fail-closed tenancy, single-holder leases) are *pinned*. But each host owns its own
> SQLite file, so a second API host sees neither the first's **records** nor its **leases**. The Protocol does not change
> for multi-host; the **backend** does — and only a backend whose store is shared by all hosts can keep the contract's
> guarantees across them.

---

## 2. The gap

The delta between §1 and "durable across hosts behind the unchanged Protocol" — each item names the concrete failure it
closes:

1. **Survive host loss.** Single-host SQLite ties the run/worker/lease state to one machine's disk. Lose the host (per
   project memory — *"pod can disappear"*) and the state is unreachable until that exact host returns. **Closes:** a dead
   API host stranding every run it coordinated. A replicated Postgres (or AOF+replicated Redis) keeps the state alive on
   another node.
2. **Let multiple schedulers / API replicas coordinate.** 03's Phase D needs >1 orchestrator; 04 needs >1 lease holder
   without double-delivery; 06 needs >1 API replica sharing tenant state. With per-host SQLite files there is no shared
   row to compare-and-set against, so two replicas cannot safely race. **Closes:** two replicas both winning the same
   lease / both creating the same record because they consulted different files.
3. **A globally-consistent view.** `list_distributed_audits`-style reads (06 §1.3) must return *the tenant's* runs, not
   "the runs this host happens to hold." With sharded-by-file state, a tenant's view depends on which host answered.
   **Closes:** a control-plane read whose result is a function of routing luck rather than of the actual ledger.
4. **One enforcement point for optimistic concurrency across hosts.** The contract's first-writer-wins
   (`_optimistic_concurrency` `:133-166`) is only meaningful if *both* writers compare-and-set against the *same* stored
   version. **Closes:** the lost-update that single-host concurrency control cannot prevent once the writers are on
   different hosts.

None of these are interface changes. They are all "the store the Protocol talks to must be the *same* store for every
host, and must enforce the contract's compare-and-set atomically across concurrent callers."

---

## 3. Postgres backend design

Postgres is the natural multi-host record-of-truth: a single logical server every API host connects to, with real
transactions, real durability config, and `UPDATE … WHERE version=?` giving compare-and-set for free. Each Protocol
method maps cleanly.

### 3.1 Records: schema + optimistic concurrency

One table keyed by the contract's identity triple `(tenant_id, kind, record_id)`, carrying the version and the full
traceability envelope:

```sql
CREATE TABLE ledger_records (
    tenant_id   text        NOT NULL,
    kind        text        NOT NULL,
    record_id   text        NOT NULL,
    version     bigint      NOT NULL,           -- monotonic; the optimistic-concurrency guard
    created_at  timestamptz NOT NULL,           -- immutable after first insert
    updated_at  timestamptz NOT NULL,
    payload     jsonb       NOT NULL,           -- opaque mapping; the substrate never interprets it
    parent_ids  text[]      NOT NULL DEFAULT '{}',
    source      text        NOT NULL DEFAULT 'unknown',
    trace_id    text,
    PRIMARY KEY (tenant_id, kind, record_id)
);
CREATE INDEX ledger_records_list_idx ON ledger_records (tenant_id, kind, created_at, record_id);
```

**`put` — create (`expected_version == 0`):** an `INSERT`. The composite primary key makes a duplicate create fail with a
unique-violation (`SQLSTATE 23505`); the backend **translates that unique-violation into `VersionConflict`** (expected 0,
actual = the stored version, fetched in the same transaction). This is exactly the contract's "re-creating an existing
record must raise VersionConflict" (`_optimistic_concurrency` `:142-151`).

```sql
INSERT INTO ledger_records
    (tenant_id, kind, record_id, version, created_at, updated_at, payload, parent_ids, source, trace_id)
VALUES (:tenant, :kind, :record_id, 1, :created_at, :updated_at, :payload, :parent_ids, :source, :trace_id);
-- 23505 unique_violation  ->  raise VersionConflict(expected=0, actual=<stored version>)
```

**`put` — update (`expected_version == N > 0`):** a single conditional `UPDATE`. The `WHERE … AND version = :expected`
clause is the compare-and-set; **0 rows affected ⇒ `VersionConflict`.** `created_at` is never written on update
(immutable, per `_records_roundtrip` `:86`); `version` is bumped server-side so monotonicity is the store's property, not
the caller's.

```sql
UPDATE ledger_records
   SET version = version + 1,
       payload = :payload,
       updated_at = :updated_at,
       parent_ids = :parent_ids,
       source = :source,
       trace_id = :trace_id
 WHERE tenant_id = :tenant AND kind = :kind AND record_id = :record_id
   AND version = :expected
RETURNING version, created_at, updated_at;
```

If `RETURNING` yields a row, that row (with its new `version`) is returned. If it yields **nothing**, the backend issues a
follow-up `SELECT version` for the key: a row present means a genuine version mismatch (`VersionConflict(expected,
actual)`); no row means the record was deleted out from under the caller (also `VersionConflict(expected, actual=None)` —
the contract carries `actual: Optional[Version]`, so `None` is a legal "store holds nothing"). **0-rows-affected is the
single decision point**, and it never silently no-ops a lost update.

**`get`:** `SELECT … WHERE tenant_id=? AND kind=? AND record_id=?`. Tenant is **in the WHERE clause**, so a cross-tenant
read returns no row → the backend returns `None`. Fail-closed by construction (the `require_tenant` helper
`interface.py:253-265` becomes redundant defence-in-depth, not the primary guard). This is `_tenant_scoping_fails_closed`
(`:114-116`) realized in SQL.

**`list`:** `SELECT … WHERE tenant_id=? AND kind=? ORDER BY created_at, record_id`. The `ORDER BY (created_at, record_id)`
matches the contract's stable order exactly (`_records_roundtrip` `:89-91`); the supporting index above serves it. Tenant
scoping is again in the WHERE clause — `list` for a tenant with no rows returns `()` (`_tenant_scoping_fails_closed`
`:120`).

**`delete`:** `DELETE … WHERE tenant_id=? AND kind=? AND record_id=? AND version=:expected`. **0 rows affected** triggers
the same disambiguation as update: a row under another tenant ⇒ `TenantScopeViolation` (the contract's loud cross-tenant
mutate, `_tenant_scoping_fails_closed` `:122-128`); a row under this tenant at a different version ⇒ `VersionConflict`
(`_delete_semantics` `:176-183`); no row at all ⇒ idempotent success or `VersionConflict` depending on the read — the
backend reads-then-decides inside one transaction so the answer is consistent.

### 3.2 Leases: schema + the conditional-reclaim insert

A second table, keyed by the contract's `(tenant_id, resource_id)` lease identity, carrying the opaque `token`, holder,
and absolute `expires_at`:

```sql
CREATE TABLE leases (
    tenant_id    text        NOT NULL,
    resource_id  text        NOT NULL,
    holder       text        NOT NULL,
    token        text        NOT NULL,          -- opaque ownership proof (today: random uuid4 — see §5.2)
    acquired_at  timestamptz NOT NULL,
    expires_at   timestamptz NOT NULL,          -- ABSOLUTE; expiry decided by comparison to server now()
    PRIMARY KEY (tenant_id, resource_id),
    UNIQUE (token)
);
```

**`acquire_lease` — the heart of the multi-host lease.** A live lease must block a different holder (`LeaseHeld`); an
expired lease must be reclaimable by anyone; the same holder re-acquiring must succeed with a **fresh token** (the
contract requires `again.token != lease.token`, `_lease_single_holder` `:214`). A conditional `INSERT … ON CONFLICT DO
UPDATE … WHERE` expresses this in one atomic statement, with **the database's `now()` as the time authority** (never the
caller's clock — see §5.1):

```sql
INSERT INTO leases (tenant_id, resource_id, holder, token, acquired_at, expires_at)
VALUES (:tenant, :resource, :holder, :new_token, now(), now() + (:ttl_seconds || ' seconds')::interval)
ON CONFLICT (tenant_id, resource_id) DO UPDATE
   SET holder      = EXCLUDED.holder,
       token       = EXCLUDED.token,
       acquired_at = EXCLUDED.acquired_at,
       expires_at  = EXCLUDED.expires_at
 WHERE leases.expires_at <= now()                       -- existing lease is dead: reclaim it
    OR leases.holder      = EXCLUDED.holder              -- same holder re-acquiring: idempotent extend
RETURNING holder, token, acquired_at, expires_at;
```

- **`RETURNING` yields a row** → the lease is ours (fresh insert, reclaimed-expired, or same-holder extend). The fresh
  `token` satisfies the "fresh token on re-acquire" contract.
- **`RETURNING` yields nothing** → the `ON CONFLICT` `WHERE` was false, i.e. a *different* holder owns a *still-live*
  lease. The backend then `SELECT holder FROM leases WHERE tenant_id=? AND resource_id=?` and raises
  **`LeaseHeld(resource_id, holder=<that holder>)`** — carrying the conflicting holder so the loser can log who it lost to
  without a second round-trip (matching `LeaseHeld`'s constructor and `_lease_single_holder` `:204-209`).

This is one statement, atomic under Postgres's row-level concurrency control: two hosts racing `acquire_lease` on the same
`(tenant, resource)` serialize on the conflicting row, and **exactly one** wins the `DO UPDATE` predicate. That is the
single-holder guarantee preserved across hosts — *modulo the dead-but-not-expired-holder hazard of §5.2, which no
acquire-time SQL can close and which fencing tokens address.*

**`renew_lease`:** `UPDATE leases SET expires_at = now() + ttl WHERE token=:token AND expires_at > now() RETURNING …`.
The `expires_at > now()` clause is what makes renew refuse a lapsed lease. Disambiguate 0-rows-affected by token lookup: a
row exists for that token but is expired ⇒ `LeaseExpired` (renew never resurrects the dead — `_lease_renew_release`
`:260-266`); no row for that token at all ⇒ `UnknownLease` (`:252-258`). Renew **preserves the token** (`:248-249`), so no
new token is minted here.

**`release_lease`:** `DELETE FROM leases WHERE token=:token`. Whether 1 or 0 rows are deleted, return `None` — releasing
an already-released (or never-issued) token is an idempotent no-op (`_lease_renew_release` `:269-272`).

**`get_lease`:** `SELECT … WHERE tenant_id=? AND resource_id=? AND expires_at > now()` — a lease past its `expires_at`
reads as **absent** (`None`), exactly as `_lease_expiry` (`:231-233`) requires. Tenant scoping is in the WHERE clause, so
another tenant's same-named resource is invisible (`_lease_single_holder` `:217-220`).

> **A note on `now`.** The contract threads an injected `now` through the lease methods so tests can drive expiry without
> sleeping (`conformance.py:17-19`). The Postgres backend honours that parameter *for test determinism* but, in
> production, the **database's** `now()` is the authority on the conflict/renew predicates — the injected `now` and the
> server clock must not both be load-bearing. The clean rule: tests inject `now`; production passes `None` and lets the
> single DB clock stamp every lease. §5.1 explains why a single server clock is the only honest time source across hosts.

### 3.3 SELECT FOR UPDATE / advisory locks — the alternative, and the tradeoff

The conditional-`INSERT … ON CONFLICT` above does the read-modify-write in **one** statement, which is why it is
preferred. Two alternatives exist for the same RMW:

- **`SELECT … FOR UPDATE` then conditional `UPDATE`/`INSERT`** inside an explicit transaction. This locks the lease row
  (or the gap, with predicate locking) so the decision is made on a pinned row. It is more flexible (arbitrary logic
  between read and write) but is **two round-trips and a held row lock** for the duration — more lock contention under a
  hot resource, and a forgotten `COMMIT`/`ROLLBACK` holds the lock. 04 uses the sibling pattern
  `SELECT … FOR UPDATE SKIP LOCKED` for *queue* claims (`04_…md §3 Phase C`, `§7 Q2`); a lease is a *named* single row, so
  it does not need `SKIP LOCKED` (there is nothing to skip to), making the single-statement `ON CONFLICT` form the better
  fit here.
- **Postgres advisory locks** (`pg_advisory_xact_lock(hashtext(tenant||resource))`) serialize acquirers on a hashed key
  without touching the row. Cheap and lock-free of the data, but: hash collisions serialize *unrelated* resources, the
  lock is invisible to anyone not using the same convention, and it adds a coordination primitive the contract does not
  need. **Reserve advisory locks for a future hot-path optimization, not the baseline.**

Baseline recommendation: **single-statement `INSERT … ON CONFLICT DO UPDATE … WHERE` for both records and leases.** It is
atomic, one round-trip, holds no lock across application code, and maps directly onto the contract's compare-and-set.

### 3.4 Durability / HA — what makes "durable across hosts" honest

A Postgres backend may claim *durable across hosts* **only** when the configuration actually earns it. The honest
prerequisites:

- **`synchronous_commit = on`** (the default) so a committed `put`/`acquire_lease` is flushed to WAL before the call
  returns. With `synchronous_commit = off`, a crash can lose the last few committed transactions — that backend is
  durable-ish, not durable, and must not claim the stronger word.
- **Replication for host-loss survival.** A *single* Postgres instance survives its own restart but **not loss of its
  host**. To claim "survives host loss," configure a standby and **`synchronous_standby_names`** with
  `synchronous_commit = remote_apply` (or at least `on`), so a commit is acknowledged only after a replica has it. Only
  then is the data alive when the primary's host dies. Asynchronous replication is a *recovery convenience*, not a
  host-loss-survival guarantee (a window of un-replicated commits is lost on failover) — say so, do not round it up.
- **Connection routing on failover.** Hosts must reconnect to the promoted primary (a managed Postgres endpoint or a
  pooler that follows the primary). This is operational, not a data property, but it gates whether "the state is still
  there" translates to "the hosts can still reach it."

The truthful claim table in §6 encodes this: **Postgres (configured)** = synchronous commit + synchronous replication +
failover routing. Anything less earns a weaker row.

---

## 4. Redis backend design

Redis is an excellent **lease/coordination** primitive and an awkward, caveat-laden **record-of-truth**. This section maps
the Protocol to Redis honestly — the clean parts and the friction — and the durability caveat is the load-bearing honesty
content of the whole workstream.

### 4.1 Leases: the natural fit

A single-holder expiring lease is *exactly* what `SET key value NX PX ttl` provides. This is the Redlock token pattern:

```
acquire:  SET  lease:{tenant}:{resource}  {holder_token}  NX  PX {ttl_ms}
```

- `NX` = set only if absent → the first acquirer wins; a second acquirer on a live key gets a nil reply → the backend
  `GET`s the current holder and raises **`LeaseHeld`**.
- `PX {ttl_ms}` = Redis expires the key itself, so a dead holder's lease vanishes with **no reaper** — expiry is the
  server's job. (`get_lease` is a `GET`; a missing key = absent = `None`, matching `_lease_expiry` `:231-233`.)
- Re-acquire by the same holder mints a **fresh token** (a new `SET` value) — satisfying `_lease_single_holder` `:214`.

`renew` and `release` must be **token-checked**, and Redis has no native compare-and-act, so each is a tiny Lua script run
atomically server-side:

```lua
-- renew: compare-and-extend (preserve token; refuse if not holder or already gone)
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('PEXPIRE', KEYS[1], ARGV[2])     -- 1 = extended
else
    return 0                                            -- token mismatch or key expired
end
```

```lua
-- release: compare-and-delete (only the token holder may release)
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0                                            -- not ours / already gone: idempotent no-op
end
```

`renew` maps a `0` return to `UnknownLease` vs `LeaseExpired` by a follow-up `EXISTS` (key gone ⇒ expired/unknown;
present-but-different-token ⇒ not ours). `release` returning `0` is an idempotent no-op (`_lease_renew_release`
`:269-272`). This is a clean, well-trodden fit — the compare-and-extend / compare-and-delete via Lua **is** the Redlock
single-node token discipline, and it preserves the contract's lease semantics faithfully.

> Redlock-across-multiple-Redis-nodes is explicitly **out of scope and not recommended here.** Multi-node Redlock has
> contested correctness under the same clock-skew / pause hazards as §5, and adding it would trade one honest primitive
> for a disputed one. A single Redis (with AOF + replication, §4.3) as the *lease* layer is the honest recommendation.

### 4.2 Records + optimistic concurrency: the friction

Records are where Redis is **harder than Postgres**, and the doc says so plainly. Redis has no `UPDATE … WHERE version=?`;
the contract's compare-and-set must be built by hand. Two honest options, both with more friction than Postgres's one
statement:

- **`WATCH`/`MULTI`/`EXEC` optimistic transaction.** `WATCH` the record key, `GET` and parse its current version, compare
  to `expected_version`, then `MULTI`/`EXEC` the write. If another client touched the key between `WATCH` and `EXEC`, the
  `EXEC` returns nil and the client retries the whole read-compare-write. This is genuine optimistic concurrency, but it
  pushes the retry loop into the backend and means a hot record can livelock under contention.
- **A Lua compare-version-and-set script** (preferred): one server-side atomic script does GET-version, compare, and
  conditional HSET/SET, returning a sentinel on mismatch the backend maps to `VersionConflict`:

```lua
-- put-if-version: atomic compare-version-and-set; returns new version, or -1 on conflict
local cur = redis.call('HGET', KEYS[1], 'version')
if (cur == false and tonumber(ARGV[1]) == 0)            -- create: expected 0, key absent
   or (cur ~= false and tonumber(cur) == tonumber(ARGV[1])) then   -- update: versions match
    local nextv = tonumber(ARGV[1]) + 1
    redis.call('HSET', KEYS[1], 'version', nextv, 'payload', ARGV[2], 'updated_at', ARGV[3],
               'created_at', ARGV[4], 'source', ARGV[5], 'trace_id', ARGV[6])
    return nextv
else
    return -1                                            -- mismatch -> VersionConflict(expected, actual=cur)
end
```

Records are stored as Redis **hashes** keyed `record:{tenant}:{kind}:{record_id}` (tenant in the key = fail-closed scoping
on `get`). But `list(tenant, kind)` is the real friction: Redis has no `ORDER BY`. Serving the contract's stable
`(created_at, record_id)` order (`_records_roundtrip` `:89-91`) requires a **secondary index** — a per-`(tenant, kind)`
sorted set (`ZADD idx:{tenant}:{kind} <created_at_score> <record_id>`) maintained **in the same Lua script** as the write,
so the index never diverges from the data. That is real machinery the relational backend gets for free from an `ORDER BY`
and an index. `SCAN`-based listing is **not** acceptable: it has no stable order, can miss or duplicate keys under
concurrent writes, and would violate the contract's `list` ordering assertion.

**Verdict on Redis-as-record-store: workable but high-friction.** Every record operation that Postgres does in one
declarative statement, Redis does as a hand-written Lua script plus a manually-maintained secondary index. It is more code,
more places for the index to drift, and a harder correctness story.

### 4.3 Durability caveat (the load-bearing honesty point)

**Redis is an in-memory store. Durability is not a default; it is a configuration you must turn on and then may claim only
to the strength it actually provides.**

- **No persistence (default-ish / cache mode):** data lives only in RAM. A restart loses **everything** — every record,
  every lease. A Redis-only substrate in this mode that called itself "durable" would be **the exact dishonesty this whole
  program exists to refuse** (`00_index.md:24-34`; `state_substrate/__init__.py:36-38` — "calling the product 'durable'
  would be the same dishonesty this whole program exists to refuse"). It may claim *behaviourally complete, non-durable* —
  no more — and it is then strictly worse than SQLite, which at least survives its own restart.
- **AOF (Append-Only File):** Redis logs every write to disk.
  - `appendfsync everysec` — fsync once per second. Survives a restart but with a **window of up to ~1 second of
    acknowledged writes lost** on a crash. This is durable-ish; the honest label is "durable with a ≤1s loss window," not
    "durable."
  - `appendfsync always` — fsync every write before acknowledging. This is genuinely durable on that node (at a real
    throughput cost), comparable to Postgres `synchronous_commit = on`.
  - RDB snapshots alone (point-in-time dumps) are **not** write-durable — everything since the last snapshot is lost on a
    crash. RDB is a backup, not a durability guarantee.
- **Replication for host-loss survival:** as with Postgres, a single AOF-durable Redis survives its *own* restart but not
  loss of its *host*. Surviving host loss requires a replica, and — critically — Redis replication is **asynchronous by
  default**, so a failover can lose the un-replicated tail. `WAIT numreplicas timeout` can force acknowledgement from N
  replicas before returning, tightening the guarantee at a latency cost. Without `WAIT` (or equivalent), "survives host
  loss" is a recovery convenience with a loss window, and must be labelled as such.

**Recommendation (the honest architecture):** use **Redis as the lease / coordination layer** (where `SET NX PX` + Lua
token discipline is a genuinely clean fit and the data is *ephemeral by nature* — a lost lease just expires and is
re-acquired) and **Postgres as the durable record-of-truth** (where `UPDATE … WHERE version=?` and real transactional
durability fit the versioned ledger). A Redis-*only* store can be honest **only** with `appendfsync always` + synchronous
replication, and even then it pays for record `list`/optimistic-concurrency with hand-built machinery Postgres gives for
free. **Splitting leases (Redis) from records (Postgres) plays each backend to its strength** — and is called out as an
open question in §7 because it means two backends behind what is *logically* one `StateStore`.

---

## 5. Distributed-systems hazards (the heart of the doc)

Sharing state across hosts surfaces failure modes that **simply do not exist** on one host. The contract's semantics are
necessary but **not sufficient**: a backend can pass every `run_state_store_contract` assertion (which run single-process,
single-clock, no concurrency) and still be unsafe across hosts. These hazards are where the real engineering — and the
real honesty — lives.

### 5.1 Clock skew and absolute lease expiry

`Lease.expires_at` is an **absolute** UTC timestamp, and `is_expired(now=)` decides expiry by comparing it to a `now`
(`interface.py:242-250`). On one host with one clock that is unambiguous. **Across hosts with skewed clocks it is not:** if
Host A stamps `expires_at = 12:00:30` using its clock, and Host B's clock reads 12:00:31 when A's clock reads 12:00:29,
Host B will consider the lease expired while A still considers it live. Both hosts comparing the *same* absolute timestamp
to *different* clocks is a split decision.

Mitigations, in order of honesty:

- **Server-authoritative time — the load-bearing rule.** Let the *store* stamp `now` and `expires_at`, never the calling
  hosts. Postgres `now()` (§3.2) and Redis's server-side `PX` (§4.1) mean expiry is decided against **one** clock — the
  store's — no matter how many hosts call in. This collapses N host-clocks down to one, eliminating the skew *between
  callers*. It does not eliminate the clock as a hazard (the store's clock can still jump), but it removes the
  *cross-host* ambiguity, which is the dominant risk. **The injected-`now` contract parameter is for test determinism;
  production must pass `None` and let the single store clock govern** (§3.2 note).
- **Bounded-skew assumption, stated explicitly.** Even with server-authoritative time, processing and network delays mean
  a host's *belief* about a lease lags reality. The honest design assumes a bounded clock skew δ (enforced operationally
  by NTP/chrony) and a bounded processing time, and **never** treats a lease as safely-held right up to its `expires_at`.
- **TTL > max plausible skew + processing + renewal interval.** A lease TTL must comfortably exceed (max skew δ) + (time
  to do the protected work or renew) + (network round-trip). A 2-second lease across hosts with 500ms of plausible skew
  and a 1-second work unit is a recipe for two hosts both believing they hold it during the overlap. TTLs are a safety
  margin, not a tight bound — size them generously and renew well before expiry.

Clock skew alone, however, is **not** the worst case. Even with perfect clocks, a holder can stall.

### 5.2 The dead-but-not-expired holder, split-brain, and FENCING TOKENS — the single most important hazard

This is the central hazard of the entire workstream.

**The scenario:** Host A acquires a lease on `shard-7` with a 30s TTL. Host A then **stalls** — a stop-the-world GC pause,
a long disk stall, a VM live-migration freeze, a network partition from the resource but not from nothing. Its lease lapses
at +30s. The store (correctly) lets Host B reclaim the lease at +31s; B is now the legitimate holder. At +35s Host A
**wakes up**, still believing it holds the lease (it has no way to know time passed), and proceeds to act on `shard-7` —
write a record, commit a result, mutate the protected resource. **Now two hosts act as the single holder.** No
acquire-time SQL or `SET NX` can prevent this: the lease *was* validly handed to B, and A's belief is simply stale. The
mutual-exclusion guarantee the contract pins (`_lease_single_holder`) is **silently violated** by a holder that pauses
across its own expiry.

**Why the current token does not save us.** `Lease.token` is, today, a **random uuid** (`interface.py` mints it via
`uuid.uuid4()`; the conformance suite only requires that re-acquire produces a *different* token —
`_lease_single_holder` `:214`). A random uuid is a perfect **proof of ownership** ("I am the holder who acquired this") but
it is **not monotonic** — it carries no notion of *order*. When stalled Host A wakes with token `uuid-A` and live Host B
holds token `uuid-B`, the protected resource has **no way to tell which token is newer**. Ownership-proof is necessary but
insufficient; what's missing is *recency*.

**The fix: a monotonic FENCING TOKEN.** Pair (or evolve) the lease `token` with a **monotonically increasing fencing
token** issued at acquire time. Every successful `acquire_lease` gets a strictly larger fencing number than every prior
acquisition of that resource:

- **Postgres:** a per-resource (or global) `BIGINT` from a Postgres **sequence** (`nextval(...)`), or simply the lease
  row's ever-incrementing `version`-style counter, stamped into the lease at acquire time.
- **Redis:** an `INCR fence:{tenant}:{resource}` in the same acquire path, returning a strictly increasing integer.

The fencing token rides along with the lease (opaque to the holder, but **monotone** by construction). Then — and this is
the part that actually closes the hazard — **the protected resource must reject any operation carrying a fencing token
lower than the highest it has already seen.** When stalled Host A wakes and tries to write with fence `42`, but live Host
B already wrote with fence `43`, the resource (the DB row, the storage layer, the WORM writer) **rejects A's fence-42
write as stale.** A's staleness is caught at the *point of effect*, not at the lease layer — which is the only place it
*can* be caught, because the lease layer already (correctly) moved on.

> The canonical statement (Kleppmann's *"How to do distributed locking"*): a lock/lease service alone cannot prevent a
> paused holder from acting after its lease lapses; **only a fencing token checked by the protected resource** can. This is
> a property of the *resource*, not of the lock.

**Interface compatibility — this is an additive strengthening, not a Protocol change.** The locked `StateStore` Protocol
and the `Lease` dataclass do not need a breaking change to gain this:

- The `token` field is **opaque** to all callers (the contract only ever asserts equality/inequality of tokens, never
  structure). So the token can *carry* or be *paired with* a monotonic fence without any caller noticing — the guarantee
  strengthens while the surface stays identical.
- The honest framing for the eventual change: either (a) the fence travels as a second opaque field alongside `token`
  (e.g. a `fence: int` added to `Lease`, ignored by code that doesn't fence, consumed by resources that do), or (b)
  `acquire_lease` begins minting a token that *embeds* a monotone component. Both are interface-compatible extensions:
  existing code keeps working; resources that opt into fencing gain real protection. **The current random-uuid token is
  good for ownership proof and NOT monotonic — so multi-host explicitly needs this addition before any resource can claim
  it is truly safe from a dead-but-not-expired holder.**

Until fencing is wired end-to-end (lease issues a fence **and** the protected resource checks it), the honest claim for
"prevents two live holders" is **"prevents two holders from *acquiring*, but not from *acting* if one stalls past
expiry"** — which is exactly the caveat carried in the §6 table.

### 5.3 At-least-once vs exactly-once, idempotent `put`, and why optimistic concurrency makes retries safe

Across hosts and an unreliable network, a caller cannot always tell whether a `put` that timed out actually committed. The
honest delivery guarantee is **at-least-once**: the caller may retry, and the retry may be a duplicate. (This is the same
honesty 04 commits to for its queue — "at-least-once delivery + idempotent merge = exactly-once *effect*", never
"exactly-once delivery", `04_…md §4`, `§7 Q1`.)

The substrate's **optimistic concurrency is precisely what makes retries safe**:

- A `put(record, expected_version=N)` is **idempotent under retry by construction.** The first attempt that lands
  promotes the version `N → N+1`. A duplicate retry still carries `expected_version=N`, but the stored version is now
  `N+1`, so the retry gets a **`VersionConflict`** — it does **not** double-apply. The caller's honest response to that
  conflict is "re-read, re-decide, re-attempt" (the `VersionConflict` docstring `interface.py:95-101`), because the state
  it based its decision on has moved.
- This turns "did my write land?" from a dangerous ambiguity into a safe one: retry freely; either the retry wins (the
  first didn't land) or it conflicts (the first did). There is no lost update and no silent double-write — the contract's
  first-writer-wins (`_optimistic_concurrency` `:153-164`) *is* the idempotency mechanism.
- **Leases get the same safety from token + fence.** A retried `acquire`/`renew` is token-checked; a duplicate effect on
  the protected resource is fence-checked. At-least-once at the transport layer composes with version/token/fence checks
  at the store layer to give exactly-once *effect* — the only honest end state.

The rule to state plainly: **the substrate assumes at-least-once and is safe under it; it must never advertise
exactly-once *delivery*.** Exactly-once *effect* is earned by optimistic concurrency (records) and fencing tokens
(leases/resources), not assumed.

---

## 6. Honesty constraints & truthful claims table

A backend may claim **exactly** what its configuration earns — no more. The matrix below is the honest summary; every
"with config" is a promise that is a lie without that config.

| Backend | Survives restart? | Survives host loss? | Prevents two live holders? | Durable writes? |
|---|---|---|---|---|
| **In-memory** (`InMemoryStateStore`) | **No** — state is RAM, lost on exit | **No** | **In-process only** — single-holder holds *within one process*; meaningless across hosts | **No** |
| **SQLite** (single host) | **Yes** — WAL + fsync, survives close/reopen of the file | **No** — the file lives on one host | **Single-host only** — single-holder holds *within one file*; two hosts = two files = both can "hold" | **Yes** (single host) |
| **Postgres (configured)** | **Yes** | **Yes — with** `synchronous_standby_names` + synchronous replica + failover routing (a lone instance survives restart, **not** host loss) | **Acquire: yes** (atomic conditional insert, §3.2). **Acting: only with fencing** — a stalled holder past expiry is stopped *only* if the protected resource checks a monotonic fence (§5.2) | **Yes — with** `synchronous_commit = on` (default); `off` ⇒ ≤N-txn loss window, **not** durable |
| **Redis (AOF)** | **Yes — with** `appendfsync always` (genuinely durable on node); `everysec` ⇒ **≤~1s loss window**, durable-ish only | **Yes — with** AOF **and** a synchronous replica (`WAIT`); async replication ⇒ loss window on failover | **Acquire: yes** (`SET NX PX` + Lua token discipline, §4.1). **Acting: only with fencing** (`INCR` fence + resource check, §5.2) | **With config only** — `appendfsync always` ⇒ yes; `everysec`/RDB-only ⇒ **no** (loss window) |
| **Redis (no AOF)** | **No** — pure in-memory; restart loses everything | **No** | **Acquire: yes** while the process lives; lost entirely on restart | **No** — claiming durable here is the dishonesty the program refuses (§4.3) |

**The two load-bearing caveats this table encodes:**

1. **"Prevents two live holders" is split into *acquire* and *act*.** Every multi-host backend can prevent two holders
   from *acquiring* a live lease (atomic conditional write). **None** can, by the lease layer alone, prevent a holder that
   **stalls past its expiry** from *acting* — that requires a **monotonic fencing token checked by the protected
   resource** (§5.2). A backend that ticks the "acquire" box but has no fencing **must not** claim "prevents two live
   holders" without the explicit *"…from acquiring; acting requires fencing"* qualifier. The current random-uuid `token`
   proves ownership but is **not** monotonic, so fencing is a required *addition* for the honest unqualified claim.
2. **Durability is per-config, never per-backend-name.** "Postgres" and "Redis" are not durability claims; *Postgres with
   synchronous commit + synchronous replication* and *Redis with `appendfsync always` + synchronous replica* are.
   Reporting a backend as "durable" or "HA" without naming the config that earns it is exactly the
   declared-vs-verified violation (`00_index.md:24-34`) this program exists to refuse. **A deployment may make precisely
   the claim its backend's *tests and config* prove** (`interface.py:14-18`, `__init__.py:36-38`).

---

## 7. Cross-references & open questions

### Cross-references

- **10 (state-substrate migration) — this is what 11 makes multi-host.** 10 cuts the live global dicts
  (`_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`) over onto the `StateStore` substrate behind a
  kill/validate gate (`state_substrate/__init__.py:40-44`). 11 supplies the *multi-host* backend that cutover eventually
  points at; the migration lands on SQLite first (single host) and swaps to Postgres/Redis without touching call sites,
  because the Protocol is unchanged.
- **03 (fleet execution at scale) — fleet across hosts.** 03's Phase D ("orchestrator recovery", `03_…md §3 Phase D`,
  `§7 Q2`) needs `_WORKERS`/`_FLEET_RUNS`/`_DISTRIBUTED_AUDITS` to become *durable and fleet-visible* so a replacement
  orchestrator resumes a dead one's run. 11's Postgres records (run/worker state) + leases (who owns the next scheduling
  pass) are that shared store; the **fencing token (§5.2)** is what stops a presumed-dead orchestrator that wakes from
  double-counting receipts — exactly 03's "zero lost or double-counted receipts" kill gate.
- **04 (queue / resume) — durable queue on the same kind of backend.** 04 builds a durable *queue* with idempotent
  leasing (`04_…md §3 Phase C`); it and 11 share the **same** Postgres-as-truth posture and the **same** at-least-once +
  idempotent-effect honesty (`04_…md §4`). The lease discipline is common: 04's queue claim and 11's resource lease both
  reduce to an atomic compare-and-set the store enforces. Decision to coordinate: whether 04's queue tables and 11's
  ledger tables live in **one** Postgres (transactional consistency between a job and its run record) or separate stores.
- **06 (tenant isolation) — tenancy at the DB layer.** 06 turns `tenant_id` from advisory into enforced
  (`06_…md §1.5`, `§3 Phase B`). 11 realizes that enforcement *in the backend*: `tenant_id` is the **leading column of
  every primary key and WHERE clause** (§3.1), so cross-tenant reads return no row by construction (fail-closed). The
  DB-layer mechanisms 06 will choose between — **row-level security (RLS)** policies vs **per-tenant schemas** vs
  **per-tenant databases** — are an 06/11 joint decision (open question below). 11's `(tenant_id, kind, record_id)` key is
  the pooled-model default; a silo model (`06_…md §7 Q1`) would shard to per-tenant schemas/DBs.
- **07 / 08 / 09 (downstream) — they sit on what 11 durably holds.** 07 (WORM) retains the artifacts whose *references*
  live in 11's records; the **fencing check (§5.2) is also the WORM writer's defence** against a stale holder committing a
  duplicate immutable write. 08 (billing) meters against run/worker records that must be durable and host-loss-survivable
  to be a trustworthy `COST_METERED` source. 09 (compliance) governs residency/retention of the rows 11 stores — and
  multi-**region** placement (below) is squarely a 09 concern.

### Open questions

1. **Connection pooling.** N API hosts × a pool each can exhaust Postgres's `max_connections` fast. Do we front Postgres
   with **PgBouncer** (transaction-pooling mode — but note it disqualifies session-level features like advisory locks held
   across statements, nudging us further toward the single-statement `ON CONFLICT` form of §3.3) or rely on per-host pool
   caps? This is an operational gate on how many hosts the substrate can fan out to before the DB is the bottleneck.
2. **Multi-region residency (ties to 09 compliance).** A single-region Postgres has bounded latency but a region-failure
   blast radius and a residency constraint (`09`). Cross-region synchronous replication trades latency for survival;
   cross-region *asynchronous* reintroduces a loss window (§3.4) that breaks the "survives host/region loss" claim. Where
   tenant data may physically reside is a 09 decision that directly constrains 11's replication topology — and may force a
   per-region silo (`06_…md §7 Q1`).
3. **Do leases and records belong in the same backend, or split?** §4 recommends **Redis for leases** (clean
   `SET NX PX` + Lua token fit, ephemeral-by-nature data) and **Postgres for records** (versioned ledger, transactional
   durability). But a split means two backends behind what is *logically* one `StateStore` — two failure domains, two
   durability stories, and the question of whether a lease and the record it protects can be updated atomically (they
   cannot, across two stores, which itself argues for fencing the *resource* rather than relying on lease+record
   atomicity). The alternative — **Postgres for both** — is one failure domain and transactional lease/record consistency
   at the cost of using a relational store for the ephemeral lease traffic Redis handles more naturally. **This is the
   load-bearing architecture decision for 11**, and it interacts with open question 1 (pooling) and cross-reference 04
   (shared vs separate queue/ledger store). Leaning: **Postgres-for-both as the honest default** (one durability story,
   fewest moving parts, fencing via a Postgres sequence), with Redis-leases as a later optimization once lease traffic is
   measured and the operational cost of a second backend is justified.
