"""POST /wrap — full 8-stage pipeline with LLM call."""

from fastapi import APIRouter

from api.llm_connectors.registry import get_connector
from api.models import WrapRequest, WrapResponse
from api.pipeline.runner import WrapPipelineRunner

router = APIRouter()


@router.post("/wrap", response_model=WrapResponse)
async def wrap(req: WrapRequest) -> WrapResponse:
    """Run the full 8-stage wrap pipeline."""
    provider = "mock" if req.mock else req.provider
    connector = get_connector(provider, model=req.model)
    runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)
    return await runner.run(req.text)
