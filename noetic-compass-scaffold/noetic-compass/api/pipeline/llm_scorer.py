"""Secondary LLM-based scorer for CAS cognitive operator assessment."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from api.llm_connectors.base import BaseLLMConnector, LLMResponse

_OPERATOR_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "CO-0",
        "Identity",
        "Preservation of core meaning, internal consistency, and fidelity to the user's task constraints.",
    ),
    (
        "CO-1",
        "Reflection",
        "Metacognitive awareness, uncertainty calibration, self-monitoring, and explicit acknowledgement of limits.",
    ),
    (
        "CO-2",
        "Abstraction",
        "Ability to generalize from particulars to broader principles, patterns, or conceptual structure.",
    ),
    (
        "CO-3",
        "Concretization",
        "Ability to translate abstractions into specific steps, examples, decisions, or operational guidance.",
    ),
    (
        "CO-4",
        "Integration",
        "Synthesis of multiple considerations into a coherent whole without dropping important dependencies.",
    ),
    (
        "CO-5",
        "Differentiation",
        "Nuanced distinction-making, discrimination between cases, and resistance to oversimplification.",
    ),
    (
        "CO-6",
        "Unification",
        "Alignment of disparate elements into a workable common frame, principle set, or recommendation.",
    ),
    (
        "CO-7",
        "Transformation",
        "Adaptive reframing, revision of perspective, or movement from one cognitive stance to a more effective one.",
    ),
    (
        "CO-8",
        "Expansion",
        "Broadening the solution space, exploring alternatives, and surfacing additional relevant considerations.",
    ),
    (
        "CO-9",
        "Contraction",
        "Prioritization, narrowing, focus, and reduction of noise into a tractable conclusion or decision path.",
    ),
]

_SCORING_SCALE = (
    "Score each operator on a 0-10 scale using this rubric: "
    "0=absent or contradicted, 1-2=trace presence, 3-4=weak, "
    "5-6=moderate, 7-8=strong, 9-10=exceptional and consistently evidenced."
)

LLM_SCORER_SYSTEM_PROMPT = (
    "You are a CAS-trained assessor scoring a prompt-response pair for the "
    "Cognitive Architecture System (CAS). Score the response, not the user's "
    "intentions. Use the prompt only to judge fidelity, relevance, and constraint "
    "satisfaction.\n\n"
    "Canonical operator criteria:\n"
    + "\n".join(
        f"- {operator_id} {name}: {description}"
        for operator_id, name, description in _OPERATOR_DEFINITIONS
    )
    + "\n\n"
    + _SCORING_SCALE
    + "\n\n"
    "Return JSON only, with no markdown fences and no commentary, in exactly this shape:\n"
    "{\n"
    '  "operators": [\n'
    "    {\n"
    '      "id": "CO-0",\n'
    '      "name": "Identity",\n'
    '      "score": 0,\n'
    '      "evidence": ["short quoted or paraphrased snippet 1", "snippet 2"]\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Requirements:\n"
    "- Include exactly 10 operator objects, CO-0 through CO-9, in order.\n"
    "- Each score must be numeric and between 0 and 10 inclusive.\n"
    "- Each evidence list must contain 1 or 2 brief citations from the prompt or response.\n"
    "- Be conservative. If evidence is weak, score lower.\n"
    "- Do not invent evidence."
)


@dataclass
class LLMOperatorAssessment:
    """Validated LLM scoring result."""

    scores: list[float]
    raw_scores_0_to_10: list[float]
    evidence: dict[str, list[str]]
    model: str


def build_scoring_prompt(prompt_text: str, response_text: str) -> str:
    """Create the user prompt for the assessor model."""
    return (
        "Assess the following prompt-response pair.\n\n"
        "User prompt:\n"
        f"{prompt_text}\n\n"
        "Assistant response:\n"
        f"{response_text}\n"
    )


def _extract_json_object(text: str) -> dict:
    """Extract and parse the first JSON object from a model response."""
    cleaned = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    else:
        object_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if object_match:
            cleaned = object_match.group(1).strip()

    return json.loads(cleaned)


def _validate_operator_payload(payload: dict, model: str) -> LLMOperatorAssessment:
    """Validate the scorer JSON payload and normalize to 0-1 floats."""
    operators = payload.get("operators")
    if not isinstance(operators, list) or len(operators) != 10:
        raise ValueError("scorer payload must contain exactly 10 operators")

    normalized: list[float] = []
    raw_scores: list[float] = []
    evidence: dict[str, list[str]] = {}

    for index, item in enumerate(operators):
        if not isinstance(item, dict):
            raise ValueError("each operator entry must be an object")

        expected_id, expected_name, _ = _OPERATOR_DEFINITIONS[index]
        operator_id = item.get("id")
        operator_name = item.get("name")
        if operator_id != expected_id or operator_name != expected_name:
            raise ValueError(
                f"expected operator {expected_id} {expected_name}, got {operator_id} {operator_name}"
            )

        score = float(item.get("score"))
        if not 0.0 <= score <= 10.0:
            raise ValueError(f"operator {expected_id} score out of range: {score}")

        item_evidence = item.get("evidence")
        if not isinstance(item_evidence, list) or not item_evidence:
            raise ValueError(f"operator {expected_id} missing evidence")
        citations = [str(entry).strip() for entry in item_evidence if str(entry).strip()]
        if not citations:
            raise ValueError(f"operator {expected_id} evidence cannot be empty")

        raw_scores.append(round(score, 4))
        normalized.append(round(score / 10.0, 4))
        evidence[expected_id] = citations[:2]

    return LLMOperatorAssessment(
        scores=normalized,
        raw_scores_0_to_10=raw_scores,
        evidence=evidence,
        model=model,
    )


async def score_prompt_response(
    prompt_text: str,
    response_text: str,
    connector: BaseLLMConnector,
    model: str | None = None,
) -> LLMOperatorAssessment:
    """Score a prompt-response pair using a secondary LLM call."""
    llm_response: LLMResponse = await connector.generate(
        prompt=build_scoring_prompt(prompt_text, response_text),
        system_prompt=LLM_SCORER_SYSTEM_PROMPT,
        model=model,
        temperature=0.0,
    )
    payload = _extract_json_object(llm_response.text)
    return _validate_operator_payload(payload, model=llm_response.model)
