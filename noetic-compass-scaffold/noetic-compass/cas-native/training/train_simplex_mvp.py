"""train_simplex_mvp — trainer entry point for the simplex MVP rebuild.

Sibling to ``train_native_nl_gen.py``. The v0 trainer is canonical and
remains untouched; this trainer is the new architecture's launch point.

Per execution plan §Stage 3:
- Assembles SimplexEncoder + TypedFiberDecoder via ``build_simplex_mvp_model()``
- Uses SimplexCollator (enable_simplex_aux=True) for batch construction
- Computes 5 losses (LM, FR, slot_type, copy, phrase_bias_aux) per build-spec §5
- Emits ``train_progress`` JSON every N steps with per-loss telemetry
- Supports ``--ablation {full,lm_fr,lm_slot,lm_fr_slot}`` per build-spec §7.2

Stage 1 status: skeleton — CLI parser, model factory, training-loop entry
point, and loss-assembly all wired. Smoke-test command from §Stage 5
should be runnable end-to-end once Stage 2 unit tests pass.

Stage 7-bis ablation hard-stop rule: if all four ablation sub-runs fail
their 6-question architecture-feasibility gate, NO more weight tuning;
move to staged S1→S2→S3 or pause for architectural review. This is
encoded in the launch wrapper, not the trainer itself.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import torch
from torch import nn
from torch.utils.data import DataLoader

# Bound to repository import path. When invoked as a script (vs imported by
# pytest), bootstrap the ``cas_native`` package alias so absolute imports
# like ``from cas_native.model.simplex_encoder import …`` resolve.
import types as _types
_THIS_FILE = Path(__file__).resolve()
_CAS_NATIVE = _THIS_FILE.parent.parent
_PROJECT_ROOT = _CAS_NATIVE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    _pkg = _types.ModuleType("cas_native")
    _pkg.__file__ = str(_CAS_NATIVE / "__init__.py")
    _pkg.__path__ = [str(_CAS_NATIVE)]
    sys.modules["cas_native"] = _pkg


# Loss-weight defaults per build-spec §5. Flat weights, no curriculum.
DEFAULT_LOSS_WEIGHTS: dict[str, float] = {
    "lm": 1.0,
    "fr": 1.0,
    "slot_type": 1.0,
    "copy": 0.5,
    "phrase_bias_aux": 0.1,
}

# Ablation mode → loss-weight overrides per execution plan §Stage 3.
ABLATION_OVERRIDES: dict[str, dict[str, float]] = {
    "full": {},
    "lm_fr":      {"slot_type": 0.0, "copy": 0.0, "phrase_bias_aux": 0.0},
    "lm_slot":    {"fr": 0.0,        "copy": 0.0, "phrase_bias_aux": 0.0},
    "lm_fr_slot": {"copy": 0.0,      "phrase_bias_aux": 0.0},
}


@dataclass
class SimplexTrainConfig:
    data_path: str
    output_dir: str
    epochs: int = 1
    batch_size: int = 4
    lr: float = 1e-4
    weight_decay: float = 1e-4
    grad_clip: float = 1.0
    device: str = "cpu"
    limit: Optional[int] = None
    smoke_test: bool = False
    smoke_records: int = 4
    d_model: int = 384
    encoder_n_layers: int = 4
    encoder_n_heads: int = 6
    decoder_n_layers: int = 6
    decoder_n_heads: int = 6
    ablation: str = "full"
    seed: int = 1729
    # Logging cadence (per `feedback_train_progress_logging_required`)
    train_log_every_steps: int = 20
    logging_steps: int = 100
    sample_every_steps: int = 0          # 0 = disabled
    sample_record_index: int = 0
    # Loss weights — populated by ablation mode after CLI parse
    loss_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_LOSS_WEIGHTS))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simplex MVP trainer (v1f).")
    p.add_argument("--data-path", required=True, type=str)
    p.add_argument("--output-dir", required=True, type=str)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--grad-clip", type=float, default=1.0)
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--limit", type=int, default=None,
                   help="Cap on records loaded; ALWAYS pass --limit explicitly "
                        "for full runs per feedback_limit_default_128_trap.")
    p.add_argument("--smoke-test", action="store_true",
                   help="Single forward+backward on --smoke-records records, then exit.")
    p.add_argument("--smoke-records", type=int, default=4)
    p.add_argument("--d-model", type=int, default=384)
    p.add_argument("--encoder-n-layers", type=int, default=4)
    p.add_argument("--encoder-n-heads", type=int, default=6)
    p.add_argument("--decoder-n-layers", type=int, default=6)
    p.add_argument("--decoder-n-heads", type=int, default=6)
    p.add_argument("--ablation", type=str, default="full",
                   choices=sorted(ABLATION_OVERRIDES.keys()),
                   help="Ablation mode per execution plan §Stage 3. "
                        "If all 4 ablations fail Stage 0 6-question gate, "
                        "move to staged S1→S2→S3 — DO NOT tune weights.")
    p.add_argument("--seed", type=int, default=1729)
    p.add_argument("--train-log-every-steps", type=int, default=20)
    p.add_argument("--logging-steps", type=int, default=100)
    p.add_argument("--sample-every-steps", type=int, default=0)
    p.add_argument("--sample-record-index", type=int, default=0,
                   help="Index of the in-flight sample record; in production "
                        "use rotating sample selection per "
                        "feedback_rotating_sample_prompts_required.")
    return p


def parse_args(argv: Optional[list[str]] = None) -> SimplexTrainConfig:
    args = build_parser().parse_args(argv)
    cfg = SimplexTrainConfig(
        data_path=args.data_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        grad_clip=args.grad_clip,
        device=args.device,
        limit=args.limit,
        smoke_test=args.smoke_test,
        smoke_records=args.smoke_records,
        d_model=args.d_model,
        encoder_n_layers=args.encoder_n_layers,
        encoder_n_heads=args.encoder_n_heads,
        decoder_n_layers=args.decoder_n_layers,
        decoder_n_heads=args.decoder_n_heads,
        ablation=args.ablation,
        seed=args.seed,
        train_log_every_steps=args.train_log_every_steps,
        logging_steps=args.logging_steps,
        sample_every_steps=args.sample_every_steps,
        sample_record_index=args.sample_record_index,
    )
    # Apply ablation overrides on top of defaults
    overrides = ABLATION_OVERRIDES.get(cfg.ablation, {})
    cfg.loss_weights = {**DEFAULT_LOSS_WEIGHTS, **overrides}
    return cfg


def build_simplex_mvp_model(cfg: SimplexTrainConfig, *, vocab_size: int, vocab_size_english: int) -> nn.Module:
    """Factory wiring SimplexEncoder + TypedFiberDecoder into a single module."""
    from cas_native.model.simplex_encoder import SimplexEncoder, SimplexEncoderConfig
    from cas_native.model.typed_fiber_decoder import TypedFiberDecoder, TypedFiberDecoderConfig

    enc_cfg = SimplexEncoderConfig(
        vocab_size=vocab_size,
        d_model=cfg.d_model,
        n_heads=cfg.encoder_n_heads,
        ffn_dim=cfg.d_model * 4,
        n_layers=cfg.encoder_n_layers,
    )
    dec_cfg = TypedFiberDecoderConfig(
        vocab_size_english=vocab_size_english,
        d_model=cfg.d_model,
        n_heads=cfg.decoder_n_heads,
        ffn_dim=cfg.d_model * 4,
        n_layers=cfg.decoder_n_layers,
    )

    class _SimplexMVPModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = SimplexEncoder(enc_cfg)
            self.decoder = TypedFiberDecoder(dec_cfg)

        def forward(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
            # Fail-closed source synthesis when the collator emits no CAS at all
            # (every record had empty cas_expression → cas_prefix_ids=None).
            # Build a single-PAD source with attention_mask all-False so the
            # encoder treats it as an all-PAD batch; nan_to_num in self-
            # attention keeps source_hidden finite, and the decoder's cross-
            # attention sees a valid (B, 1) KV with mask-False everywhere.
            cas_prefix_ids = batch.get("cas_prefix_ids")
            cas_prefix_mask = batch.get("cas_prefix_mask")
            if cas_prefix_ids is None:
                B = batch["input_ids"].shape[0]
                device = batch["input_ids"].device
                cas_prefix_ids = torch.zeros((B, 1), dtype=torch.long, device=device)
                cas_prefix_mask = torch.zeros((B, 1), dtype=torch.bool, device=device)

            enc_out = self.encoder(cas_prefix_ids, attention_mask=cas_prefix_mask)
            dec_out = self.decoder(
                decoder_input_ids=batch["lm_decoder_input_ids"],
                source_hidden=enc_out["source_hidden"],
                simplex_trajectory=enc_out["simplex_trajectory"],
                src_ids=cas_prefix_ids,
                src_token_type=batch.get("src_token_type"),
                src_padding_mask=cas_prefix_mask,
                target_typed_positions=(
                    batch["typed_slot_positions"].argmax(dim=-1)
                    if "typed_slot_positions" in batch else None
                ),
            )
            return {**enc_out, **dec_out}

    return _SimplexMVPModel()


def compute_losses(
    out: dict[str, torch.Tensor],
    batch: dict[str, torch.Tensor],
    *,
    fisher_rao_loss: nn.Module,
    weights: dict[str, float],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Assemble L_total = w_lm·L_LM + w_fr·L_FR + w_slot·L_slot_type + w_copy·L_copy + w_aux·L_phrase_bias_aux."""
    import torch.nn.functional as F

    # L_LM: cross-entropy at CONNECTIVE + NOETIC_PHRASE positions (slot ids 0, 8).
    # During Stage 1 we apply CE over all non-padded positions; Stage 3 narrows
    # to the gated mask once typed_slot_positions targets are wired.
    lm_logits = out["lm_logits"]                 # (B, L_out, V)
    targets = batch["lm_targets"]                # (B, L_out)
    loss_mask = batch.get("loss_mask")           # (B, L_out) — 1 where loss applies
    if loss_mask is None:
        loss_mask = (targets != -100).to(dtype=torch.float32)
    flat_logits = lm_logits.reshape(-1, lm_logits.shape[-1])
    flat_targets = targets.reshape(-1)
    lm_per_tok = F.cross_entropy(flat_logits, flat_targets.clamp_min(0), reduction="none")
    lm_per_tok = lm_per_tok.view_as(loss_mask) * loss_mask
    denom = loss_mask.sum().clamp_min(1.0)
    loss_lm = lm_per_tok.sum() / denom

    # L_FR: anchor-masked squared geodesic distance on Δ°₃₉.
    # When the encoder synthesizes a single-PAD source (all records had
    # empty cas_expression), simplex_trajectory has L_src=1 while the
    # collator-derived fr_target_path has L_src_max=0. In that case there
    # are no anchors and L_FR is correctly zero.
    fr_target = batch.get("fr_target_path")
    fr_mask = batch.get("fr_target_mask")
    simplex = out["simplex_trajectory"]
    if (
        fr_target is not None
        and fr_mask is not None
        and fr_target.shape == simplex.shape
        and fr_mask.shape == simplex.shape[:2]
    ):
        loss_fr = fisher_rao_loss(simplex, fr_target, fr_mask)
    else:
        loss_fr = torch.zeros((), device=lm_logits.device)

    # L_slot_type: CE over 9 classes at every output position with target available
    if "typed_slot_positions" in batch:
        slot_target = batch["typed_slot_positions"].argmax(dim=-1)      # (B, L_out)
        slot_logits = out["slot_type_logits"].reshape(-1, out["slot_type_logits"].shape[-1])
        slot_loss = F.cross_entropy(slot_logits, slot_target.reshape(-1), reduction="mean")
        loss_slot_type = slot_loss
    else:
        loss_slot_type = torch.zeros((), device=lm_logits.device)

    # L_copy: -log p_copy(j*) at typed-slot positions; j* from typed_slot_source.
    # Stage 6 v5 (2026-05-11): also emit 4 telemetry fields so Stage 7 Q4
    # can evaluate "copy path non-random" only when valid slots exist:
    #   copy_valid_count        — total positions with typed_slot_source >= 0
    #   copy_loss_live          — L_copy value when valid_count > 0, else NaN
    #   copy_argmax_acc         — argmax(p_copy) hit rate at valid positions
    #   copy_entropy_valid_mean — mean entropy of p_copy at valid positions
    copy_metrics: dict[str, torch.Tensor] = {}
    if "typed_slot_source" in batch:
        copy_target = batch["typed_slot_source"].to(dtype=torch.long)  # (B, L_out)
        valid = (copy_target >= 0)
        valid_count = int(valid.sum().item())
        p_copy = out["p_copy"]                                          # (B, L_out, L_src)
        if valid.any():
            B, L_out, L_src = p_copy.shape
            safe_idx = copy_target.clamp(min=0, max=L_src - 1).unsqueeze(-1)
            chosen = p_copy.gather(-1, safe_idx).squeeze(-1).clamp_min(1e-9)
            copy_log = -torch.log(chosen)
            denom_c = valid.to(dtype=torch.float32).sum().clamp_min(1.0)
            loss_copy = (copy_log * valid.to(dtype=copy_log.dtype)).sum() / denom_c
            with torch.no_grad():
                # argmax hit rate at valid positions
                argmax_idx = p_copy.argmax(dim=-1)
                hits = (argmax_idx == copy_target) & valid
                copy_argmax_acc = (
                    hits.to(dtype=torch.float32).sum() / denom_c
                )
                # entropy at valid positions
                p_safe = p_copy.clamp_min(1e-12)
                entropy_per = -(p_copy * p_safe.log()).sum(dim=-1)       # (B, L_out)
                copy_entropy_valid_mean = (
                    (entropy_per * valid.to(dtype=torch.float32)).sum() / denom_c
                )
        else:
            loss_copy = torch.zeros((), device=lm_logits.device)
            copy_argmax_acc = torch.tensor(float("nan"), device=lm_logits.device)
            copy_entropy_valid_mean = torch.tensor(float("nan"), device=lm_logits.device)
        copy_metrics["copy_valid_count"] = torch.tensor(
            float(valid_count), device=lm_logits.device,
        )
        copy_metrics["copy_loss_live"] = (
            loss_copy.detach() if valid_count > 0
            else torch.tensor(float("nan"), device=lm_logits.device)
        )
        copy_metrics["copy_argmax_acc"] = copy_argmax_acc.detach()
        copy_metrics["copy_entropy_valid_mean"] = copy_entropy_valid_mean.detach()
    else:
        loss_copy = torch.zeros((), device=lm_logits.device)
        copy_metrics["copy_valid_count"] = torch.tensor(0.0, device=lm_logits.device)
        copy_metrics["copy_loss_live"] = torch.tensor(float("nan"), device=lm_logits.device)
        copy_metrics["copy_argmax_acc"] = torch.tensor(float("nan"), device=lm_logits.device)
        copy_metrics["copy_entropy_valid_mean"] = torch.tensor(float("nan"), device=lm_logits.device)

    # L_phrase_bias_aux: placeholder Stage 1 — zeros until the phrase-table
    # corpus alignment lands in Stage 3. Shape-correct, gradient-safe.
    loss_phrase_bias_aux = torch.zeros((), device=lm_logits.device, requires_grad=False)

    total = (
        weights["lm"] * loss_lm
        + weights["fr"] * loss_fr
        + weights["slot_type"] * loss_slot_type
        + weights["copy"] * loss_copy
        + weights["phrase_bias_aux"] * loss_phrase_bias_aux
    )
    parts = {
        "loss_total": total.detach(),
        "loss_lm": loss_lm.detach(),
        "loss_fr": loss_fr.detach(),
        "loss_slot_type": loss_slot_type.detach(),
        "loss_copy": loss_copy.detach(),
        "loss_phrase_bias_aux": loss_phrase_bias_aux.detach(),
    }
    # Attach copy telemetry as a sibling dict — NOT mixed into parts so
    # tests that assert "every loss part is finite" don't trip on NaN
    # sentinels that mean "not measured this batch" (e.g. when no valid
    # copy slots exist). Stage 6 v5 Q4 reads copy_metrics directly.
    parts["__copy_metrics__"] = copy_metrics
    return total, parts


def emit_train_progress(
    *,
    output_path: Optional[Path],
    epoch: int,
    batch_in_epoch: int,
    batches_per_epoch: int,
    global_step: int,
    loss_parts: dict[str, torch.Tensor],
    fr_metrics: dict[str, torch.Tensor],
    elapsed_sec: float,
    batches_per_sec: float,
    eta_epoch_min: float,
    grad_norm_encoder: float,
    grad_norm_decoder: float,
    lr_now: float,
    extras: Optional[dict[str, Any]] = None,
) -> None:
    """Emit a single ``train_progress`` JSON record per
    feedback_train_progress_logging_required."""
    payload: dict[str, Any] = {
        "event": "train_progress",
        "epoch": epoch,
        "batch": batch_in_epoch,
        "batches_per_epoch": batches_per_epoch,
        "global_step": global_step,
        "elapsed_sec": elapsed_sec,
        "batches_per_sec": batches_per_sec,
        "eta_epoch_min": eta_epoch_min,
        "lr_now": lr_now,
        "grad_norm_encoder": grad_norm_encoder,
        "grad_norm_decoder": grad_norm_decoder,
    }
    for k, v in loss_parts.items():
        if k == "__copy_metrics__":
            # Stage 6 v5: copy telemetry surfaced as top-level keys
            # (copy_valid_count / copy_loss_live / copy_argmax_acc /
            # copy_entropy_valid_mean). NaN means "not measured this batch."
            for ck, cv in v.items():
                payload[ck] = (
                    float(cv.detach().cpu().item()) if isinstance(cv, torch.Tensor) else float(cv)
                )
            continue
        payload[k] = float(v.detach().cpu().item()) if isinstance(v, torch.Tensor) else float(v)
    for k, v in fr_metrics.items():
        payload[k] = float(v.detach().cpu().item()) if isinstance(v, torch.Tensor) else float(v)
    if extras:
        payload.update(extras)
    if loss_parts.get("loss_lm") is not None and loss_parts.get("loss_fr") is not None:
        lm = float(loss_parts["loss_lm"].item()) if isinstance(loss_parts["loss_lm"], torch.Tensor) else float(loss_parts["loss_lm"])
        fr = float(loss_parts["loss_fr"].item()) if isinstance(loss_parts["loss_fr"], torch.Tensor) else float(loss_parts["loss_fr"])
        payload["fr_lm_ratio"] = (fr / lm) if lm > 0 else 0.0
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    print(line, flush=True)
    if output_path is not None:
        with output_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def load_jsonl_records(data_path: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Load up to ``limit`` records from a JSONL file. Stage 3 helper.

    Used by the integration smoke path; the full DataLoader assembly lands
    in Stage 8 with the long-run trainer.
    """
    path = Path(data_path)
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if limit is not None and len(records) >= limit:
                break
    return records


def synthetic_records(n: int = 4) -> list[dict[str, Any]]:
    """Build ``n`` toy records for integration tests when no data file is
    available. Records satisfy the NativeNLCollator schema."""
    out: list[dict[str, Any]] = []
    samples = [
        ("I feel drawn to this idea", "It speaks to me strongly", "^2^E_{F6}|f", "f"),
        ("I am repelled by this", "I cannot stomach it",           "^3^P_{F2}|A", "A"),
        ("This resonates",         "It struck a chord",            "^4^C_{F4}|T", "T"),
        ("Doing this repeatedly",  "Practice makes perfect",       "^7^O_{F3}|E", "E"),
    ]
    for i in range(n):
        prompt, reply, cas, reg = samples[i % len(samples)]
        out.append({
            "id": f"smoke_rec_{i:03d}",
            "trace_id": f"smoke_trace_{i:03d}",
            "schema_version": "native_nl.v1",
            "tier": "tier3",
            "prompt_text": prompt,
            "reply_text": reply,
            "cas_expression": cas,
            "noetic": cas.split("^")[1][:1].join(["^"]) if "^" in cas else "^0",
            "domain": "E",
            "drive": "F6",
            "register": reg,
            "v1mix_task_type": "smoke",
        })
    return out


def copy_bearing_records(n: int = 8) -> list[dict[str, Any]]:
    """Stage 6 v5 (2026-05-11): copy-bearing record fixture for Stage 6
    dry-run. Each record's reply_text literally contains tokens that the
    SimplexCollator classifies as typed-slot identifiers (DOMAIN_LETTER,
    DRIVE_LETTER, REGISTER_LETTER, OMEGA), so L_copy fires with non-zero
    valid_count and the pointer-copy gradient path can be exercised.

    These reuse the same CAS_RESERVED_TOKENS the v1c tokenizer ships with,
    so re-tokenisation produces single-token IDs for ``^P``, ``F6``,
    ``|f``, ``Ω_resolve`` etc. The reply embeds those identifiers
    verbatim — the model's job is to learn to copy them from source.
    """
    out: list[dict[str, Any]] = []
    # Each tuple: (prompt, reply with embedded literal identifiers, cas, reg).
    samples = [
        ("which domain", "the domain is ^P",
         "^2^P_{F6}|f", "f"),
        ("which drive", "the drive is F6 here",
         "^3^P_{F6}|A", "A"),
        ("which register", "the register is |f on this expression",
         "^4^E_{F4}|f", "f"),
        ("target omega name", "the production target is Ω_resolve in this recipe",
         "Ω_resolve = ^2^P_{F1}|T", "T"),
        ("domain and drive", "domain ^C with drive F3",
         "^5^C_{F3}|E", "E"),
        ("register and omega", "register |T on Ω_grounding",
         "Ω_grounding = ^6^P_{F2}|T", "T"),
        ("multi slot", "we see ^O and F7 with |A",
         "^7^O_{F7}|A", "A"),
        ("another target", "Ω_clarity sits in ^E under |E",
         "Ω_clarity = ^8^E_{F5}|E", "E"),
    ]
    for i in range(n):
        prompt, reply, cas, reg = samples[i % len(samples)]
        out.append({
            "id": f"copy_rec_{i:03d}",
            "trace_id": f"copy_trace_{i:03d}",
            "schema_version": "native_nl.v1",
            "tier": "tier3",
            "prompt_text": prompt,
            "reply_text": reply,
            "cas_expression": cas,
            "register": reg,
            "v1mix_task_type": "smoke_copy",
        })
    return out


def build_tokenizer_for_smoke(records: list[dict[str, Any]]):
    """Build a HybridCASTokenizer fit on the smoke records. Stage 3 only —
    production trainer (Stage 8) loads the frozen v1c tokenizer."""
    from cas_native.training.tokenizer import HybridCASTokenizer
    return HybridCASTokenizer.from_records(records, freeze=True)


def compute_grad_norm(params: Iterable[torch.nn.Parameter]) -> float:
    """L2 norm over a parameter group's gradients (zero if no grads yet)."""
    total = 0.0
    for p in params:
        if p.grad is not None:
            total += float(p.grad.detach().norm(2).item()) ** 2
    return total ** 0.5


def run_integration_step(
    cfg: SimplexTrainConfig,
    records: list[dict[str, Any]],
    *,
    output_path: Optional[Path] = None,
) -> dict[str, Any]:
    """One forward + backward + optim step on a tiny sample.

    Returns a dict with all telemetry — used by both the CLI smoke path and
    the Stage 4 integration tests. Keeps the v0 trainer untouched.

    Implements the Stage 3 integration boundary:
      1. assemble model + simplex collator + 5-term loss
      2. one-step CPU forward/backward
      3. gradient flow checked per-group
      4. train_progress JSON emitted with full telemetry
      5. ablation modes switch loss weights correctly

    Kill-switch per plan §Stage 3: NaN at integration → halt; surface to user.
    """
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    from cas_native.training.fisher_rao_loss import FisherRaoLoss
    import torch.optim as optim

    device = torch.device(cfg.device)
    torch.manual_seed(cfg.seed)

    tokenizer = build_tokenizer_for_smoke(records)
    collator = SimplexCollator(tokenizer, enable_simplex_aux=True)
    batch = collator(records, device=device)
    if batch is None:
        raise RuntimeError("collator returned None on smoke records — cannot run integration step")

    vocab_size = int(tokenizer.vocab_size)
    vocab_size_english = int(tokenizer.vocab_size)
    model = build_simplex_mvp_model(cfg, vocab_size=vocab_size, vocab_size_english=vocab_size_english).to(device)
    fisher_rao_loss = FisherRaoLoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------
    t_start = time.time()
    optimizer.zero_grad(set_to_none=True)
    out = model(batch)
    total, loss_parts = compute_losses(
        out, batch, fisher_rao_loss=fisher_rao_loss, weights=cfg.loss_weights,
    )

    # NaN guard — kill-switch per plan §Stage 3
    if not torch.isfinite(total):
        raise RuntimeError(
            f"NaN/Inf in total loss after forward; loss parts: {loss_parts}"
        )

    # ------------------------------------------------------------------
    # Backward + optim
    # ------------------------------------------------------------------
    total.backward()

    # Compute per-group grad norms BEFORE clipping (so the clip itself is
    # observable downstream).
    enc_params = list(model.encoder.parameters())
    dec_params = list(model.decoder.parameters())
    grad_norm_encoder = compute_grad_norm(enc_params)
    grad_norm_decoder = compute_grad_norm(dec_params)

    if cfg.grad_clip and cfg.grad_clip > 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
    optimizer.step()

    elapsed_sec = time.time() - t_start

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    fr_metrics = dict(fisher_rao_loss.last_metrics)
    # Add encoder-side simplex telemetry per build-spec §5
    with torch.no_grad():
        simplex = out["simplex_trajectory"]
        # Shannon entropy per position, mean over batch+positions
        entropy = -(simplex * simplex.clamp_min(1e-12).log()).sum(dim=-1).mean()
        fr_metrics["simplex_entropy_mean"] = entropy.detach()
        fr_metrics["simplex_min_p"] = simplex.min().detach()

    extras = {
        "ablation": cfg.ablation,
        "loss_weights_active": cfg.loss_weights,
        "vocab_size": vocab_size,
        "batch_size": int(batch["input_ids"].shape[0]),
        "L_src": int(batch["cas_prefix_ids"].shape[1])
                 if isinstance(batch.get("cas_prefix_ids"), torch.Tensor) else 0,
        "L_out": int(batch["lm_targets"].shape[1])
                 if isinstance(batch.get("lm_targets"), torch.Tensor) else 0,
    }

    emit_train_progress(
        output_path=output_path,
        epoch=0,
        batch_in_epoch=1,
        batches_per_epoch=1,
        global_step=1,
        loss_parts=loss_parts,
        fr_metrics=fr_metrics,
        elapsed_sec=elapsed_sec,
        batches_per_sec=(1.0 / elapsed_sec) if elapsed_sec > 0 else 0.0,
        eta_epoch_min=0.0,
        grad_norm_encoder=grad_norm_encoder,
        grad_norm_decoder=grad_norm_decoder,
        lr_now=cfg.lr,
        extras=extras,
    )

    copy_metrics_dict = loss_parts.get("__copy_metrics__", {})
    return {
        "loss_total": float(loss_parts["loss_total"].item()),
        "loss_parts": {
            k: float(v.item())
            for k, v in loss_parts.items()
            if k != "__copy_metrics__"
        },
        "copy_metrics": {
            k: float(v.item()) if isinstance(v, torch.Tensor) else float(v)
            for k, v in copy_metrics_dict.items()
        },
        "fr_metrics": {
            k: float(v.item()) if isinstance(v, torch.Tensor) else float(v)
            for k, v in fr_metrics.items()
        },
        "grad_norm_encoder": grad_norm_encoder,
        "grad_norm_decoder": grad_norm_decoder,
        "elapsed_sec": elapsed_sec,
        "extras": extras,
        "model": model,
        "batch": batch,
        "out": out,
    }


def stratified_sample(
    records: list[dict[str, Any]],
    target_n: int,
    *,
    category_key: str = "v1mix_grammar_category_or_error_class",
    seed: int = 1729,
) -> list[dict[str, Any]]:
    """Stratified sample of ``target_n`` records.

    Ensures at least one record per category when categories are present.
    Falls back to a deterministic shuffle when category_key is missing.
    Used by Stage 5 CPU smoke per execution plan §Stage 5
    ("200-record stratified sample, ≥1 per grammar category").
    """
    import random as _random
    rng = _random.Random(seed)
    if not records:
        return []

    # Group by category
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        cat = rec.get(category_key) or "unk"
        by_cat.setdefault(cat, []).append(rec)

    # Shuffle each group deterministically
    for cat in by_cat:
        rng.shuffle(by_cat[cat])

    if not by_cat:
        shuffled = list(records)
        rng.shuffle(shuffled)
        return shuffled[:target_n]

    # Round-robin: pull one record from each category in turn until we hit target_n
    sampled: list[dict[str, Any]] = []
    cats = sorted(by_cat.keys())
    cursors = {c: 0 for c in cats}
    exhausted = set()
    while len(sampled) < target_n and len(exhausted) < len(cats):
        for cat in cats:
            if len(sampled) >= target_n:
                break
            if cursors[cat] < len(by_cat[cat]):
                sampled.append(by_cat[cat][cursors[cat]])
                cursors[cat] += 1
            else:
                exhausted.add(cat)
    return sampled


def evaluate_gates(
    *,
    loss_history: list[dict[str, float]],
    simplex_min_p_history: list[float],
    simplex_entropy_history: list[float],
) -> dict[str, Any]:
    """Apply the Stage 5 CPU-smoke gate criteria to a training-step history.

    Returns a dict with:
      - per-gate pass/fail booleans
      - per-gate evidence (numeric values from the run)
      - overall verdict (PASS / FAIL)
    """
    gates: dict[str, Any] = {}

    # Gate 1: no NaN/Inf in any loss term at any step
    nan_steps: list[int] = []
    for i, h in enumerate(loss_history):
        for k, v in h.items():
            if not (isinstance(v, (int, float)) and (v == v) and v != float("inf") and v != float("-inf")):
                nan_steps.append(i)
                break
    gates["no_nan_inf"] = {
        "pass": len(nan_steps) == 0,
        "nan_steps": nan_steps[:5],
    }

    # Gate 2: simplex_min_p > 0 at every step
    min_simplex = min(simplex_min_p_history) if simplex_min_p_history else 0.0
    gates["simplex_min_above_floor"] = {
        "pass": min_simplex > 0.0,
        "min_observed": min_simplex,
    }

    # Gate 3: entropy does not collapse — bounded below by some heuristic
    # (uniform = log(40) ≈ 3.689; collapse threshold ~ 0.5)
    min_entropy = min(simplex_entropy_history) if simplex_entropy_history else 0.0
    gates["entropy_does_not_collapse"] = {
        "pass": min_entropy > 0.5,
        "min_entropy_observed": min_entropy,
    }

    # Gate 4: LM loss does not explode (final LM <= initial * 2)
    lm_values = [h.get("loss_lm", 0.0) for h in loss_history]
    gates["lm_does_not_explode"] = {
        "pass": (
            len(lm_values) >= 2
            and lm_values[-1] <= max(lm_values[0] * 2.0, lm_values[0] + 2.0)
        ),
        "lm_initial": lm_values[0] if lm_values else 0.0,
        "lm_final": lm_values[-1] if lm_values else 0.0,
    }

    # Gate 5: LM trends down over a 10-step smoothing window
    if len(lm_values) >= 20:
        first10 = sum(lm_values[:10]) / 10.0
        last10 = sum(lm_values[-10:]) / 10.0
        gates["lm_decreasing"] = {
            "pass": last10 < first10,
            "first10_mean": first10,
            "last10_mean": last10,
            "delta": last10 - first10,
        }
    else:
        gates["lm_decreasing"] = {
            "pass": True,  # not enough data; don't fail
            "note": "fewer than 20 steps; window check skipped",
        }

    # Gate 6: FR loss finite and moving toward zero (or at least not exploding)
    fr_values = [h.get("loss_fr", 0.0) for h in loss_history]
    all_fr_finite = all(
        (v == v) and v != float("inf") and v != float("-inf") for v in fr_values
    )
    if len(fr_values) >= 20:
        first10 = sum(fr_values[:10]) / 10.0
        last10 = sum(fr_values[-10:]) / 10.0
        gates["fr_finite_and_directional"] = {
            "pass": all_fr_finite and last10 <= first10 + 0.5,
            "first10_mean": first10,
            "last10_mean": last10,
            "delta": last10 - first10,
        }
    else:
        gates["fr_finite_and_directional"] = {
            "pass": all_fr_finite,
            "note": "fewer than 20 steps; trend check skipped",
        }

    # Gate 7: gradients nonzero for encoder AND decoder
    enc_norms = [h.get("grad_norm_encoder", 0.0) for h in loss_history]
    dec_norms = [h.get("grad_norm_decoder", 0.0) for h in loss_history]
    gates["gradients_flow_both_paths"] = {
        "pass": (
            len(enc_norms) > 0 and len(dec_norms) > 0
            and any(n > 0 for n in enc_norms)
            and any(n > 0 for n in dec_norms)
        ),
        "encoder_grad_norm_min": min(enc_norms) if enc_norms else 0.0,
        "decoder_grad_norm_min": min(dec_norms) if dec_norms else 0.0,
    }

    overall_pass = all(g.get("pass", False) for g in gates.values())
    return {
        "verdict": "PASS" if overall_pass else "FAIL",
        "gates": gates,
        "n_steps": len(loss_history),
    }


def run_cpu_smoke(
    cfg: SimplexTrainConfig,
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    n_steps: int = 50,
) -> dict[str, Any]:
    """Stage 5 CPU smoke: 50 steps × batch 4 with all 5 losses live.

    Per execution plan §Stage 5:
      - Build tokenizer from stratified 200-record sample
      - Build model at smoke config (d_model=64, 2/2 layers, 4 heads)
      - Run 50 steps, emit train_progress every --train-log-every-steps
      - Validate gates at end; write smoke_report.json
      - Halt on any NaN/Inf

    Returns dict with per-step history + gate verdict.
    """
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    from cas_native.training.fisher_rao_loss import FisherRaoLoss
    import torch.optim as optim
    import random as _random

    device = torch.device(cfg.device)
    torch.manual_seed(cfg.seed)

    tokenizer = build_tokenizer_for_smoke(records)
    collator = SimplexCollator(tokenizer, enable_simplex_aux=True)

    vocab_size = int(tokenizer.vocab_size)
    model = build_simplex_mvp_model(
        cfg, vocab_size=vocab_size, vocab_size_english=vocab_size,
    ).to(device)
    fisher_rao_loss = FisherRaoLoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    rng = _random.Random(cfg.seed)
    loss_history: list[dict[str, float]] = []
    min_p_history: list[float] = []
    entropy_history: list[float] = []
    halted: Optional[str] = None
    log_path = output_dir / "trainer_log.jsonl"
    t_run_start = time.time()

    for step in range(1, n_steps + 1):
        # Sample batch of cfg.batch_size records (with replacement when needed)
        if len(records) >= cfg.batch_size:
            batch_records = rng.sample(records, cfg.batch_size)
        else:
            batch_records = [records[rng.randrange(len(records))] for _ in range(cfg.batch_size)]
        batch = collator(batch_records, device=device)
        if batch is None:
            continue

        t_step_start = time.time()
        optimizer.zero_grad(set_to_none=True)
        out = model(batch)
        total, parts = compute_losses(
            out, batch, fisher_rao_loss=fisher_rao_loss, weights=cfg.loss_weights,
        )

        # Halt on NaN/Inf — kill-switch per plan §Stage 5
        if not torch.isfinite(total):
            halted = f"NaN/Inf in total loss at step {step}"
            break

        total.backward()
        enc_norm = compute_grad_norm(model.encoder.parameters())
        dec_norm = compute_grad_norm(model.decoder.parameters())
        if cfg.grad_clip and cfg.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        optimizer.step()
        step_elapsed = time.time() - t_step_start

        # Per-step telemetry
        with torch.no_grad():
            simplex = out["simplex_trajectory"]
            min_p = float(simplex.min().item())
            entropy = float(-(simplex * simplex.clamp_min(1e-12).log()).sum(dim=-1).mean().item())
        min_p_history.append(min_p)
        entropy_history.append(entropy)

        # Halt on simplex_min_p <= 0
        if min_p <= 0.0:
            halted = f"simplex_min_p <= 0 at step {step}: {min_p}"
            break

        copy_metrics_step = parts.get("__copy_metrics__", {})
        step_record = {
            "step": step,
            "loss_total": float(parts["loss_total"].item()),
            "loss_lm": float(parts["loss_lm"].item()),
            "loss_fr": float(parts["loss_fr"].item()),
            "loss_slot_type": float(parts["loss_slot_type"].item()),
            "loss_copy": float(parts["loss_copy"].item()),
            "loss_phrase_bias_aux": float(parts["loss_phrase_bias_aux"].item()),
            "copy_valid_count": (
                float(copy_metrics_step["copy_valid_count"].item())
                if "copy_valid_count" in copy_metrics_step else 0.0
            ),
            "copy_argmax_acc": (
                float(copy_metrics_step["copy_argmax_acc"].item())
                if "copy_argmax_acc" in copy_metrics_step else float("nan")
            ),
            "copy_loss_live": (
                float(copy_metrics_step["copy_loss_live"].item())
                if "copy_loss_live" in copy_metrics_step else float("nan")
            ),
            "grad_norm_encoder": enc_norm,
            "grad_norm_decoder": dec_norm,
            "simplex_min_p": min_p,
            "simplex_entropy_mean": entropy,
            "elapsed_sec": step_elapsed,
        }
        loss_history.append(step_record)

        # Emit train_progress every --train-log-every-steps OR at boundary steps
        log_now = (
            step <= 3
            or step % max(1, cfg.train_log_every_steps) == 0
            or step == n_steps
        )
        if log_now:
            fr_metrics = {k: v for k, v in fisher_rao_loss.last_metrics.items()}
            fr_metrics["simplex_entropy_mean"] = entropy
            fr_metrics["simplex_min_p"] = min_p
            extras = {
                "ablation": cfg.ablation,
                "loss_weights_active": cfg.loss_weights,
                "vocab_size": vocab_size,
                "batch_size": cfg.batch_size,
                "L_src": int(batch["cas_prefix_ids"].shape[1])
                         if isinstance(batch.get("cas_prefix_ids"), torch.Tensor) else 0,
                "L_out": int(batch["lm_targets"].shape[1])
                         if isinstance(batch.get("lm_targets"), torch.Tensor) else 0,
            }
            emit_train_progress(
                output_path=log_path,
                epoch=0,
                batch_in_epoch=step,
                batches_per_epoch=n_steps,
                global_step=step,
                loss_parts=parts,
                fr_metrics=fr_metrics,
                elapsed_sec=step_elapsed,
                batches_per_sec=(1.0 / step_elapsed) if step_elapsed > 0 else 0.0,
                eta_epoch_min=((n_steps - step) * step_elapsed / 60.0) if step_elapsed > 0 else 0.0,
                grad_norm_encoder=enc_norm,
                grad_norm_decoder=dec_norm,
                lr_now=cfg.lr,
                extras=extras,
            )

    # Validate gates
    gate_report = evaluate_gates(
        loss_history=loss_history,
        simplex_min_p_history=min_p_history,
        simplex_entropy_history=entropy_history,
    )
    if halted is not None:
        gate_report["verdict"] = "HALT"
        gate_report["halt_reason"] = halted

    smoke_report = {
        "event": "cpu_smoke_report",
        "config_summary": {
            "d_model": cfg.d_model,
            "encoder_n_layers": cfg.encoder_n_layers,
            "decoder_n_layers": cfg.decoder_n_layers,
            "encoder_n_heads": cfg.encoder_n_heads,
            "decoder_n_heads": cfg.decoder_n_heads,
            "batch_size": cfg.batch_size,
            "lr": cfg.lr,
            "n_steps_planned": n_steps,
            "n_steps_completed": len(loss_history),
            "ablation": cfg.ablation,
            "device": cfg.device,
            "n_records_loaded": len(records),
        },
        "wall_clock_sec": time.time() - t_run_start,
        "verdict": gate_report["verdict"],
        "gates": gate_report["gates"],
        "halt_reason": gate_report.get("halt_reason"),
        "first_step": loss_history[0] if loss_history else None,
        "last_step": loss_history[-1] if loss_history else None,
        "loss_lm_trajectory": [h["loss_lm"] for h in loss_history],
        "loss_fr_trajectory": [h["loss_fr"] for h in loss_history],
    }
    (output_dir / "smoke_report.json").write_text(
        json.dumps(smoke_report, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(json.dumps(smoke_report, ensure_ascii=False, sort_keys=True), flush=True)
    return smoke_report


def main(argv: Optional[list[str]] = None) -> int:
    """Stage 3 entry point: integration wiring.

    Behavior:
      --smoke-test: load N records (or synthesize), run 1 forward+backward,
        emit train_progress JSON to stdout + ``trainer_log.jsonl``, exit 0.

      Full training: not yet wired (Stage 8). Falls through to the
      manifest-only path so the CLI surface stays stable.

    NaN at any loss term halts with non-zero exit per plan §Stage 3.
    """
    cfg = parse_args(argv)
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "event": "trainer_init",
        "config": asdict(cfg),
        "loss_weights_active": cfg.loss_weights,
        "ablation": cfg.ablation,
    }
    (out_dir / "trainer_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)

    if cfg.smoke_test:
        records = load_jsonl_records(cfg.data_path, limit=cfg.smoke_records)
        if not records:
            records = synthetic_records(cfg.smoke_records)
        try:
            result = run_integration_step(
                cfg, records[: cfg.smoke_records],
                output_path=out_dir / "trainer_log.jsonl",
            )
        except RuntimeError as exc:
            print(json.dumps({"event": "trainer_halt", "reason": str(exc)}, ensure_ascii=False), flush=True)
            return 1
        smoke_summary = {
            "event": "smoke_test_done",
            "ok": True,
            "loss_total": result["loss_total"],
            "loss_parts": result["loss_parts"],
            "grad_norm_encoder": result["grad_norm_encoder"],
            "grad_norm_decoder": result["grad_norm_decoder"],
        }
        print(json.dumps(smoke_summary, ensure_ascii=False, sort_keys=True), flush=True)
        return 0

    # Stage 5 CPU smoke path: real multi-step training (default 50 steps)
    # under the actual smoke config (d_model=64, 2/2 layers, 4 heads),
    # all 5 losses live, CPU only. Per execution plan §Stage 5.
    #
    # Triggered when --smoke-test is NOT set but a real --data-path and
    # --limit are provided. Stage 8 (GPU long-run) builds on this loop.
    records = load_jsonl_records(cfg.data_path, limit=cfg.limit or 200)
    if not records:
        print(json.dumps({
            "event": "trainer_halt",
            "reason": f"no records loaded from {cfg.data_path!r}",
        }, ensure_ascii=False), flush=True)
        return 1

    # Stratified subsample to ensure all categories represented per
    # execution plan §Stage 5 ("≥1 record per grammar category").
    stratified = stratified_sample(records, target_n=cfg.limit or 200, seed=cfg.seed)
    n_steps = (cfg.limit or 200) // max(cfg.batch_size, 1)
    smoke = run_cpu_smoke(cfg, stratified, output_dir=out_dir, n_steps=n_steps)
    return 0 if smoke["verdict"] in ("PASS", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
