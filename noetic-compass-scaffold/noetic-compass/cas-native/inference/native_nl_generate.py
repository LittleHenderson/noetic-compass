"""Autoregressive sampling helper for CASNativeModel + NLGenerationHead.

This is the inference complement to the teacher-forced training path in
``cas-native/training/train_native_nl_gen.py``. The trainer uses
``CASNativeModel.forward_with_lm()`` with a known target reply at every
position simultaneously. Inference-time generation is different: feed BOS,
get the next-token distribution, sample, append, feed back, repeat until
EOS or ``max_new_tokens``.

Usage::

    from cas_native.inference.native_nl_generate import generate_reply

    out = generate_reply(
        model=cas_native_model_with_attached_head,
        tokenizer=extended_tokenizer_or_hybrid,
        prompt_text="I keep going back and forth on this decision.",
        cas_expression="^4^E_{F2}|f",
        register="f",
        max_new_tokens=80,
        sampling="temperature",
        temperature=0.8,
    )
    print(out["reply_text"])

Three sampling modes:

* ``greedy``: argmax — deterministic, useful for debugging
* ``temperature``: scaled softmax + multinomial (default)
* ``top_p``: nucleus sampling with temperature scaling

The encoder pass runs ONCE per call. Each subsequent decoder step reuses
the cached ``encoder_outputs`` and ``bottleneck_z``, so generation cost
scales with output length, not with re-encoding the prompt every step.

When ``return_trace=True`` the helper captures the head's
``GenerationTrace`` metadata (model_code_version, weights_sha,
cas_conditioning_repr) at the final decoding step. Per-step traces are
not captured by default — that would require running ``return_meta=True``
inside the loop and is a follow-on if Mode 7 needs per-token attribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import torch


# Match the collator's register-to-id mapping so generated samples are
# conditioned the same way the model was trained.
DEFAULT_REGISTER_TO_ID: dict[str, int] = {"T": 0, "A": 1, "f": 2, "E": 3}


def _resolve_bottleneck_z(pooled: torch.Tensor, bottleneck_dim: int) -> torch.Tensor:
    """Slice or zero-pad pooled hidden state to bottleneck_dim.

    Mirrors ``CASNativeModel.forward_with_lm``'s logic so inference and
    training use identical bottleneck construction.
    """
    if pooled.shape[-1] >= bottleneck_dim:
        return pooled[..., :bottleneck_dim].contiguous()
    pad = torch.zeros(
        pooled.shape[0],
        bottleneck_dim - pooled.shape[-1],
        device=pooled.device,
        dtype=pooled.dtype,
    )
    return torch.cat([pooled, pad], dim=-1)


def _sample_token(
    logits: torch.Tensor,
    *,
    sampling: str,
    temperature: float,
    top_p: float,
    disallowed: set[int],
) -> int:
    """Pick the next token id from a 1-D logits vector."""
    if logits.dim() != 1:
        raise ValueError(f"logits must be 1-D vocab vector; got {tuple(logits.shape)}")

    masked = logits.clone()
    for tok_id in disallowed:
        if 0 <= tok_id < masked.shape[0]:
            masked[tok_id] = float("-inf")

    if sampling == "greedy":
        return int(masked.argmax().item())

    if temperature <= 0:
        raise ValueError(f"temperature must be > 0 for stochastic sampling; got {temperature}")
    scaled = masked / float(temperature)
    probs = torch.softmax(scaled, dim=-1)

    if sampling == "temperature":
        return int(torch.multinomial(probs, num_samples=1).item())

    if sampling == "top_p":
        if not (0.0 < top_p <= 1.0):
            raise ValueError(f"top_p must be in (0, 1]; got {top_p}")
        sorted_probs, sorted_idx = torch.sort(probs, descending=True)
        cumprobs = torch.cumsum(sorted_probs, dim=-1)
        # Smallest index where cumulative prob crosses top_p — keep at
        # least one token.
        above = (cumprobs >= top_p).nonzero(as_tuple=False)
        cutoff = int(above[0].item()) if len(above) > 0 else len(sorted_probs) - 1
        mask = torch.zeros_like(probs)
        mask[sorted_idx[: cutoff + 1]] = 1.0
        masked_probs = probs * mask
        total = masked_probs.sum()
        if total.item() <= 0:
            return int(probs.argmax().item())
        masked_probs = masked_probs / total
        return int(torch.multinomial(masked_probs, num_samples=1).item())

    raise ValueError(f"unknown sampling mode: {sampling!r} (expected greedy|temperature|top_p)")


@dataclass(frozen=True)
class GenerateConfig:
    """Frozen sampling configuration. Constructed inside ``generate_reply``;
    surfaced in the result dict for provenance."""

    max_new_tokens: int
    sampling: str
    temperature: float
    top_p: float
    use_cas_prefix: bool
    register: str
    register_id: int


def generate_reply(
    model: Any,
    tokenizer: Any,
    prompt_text: str,
    *,
    cas_expression: Optional[str] = None,
    register: str = "T",
    register_to_id: Optional[dict[str, int]] = None,
    max_prompt_len: int = 256,
    max_cas_prefix_len: int = 32,
    max_new_tokens: int = 100,
    sampling: str = "temperature",
    temperature: float = 0.8,
    top_p: float = 0.9,
    use_cas_prefix: bool = False,
    device: str | torch.device = "cpu",
    return_trace: bool = False,
    seed_decoder_text: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a reply by sampling from CASNativeModel + NLGenerationHead.

    Args:
        model: ``CASNativeModel`` with ``nl_gen_head`` already attached
            via ``attach_nl_gen_head``.
        tokenizer: ``HybridCASTokenizer`` or ``ExtendedHybridCASTokenizer``.
            Must expose ``encode(text, max_length, *, add_special)``,
            ``decode(ids, *, skip_special)``, ``BOS_ID``, ``EOS_ID``,
            ``PAD_ID``, ``UNK_ID``, and (optional) ``vocab_size``.
        prompt_text: the user's input as a single string.
        cas_expression: optional CAS expression to use as discrete prefix
            tokens. Only consumed when ``use_cas_prefix=True``; default
            False matches the trainer's --use-cas-prefix off default
            (PAD-leakage guard until NLGenerationHead exposes a mask).
        register: register character (``T``/``A``/``f``/``E``).
        register_to_id: override the default register-to-id mapping.
        max_prompt_len: cap on prompt token length.
        max_cas_prefix_len: cap on CAS expression token length.
        max_new_tokens: hard upper bound on generated reply length.
        sampling: ``"greedy"`` | ``"temperature"`` | ``"top_p"``.
        temperature: softmax temperature for stochastic sampling.
        top_p: nucleus cutoff (only used when ``sampling="top_p"``).
        use_cas_prefix: pass cas_prefix_ids into the head. Default OFF.
        device: torch device for tensors.
        return_trace: when True, capture the head's metadata
            (``model_code_version``, ``model_weights_sha``,
            ``cas_conditioning_id``, ``attention_summary``) at the final
            decoding step.

    Returns:
        A dict with::

            {
                "reply_text": str,           # decoded reply (special tokens stripped)
                "token_ids": list[int],      # generated token ids (excluding BOS, EOS)
                "n_steps": int,              # how many tokens were sampled
                "stopped_on_eos": bool,      # True if EOS terminated, False if max_new_tokens hit
                "prompt_text": str,
                "cas_expression": str | None,
                "config": dict,              # full GenerateConfig as dict
                "trace": dict | None,        # head metadata when return_trace=True
            }

    Raises:
        RuntimeError: if ``model.nl_gen_head`` is not attached.
        ValueError: if sampling mode or temperature is invalid.
    """
    head = getattr(model, "nl_gen_head", None)
    if head is None:
        raise RuntimeError(
            "model.nl_gen_head is not attached — call "
            "model.attach_nl_gen_head(NLGenerationHead(...)) before generating."
        )

    reg_map = dict(register_to_id) if register_to_id is not None else dict(DEFAULT_REGISTER_TO_ID)
    register_id = int(reg_map.get(register, 0))
    config = GenerateConfig(
        max_new_tokens=int(max_new_tokens),
        sampling=str(sampling),
        temperature=float(temperature),
        top_p=float(top_p),
        use_cas_prefix=bool(use_cas_prefix),
        register=str(register),
        register_id=register_id,
    )

    device_t = torch.device(device)
    model.eval()

    # ------------------------------------------------------------------
    # 1. Tokenize prompt + (optional) CAS expression
    # ------------------------------------------------------------------
    prompt_ids = list(tokenizer.encode(prompt_text, max_length=max_prompt_len, add_special=False))[:max_prompt_len]
    if not prompt_ids:
        # Defensive: tokenizer returned nothing — treat as a single-pad
        # encoding so the encoder still runs without index errors.
        prompt_ids = [int(tokenizer.PAD_ID)]

    cas_prefix_ids: list[int] = []
    if use_cas_prefix and cas_expression:
        cas_prefix_ids = list(
            tokenizer.encode(cas_expression, max_length=max_cas_prefix_len, add_special=False)
        )[:max_cas_prefix_len]

    # ------------------------------------------------------------------
    # 2. Encoder pass once — cache encoder_outputs + bottleneck_z
    # ------------------------------------------------------------------
    input_ids = torch.tensor([prompt_ids], dtype=torch.long, device=device_t)
    attention_mask = torch.ones_like(input_ids, dtype=torch.bool)

    head_cfg = head.config
    bottleneck_dim = int(head_cfg.bottleneck_dim)

    with torch.no_grad():
        encoder_out = model.forward(input_ids, attention_mask=attention_mask)
        encoder_outputs = encoder_out["hidden_states"]
        pooled = encoder_out["pooled_hidden_state"]
        bottleneck_z = _resolve_bottleneck_z(pooled, bottleneck_dim)

    cas_prefix_tensor: Optional[torch.Tensor] = None
    cas_prefix_mask_tensor: Optional[torch.Tensor] = None
    if cas_prefix_ids:
        cas_prefix_tensor = torch.tensor([cas_prefix_ids], dtype=torch.long, device=device_t)
        # Single example, no PAD — every prefix position is real. The
        # mask is still required so that the head's self-attention path
        # honors the same B-4 PAD-leak guard regardless of caller.
        cas_prefix_mask_tensor = torch.ones(
            (1, len(cas_prefix_ids)), dtype=torch.bool, device=device_t
        )

    register_tensor = torch.tensor([register_id], dtype=torch.long, device=device_t)

    # ------------------------------------------------------------------
    # 3. Autoregressive sampling loop
    # ------------------------------------------------------------------
    bos_id = int(tokenizer.BOS_ID)
    eos_id = int(tokenizer.EOS_ID)
    pad_id = int(tokenizer.PAD_ID)
    unk_id = int(tokenizer.UNK_ID)
    disallowed: set[int] = {pad_id, unk_id, bos_id}

    seq: list[int] = [bos_id]
    seed_token_count = 0
    if seed_decoder_text:
        # Decoder-seeding: force the autoregressive trajectory to start
        # from a specific surface form. Used as a diagnostic patch for
        # the v1 PREFIX128 5ep rpm_chain misroute (the model's cas_prefix
        # is locked into invalid-explanation language for `let X = ...;
        # X -> Y` shapes; seeding the decoder with `"Let X name "` forces
        # it onto the let-binding silhouette so we can test whether the
        # rpm_chain content is recoverable). Seeded tokens are part of
        # `seq` and become part of the output reply; `n_steps` counts
        # only NEWLY GENERATED tokens after the seed.
        seed_ids = list(
            tokenizer.encode(
                seed_decoder_text,
                max_length=1024,
                add_special=False,
            )
        )
        seq.extend(seed_ids)
        seed_token_count = len(seed_ids)
    stopped_on_eos = False
    final_meta: Optional[dict[str, Any]] = None

    for step in range(int(max_new_tokens)):
        dec_input = torch.tensor([seq], dtype=torch.long, device=device_t)
        with torch.no_grad():
            is_last_possible = (step == int(max_new_tokens) - 1)
            want_meta = bool(return_trace) and is_last_possible
            head_out = head(
                dec_input,
                bottleneck_z,
                cas_prefix_ids=cas_prefix_tensor,
                cas_prefix_mask=cas_prefix_mask_tensor,
                encoder_outputs=encoder_outputs,
                domain_mask=attention_mask,
                register_id=register_tensor,
                return_meta=want_meta,
            )
            if want_meta:
                logits, meta = head_out  # head returns (logits, meta) when return_meta=True
                final_meta = dict(meta)
            else:
                logits = head_out

        next_logits = logits[0, -1, :]
        next_id = _sample_token(
            next_logits,
            sampling=config.sampling,
            temperature=config.temperature,
            top_p=config.top_p,
            disallowed=disallowed,
        )

        seq.append(next_id)
        if next_id == eos_id:
            stopped_on_eos = True
            # If the caller asked for trace, also capture meta on the
            # actual final step (which won't be max-1 if EOS came early).
            if return_trace and final_meta is None:
                with torch.no_grad():
                    _logits, meta = head(
                        torch.tensor([seq], dtype=torch.long, device=device_t),
                        bottleneck_z,
                        cas_prefix_ids=cas_prefix_tensor,
                        cas_prefix_mask=cas_prefix_mask_tensor,
                        encoder_outputs=encoder_outputs,
                        domain_mask=attention_mask,
                        register_id=register_tensor,
                        return_meta=True,
                    )
                    final_meta = dict(meta)
            break

    # ------------------------------------------------------------------
    # 4. Decode (skip BOS, drop trailing EOS if present)
    # ------------------------------------------------------------------
    output_ids = seq[1:]  # drop BOS
    if stopped_on_eos and output_ids and output_ids[-1] == eos_id:
        output_ids = output_ids[:-1]

    reply_text = tokenizer.decode(output_ids, skip_special=True)

    return {
        "reply_text": reply_text,
        "token_ids": list(output_ids),
        # n_steps counts NEWLY GENERATED tokens only — the BOS and the
        # optional decoder-seed prefix do not count as model "steps."
        "n_steps": len(seq) - 1 - seed_token_count,
        "seed_token_count": seed_token_count,
        "stopped_on_eos": stopped_on_eos,
        "prompt_text": prompt_text,
        "cas_expression": cas_expression,
        "config": {
            "max_new_tokens": config.max_new_tokens,
            "sampling": config.sampling,
            "temperature": config.temperature if config.sampling != "greedy" else None,
            "top_p": config.top_p if config.sampling == "top_p" else None,
            "use_cas_prefix": config.use_cas_prefix,
            "register": config.register,
            "register_id": config.register_id,
        },
        "trace": final_meta,
    }


__all__ = ["generate_reply", "GenerateConfig", "DEFAULT_REGISTER_TO_ID"]
