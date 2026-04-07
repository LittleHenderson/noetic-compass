"""POST /batch — batch assessment with async concurrency."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from api.llm_connectors.registry import get_connector
from api.models import BatchRequest, BatchResponse, WrapResponse
from api.pipeline.runner import WrapPipelineRunner

router = APIRouter()


@router.post("/batch", response_model=BatchResponse)
async def batch(req: BatchRequest) -> BatchResponse:
    """Run the wrap pipeline concurrently for a batch of texts."""
    provider = "mock" if req.mock else req.provider
    connector = get_connector(provider, model=req.model)
    runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)

    semaphore = asyncio.Semaphore(req.max_concurrency)

    async def process_one(text: str) -> WrapResponse | None:
        async with semaphore:
            try:
                return await runner.run(text)
            except Exception:
                return None

    tasks = [process_one(text) for text in req.texts]
    raw_results = await asyncio.gather(*tasks)

    results: list[WrapResponse] = []
    succeeded = 0
    failed = 0

    for r in raw_results:
        if r is not None:
            results.append(r)
            succeeded += 1
        else:
            failed += 1

    return BatchResponse(
        results=results,
        total=len(req.texts),
        succeeded=succeeded,
        failed=failed,
    )
