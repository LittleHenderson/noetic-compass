from fastapi import APIRouter, Query

from ..data import account_reconciliation

router = APIRouter()


@router.get("/account")
async def get_account_reconciliation(sync_to_broker: bool = Query(default=False)):
    """Returns the broker/demo account reconciliation report.

    By default this compares the owner/risk-review paper ledger against broker
    evidence. Set ``sync_to_broker=true`` to preview a paper/demo reconciliation
    ledger seeded from the verified broker account snapshot balance; this is
    accounting/reconciliation only and does not authorize live money.
    """
    return account_reconciliation(sync_to_broker=sync_to_broker)
