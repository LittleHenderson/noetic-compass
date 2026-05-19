"""POST /wrap — full 8-stage pipeline with LLM call."""

from fastapi import APIRouter, Request

from api.llm_connectors.registry import get_connector
from api.models import WrapRequest, WrapResponse
from api.pipeline.runner import WrapPipelineRunner
from api.store import save_assessment

router = APIRouter()


@router.post("/wrap", response_model=WrapResponse)
async def wrap(req: WrapRequest, request: Request) -> WrapResponse:
    """Run the full 8-stage wrap pipeline and persist the result."""
    provider = "mock" if req.mock else req.provider
    connector = get_connector(provider, model=req.model)
    runner = WrapPipelineRunner(connector=connector, dial_config=req.dial_config)
    result = await runner.run(
        req.text,
        scoring_mode=req.scoring_mode,
        scoring_provider=req.scoring_provider,
        scoring_model=req.scoring_model,
        # Stage 20 Generation Readiness Gate — opt-in Output Gate companion.
        # When the gate is disabled (request flag and server default both
        # falsy), these arguments are no-ops and the pipeline behaves
        # exactly as before.
        readiness_gate_enabled=req.readiness_gate_enabled,
        verification_mode=req.verification_mode,
        verification=req.verification,
    )

    # Persist assessment
    api_key = getattr(getattr(request, "state", None), "api_key", "default")
    await save_assessment(
        api_key=api_key,
        text=req.text,
        response=result.model_dump(mode="json"),
    )

    return result
