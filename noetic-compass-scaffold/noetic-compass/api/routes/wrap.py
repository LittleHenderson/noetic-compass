"""POST /wrap — full 8-stage pipeline with LLM call."""

from fastapi import APIRouter, Request

from api.llm_connectors.registry import get_connector
from api.models import WrapRequest, WrapResponse
from api.pipeline.runner import WrapPipelineRunner
from api.store import save_assessment

router = APIRouter()


@router.post("/wrap", response_model=WrapResponse)
async def wrap(req: WrapRequest, request: Request) -> WrapResponse:
    """Run the full 8-stage wrap pipeline."""
    provider = "mock" if req.mock else req.provider
    connector = get_connector(provider, model=req.model)
    runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)
    result = await runner.run(req.text)

    # Persist to in-memory store for export
    api_key = getattr(request.state, "api_key", "default")
    save_assessment(api_key, req.text, result.model_dump())

    return result
