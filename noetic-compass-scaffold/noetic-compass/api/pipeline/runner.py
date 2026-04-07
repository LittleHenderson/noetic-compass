"""Wrap pipeline runner — orchestrates the 8 stages."""

from __future__ import annotations

import hashlib
import time

from api.llm_connectors.base import BaseLLMConnector, LLMResponse
from api.models import (
    DialConfigSchema,
    LLMResponseSchema,
    NccsResponse,
    StageResult,
    WrapResponse,
)
from api.pipeline.stages import (
    input_analyzer,
    rpm_gate,
    dial_adjustment,
    base_llm_call,
    operator_scoring,
    domain_coherence,
    inversion_scan,
    output_gate,
)


class WrapPipelineRunner:
    """Orchestrates the 8-stage wrap pipeline."""

    def __init__(self, connector: BaseLLMConnector, dial_config: DialConfigSchema):
        self.connector = connector
        self.dial_config = dial_config

    async def run(self, text: str) -> WrapResponse:
        """Execute the full 8-stage pipeline."""
        stages: list[StageResult] = []
        llm_resp: LLMResponse | None = None
        t0 = time.monotonic()

        # Stage 1: Input Analyzer
        analyzed = await input_analyzer(text)
        stages.append(StageResult(
            stage="input_analyzer",
            success=True,
            data={
                "token_count": analyzed.token_count,
                "word_count": analyzed.word_count,
                "sentence_count": analyzed.sentence_count,
                "vocab_richness": analyzed.vocab_richness,
            },
        ))

        # Stage 2: RPM Gate
        rpm_result = await rpm_gate(analyzed)
        # Flatten drive_scores [[D,W,P], ...] → [D1, D2, ...D7] (top-level only)
        flat_drives = [chain[0] for chain in rpm_result.drive_scores]
        stages.append(StageResult(
            stage="rpm_gate",
            success=rpm_result.passed,
            data={
                "a0_score": rpm_result.a0_score,
                "rpm_completeness": rpm_result.rpm_completeness,
                "drive_scores": rpm_result.drive_scores,
                "heuristic": rpm_result.heuristic,
            },
        ))

        # Stage 3: Dial Adjustment
        adjusted = await dial_adjustment(analyzed, self.dial_config)
        stages.append(StageResult(
            stage="dial_adjustment",
            success=True,
            data={"dial_values": adjusted.dial_config.as_list()},
        ))

        # Stage 4: Base LLM Call
        llm_resp = await base_llm_call(adjusted, self.connector)
        stages.append(StageResult(
            stage="base_llm_call",
            success=True,
            data={"model": llm_resp.model, "latency_ms": llm_resp.latency_ms},
        ))

        # Stage 5: Operator Scoring
        op_result = await operator_scoring(llm_resp)
        stages.append(StageResult(
            stage="operator_scoring",
            success=True,
            data={
                "profile_score": op_result.profile_score,
                "scores": op_result.scores,
                "involution_balances": op_result.involution_balances,
            },
        ))

        # Stage 6: Domain Coherence
        dc_result = await domain_coherence(op_result)
        stages.append(StageResult(
            stage="domain_coherence",
            success=True,
            data={"dci": dc_result.dci, "domain_averages": dc_result.domain_averages},
        ))

        # Stage 7: Inversion Scan — pass real drive scores and domain averages
        inv_result = await inversion_scan(
            op_result,
            drive_scores=flat_drives,
            domain_averages=dc_result.domain_averages,
        )
        stages.append(StageResult(
            stage="inversion_scan",
            success=True,
            data={
                "resistance_score": inv_result.resistance_score,
                "stealth_resistance": inv_result.stealth_resistance,
                "axis_scores": inv_result.axis_scores,
            },
        ))

        # Stage 8: Output Gate (NCCS) — pass real drive scores
        nccs = await output_gate(
            op_result, dc_result, inv_result, rpm_result,
            drive_scores=flat_drives,
        )
        stages.append(StageResult(
            stage="output_gate",
            success=True,
            data={"composite": nccs.composite, "certification": nccs.certification},
        ))

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        nccs_response = NccsResponse(
            operator_profile=nccs.operator_profile,
            domain_coherence=nccs.domain_coherence,
            drive_rpm_integrity=nccs.drive_rpm_integrity,
            pathway_quality=nccs.pathway_quality,
            inversion_resistance=nccs.inversion_resistance,
            social_engineering=nccs.social_engineering,
            composite=nccs.composite,
            certification=nccs.certification,
            not_measured=nccs.not_measured,
        )

        llm_response_schema = None
        if llm_resp:
            llm_response_schema = LLMResponseSchema(
                text=llm_resp.text,
                model=llm_resp.model,
                usage=llm_resp.usage,
                latency_ms=llm_resp.latency_ms,
            )

        # Provenance metadata for reproducibility
        provenance = {
            "pipeline_version": "0.2.0",
            "engine": "cas-engine",
            "input_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            "connector": self.connector.provider_name,
            "elapsed_ms": elapsed_ms,
            "rpm_heuristic": rpm_result.heuristic,
        }

        return WrapResponse(
            nccs=nccs_response,
            stages=stages,
            llm_response=llm_response_schema,
            provenance=provenance,
        )
