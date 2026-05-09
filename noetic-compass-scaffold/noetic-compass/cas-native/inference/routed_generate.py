"""Unified inference entry point: routing + generation + postprocess.

Composes the three library pieces that have been built separately:

* :func:`cas_native.inference.cas_routing.route_by_compilability` —
  decides ``cas_to_english`` vs ``invalid_to_explanation`` from the
  compiler's verdict on the source CAS.
* :func:`cas_native.inference.native_nl_generate.generate_reply` — the
  underlying autoregressive generator over a v1+ checkpoint.
* :func:`cas_native.inference.postprocessor.postprocess` — identifier
  repair (opt-in), quality checks, truncation flagging.

This is the function eval scripts and chat.py should call instead of
``generate_reply`` directly. The intent is that callers stop having to
manually construct prompts, manually decide which task wrapper to use,
or manually wire the postprocessor — one entry point composes all of it
with task-aware defaults.

Task-aware ``max_new_tokens`` defaults:
* ``cas_to_english``: 150 tokens (target average ~177 chars / ~50-90 tokens)
* ``invalid_to_explanation``: 250 tokens (target average ~330 chars /
  ~80-150 tokens; v1 PREFIX128 5ep audit found records 7-8 truncated
  at the prior 120-token cap with output cut mid-clause)

Callers that want the same budget for both tasks can override
``max_new_tokens`` directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from cas_native.inference.cas_routing import (
    RoutingDecision,
    build_prompt_from_routing,
    route_by_compilability,
)
from cas_native.inference.native_nl_generate import generate_reply
from cas_native.inference.postprocessor import PostprocessResult, postprocess


# Task-aware token budget defaults (see module docstring for derivation).
_DEFAULT_MAX_NEW_TOKENS = {
    "cas_to_english": 150,
    "invalid_to_explanation": 250,
}


@dataclass
class RoutedGenerationResult:
    """Audit-friendly bundle of everything ``routed_generate`` produced.

    This is the surface chat.py and eval scripts should consume. It
    carries the model output (final + raw), the routing decision that
    selected the task, the prompt that was actually fed to the model,
    the full postprocess result (repair log, recovery scores, quality
    flags including truncation), and the generation metadata for any
    deeper trace work.
    """
    final_text: str
    raw_text: str
    routing: RoutingDecision
    prompt_used: str
    postprocess_result: PostprocessResult
    generation_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def task_type(self) -> str:
        return self.routing.task_type

    @property
    def truncated(self) -> bool:
        return self.postprocess_result.truncated

    @property
    def quality_passed(self) -> bool:
        return self.postprocess_result.quality_passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_text": self.final_text,
            "raw_text": self.raw_text,
            "routing": self.routing.to_dict(),
            "prompt_used": self.prompt_used,
            "postprocess": self.postprocess_result.to_dict(),
            "generation_metadata": dict(self.generation_metadata),
        }


def _resolve_max_new_tokens(
    routing: RoutingDecision,
    override: Optional[int],
) -> int:
    if override is not None:
        return int(override)
    return _DEFAULT_MAX_NEW_TOKENS.get(routing.task_type, 150)


def routed_generate(
    *,
    model: Any,
    tokenizer: Any,
    source_cas: str,
    register: str = "T",
    apply_repair: bool = True,
    max_new_tokens: Optional[int] = None,
    sampling: str = "greedy",
    temperature: float = 0.7,
    top_p: float = 0.9,
    use_cas_prefix: bool = True,
    device: Any = None,
) -> RoutedGenerationResult:
    """Run the unified routing + generation + postprocess pipeline.

    Args:
        model: a v1+ ``CASNativeModel`` with an ``NLGenerationHead``
            attached. Must have been loaded from a checkpoint trained
            with ``--use-cas-prefix`` if ``use_cas_prefix=True``.
        tokenizer: the corresponding ``HybridCASTokenizer`` (or
            ``ExtendedHybridCASTokenizer`` with English BPE).
        source_cas: the CAS expression to translate. Drives both the
            routing decision and the prompt content.
        register: register hint for the generation head's FiLM
            modulation. Default ``"T"`` (transcendent) matches the v1
            corpus convention where the Wave 2.5 records carry no
            explicit register annotation.
        apply_repair: when True (default), run identifier_repair as a
            post-gen step. Ω names, coefficients, and variable names
            are substituted from source where slots exist in the gen.
        max_new_tokens: override the task-aware default. None uses
            150 for cas_to_english, 250 for invalid_to_explanation.
        sampling: ``"greedy"`` (deterministic, recommended for eval),
            ``"temperature"``, or ``"top_p"``.
        temperature, top_p: sampling controls. Ignored for greedy.
        use_cas_prefix: passes both cas_prefix_ids and cas_prefix_mask
            to the head. Default True (the B-4 architectural fix).
        device: torch device. Defaults to the model's device.
    """
    routing = route_by_compilability(source_cas)
    prompt_text = build_prompt_from_routing(
        source_cas=source_cas, routing=routing,
    )
    budget = _resolve_max_new_tokens(routing, max_new_tokens)

    gen_out = generate_reply(
        model=model,
        tokenizer=tokenizer,
        prompt_text=prompt_text,
        cas_expression=source_cas,
        register=register,
        max_new_tokens=budget,
        sampling=sampling,
        temperature=temperature,
        top_p=top_p,
        use_cas_prefix=use_cas_prefix,
        device=device,
    )
    raw_text = str(gen_out.get("reply_text", ""))
    stopped_on_eos = bool(gen_out.get("stopped_on_eos", False))

    pp = postprocess(
        source_cas=source_cas,
        raw_gen=raw_text,
        routing=routing,
        apply_repair=apply_repair,
        stopped_on_eos=stopped_on_eos,
    )

    return RoutedGenerationResult(
        final_text=pp.final_text,
        raw_text=raw_text,
        routing=routing,
        prompt_used=prompt_text,
        postprocess_result=pp,
        generation_metadata={
            "n_steps": gen_out.get("n_steps"),
            "stopped_on_eos": stopped_on_eos,
            "max_new_tokens": budget,
            "sampling_config": gen_out.get("config", {}),
            "token_ids_preview": gen_out.get("token_ids", [])[:32],
        },
    )


__all__ = [
    "RoutedGenerationResult",
    "routed_generate",
]
