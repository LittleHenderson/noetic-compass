"""Wrap pipeline runner — orchestrates the 8 stages."""

from __future__ import annotations

import hashlib
import time

from api.config import settings
from api.llm_connectors.base import BaseLLMConnector, LLMResponse
from api.llm_connectors.registry import get_connector
from api.models import (
    DialConfigSchema,
    LLMResponseSchema,
    NccsResponse,
    StageResult,
    WrapResponse,
)
from api.pipeline.interpreter import generate_interpretation, DRIVE_NAMES
from api.pipeline.fractal_analysis import analyze_fractal
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

    def _resolve_scoring_connector(self) -> tuple[BaseLLMConnector | None, str | None, str | None]:
        """Resolve the secondary scorer LLM, if configured/available."""
        try:
            configured_provider = settings.scoring_provider.strip().lower()
            configured_model = settings.scoring_model.strip() or None

            if configured_provider:
                connector = get_connector(configured_provider, model=configured_model)
                return connector, configured_provider, configured_model

            if self.connector.provider_name in {"openai", "anthropic"}:
                default_models = {
                    "openai": "gpt-4o",
                    "anthropic": "claude-sonnet-4-6",
                }
                provider = self.connector.provider_name
                model = configured_model or default_models[provider]
                connector = get_connector(provider, model=model)
                return connector, provider, model
        except Exception:
            return None, None, None

        return None, None, None

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
        scorer_connector, scorer_provider, scorer_model = self._resolve_scoring_connector()
        op_result = await operator_scoring(
            llm_resp,
            prompt_text=adjusted.text,
            scorer_connector=scorer_connector,
            scorer_model=scorer_model,
        )
        stages.append(StageResult(
            stage="operator_scoring",
            success=True,
            data={
                "profile_score": op_result.profile_score,
                "scores": op_result.scores,
                "raw_scores_0_to_10": op_result.raw_scores_0_to_10,
                "involution_balances": op_result.involution_balances,
                "scoring_method": op_result.scoring_method,
                "evidence": op_result.evidence,
                "scorer_provider": op_result.scorer_provider,
                "scorer_model": op_result.scorer_model,
                "fallback_reason": op_result.fallback_reason,
            },
        ))

        # Stage 6: Domain Coherence
        dc_result = await domain_coherence(op_result)
        stages.append(StageResult(
            stage="domain_coherence",
            success=True,
            data={"dci": dc_result.dci, "domain_averages": dc_result.domain_averages},
        ))

        # Stage 7: Inversion Scan — pass real drive scores, domain averages, and LLM text for evidence
        inv_result = await inversion_scan(
            op_result,
            drive_scores=flat_drives,
            domain_averages=dc_result.domain_averages,
            llm_text=llm_resp.text if llm_resp else "",
            rpm_drive_scores=rpm_result.drive_scores,
        )
        stages.append(StageResult(
            stage="inversion_scan",
            success=True,
            data={
                "resistance_score": inv_result.resistance_score,
                "stealth_resistance": inv_result.stealth_resistance,
                "axis_scores": inv_result.axis_scores,
                "evidence": [
                    {
                        "axis": e.axis,
                        "axis_index": e.axis_index,
                        "score": e.score,
                        "flagged": e.flagged,
                        "severity": e.severity,
                        "trigger": e.trigger,
                        "transcript_snippet": e.transcript_snippet,
                    }
                    for e in inv_result.evidence
                ],
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
            bias_flags=nccs.bias_flags,
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
            "scoring_method": op_result.scoring_method,
            "scorer_provider": op_result.scorer_provider or scorer_provider,
            "scorer_model": op_result.scorer_model or scorer_model,
            "elapsed_ms": elapsed_ms,
            "rpm_heuristic": rpm_result.heuristic,
        }

        # Post-pipeline: AI interpretation (not a 9th stage)
        broken_chains = [
            DRIVE_NAMES[i]
            for i, chain in enumerate(rpm_result.drive_scores)
            if any(s < 0.5 for s in [rpm_result.a0_score, *chain])
        ]
        # Use the generator model's name so the briefing explicitly names
        # the subject of analysis (the AI being assessed — never the user).
        generator_model_name = getattr(self.connector, "model", None) or self.connector.provider_name
        interpretation = await generate_interpretation(
            self.connector,
            composite=nccs.composite,
            certification=nccs.certification,
            operator_scores=op_result.scores,
            domain_averages=dc_result.domain_averages,
            drive_scores=flat_drives,
            inversion_axis_scores=inv_result.axis_scores,
            rpm_completeness=rpm_result.rpm_completeness,
            broken_chains=broken_chains,
            model_name=generator_model_name,
        )

        # Fractal analysis on operator sequence
        from api.models import FractalAnalysisSchema
        fractal = analyze_fractal(op_result.scores)
        fractal_schema = FractalAnalysisSchema(
            dominant_sequence=fractal.dominant_sequence,
            canonical_form=fractal.canonical_form,
            cancellations_detected=fractal.cancellations_detected,
            classification=fractal.classification,
            orbit_length=fractal.orbit_length,
            has_fixed_point=fractal.has_fixed_point,
        )

        return WrapResponse(
            nccs=nccs_response,
            stages=stages,
            llm_response=llm_response_schema,
            scoring_method=op_result.scoring_method,
            provenance=provenance,
            interpretation=interpretation,
            fractal_analysis=fractal_schema,
        )
