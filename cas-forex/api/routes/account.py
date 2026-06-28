from fastapi import APIRouter, Query
from ..data import account_ledger, apply_broker_synced_risk_review, broker_synced_risk_preview

router = APIRouter()


@router.get("/ledger")
async def get_account_ledger(initial_investment: float | None = Query(default=None, gt=0)):
    """Returns owner-selectable paper/demo account ledger state.

    ``initial_investment`` previews any positive owner-selected paper/demo seed.
    It does not deposit, withdraw, place live orders, or move external money.
    """
    return account_ledger(initial_investment_usd=initial_investment)


@router.get("/broker-sync-risk-preview")
async def get_broker_synced_risk_preview():
    """Returns paper risk sizing rerun from the verified broker demo balance.

    This is preview-only. It does not append the paper-risk evidence chain,
    place orders, create broker ACCEPT, or move money.
    """
    return broker_synced_risk_preview()


@router.post("/apply-broker-sync-risk-review")
async def post_apply_broker_synced_risk_review(confirm_apply: bool = Query(default=False)):
    """Append broker-synced paper risk sizing after explicit owner confirmation.

    This mutates only the local paper-risk evidence chain. It does not place
    orders, create broker ACCEPT, deposit, withdraw, or move external money.
    """
    return apply_broker_synced_risk_review(confirm_apply=confirm_apply)
