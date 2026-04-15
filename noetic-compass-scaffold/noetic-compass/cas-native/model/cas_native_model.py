"""
CASNativeModel: Full model assembly combining all CAS-Native components
into a complete transformer-based architecture.

Architecture:
  - Token embedding + positional encoding
  - CognitiveStateEmbedding branch (parallel to main pathway)
  - N transformer layers, each with:
    - DomainDescentAttention (replaces standard attention)
    - FractalAttentionHead (additional multi-scale heads)
    - PrerequisiteGateLayer after attention
    - FFN + LayerNorm
  - CognitiveToposReasoner output head
  - LM head (nn.Linear -> vocab_size)

Forward returns dict: logits, cognitive_state, rpm_satisfaction,
inversion_flags, topos_truth_values
"""

import math
from dataclasses import dataclass

import torch
import torch.nn as nn

from .embedding import CognitiveStateEmbedding
from .domain_descent import DomainDescentAttention
from .rpm_gate import PrerequisiteGateLayer
from .fractal_attention import FractalAttentionHead
from .topos_reasoner import CognitiveToposReasoner
from .composition import GenerativeHead
from .lacunarity_gate import LacunarityGate
from .lacunarity_head import LacunarityHead


@dataclass
class CASNativeConfig:
    """Configuration for the CAS-Native model."""

    d_model: int = 512
    n_layers: int = 6
    n_heads: int = 8
    vocab_size: int = 32000
    max_seq_len: int = 2048
    fractal_depth: int = 3
    num_ethical_propositions: int = 7
    dropout: float = 0.1
    rpm_threshold: float = 0.5
    num_ifs_maps: int = 4


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding."""

    def __init__(self, d_model: int, max_seq_len: int = 2048, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_seq_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encoding to input embeddings."""
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class CASTransformerLayer(nn.Module):
    """Single transformer layer with CAS-specific components.

    Each layer contains:
      - DomainDescentAttention (domain-masked attention)
      - FractalAttentionHead (multi-scale fractal attention)
      - PrerequisiteGateLayer (RPM gating)
      - FFN + LayerNorm (standard transformer components)
    """

    def __init__(self, config: CASNativeConfig):
        super().__init__()

        # Domain descent attention (replaces standard self-attention)
        self.domain_attn = DomainDescentAttention(
            d_model=config.d_model,
            n_heads=config.n_heads,
        )
        self.norm1 = nn.LayerNorm(config.d_model)

        # Fractal attention (additional multi-scale heads)
        self.fractal_attn = FractalAttentionHead(
            d_model=config.d_model,
            n_heads=config.n_heads,
            fractal_depth=config.fractal_depth,
            num_ifs_maps=config.num_ifs_maps,
        )
        self.norm2 = nn.LayerNorm(config.d_model)

        # Fractal mixing weight (learnable blend of domain + fractal attention)
        self.fractal_gate = nn.Parameter(torch.tensor(0.5))

        # RPM prerequisite gate
        self.rpm_gate = PrerequisiteGateLayer(
            d_model=config.d_model,
            threshold=config.rpm_threshold,
        )
        self.norm3 = nn.LayerNorm(config.d_model)

        # Feed-forward network
        self.ffn = nn.Sequential(
            nn.Linear(config.d_model, config.d_model * 4),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model * 4, config.d_model),
            nn.Dropout(config.dropout),
        )
        self.norm4 = nn.LayerNorm(config.d_model)

    def forward(
        self,
        x: torch.Tensor,
        cognitive_state: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """
        Args:
            x: Input tensor (batch, seq, d_model)
            cognitive_state: Token-to-slot weights (batch, seq, 40)
            attention_mask: Optional padding mask (batch, seq)

        Returns:
            Tuple of (output, rpm_satisfaction_dict)
        """
        mask = None
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).to(x.dtype)

        # Domain descent attention + fractal attention (blended)
        domain_out = self.domain_attn(
            self.norm1(x),
            cognitive_state,
            attention_mask=attention_mask,
        )
        fractal_out = self.fractal_attn(self.norm2(x), attention_mask=attention_mask)

        gate = torch.sigmoid(self.fractal_gate)
        attn_out = gate * domain_out + (1.0 - gate) * fractal_out
        x = x + attn_out
        if mask is not None:
            x = x * mask

        # RPM prerequisite gate
        gated, rpm_satisfaction = self.rpm_gate(self.norm3(x))
        x = x + gated
        if mask is not None:
            x = x * mask

        # Feed-forward
        x = x + self.ffn(self.norm4(x))
        if mask is not None:
            x = x * mask

        return x, rpm_satisfaction


class InversionDetector(nn.Module):
    """Detects inversions across the 7 CAS inversion axes.

    Axes: N (Operator), W (Domain), F (Drive), E (State),
          S (Sub-Drive), A (Pathway), P (Compound)
    """

    NUM_AXES = 7

    def __init__(self, d_model: int):
        super().__init__()
        self.detector = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, self.NUM_AXES),
            nn.Sigmoid(),  # Output in [0, 1] per axis
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Pooled representation (batch, d_model)

        Returns:
            Inversion scores (batch, 7) in [0, 1]
        """
        return self.detector(x)


class CASNativeModel(nn.Module):
    """Complete CAS-Native model combining all components.

    Architecture:
      - Token embedding + positional encoding
      - CognitiveStateEmbedding branch (parallel)
      - N CAS transformer layers
      - CognitiveToposReasoner output head
      - LM head
      - Inversion detector
    """

    def __init__(self, config: CASNativeConfig | None = None):
        super().__init__()
        if config is None:
            config = CASNativeConfig()
        self.config = config

        # Token embedding + positional encoding
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.pos_encoding = PositionalEncoding(
            config.d_model, config.max_seq_len, config.dropout
        )

        # Cognitive state embedding branch (parallel to main pathway)
        self.cognitive_embedding = CognitiveStateEmbedding(config.d_model)

        # CAS transformer layers
        self.layers = nn.ModuleList([
            CASTransformerLayer(config)
            for _ in range(config.n_layers)
        ])

        # Final layer norm
        self.final_norm = nn.LayerNorm(config.d_model)

        # Output heads
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.topos_reasoner = CognitiveToposReasoner(
            config.d_model,
            config.num_ethical_propositions,
        )
        self.inversion_detector = InversionDetector(config.d_model)
        self.generative_head = GenerativeHead(config.d_model)
        self.lacunarity_gate = LacunarityGate(num_slots=40)
        self.lacunarity_head = LacunarityHead(config.d_model)

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    @staticmethod
    def _masked_mean(x: torch.Tensor, attention_mask: torch.Tensor | None) -> torch.Tensor:
        """Average across sequence positions while ignoring padding."""
        if attention_mask is None:
            return x.mean(dim=1)

        weights = attention_mask.to(x.dtype).unsqueeze(-1)
        return (x * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """
        Args:
            input_ids: Token IDs of shape (batch, seq)
            attention_mask: Optional mask of shape (batch, seq)

        Returns:
            Dict with keys:
              - logits: LM logits (batch, seq, vocab_size)
              - cognitive_state: Cognitive state on simplex (batch, seq, 40)
              - rpm_satisfaction: Mean RPM satisfaction scalar
              - inversion_flags: Inversion scores (batch, 7)
              - topos_truth_values: Truth values (batch, num_propositions, 3)
        """
        # Token embedding + positional encoding
        x = self.token_embedding(input_ids)
        x = self.pos_encoding(x)

        # Apply attention mask if provided (zero out padded positions)
        if attention_mask is not None:
            x = x * attention_mask.unsqueeze(-1).float()

        # CAS transformer layers
        all_rpm_satisfaction: list[dict[str, torch.Tensor]] = []
        for layer in self.layers:
            layer_cognitive_state = self.cognitive_embedding(x)
            x, rpm_sat = layer(
                x,
                layer_cognitive_state,
                attention_mask=attention_mask,
            )
            all_rpm_satisfaction.append(rpm_sat)

        # Final normalization
        x = self.final_norm(x)
        if attention_mask is not None:
            x = x * attention_mask.unsqueeze(-1).float()

        # LM head
        logits = self.lm_head(x)

        # Recompute cognitive state from final hidden states
        cognitive_state = self.cognitive_embedding(x)

        # Lacunarity self-correction: if activation is too concentrated, rebalance
        corrected_state, lacunarity_scores = self.lacunarity_gate(cognitive_state)

        # Pooled representation for global heads
        pooled = self._masked_mean(x, attention_mask)  # (batch, d_model)

        # Topos reasoning (intuitionistic 3-valued logic)
        topos_truth_values = self.topos_reasoner(pooled)

        # Inversion detection
        inversion_flags = self.inversion_detector(pooled)

        # Metacognitive lacunarity reporting
        lacunarity_meta = self.lacunarity_head(x)

        # Aggregate RPM satisfaction across layers
        mean_rpm = torch.tensor(0.0, device=input_ids.device)
        count = 0
        for rpm_dict in all_rpm_satisfaction:
            for name, sat in rpm_dict.items():
                mean_rpm = mean_rpm + sat.mean()
                count += 1
        if count > 0:
            mean_rpm = mean_rpm / count

        return {
            "logits": logits,
            "cognitive_state": corrected_state,
            "raw_cognitive_state": cognitive_state,
            "rpm_satisfaction": mean_rpm,
            "inversion_flags": inversion_flags,
            "topos_truth_values": topos_truth_values,
            "lacunarity_scores": lacunarity_scores,
            "lacunarity_meta": lacunarity_meta,
        }
