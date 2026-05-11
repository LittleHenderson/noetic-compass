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

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from cas_native.inference.cas_routing import (
    RoutingDecision,
    build_prompt_from_routing,
    route_by_compilability,
)
from cas_native.inference.fractal_decoder import (
    FractalConstraintState,
    FractalDecoderLog,
    build_boundary_token_ids,
    build_fractal_phrase_trie,
    constrained_strictly_beats_baseline,
    make_logits_processor,
)
from cas_native.inference.fractal_repair import (
    FractalRepairLog,
    parse_fractal,
    verify_fractal_rendering,
)
from cas_native.inference.native_nl_generate import generate_reply
from cas_native.inference.postprocessor import PostprocessResult, postprocess
from cas_native.inference.rpm_retry import (
    RpmRetryLog,
    build_corrective_prompt,
    retry_strictly_beats_original,
    should_attempt_retry,
)


# rpm_chain decoder-seeding regex — extracts the FIRST let-binding's
# variable name from a source CAS expression like:
#   "let stageA0_3_0234 = ^0^P; let stageD3_3_0234 = ^9^P_{F3}; ..."
# The seed text "Let <var> name " forces the decoder onto the canonical
# rpm_chain English silhouette (the v1 PREFIX128 5ep 24-record audit
# found that bare cas_to_english routing did NOT change the model's
# output for valid rpm_chain — it still emitted invalid-explanation
# language. Decoder-seeding is a diagnostic patch that answers: if we
# force the opening, can the model continue correctly?).
_LET_VAR_RX = re.compile(r"^\s*let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)


def _build_rpm_silhouette_seed(source_cas: str) -> Optional[str]:
    """Return the decoder-seed text for valid rpm_chain / let_binding
    sources, or None when the source is not a let-binding shape.

    The seed is ``"Let <first_var_name> name "``. Picking the FIRST
    variable matches how Path D Wave 2.5 records always open: the
    target reply introduces variables in source order, starting with
    ``stageA0_*`` (the canonical RPM A0 axis).
    """
    m = _LET_VAR_RX.search(source_cas)
    if not m:
        return None
    var_name = m.group(1)
    return f"Let {var_name} name "


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
    deeper trace work. ``seed_decoder_text`` records the seed text
    used to prime the decoder when ``seed_rpm_silhouette`` was
    enabled (None when no seeding fired).
    """
    final_text: str
    raw_text: str
    routing: RoutingDecision
    prompt_used: str
    postprocess_result: PostprocessResult
    generation_metadata: dict[str, Any] = field(default_factory=dict)
    seed_decoder_text: Optional[str] = None
    rpm_retry_log: Optional[RpmRetryLog] = None
    fractal_decoder_log: Optional[FractalDecoderLog] = None

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
            "rpm_retry_log": (
                self.rpm_retry_log.to_dict()
                if self.rpm_retry_log is not None else None
            ),
            "fractal_decoder_log": (
                self.fractal_decoder_log.to_dict()
                if self.fractal_decoder_log is not None else None
            ),
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
    seed_rpm_silhouette: bool = True,
    prepend_task_token: bool = False,
    apply_rpm_retry: bool = False,
    apply_fractal_decoder: bool = False,
    fractal_decoder_eos_bias: float = 0.0,
    fractal_decoder_first_n_mode: bool = False,
    fractal_decoder_leaf_exit_boundary: bool = False,
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
        seed_rpm_silhouette: when True, AND routing says
            ``cas_to_english``, AND source starts with ``let ...``,
            prime the decoder with ``"Let <first_var_name> name "``
            so the model is forced onto the let-binding silhouette
            instead of collapsing to invalid-explanation language.
            Default ``True`` (promoted to gated production fallback
            per user audit 2026-05-10, commit b281202): the v1c
            VALIDTOK 5ep retrain shipped the [VALID]/[INVALID] task
            tokens but at 5-epoch scale they did NOT have enough
            leverage to override the decoder's learned
            "The expression..." opener for valid rpm_chain shapes;
            human grading was 3/3 hijack. The seed flipped that to
            0/3 (commit e51f061) without leaking to the
            invalid_to_explanation path. Three layers of automatic
            gating keep this surgical:
              1. The flag itself.
              2. ``routing.task_type == "cas_to_english"`` — invalid
                 CAS routes to invalid_to_explanation and the seed
                 does not fire.
              3. ``_LET_VAR_RX`` matches only sources beginning with
                 ``let <var> = ...`` — non-let shapes (state
                 literals, recipes, fractals, meta-logic, CRO)
                 cause ``_build_rpm_silhouette_seed`` to return
                 ``None`` and no seed text is prepended.
            Pass ``seed_rpm_silhouette=False`` explicitly when
            running v1-vs-v1c-vs-seed comparison evals or any
            diagnostic that needs the raw model behavior.
        prepend_task_token: Option C v1c — when True, the tokenizer
            MUST be a ``TaskTokenExtendedTokenizer`` exposing
            ``task_token_ids``. The compilability gate's task_type
            is converted to the matching ``[VALID]`` / ``[INVALID]``
            token ID and prepended to ``cas_prefix_ids`` at position
            0 inside ``generate_reply``. Default ``False`` so v1
            checkpoints continue to work unchanged.
        apply_rpm_retry: Phase 3 experiment (default ``False`` —
            opt-in). When True, AND the first generation produced
            a non-empty ``rpm_repair_log.semantic_drifts`` AND the
            structural skeleton is intact, ``generate_reply`` is
            called a second time with a corrective prompt that
            includes vocabulary hints derived from the drifted
            axes. The retry result is postprocessed through
            Phase 1 + Phase 2; if it has STRICTLY FEWER drifts
            AND preserves stage coverage AND the edge match, it
            replaces the original. Otherwise the original stands.
            The model was NOT trained on corrective prompts, so
            in-context learning is the only mechanism by which
            the hint can bias the output. The experiment will tell
            us whether that's enough; falling back to the original
            on rejection means worst case is no regression.
        apply_fractal_decoder: v1e Phase 1B opt-in shadow mode
            (default ``False`` — production-default earned by data,
            not asserted). When True, AND routing is cas_to_english,
            AND ``parse_fractal(source_cas)`` returns non-None, the
            orchestrator runs TWO generations: a baseline
            (unconstrained) pass and a constrained pass that biases
            the decoder via a phrase-trie over the canonical Noetic
            colloquialism phrases for each fractal slot. The
            fail-closed comparator
            (``fractal_decoder.constrained_strictly_beats_baseline``)
            selects the constrained output ONLY when its verifier
            strictly improves on baseline AND its prose-quality is
            within 0.2 of baseline AND the constrained run did not
            hit a mid-decode failure state. Otherwise the baseline
            is returned and the failed constrained attempt is
            preserved in ``fractal_decoder_log`` for diagnosis.
            Per audit 2026-05-10: phrase-trie not first-token mask
            alone; fail-closed; preserve both outputs in eval
            artifacts. See ``docs/working/v1e_pointer_copy_fractal_
            decoder_design_2026_05_10.md`` for the full design.
        fractal_decoder_eos_bias: v1e Phase 1B Task #135 tuning
            lever 1 (default 0.0 — disabled). When > 0, the
            constrained pass adds this bias to the EOS logit AFTER
            all expected slots are committed. Suppresses trailing
            prose past the final slot that would otherwise
            contaminate the verifier's noetic count. Ignored when
            ``apply_fractal_decoder=False``. Smoke evidence
            2026-05-10: the model lands all slots in source order
            but trailing prose pushes ``found_k_count`` above
            expected; EOS bias is the targeted fix.
        fractal_decoder_first_n_mode: v1e Phase 1B Task #135 tuning
            lever 2 (default False). When True, the fail-closed
            comparator scores BOTH baseline and constrained on only
            the FIRST ``n`` extracted noetics (where ``n`` is the
            expected k-count). Decouples comparator from
            trailing-prose contamination without changing decode
            behavior. Ignored when ``apply_fractal_decoder=False``.
        fractal_decoder_leaf_exit_boundary: v1e Phase 1B Task #138
            tuning lever 3 (default False). When True, on EVERY
            trie-leaf reach the next decoder step is masked to
            allow ONLY whitespace / punctuation / conjunction
            tokens (plus EOS if pos==n). One-shot per leaf; clears
            after one step. Targets the word-boundary corruption
            failure mode where the trie commits "averse" but free
            decode emits "n" next, producing "aversen" which the
            verifier's word-boundary rule rejects. Ignored when
            ``apply_fractal_decoder=False``.
    """
    routing = route_by_compilability(source_cas)
    prompt_text = build_prompt_from_routing(
        source_cas=source_cas, routing=routing,
    )
    budget = _resolve_max_new_tokens(routing, max_new_tokens)

    seed_text: Optional[str] = None
    if seed_rpm_silhouette and routing.task_type == "cas_to_english":
        seed_text = _build_rpm_silhouette_seed(source_cas)

    prepend_token_id: Optional[int] = None
    if prepend_task_token:
        # The tokenizer must be a TaskTokenExtendedTokenizer with
        # task_token_ids. Pull the matching ID from the routing.
        task_ids = getattr(tokenizer, "task_token_ids", None)
        if task_ids is None:
            raise RuntimeError(
                "prepend_task_token=True requires a "
                "TaskTokenExtendedTokenizer with .task_token_ids; "
                f"got {type(tokenizer).__name__} with no task_token_ids"
            )
        prepend_token_id = int(task_ids.for_task_type(routing.task_type))

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
        seed_decoder_text=seed_text,
        prepend_cas_prefix_token_id=prepend_token_id,
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

    # Default outputs: baseline pass. Subsequent opt-in blocks
    # (fractal decoder, rpm retry) may replace these.
    final_pp = pp
    final_text = pp.final_text
    fractal_decoder_log: Optional[FractalDecoderLog] = None

    # v1e Phase 1B — opt-in shadow-mode fractal-aware constrained
    # decoder. Per audit 2026-05-10: dual-decode (baseline + constrained)
    # with fail-closed comparator; preserve both outputs in eval
    # artifacts. Default OFF until eval data proves promotion.
    if apply_fractal_decoder and routing.task_type == "cas_to_english":
        fractal_seq = parse_fractal(source_cas)
        if fractal_seq is not None:
            fractal_decoder_log = FractalDecoderLog(
                enabled=True,
                fired=True,
                notation=fractal_seq.notation,
                expected_k_values=list(fractal_seq.k_values),
                baseline_text=pp.final_text,
                baseline_verifier=(
                    pp.fractal_repair_log.to_dict()
                    if pp.fractal_repair_log is not None else None
                ),
            )
            trie = build_fractal_phrase_trie(tokenizer)
            state = FractalConstraintState(expected_k=fractal_seq.k_values)
            # Resolve EOS id once — used by both lever 1 (eos_bias) and
            # lever 3 (boundary mask, which adds EOS to the allowed set
            # when the boundary fires AFTER the final slot has committed).
            resolved_eos_id: Optional[int] = int(getattr(tokenizer, "EOS_ID", 0)) or None
            # v1e Phase 1B tuning lever 1 — optional EOS bias after the
            # final slot commits, suppressing trailing prose
            # contamination of the verifier's found_k_count.
            eos_id_for_bias: Optional[int] = None
            if fractal_decoder_eos_bias > 0.0:
                eos_id_for_bias = resolved_eos_id
            # v1e Phase 1B tuning lever 3 (Task #138) — leaf-exit
            # boundary-token bias. On EVERY trie-leaf reach, the
            # processor masks the next step to whitespace /
            # punctuation / conjunction tokens (or EOS if at
            # pos==n). Prevents "averse" → "aversen" corruption.
            boundary_ids: Optional[set[int]] = None
            if fractal_decoder_leaf_exit_boundary:
                boundary_ids = build_boundary_token_ids(tokenizer)
            callback = make_logits_processor(
                state, trie, tokenizer,
                eos_id=(
                    eos_id_for_bias
                    if eos_id_for_bias is not None
                    else (resolved_eos_id if fractal_decoder_leaf_exit_boundary else None)
                ),
                eos_bias=float(fractal_decoder_eos_bias),
                enforce_leaf_exit_boundary=bool(fractal_decoder_leaf_exit_boundary),
                boundary_token_ids=boundary_ids,
            )
            constrained_gen_out = generate_reply(
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
                seed_decoder_text=seed_text,
                prepend_cas_prefix_token_id=prepend_token_id,
                step_callback=callback,
            )
            constrained_raw = str(constrained_gen_out.get("reply_text", ""))
            constrained_stopped_on_eos = bool(
                constrained_gen_out.get("stopped_on_eos", False)
            )
            constrained_pp = postprocess(
                source_cas=source_cas,
                raw_gen=constrained_raw,
                routing=routing,
                apply_repair=apply_repair,
                stopped_on_eos=constrained_stopped_on_eos,
            )
            fractal_decoder_log.constrained_text = constrained_pp.final_text
            fractal_decoder_log.constrained_verifier = (
                constrained_pp.fractal_repair_log.to_dict()
                if constrained_pp.fractal_repair_log is not None else None
            )
            fractal_decoder_log.slot_commits = list(state.slot_commits)
            if state.failure_reason:
                fractal_decoder_log.notes.append(
                    f"constraint mid-decode failure: {state.failure_reason}"
                )
            # Fail-closed selection: constrained wins ONLY if its
            # verifier strictly improves AND prose-quality is within
            # 0.2 of baseline AND no mid-decode failure occurred.
            if (
                pp.fractal_repair_log is not None
                and constrained_pp.fractal_repair_log is not None
            ):
                better, reason = constrained_strictly_beats_baseline(
                    constrained_text=constrained_pp.final_text,
                    constrained_stopped_on_eos=constrained_stopped_on_eos,
                    constrained_verifier=constrained_pp.fractal_repair_log,
                    baseline_text=pp.final_text,
                    baseline_stopped_on_eos=stopped_on_eos,
                    baseline_verifier=pp.fractal_repair_log,
                    constraint_failure_reason=state.failure_reason,
                    first_n_mode=bool(fractal_decoder_first_n_mode),
                )
                if better:
                    fractal_decoder_log.selected = "constrained"
                    fractal_decoder_log.notes.append(reason)
                    final_pp = constrained_pp
                    final_text = constrained_pp.final_text
                else:
                    fractal_decoder_log.selected = "baseline"
                    fractal_decoder_log.fallback_reason = reason
            else:
                fractal_decoder_log.selected = "baseline"
                fractal_decoder_log.fallback_reason = (
                    "missing fractal_repair_log on one or both passes"
                )
        else:
            # Flag on but source isn't a fractal — log the no-fire so
            # the eval artifact carries proof the gate was respected.
            fractal_decoder_log = FractalDecoderLog(
                enabled=True, fired=False,
                fallback_reason="parse_fractal returned None",
            )
    elif apply_fractal_decoder:
        # Flag on but routing is invalid_to_explanation — log no-fire.
        fractal_decoder_log = FractalDecoderLog(
            enabled=True, fired=False,
            fallback_reason=(
                f"routing.task_type={routing.task_type!r}, "
                "fractal decoder only fires on cas_to_english"
            ),
        )

    # Phase 3 — corrective retry experiment. Opt-in via
    # apply_rpm_retry=True. Only fires when the original generation
    # had detectable Phase 2 drifts AND structural skeleton is
    # intact. The retry calls generate_reply a second time with a
    # corrective prompt (vocabulary hints derived from drifted axes)
    # and is accepted only if it strictly beats the original by the
    # comparison heuristic. The user's "don't auto-rewrite semantic
    # labels yet" guard is satisfied: the retry produces a fresh
    # generation; nothing is substituted in the post-generated text.
    rpm_retry_log: Optional[RpmRetryLog] = None
    if apply_rpm_retry and pp.rpm_repair_log is not None:
        rpm_retry_log = RpmRetryLog()
        gate_ok, gate_reason = should_attempt_retry(pp.rpm_repair_log)
        if not gate_ok:
            rpm_retry_log.attempted = False
            rpm_retry_log.reason = gate_reason
        else:
            corrective_prompt, hint_axes = build_corrective_prompt(
                source_cas=source_cas,
                drifts=pp.rpm_repair_log.semantic_drifts,
            )
            rpm_retry_log.attempted = True
            rpm_retry_log.hint_axes = hint_axes
            rpm_retry_log.corrective_prompt = corrective_prompt
            rpm_retry_log.n_drifts_original = len(
                pp.rpm_repair_log.semantic_drifts
            )
            if not hint_axes:
                rpm_retry_log.attempted = False
                rpm_retry_log.reason = "no actionable hints derivable from drifts"
            else:
                retry_gen_out = generate_reply(
                    model=model,
                    tokenizer=tokenizer,
                    prompt_text=corrective_prompt,
                    cas_expression=source_cas,
                    register=register,
                    max_new_tokens=budget,
                    sampling=sampling,
                    temperature=temperature,
                    top_p=top_p,
                    use_cas_prefix=use_cas_prefix,
                    device=device,
                    seed_decoder_text=seed_text,
                    prepend_cas_prefix_token_id=prepend_token_id,
                )
                retry_raw = str(retry_gen_out.get("reply_text", ""))
                retry_stopped_on_eos = bool(
                    retry_gen_out.get("stopped_on_eos", False)
                )
                retry_pp = postprocess(
                    source_cas=source_cas,
                    raw_gen=retry_raw,
                    routing=routing,
                    apply_repair=apply_repair,
                    stopped_on_eos=retry_stopped_on_eos,
                )
                rpm_retry_log.n_drifts_retry = (
                    len(retry_pp.rpm_repair_log.semantic_drifts)
                    if retry_pp.rpm_repair_log is not None else 0
                )
                better, reason = retry_strictly_beats_original(
                    original_log=pp.rpm_repair_log,
                    retry_log=retry_pp.rpm_repair_log,
                ) if retry_pp.rpm_repair_log is not None else (
                    False, "retry produced no rpm_repair_log"
                )
                rpm_retry_log.reason = reason
                if better:
                    rpm_retry_log.used_retry = True
                    final_pp = retry_pp
                    final_text = retry_pp.final_text

    return RoutedGenerationResult(
        final_text=final_text,
        raw_text=raw_text,
        routing=routing,
        prompt_used=prompt_text,
        postprocess_result=final_pp,
        seed_decoder_text=seed_text,
        rpm_retry_log=rpm_retry_log,
        fractal_decoder_log=fractal_decoder_log,
        generation_metadata={
            "n_steps": gen_out.get("n_steps"),
            "seed_token_count": gen_out.get("seed_token_count", 0),
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
