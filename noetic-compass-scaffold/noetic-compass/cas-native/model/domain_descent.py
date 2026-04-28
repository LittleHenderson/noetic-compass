"""
DomainDescentAttention over explicit 40 cognitive-state slots.

This layer applies the P -> C -> E -> O descent mask to a fixed bank of
40 slot representations, not to token positions. Token hidden states are first
aggregated into slot states using externally supplied slot weights, then the
domain mask is enforced over slot-to-slot attention, and finally the updated
slot states are projected back to token positions.

The domain-order mask is an explicit CAS structural constraint. The token-to-
slot assignment remains a learned neural approximation supplied by the model's
cognitive-state head.
"""

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


NUM_COGNITIVE_STATES = 40
DOMAIN_SIZE = 10  # 10 operators per domain


def build_domain_descent_mask(num_states: int = NUM_COGNITIVE_STATES) -> torch.Tensor:
    """Build the slot-level domain descent mask."""
    mask = torch.zeros(num_states, num_states, dtype=torch.bool)

    mask[0:10, 0:10] = True
    mask[10:20, 0:20] = True
    mask[20:30, 0:30] = True
    mask[30:40, 0:40] = True

    return mask


class DomainDescentAttention(nn.Module):
    """Multi-head attention constrained by the CAS domain order on 40 slots."""

    def __init__(self, d_model: int, n_heads: int, num_states: int = NUM_COGNITIVE_STATES):
        super().__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"

        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.num_states = num_states
        self.scale = math.sqrt(self.head_dim)

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.feedback_proj = nn.Linear(d_model, d_model)

        self.register_buffer("domain_mask", build_domain_descent_mask(num_states))

    @staticmethod
    def _normalize_attention_mask(
        attention_mask: Optional[torch.Tensor],
        batch: int,
        seq_len: int,
        device: torch.device,
    ) -> torch.Tensor:
        if attention_mask is None:
            return torch.ones(batch, seq_len, device=device, dtype=torch.bool)
        return attention_mask.to(device=device, dtype=torch.bool)

    def _aggregate_slots(
        self,
        x: torch.Tensor,
        slot_weights: torch.Tensor,
        attention_mask: Optional[torch.Tensor],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Aggregate token states into explicit cognitive-state slots."""
        batch, seq_len, _ = x.shape
        token_mask = self._normalize_attention_mask(attention_mask, batch, seq_len, x.device)
        masked_slot_weights = slot_weights * token_mask.unsqueeze(-1).to(slot_weights.dtype)

        slot_mass = masked_slot_weights.sum(dim=1)  # (batch, 40)
        slot_states = torch.einsum("bsd,bsk->bkd", x, masked_slot_weights)
        slot_states = slot_states / slot_mass.unsqueeze(-1).clamp_min(1e-8)
        slot_mask = slot_mass > 1e-8

        return slot_states, slot_mask, masked_slot_weights

    def slot_attention_weights(
        self,
        slot_states: torch.Tensor,
        slot_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Return slot-level attention weights after the descent mask is applied."""
        batch, num_slots, _ = slot_states.shape
        if num_slots != self.num_states:
            raise ValueError(f"expected {self.num_states} slots, got {num_slots}")

        q = self.q_proj(slot_states).view(batch, num_slots, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(slot_states).view(batch, num_slots, self.n_heads, self.head_dim).transpose(1, 2)
        attn_logits = torch.matmul(q, k.transpose(-2, -1)) / self.scale

        allowed = self.domain_mask.unsqueeze(0).unsqueeze(0)
        if slot_mask is not None:
            key_mask = slot_mask.unsqueeze(1).unsqueeze(1)
            allowed = allowed & key_mask

        attn_logits = attn_logits.masked_fill(~allowed, -1e9)
        attn_weights = F.softmax(attn_logits, dim=-1)

        if slot_mask is not None:
            query_mask = slot_mask.unsqueeze(1).unsqueeze(-1).to(attn_weights.dtype)
            attn_weights = attn_weights * query_mask
            attn_weights = attn_weights / attn_weights.sum(dim=-1, keepdim=True).clamp_min(1e-8)

        return attn_weights

    def forward(
        self,
        x: torch.Tensor,
        slot_weights: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        causal: bool = False,
    ) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model)
            slot_weights: Token-to-slot weights of shape (batch, seq, 40)
            attention_mask: Optional padding mask of shape (batch, seq)
            causal: If True, each token position aggregates only its prefix.

        Returns:
            Output tensor of shape (batch, seq, d_model)
        """
        batch, seq_len, _ = x.shape
        if slot_weights.shape != (batch, seq_len, self.num_states):
            raise ValueError(
                f"slot_weights must have shape {(batch, seq_len, self.num_states)}, "
                f"got {tuple(slot_weights.shape)}"
            )

        token_mask = self._normalize_attention_mask(attention_mask, batch, seq_len, x.device)
        if causal:
            outputs = []
            for pos in range(seq_len):
                prefix_x = x[:, : pos + 1, :]
                prefix_slot_weights = slot_weights[:, : pos + 1, :]
                prefix_mask = token_mask[:, : pos + 1]
                slot_states, slot_mask, masked_prefix_weights = self._aggregate_slots(
                    prefix_x,
                    prefix_slot_weights,
                    prefix_mask,
                )

                q = self.q_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)
                k = self.k_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)
                v = self.v_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)

                attn_logits = torch.matmul(q, k.transpose(-2, -1)) / self.scale
                allowed = self.domain_mask.unsqueeze(0).unsqueeze(0) & slot_mask.unsqueeze(1).unsqueeze(1)
                attn_logits = attn_logits.masked_fill(~allowed, -1e9)

                attn_weights = F.softmax(attn_logits, dim=-1)
                query_mask = slot_mask.unsqueeze(1).unsqueeze(-1).to(attn_weights.dtype)
                attn_weights = attn_weights * query_mask
                attn_weights = attn_weights / attn_weights.sum(dim=-1, keepdim=True).clamp_min(1e-8)

                slot_output = torch.matmul(attn_weights, v)
                slot_output = slot_output.transpose(1, 2).contiguous().view(batch, self.num_states, self.d_model)
                slot_output = self.out_proj(slot_output)
                slot_output = slot_output * slot_mask.unsqueeze(-1).to(slot_output.dtype)

                # Preserve the same O -> P feedback behavior, but only over
                # slots visible in the current prefix.
                o_mask = slot_mask[:, 30:40]
                if o_mask.any():
                    o_states = slot_output[:, 30:40, :]
                    feedback_denom = o_mask.sum(dim=1, keepdim=True).clamp_min(1).to(o_states.dtype)
                    feedback = (o_states * o_mask.unsqueeze(-1).to(o_states.dtype)).sum(dim=1, keepdim=True)
                    feedback = self.feedback_proj(feedback / feedback_denom.unsqueeze(-1))
                    slot_output = slot_output.clone()
                    slot_output[:, 0:10, :] = slot_output[:, 0:10, :] + feedback

                current_slot_weights = masked_prefix_weights[:, -1, :]
                outputs.append(torch.einsum("bkd,bk->bd", slot_output, current_slot_weights))

            token_output = torch.stack(outputs, dim=1)
            return token_output * token_mask.unsqueeze(-1).to(token_output.dtype)

        slot_states, slot_mask, masked_slot_weights = self._aggregate_slots(
            x, slot_weights, token_mask
        )

        q = self.q_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(slot_states).view(batch, self.num_states, self.n_heads, self.head_dim).transpose(1, 2)

        attn_logits = torch.matmul(q, k.transpose(-2, -1)) / self.scale
        allowed = self.domain_mask.unsqueeze(0).unsqueeze(0) & slot_mask.unsqueeze(1).unsqueeze(1)
        attn_logits = attn_logits.masked_fill(~allowed, -1e9)

        attn_weights = F.softmax(attn_logits, dim=-1)
        query_mask = slot_mask.unsqueeze(1).unsqueeze(-1).to(attn_weights.dtype)
        attn_weights = attn_weights * query_mask
        attn_weights = attn_weights / attn_weights.sum(dim=-1, keepdim=True).clamp_min(1e-8)

        slot_output = torch.matmul(attn_weights, v)
        slot_output = slot_output.transpose(1, 2).contiguous().view(batch, self.num_states, self.d_model)
        slot_output = self.out_proj(slot_output)
        slot_output = slot_output * slot_mask.unsqueeze(-1).to(slot_output.dtype)

        # Learned O -> P feedback on the explicit slot bank.
        o_mask = slot_mask[:, 30:40]
        if o_mask.any():
            o_states = slot_output[:, 30:40, :]
            feedback_denom = o_mask.sum(dim=1, keepdim=True).clamp_min(1).to(o_states.dtype)
            feedback = (o_states * o_mask.unsqueeze(-1).to(o_states.dtype)).sum(dim=1, keepdim=True)
            feedback = self.feedback_proj(feedback / feedback_denom.unsqueeze(-1))
            slot_output = slot_output.clone()
            slot_output[:, 0:10, :] = slot_output[:, 0:10, :] + feedback

        token_output = torch.einsum("bkd,bsk->bsd", slot_output, masked_slot_weights)
        token_output = token_output * token_mask.unsqueeze(-1).to(token_output.dtype)
        return token_output
