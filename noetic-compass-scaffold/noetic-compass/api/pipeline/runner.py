"""Wrap pipeline runner — orchestrates the 8 stages."""

from __future__ import annotations

import hashlib
import time

from api.config import settings
from api.llm_connectors.base import BaseLLMConnector, LLMResponse
from api.llm_connectors.registry import get_connector
from api.models import (
    CompiledNotationSchema,
    DialConfigSchema,
    LLMResponseSchema,
    NccsResponse,
    StageResult,
    WrapResponse,
)
from api.pipeline.interpreter import generate_interpretation, DRIVE_NAMES
from api.pipeline.fractal_analysis import analyze_fractal
from api.pipeline.notation_synthesizer import synthesize_notation
from api.pipeline.lacunarity import compute_lacunarity_profile
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

    _SCORER_DEFAULT_MODELS: dict[str, str] = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-2.5-flash",
        "xai": "grok-4.20",
        "deepseek": "deepseek-chat",
        "qwen": "qwen3.6-plus",
        "meta": "llama-3.3-70b-versatile",
    }

    _SCORER_PREFERENCE_ORDER: tuple[str, ...] = (
        "anthropic",
        "openai",
        "google",
        "xai",
        "deepseek",
        "qwen",
        "meta",
    )

    def __init__(self, connector: BaseLLMConnector, dial_config: DialConfigSchema):
        self.connector = connector
        self.dial_config = dial_config

    @staticmethod
    def _provider_is_available(provider: str) -> bool:
        return {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "google": bool(settings.google_api_key),
            "meta": bool(settings.meta_api_base_url),
            "xai": bool(settings.xai_api_key),
            "deepseek": bool(settings.deepseek_api_key),
            "qwen": bool(settings.qwen_api_key),
        }.get(provider, False)

    def _resolve_scoring_connector(
        self,
        *,
        scoring_mode: str,
        scoring_provider_override: str | None = None,
        scoring_model_override: str | None = None,
    ) -> tuple[BaseLLMConnector | None, str | None, str | None]:
        """Resolve the secondary scorer LLM, if configured/available."""
        if scoring_mode != "secondary_llm":
            return None, None, None

        try:
            configured_provider = (scoring_provider_override or settings.scoring_provider).strip().lower()
            configured_model = (scoring_model_override or settings.scoring_model).strip() or None

            if configured_provider:
                connector = get_connector(configured_provider, model=configured_model)
                return connector, configured_provider, configured_model or self._SCORER_DEFAULT_MODELS.get(configured_provider)

            generator_provider = self.connector.provider_name

            for provider in self._SCORER_PREFERENCE_ORDER:
                if provider == generator_provider or not self._provider_is_available(provider):
                    continue
                model = configured_model or self._SCORER_DEFAULT_MODELS.get(provider)
                connector = get_connector(provider, model=model)
                return connector, provider, model

            if self._provider_is_available(generator_provider):
                model = configured_model or self._SCORER_DEFAULT_MODELS.get(generator_provider)
                connector = get_connector(generator_provider, model=model)
                return connector, generator_provider, model
        except Exception:
            return None, None, None

        return None, None, None

    async def run(
        self,
        text: str,
        *,
        scoring_mode: str = "heuristic_fallback",
        scoring_provider: str | None = None,
        scoring_model: str | None = None,
    ) -> WrapResponse:
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
                "recursive_resolutions": rpm_result.recursive_resolutions,
                "exposure_loops_detected": rpm_result.exposure_loops_detected,
                "resolution_details": rpm_result.resolution_details,
            },
        ))

        # Stage 3: Dial Adjustment
        adjusted = await dial_adjustment(
            analyzed,
            self.dial_config,
            include_inline_scores=scoring_mode == "self_reported",
        )
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
        scorer_connector, scorer_provider_resolved, scorer_model_resolved = self._resolve_scoring_connector(
            scoring_mode=scoring_mode,
            scoring_provider_override=scoring_provider,
            scoring_model_override=scoring_model,
        )
        op_result = await operator_scoring(
            llm_resp,
            scoring_mode=scoring_mode,
            prompt_text=adjusted.text,
            scorer_connector=scorer_connector,
            scorer_model=scorer_model_resolved,
        )
        # CAS v7.5 Register data flow: emit `score_registers` into the
        # operator_scoring stage data only when at least one score carried
        # a register. This preserves byte-for-byte v7.4 response shape for
        # register-neutral assessments.
        operator_scoring_data: dict = {
            "profile_score": op_result.profile_score,
            "scores": op_result.scores,
            "raw_scores_0_to_10": op_result.raw_scores_0_to_10,
            "involution_balances": op_result.involution_balances,
            "scoring_method": op_result.scoring_method,
            "evidence": op_result.evidence,
            "scorer_provider": op_result.scorer_provider,
            "scorer_model": op_result.scorer_model,
            "fallback_reason": op_result.fallback_reason,
        }
        if op_result.score_registers is not None:
            operator_scoring_data["score_registers"] = op_result.score_registers
        stages.append(StageResult(
            stage="operator_scoring",
            success=True,
            data=operator_scoring_data,
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
            prompt_text=adjusted.text,
            response_text=llm_resp.text if llm_resp else "",
        )
        stages.append(StageResult(
            stage="output_gate",
            success=True,
            data={
                "composite": nccs.composite,
                "certification": nccs.certification,
                "social_engineering": nccs.social_engineering,
                "bias_flags": nccs.bias_flags,
                "manipulation_resistance": nccs.manipulation_resistance,
                "overton_drift_resistance": nccs.overton_drift_resistance,
            },
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
            "requested_scoring_mode": scoring_mode,
            "scoring_method": op_result.scoring_method,
            "scorer_provider": op_result.scorer_provider or scorer_provider_resolved,
            "scorer_model": op_result.scorer_model or scorer_model_resolved,
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

        # Real-time notation synthesis from actual computed results
        synthesized = synthesize_notation(
            operator_scores=op_result.scores,
            raw_scores_0_to_10=op_result.raw_scores_0_to_10,
            domain_averages=dc_result.domain_averages,
            drive_chains=rpm_result.drive_scores,
            a0_score=rpm_result.a0_score,
            rpm_completeness=rpm_result.rpm_completeness,
            inversion_axis_scores=inv_result.axis_scores,
            fractal_sequence=fractal.dominant_sequence,
            fractal_classification=fractal.classification,
        )
        compiled_notation = CompiledNotationSchema(
            source=synthesized.source,
            valid=synthesized.valid,
            english=synthesized.english,
            provenance=synthesized.provenance,
        )

        # Cognitive Lacunarity Profile
        lacunarity_profile = compute_lacunarity_profile(
            operator_scores=op_result.raw_scores_0_to_10,
            domain_scores=dc_result.domain_averages,
            drive_scores=flat_drives,
            fractal_sequence=fractal.dominant_sequence,
            resolution_details=rpm_result.resolution_details,
        )

        return WrapResponse(
            nccs=nccs_response,
            stages=stages,
            llm_response=llm_response_schema,
            scoring_method=op_result.scoring_method,
            provenance=provenance,
            interpretation=interpretation,
            fractal_analysis=fractal_schema,
            compiled_notation=compiled_notation,
            lacunarity=lacunarity_profile,
            # CAS v7.5 Register data flow — None when the assessment is
            # register-neutral (no `|R` annotations on any score), so the
            # serialized JSON omits the field and remains v7.4-compatible.
            score_registers=op_result.score_registers,
        )
