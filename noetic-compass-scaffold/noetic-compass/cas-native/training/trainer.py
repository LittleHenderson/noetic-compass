"""
CASTrainer: Training loop for the CAS-Native model.

Features:
  - Adam optimizer with cosine LR schedule (warmup 1000 steps)
  - Gradient clipping at 1.0
  - Checkpoint saving every 1000 steps
  - Optional W&B logging (WANDB_ENABLED env var)
  - Evaluation every 500 steps
  - Training target: NCCS >= 75 (Gold certification)
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader

from ..model.cas_native_model import CASNativeModel, CASNativeConfig
from ..model.loss import CognitiveMetricLoss
from ..model.embedding import CognitiveStateEmbedding


class CASTrainer:
    """Training loop for the CAS-Native model.

    Manages the full training lifecycle: optimizer setup, scheduling,
    gradient clipping, checkpointing, logging, and evaluation.
    """

    def __init__(
        self,
        model: CASNativeModel,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader

        # Training config with defaults
        cfg = config or {}
        self.lr = cfg.get("lr", 1e-4)
        self.warmup_steps = cfg.get("warmup_steps", 1000)
        self.max_steps = cfg.get("max_steps", 100000)
        self.grad_clip = cfg.get("grad_clip", 1.0)
        self.checkpoint_every = cfg.get("checkpoint_every", 1000)
        self.eval_every = cfg.get("eval_every", 500)
        self.checkpoint_dir = Path(cfg.get("checkpoint_dir", "checkpoints"))
        self.target_nccs = cfg.get("target_nccs", 75.0)

        # Loss function
        self.loss_fn = CognitiveMetricLoss(
            lambda_operator_balance=cfg.get("lambda_operator_balance", 1.0),
            lambda_domain_coherence=cfg.get("lambda_domain_coherence", 1.0),
            lambda_rpm_satisfaction=cfg.get("lambda_rpm_satisfaction", 1.0),
            lambda_inversion_penalty=cfg.get("lambda_inversion_penalty", 1.0),
            lambda_cognitive_drift=cfg.get("lambda_cognitive_drift", 1.0),
        )

        # Optimizer
        self.optimizer = Adam(model.parameters(), lr=self.lr, betas=(0.9, 0.98), eps=1e-9)

        # LR schedule: linear warmup then cosine annealing
        warmup_scheduler = LinearLR(
            self.optimizer,
            start_factor=1e-8 / self.lr if self.lr > 0 else 1.0,
            end_factor=1.0,
            total_iters=self.warmup_steps,
        )
        cosine_scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=max(self.max_steps - self.warmup_steps, 1),
            eta_min=self.lr * 0.01,
        )
        self.scheduler = SequentialLR(
            self.optimizer,
            schedulers=[warmup_scheduler, cosine_scheduler],
            milestones=[self.warmup_steps],
        )

        # W&B logging (optional)
        self.wandb_enabled = os.environ.get("WANDB_ENABLED", "false").lower() == "true"
        self._wandb = None
        if self.wandb_enabled:
            try:
                import wandb
                self._wandb = wandb
            except ImportError:
                self.wandb_enabled = False

        # Training state
        self.global_step = 0
        self.best_val_loss = float("inf")
        self.device = next(model.parameters()).device

    def _save_checkpoint(self, tag: str = "step") -> Path:
        """Save a model checkpoint."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        ckpt_path = self.checkpoint_dir / f"cas_native_{tag}_{self.global_step}.pt"
        torch.save(
            {
                "global_step": self.global_step,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "scheduler_state_dict": self.scheduler.state_dict(),
                "best_val_loss": self.best_val_loss,
            },
            ckpt_path,
        )
        return ckpt_path

    def load_checkpoint(self, ckpt_path: str | Path) -> None:
        """Load a model checkpoint."""
        ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        self.scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        self.global_step = ckpt["global_step"]
        self.best_val_loss = ckpt.get("best_val_loss", float("inf"))

    def _generate_target_cognitive_state(self, batch_size: int, seq_len: int) -> torch.Tensor:
        """Generate a target cognitive state on the open simplex.

        For training, we use a uniform distribution as the balanced target.
        """
        # Uniform on the open simplex
        target = torch.ones(batch_size, seq_len, 40, device=self.device) / 40.0
        return target

    def _train_step(self, batch: dict[str, torch.Tensor]) -> dict[str, float]:
        """Execute a single training step."""
        self.model.train()

        input_ids = batch["input_ids"].to(self.device)
        targets = batch["targets"].to(self.device)
        attention_mask = batch.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)

        # Forward pass
        outputs = self.model(input_ids, attention_mask=attention_mask)

        # Generate target cognitive state
        batch_size, seq_len = input_ids.shape
        target_cog = self._generate_target_cognitive_state(batch_size, seq_len)

        # Build RPM satisfaction dict from scalar
        rpm_sat_dict = {"mean": outputs["rpm_satisfaction"].unsqueeze(0)}

        # Compute loss
        total_loss, components = self.loss_fn(
            logits=outputs["logits"],
            targets=targets,
            cognitive_state=outputs["cognitive_state"],
            target_cognitive_state=target_cog,
            rpm_satisfaction=rpm_sat_dict,
            inversion_scores=outputs["inversion_flags"],
        )

        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)

        # Optimizer step
        self.optimizer.step()
        self.scheduler.step()

        # Return metrics
        metrics = {k: v.item() for k, v in components.items()}
        metrics["lr"] = self.scheduler.get_last_lr()[0]
        return metrics

    @torch.no_grad()
    def evaluate(self) -> dict[str, float]:
        """Evaluate the model on the validation set."""
        if self.val_loader is None:
            return {}

        self.model.eval()
        total_loss = 0.0
        total_rpm_sat = 0.0
        num_batches = 0

        for batch in self.val_loader:
            input_ids = batch["input_ids"].to(self.device)
            targets = batch["targets"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)

            outputs = self.model(input_ids, attention_mask=attention_mask)

            batch_size, seq_len = input_ids.shape
            target_cog = self._generate_target_cognitive_state(batch_size, seq_len)

            rpm_sat_dict = {"mean": outputs["rpm_satisfaction"].unsqueeze(0)}

            loss, components = self.loss_fn(
                logits=outputs["logits"],
                targets=targets,
                cognitive_state=outputs["cognitive_state"],
                target_cognitive_state=target_cog,
                rpm_satisfaction=rpm_sat_dict,
                inversion_scores=outputs["inversion_flags"],
            )

            total_loss += loss.item()
            total_rpm_sat += outputs["rpm_satisfaction"].item()
            num_batches += 1

        if num_batches == 0:
            return {}

        return {
            "val_loss": total_loss / num_batches,
            "val_rpm_satisfaction": total_rpm_sat / num_batches,
        }

    def train(self) -> dict[str, Any]:
        """Run the full training loop.

        Returns:
            Dict with training summary.
        """
        print(f"Starting CAS-Native training for {self.max_steps} steps")
        print(f"  Target NCCS: {self.target_nccs} (Gold certification)")
        print(f"  Checkpoint dir: {self.checkpoint_dir}")
        print(f"  W&B logging: {self.wandb_enabled}")

        if self.wandb_enabled and self._wandb is not None:
            self._wandb.init(project="cas-native", config={"max_steps": self.max_steps})

        training_log: list[dict[str, Any]] = []
        start_time = time.time()

        data_iter = iter(self.train_loader)

        while self.global_step < self.max_steps:
            # Get next batch (cycle through data)
            try:
                batch = next(data_iter)
            except StopIteration:
                data_iter = iter(self.train_loader)
                batch = next(data_iter)

            # Training step
            metrics = self._train_step(batch)
            self.global_step += 1

            # Log
            if self.global_step % 100 == 0:
                elapsed = time.time() - start_time
                print(
                    f"Step {self.global_step}/{self.max_steps} | "
                    f"Loss: {metrics['total']:.4f} | "
                    f"LR: {metrics['lr']:.2e} | "
                    f"Time: {elapsed:.1f}s"
                )

            if self.wandb_enabled and self._wandb is not None:
                self._wandb.log(metrics, step=self.global_step)

            # Evaluation
            if self.global_step % self.eval_every == 0:
                val_metrics = self.evaluate()
                if val_metrics:
                    print(f"  Eval @ step {self.global_step}: {val_metrics}")
                    if val_metrics.get("val_loss", float("inf")) < self.best_val_loss:
                        self.best_val_loss = val_metrics["val_loss"]
                        self._save_checkpoint(tag="best")

                    if self.wandb_enabled and self._wandb is not None:
                        self._wandb.log(val_metrics, step=self.global_step)

            # Checkpointing
            if self.global_step % self.checkpoint_every == 0:
                ckpt_path = self._save_checkpoint(tag="step")
                print(f"  Checkpoint saved: {ckpt_path}")

            training_log.append({"step": self.global_step, **metrics})

        # Final checkpoint
        self._save_checkpoint(tag="final")

        elapsed = time.time() - start_time
        summary = {
            "total_steps": self.global_step,
            "total_time_seconds": elapsed,
            "best_val_loss": self.best_val_loss,
            "final_metrics": training_log[-1] if training_log else {},
        }

        if self.wandb_enabled and self._wandb is not None:
            self._wandb.finish()

        return summary
