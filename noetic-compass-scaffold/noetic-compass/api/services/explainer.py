"""Public-safe Gemini explainer for CAS Harness.

The explainer is deliberately separate from the CAS scoring prompt and from source-code context.
It reads only curated documents from ``docs/explainer`` and sends those documents to Gemini with
strict IP guardrails. If a user asks for proprietary implementation details, the service refuses
without calling Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from api.config import settings
from api.errors import LLMError
from api.llm_connectors.google_connector import GoogleConnector


MAX_QUESTION_CHARS = 1200
MAX_CONTEXT_CHARS = 14000

PROPRIETARY_TRIGGERS = (
    "reverse engineer",
    "reverse-engineer",
    "recreate",
    "clone",
    "source code",
    "system prompt",
    "internal prompt",
    "hidden prompt",
    "scoring formula",
    "weighting formula",
    "private weights",
    "proprietary weights",
    "probe internals",
    "activation method",
    "model internals",
    "training data",
    "non-public",
    "secret key",
    "api key",
    "bypass",
    "circumvent",
    "jailbreak",
)

SAFE_REFUSAL = (
    "I cannot provide proprietary implementation details. I can explain the user-facing CAS "
    "Harness workflow: how to choose a target, run an audit, read the verdict, and review the "
    "evidence packet."
)

SYSTEM_PROMPT = """You are the CAS Harness user explainer.

You are not a CAS Harness engineer. You do not have access to source code, internal prompts,
private research notes, hidden formulas, scoring weights, probe internals, secrets, or deployment
details.

Use only the prepared public knowledge base supplied in the prompt. Explain just enough for a user
to understand how CAS Harness works, what it does, and how to move through the app. If the user asks
for proprietary implementation details or reverse-engineering help, refuse briefly and redirect to
the safe user workflow.

Rules:
- Plain English first.
- Define technical terms when needed.
- Guide users through the CAS Harness process.
- Do not expose proprietary IP.
- Do not invent proof.
- If the knowledge base does not support an answer, say that it is not available in the public
  explainer material.
"""


@dataclass(frozen=True)
class ExplainerDocument:
    """One prepared public-safe explainer document."""

    title: str
    source: str
    text: str


@dataclass(frozen=True)
class ExplainerAnswer:
    """Answer returned by the explainer route."""

    answer: str
    sources: tuple[str, ...]
    used_gemini: bool
    model: str
    safety_mode: str = "public_kb_only"


def default_knowledge_base_dir() -> Path:
    """Return the repository ``docs/explainer`` directory."""

    return Path(__file__).resolve().parents[2] / "docs" / "explainer"


def load_knowledge_base(kb_dir: Path | None = None) -> tuple[ExplainerDocument, ...]:
    """Load curated Markdown docs that are safe to send to Gemini."""

    root = kb_dir or default_knowledge_base_dir()
    if not root.exists():
        return ()

    docs: list[ExplainerDocument] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        title = _title_from_markdown(text) or path.stem.replace("_", " ").title()
        docs.append(
            ExplainerDocument(
                title=title,
                source=path.relative_to(root.parent.parent).as_posix(),
                text=text,
            )
        )
    return tuple(docs)


def is_proprietary_request(question: str) -> bool:
    """Return True if the question asks for details the explainer must not provide."""

    normalized = " ".join(question.lower().split())
    return any(trigger in normalized for trigger in PROPRIETARY_TRIGGERS)


async def explain_question(
    question: str,
    *,
    docs: Iterable[ExplainerDocument] | None = None,
    connector: GoogleConnector | None = None,
) -> ExplainerAnswer:
    """Answer a CAS Harness explainer question from public-safe docs only."""

    cleaned = question.strip()
    if not cleaned:
        return ExplainerAnswer(
            answer="Ask me what you want to understand about using CAS Harness.",
            sources=(),
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )
    if len(cleaned) > MAX_QUESTION_CHARS:
        cleaned = cleaned[:MAX_QUESTION_CHARS]

    documents = tuple(docs) if docs is not None else load_knowledge_base()
    sources = tuple(doc.source for doc in documents)

    if is_proprietary_request(cleaned):
        return ExplainerAnswer(
            answer=SAFE_REFUSAL,
            sources=sources,
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    if not documents:
        return ExplainerAnswer(
            answer=(
                "The public explainer knowledge base is not available yet. I can only answer once "
                "prepared safe documents are present under docs/explainer."
            ),
            sources=(),
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    if not settings.google_api_key:
        return ExplainerAnswer(
            answer=(
                "Gemini is not configured on this server. The explainer knowledge base is present, "
                "but NC_GOOGLE_API_KEY or GOOGLE_API_KEY is missing from the server environment."
            ),
            sources=sources,
            used_gemini=False,
            model=settings.gemini_explainer_model,
        )

    active_connector = connector or GoogleConnector(
        api_key=settings.google_api_key,
        model=settings.gemini_explainer_model,
    )
    prompt = _build_prompt(cleaned, documents)
    try:
        response = await active_connector.generate(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            model=settings.gemini_explainer_model,
        )
    except Exception as exc:  # pragma: no cover - provider/network failure is environment-specific
        raise LLMError(f"Gemini explainer failed: {exc}", provider="google") from exc

    answer = (response.text or "").strip()
    if not answer:
        answer = "Gemini returned an empty answer. Try rephrasing the question."

    return ExplainerAnswer(
        answer=answer,
        sources=sources,
        used_gemini=True,
        model=response.model or settings.gemini_explainer_model,
    )


def _build_prompt(question: str, docs: tuple[ExplainerDocument, ...]) -> str:
    context = _render_context(docs)
    return (
        "PUBLIC KNOWLEDGE BASE START\n"
        f"{context}\n"
        "PUBLIC KNOWLEDGE BASE END\n\n"
        "User question:\n"
        f"{question}\n\n"
        "Answer the user from the public knowledge base only. If the answer would require "
        "proprietary implementation details, refuse and redirect to safe user guidance."
    )


def _render_context(docs: tuple[ExplainerDocument, ...]) -> str:
    chunks: list[str] = []
    total = 0
    for doc in docs:
        rendered = f"## Source: {doc.source}\n{doc.text}\n"
        remaining = MAX_CONTEXT_CHARS - total
        if remaining <= 0:
            break
        if len(rendered) > remaining:
            rendered = rendered[:remaining]
        chunks.append(rendered)
        total += len(rendered)
    return "\n".join(chunks)


def _title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None
