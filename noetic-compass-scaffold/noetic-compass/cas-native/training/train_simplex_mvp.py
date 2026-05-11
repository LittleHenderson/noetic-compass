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
from typing import Any, Optional

import torch
from torch import nn
from torch.utils.data import DataLoader

# Bound to repository import path
_THIS_FILE = Path(__file__).resolve()
_CAS_NATIVE = _THIS_FILE.parent.parent
if str(_CAS_NATIVE) not in sys.path:
    sys.path.insert(0, str(_CAS_NATIVE))


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
            enc_out = self.encoder(batch["cas_prefix_ids"], attention_mask=batch.get("cas_prefix_mask"))
            dec_out = self.decoder(
                decoder_input_ids=batch["lm_decoder_input_ids"],
                source_hidden=enc_out["source_hidden"],
                simplex_trajectory=enc_out["simplex_trajectory"],
                src_ids=batch["cas_prefix_ids"],
                src_token_type=batch.get("src_token_type"),
                src_padding_mask=batch.get("cas_prefix_mask"),
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

    # L_FR: anchor-masked squared geodesic distance on Δ°₃₉
    if "fr_target_path" in batch and "fr_target_mask" in batch:
        loss_fr = fisher_rao_loss(
            out["simplex_trajectory"], batch["fr_target_path"], batch["fr_target_mask"],
        )
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
    if "typed_slot_source" in batch:
        copy_target = batch["typed_slot_source"].to(dtype=torch.long)  # (B, L_out)
        valid = (copy_target >= 0)
        if valid.any():
            p_copy = out["p_copy"]                                       # (B, L_out, L_src)
            B, L_out, L_src = p_copy.shape
            # Clamp to valid range so gather doesn't fault; mask zeroes them.
            safe_idx = copy_target.clamp(min=0, max=L_src - 1).unsqueeze(-1)
            chosen = p_copy.gather(-1, safe_idx).squeeze(-1).clamp_min(1e-9)
            copy_log = -torch.log(chosen)
            denom_c = valid.to(dtype=torch.float32).sum().clamp_min(1.0)
            loss_copy = (copy_log * valid.to(dtype=copy_log.dtype)).sum() / denom_c
        else:
            loss_copy = torch.zeros((), device=lm_logits.device)
    else:
        loss_copy = torch.zeros((), device=lm_logits.device)

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


def main(argv: Optional[list[str]] = None) -> int:
    """Skeleton entry point.

    Stage 1 only verifies that the trainer is importable + parses CLI.
    Real model construction + DataLoader assembly + training loop lands in
    Stage 3 once unit tests in Stage 2 force correctness of the components.
    """
    cfg = parse_args(argv)
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "event": "trainer_init",
        "config": asdict(cfg),
        "loss_weights_active": cfg.loss_weights,
        "ablation": cfg.ablation,
        "note": "Stage 1 skeleton — full training loop lands in Stage 3.",
    }
    (out_dir / "trainer_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
