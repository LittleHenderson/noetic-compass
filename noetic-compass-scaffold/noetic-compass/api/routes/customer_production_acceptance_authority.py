"""Secret-free public JSON reads for customer-production acceptance authority."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from api.acceptance_authority_contract import ACCEPTANCE_AUTHORITY_PATH_BY_GATE
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityInvalid,
    AcceptanceAuthorityNotFound,
    AcceptanceAuthorityUnavailable,
    CustomerProductionAcceptanceAuthorityStore,
)


router = APIRouter(tags=["customer_production_acceptance"])
logger = logging.getLogger("noetic.acceptance_authority")

_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


async def _read_authority_document(request: Request, gate: str) -> Response:
    store = getattr(request.app.state, "acceptance_authority_store", None)
    if not isinstance(store, CustomerProductionAcceptanceAuthorityStore):
        return JSONResponse(
            status_code=503,
            content={"detail": "Acceptance evidence authority is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    try:
        document = store.load(gate)
    except AcceptanceAuthorityNotFound:
        return JSONResponse(
            status_code=404,
            content={"detail": "Acceptance evidence is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    except (AcceptanceAuthorityInvalid, AcceptanceAuthorityUnavailable) as exc:
        # Do not copy exception text into the response: a storage/provider error
        # can contain infrastructure details.  The log records only its class.
        logger.warning(
            "acceptance authority read failed gate=%s reason=%s",
            gate,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "Acceptance evidence authority is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    return Response(
        content=document.body,
        status_code=200,
        media_type="application/json",
        headers={
            **_NO_STORE_HEADERS,
            "ETag": f'"sha256:{document.sha256}"',
        },
    )


def _route_handler(gate: str):  # type: ignore[no-untyped-def]
    async def read_gate(request: Request) -> Response:
        return await _read_authority_document(request, gate)

    read_gate.__name__ = f"read_customer_production_{gate}"
    read_gate.__doc__ = (
        "Return the active persisted evidence document, or fail closed when absent/invalid."
    )
    return read_gate


# Register exact static routes.  A path parameter would make future sibling
# endpoints look anonymous even though the middleware uses a strict allowlist.
for _gate, _path in ACCEPTANCE_AUTHORITY_PATH_BY_GATE.items():
    router.add_api_route(
        _path,
        _route_handler(_gate),
        methods=["GET"],
        name=f"customer_production_acceptance_{_gate}",
        response_class=Response,
        responses={
            404: {"description": "No active evidence revision"},
            503: {"description": "Authority storage/evidence is unavailable"},
        },
    )


__all__ = ["router"]
