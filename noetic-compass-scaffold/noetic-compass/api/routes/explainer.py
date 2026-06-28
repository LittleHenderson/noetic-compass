"""Gemini-backed public-safe CAS Harness explainer."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.services.explainer import explain_question

router = APIRouter(tags=["explainer"])


class ExplainerChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1200)


class ExplainerChatResponse(BaseModel):
    answer: str
    sources: list[str]
    used_gemini: bool
    model: str
    safety_mode: str


@router.post("/explainer/chat", response_model=ExplainerChatResponse)
async def explainer_chat(body: ExplainerChatRequest) -> ExplainerChatResponse:
    """Answer a CAS Harness user-help question from the public-safe knowledge base."""

    result = await explain_question(body.question)
    return ExplainerChatResponse(
        answer=result.answer,
        sources=list(result.sources),
        used_gemini=result.used_gemini,
        model=result.model,
        safety_mode=result.safety_mode,
    )
