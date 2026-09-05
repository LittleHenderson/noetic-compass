# One continued AWS allowance

The owner amended the total CASformer allowance to **$400**, including the
earlier pilot, the 12-hour campaign and any later research. It is not a fresh
$400 allowance. This initialization preserves the two earlier $2 reservations:
**$4 reserved; $396 unreserved.** Reservations are conservative spending bounds,
not AWS invoice totals, and are never refunded automatically.

`OWNER_APPROVAL_SOURCE.json` records the exact active user goal returned to the
root agent. `campaign_ledger.json` binds that approval and the unchanged META1
ledger by SHA-256 and preserves the full earlier reservation records. The
numbered `campaign_ledger.json.history/` states form an append-only digest chain.

All future campaign launchers must call `aws.budget.reserve_budget` against this
one canonical ledger **before creating any paid resources**. The historical
META1 launcher and $100 ledger remain evidence only; they are not a second
spending allowance. No ledger can intercept unrelated manual AWS spending.

The budget code checks the total, every prior reservation, source/archive/plan
identities, the owner's approval, a modern GPU family, one bounded instance,
no automatic retry, and the declared compute-plus-ancillary cost bound. It uses
an exclusive lock and atomic replacement, including bounded Windows lock
retries. An interrupted replacement, stale lock, changed predecessor, changed
approval, inconsistent total or broken history blocks further spending.

The launcher must separately enforce resource sizes, artifact limits, retention,
shutdown, cleanup and current AWS prices. The caller must reserve enough for
storage, IPv4, requests, transfer and taxes as well as compute. A schema check
does not establish that an AWS job actually launched or shut down successfully.

No new paid job was launched while preparing this amendment. No provider
resources were modified. The 38 local tests are JSON/file-system tests only;
they do not import or execute a neural model.

Verification: `validation_20260905/test_receipt.json` and its raw output.
Definitive provider snapshot:
`../provider/20260905_current_campaign_precise_market/provider_snapshot.json`.
The earlier partial snapshot is preserved; its broad H100 price query included
a separate Capacity Block product. The definitive query explicitly selects
`marketoption=OnDemand` and `operation=RunInstances`.
