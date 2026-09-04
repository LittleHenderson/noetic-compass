"""Optional differentiable passive conductance operator for CASformer graphs."""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class ConductanceCircuitResult:
    node_potential: Tensor
    edge_current: Tensor
    conductance: Tensor
    laplacian: Tensor
    solve_residual: Tensor


class DifferentiableConductanceCircuit(nn.Module):
    """Solve a regularized positive-conductance graph.

    For incidence matrix ``B`` and edge conductance ``G = 1/R`` this computes
    ``L = B.T @ diag(G) @ B`` and solves ``(L + damping*I)u = drive``.
    It captures passive series/parallel topology.  Directed Cause-to-Effect CJT
    transformations remain separate controlled operators.
    """

    def __init__(self, *, damping: float = 1e-3, minimum_resistance: float = 0.1) -> None:
        super().__init__()
        if (
            not math.isfinite(damping)
            or not math.isfinite(minimum_resistance)
            or damping <= 0
            or minimum_resistance <= 0
        ):
            raise ValueError("damping and minimum_resistance must be finite and positive")
        self.damping = damping
        self.minimum_resistance = minimum_resistance

    def forward(
        self,
        incidence: Tensor,
        resistance: Tensor,
        drive: Tensor,
    ) -> ConductanceCircuitResult:
        if drive.ndim != 3 or not drive.is_floating_point():
            raise ValueError("drive must be floating point with shape [batch, nodes, channels]")
        batch, nodes, _ = drive.shape
        typed_damping = torch.as_tensor(
            self.damping, dtype=drive.dtype, device=drive.device
        )
        typed_minimum_resistance = torch.as_tensor(
            self.minimum_resistance, dtype=drive.dtype, device=drive.device
        )
        if not bool(torch.isfinite(typed_damping).item()) or not bool(
            (typed_damping > 0).item()
        ):
            raise ValueError("damping must be representably positive in the runtime dtype")
        if not bool(torch.isfinite(typed_minimum_resistance).item()) or not bool(
            (typed_minimum_resistance > 0).item()
        ):
            raise ValueError(
                "minimum_resistance must be representably positive in the runtime dtype"
            )
        if incidence.ndim == 2:
            incidence = incidence.unsqueeze(0).expand(batch, -1, -1)
        if incidence.ndim != 3 or incidence.shape[0] != batch or incidence.shape[2] != nodes:
            raise ValueError("incidence must have shape [edges, nodes] or [batch, edges, nodes]")
        edges = incidence.shape[1]
        if resistance.ndim == 1:
            resistance = resistance.unsqueeze(0).expand(batch, -1)
        if tuple(resistance.shape) != (batch, edges):
            raise ValueError("resistance must have shape [edges] or [batch, edges]")
        if incidence.dtype != drive.dtype or resistance.dtype != drive.dtype:
            raise ValueError("incidence, resistance, and drive must share a floating dtype")
        if incidence.device != drive.device or resistance.device != drive.device:
            raise ValueError("incidence, resistance, and drive must share a device")
        for name, value in {
            "incidence": incidence,
            "resistance": resistance,
            "drive": drive,
        }.items():
            if not bool(torch.isfinite(value).all().item()):
                raise ValueError(f"{name} must be finite")
        if bool((resistance < typed_minimum_resistance).any().item()):
            raise ValueError(
                f"resistance must be at least {self.minimum_resistance}"
            )

        conductance = resistance.reciprocal()
        if not bool(torch.isfinite(conductance).all().item()) or not bool(
            (conductance > 0).all().item()
        ):
            raise ValueError(
                "circuit conductance must be finite and representably positive"
            )
        weighted_incidence = incidence * conductance.unsqueeze(-1)
        if not bool(torch.isfinite(weighted_incidence).all().item()):
            raise ValueError("weighted circuit incidence overflowed or became non-finite")
        laplacian = torch.matmul(incidence.transpose(-2, -1), weighted_incidence)
        if not bool(torch.isfinite(laplacian).all().item()):
            raise ValueError("circuit Laplacian overflowed or became non-finite")
        identity = torch.eye(nodes, dtype=drive.dtype, device=drive.device).expand(
            batch, nodes, nodes
        )
        system = laplacian + typed_damping * identity
        if not bool(torch.isfinite(system).all().item()):
            raise ValueError("circuit system overflowed or became non-finite")
        if not bool(
            (system.diagonal(dim1=-2, dim2=-1) > laplacian.diagonal(dim1=-2, dim2=-1))
            .all()
            .item()
        ):
            raise ValueError(
                "damping is too small to survive addition to the circuit "
                "Laplacian in the runtime dtype"
            )
        try:
            node_potential = torch.linalg.solve(system, drive)
        except RuntimeError as error:
            raise ValueError("regularized circuit system could not be solved") from error
        edge_drop = torch.matmul(incidence, node_potential)
        edge_current = conductance.unsqueeze(-1) * edge_drop
        residual = torch.matmul(system, node_potential) - drive
        if not all(
            bool(torch.isfinite(value).all().item())
            for value in (node_potential, edge_current, residual)
        ):
            raise ValueError("circuit solution became non-finite")
        return ConductanceCircuitResult(
            node_potential=node_potential,
            edge_current=edge_current,
            conductance=conductance,
            laplacian=laplacian,
            solve_residual=residual,
        )
