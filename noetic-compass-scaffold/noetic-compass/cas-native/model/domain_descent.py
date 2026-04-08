"""
DomainDescentAttention: Custom attention with causal mask enforcing the
Domain Descent hierarchy P -> C -> E -> O.

The 40 cognitive states are grouped by domain:
  P (Principled):  indices 0-9   (CO-0 through CO-9)
  C (Cognitive):   indices 10-19
  E (Evaluative):  indices 20-29
  O (Operational): indices 30-39

Information flow rules:
  - P attends only to P         (positions 0-9)
  - C attends to P + C          (positions 0-19)
  - E attends to P + C + E      (positions 0-29)
  - O attends to all            (positions 0-39)
  - O -> P feedback via learned skip connection (nn.Linear)
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


NUM_COGNITIVE_STATES = 40
DOMAIN_SIZE = 10  # 10 operators per domain


def build_domain_descent_mask(num_states: int = NUM_COGNITIVE_STATES) -> torch.Tensor:
    """Build the domain descent causal mask.

    Returns:
        Boolean mask of shape (num_states, num_states) where True means
        "allowed to attend". mask[i, j] = True if state i can attend to state j.
    """
    mask = torch.zeros(num_states, num_states, dtype=torch.bool)

    # P (0-9) attends only to P (0-9)
    mask[0:10, 0:10] = True

    # C (10-19) attends to P + C (0-19)
    mask[10:20, 0:20] = True

    # E (20-29) attends to P + C + E (0-29)
    mask[20:30, 0:30] = True

    # O (30-39) attends to all (0-39)
    mask[30:40, 0:40] = True

    return mask


class DomainDescentAttention(nn.Module):
    """Multi-head attention with domain descent causal masking.

    Implements scaled dot-product attention where the attention pattern
    is constrained by the P -> C -> E -> O information flow hierarchy.
    Includes O -> P feedback via a learned skip connection.
    """

    def __init__(self, d_model: int, n_heads: int, num_states: int = NUM_COGNITIVE_STATES):
        super().__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"

        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.num_states = num_states
        self.scale = math.sqrt(self.head_dim)

        # Standard QKV projections
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # O -> P feedback: learned skip connection from Operational back to Principled
        self.feedback_proj = nn.Linear(d_model, d_model)

        # Register the domain descent mask as a buffer (non-learnable)
        self.register_buffer("domain_mask", build_domain_descent_mask(num_states))

    def _apply_domain_mask(self, attn_weights: torch.Tensor, seq_len: int) -> torch.Tensor:
        """Apply the domain descent mask to attention weights.

        For sequences shorter or longer than 40, we tile/truncate the mask
        to cover the full sequence length.
        """
        # Build a mask for the actual sequence length
        if seq_len <= self.num_states:
            mask = self.domain_mask[:seq_len, :seq_len]
        else:
            # Tile the 40x40 mask to cover longer sequences
            repeats_r = (seq_len + self.num_states - 1) // self.num_states
            repeats_c = repeats_r
            mask = self.domain_mask.repeat(repeats_r, repeats_c)[:seq_len, :seq_len]

        # Where mask is False, fill with -inf to zero out after softmax
        attn_weights = attn_weights.masked_fill(
            ~mask.unsqueeze(0).unsqueeze(0),  # (1, 1, seq, seq)
            float("-inf"),
        )
        return attn_weights

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model)

        Returns:
            Output tensor of shape (batch, seq, d_model)
        """
        batch, seq_len, _ = x.shape

        # QKV projections
        q = self.q_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)

        # Scaled dot-product attention
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / self.scale

        # Apply domain descent mask
        attn_weights = self._apply_domain_mask(attn_weights, seq_len)

        # Softmax (masked positions become 0 attention)
        attn_weights = F.softmax(attn_weights, dim=-1)

        # Attend to values
        attn_output = torch.matmul(attn_weights, v)

        # Reshape back
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch, seq_len, self.d_model)
        output = self.out_proj(attn_output)

        # O -> P feedback: extract O domain states and project back to P positions
        if seq_len >= self.num_states:
            # Extract Operational domain output (positions 30-39)
            o_states = output[:, 30:40, :]
            # Project and aggregate feedback
            feedback = self.feedback_proj(o_states.mean(dim=1, keepdim=True))
            # Add feedback to Principled domain positions (0-9)
            output = output.clone()
            output[:, 0:10, :] = output[:, 0:10, :] + feedback

        return output
