"""A trainable collection of Neural CJTs with explicit typed topology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from torch import Tensor, nn

from casformer import CASControl, CASformerConfig

from .neural import NeuralCJT, NeuralCJTProposal
from .types import CausePacket


class NetworkError(ValueError):
    """A node identity, topology edge, or selection request was invalid."""


@dataclass(frozen=True, slots=True)
class CJTNodeSpec:
    cjt_id: str
    operation_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.cjt_id, str) or not self.cjt_id:
            raise NetworkError("cjt_id must be a nonempty string")
        if not isinstance(self.operation_id, str) or not self.operation_id:
            raise NetworkError("operation_id must be a nonempty string")


@dataclass(frozen=True, slots=True)
class TopologyEdge:
    source_cjt_id: str
    target_cjt_id: str
    permitted: bool = True


class NeuralCJTNetwork(nn.Module):
    """Module container plus deterministic operation and topology selection.

    Selection only chooses proposal machinery.  It does not verify, publish, or
    commit an Effect.
    """

    def __init__(
        self,
        config: CASformerConfig,
        node_specs: Sequence[CJTNodeSpec],
        *,
        topology: Sequence[TopologyEdge] = (),
    ) -> None:
        super().__init__()
        specs = tuple(node_specs)
        if not specs or len({item.cjt_id for item in specs}) != len(specs):
            raise NetworkError("network requires unique CJT node identities")
        self.config = config
        self._specs = {item.cjt_id: item for item in specs}
        self._module_keys = {
            item.cjt_id: f"node_{index:04d}" for index, item in enumerate(specs)
        }
        self.cells = nn.ModuleDict(
            {
                self._module_keys[item.cjt_id]: NeuralCJT(config)
                for item in specs
            }
        )
        edges = tuple(topology)
        known = set(self._specs)
        if any(
            edge.source_cjt_id not in known or edge.target_cjt_id not in known
            for edge in edges
        ):
            raise NetworkError("topology refers to an unknown CJT")
        if len({(edge.source_cjt_id, edge.target_cjt_id) for edge in edges}) != len(edges):
            raise NetworkError("topology contains duplicate directed edges")
        self._topology = {
            (edge.source_cjt_id, edge.target_cjt_id): edge.permitted for edge in edges
        }

    @property
    def node_specs(self) -> tuple[CJTNodeSpec, ...]:
        return tuple(self._specs[key] for key in sorted(self._specs))

    def node(self, cjt_id: str) -> NeuralCJT:
        try:
            return self.cells[self._module_keys[cjt_id]]
        except KeyError as exc:
            raise NetworkError(f"unknown CJT node: {cjt_id}") from exc

    def spec(self, cjt_id: str) -> CJTNodeSpec:
        try:
            return self._specs[cjt_id]
        except KeyError as exc:
            raise NetworkError(f"unknown CJT node: {cjt_id}") from exc

    def edge_permitted(self, source_cjt_id: str, target_cjt_id: str) -> bool:
        if source_cjt_id not in self._specs or target_cjt_id not in self._specs:
            return False
        return self._topology.get((source_cjt_id, target_cjt_id), False)

    def select_candidates(self, cause: CausePacket) -> tuple[str, ...]:
        """Return nodes whose registered operation is requested by the Cause."""

        requested = set(cause.candidate_operation_ids)
        candidates = [
            spec.cjt_id
            for spec in self.node_specs
            if spec.operation_id in requested
        ]
        if cause.originating_cjt_id is not None:
            candidates = [
                cjt_id
                for cjt_id in candidates
                if self.edge_permitted(cause.originating_cjt_id, cjt_id)
            ]
        return tuple(candidates)

    def forward_node(
        self,
        cjt_id: str,
        x: Tensor,
        control: CASControl,
    ) -> NeuralCJTProposal:
        spec = self.spec(cjt_id)
        return self.node(cjt_id)(x, control, operation_id=spec.operation_id)

    def parameter_names_for_node(
        self,
        cjt_id: str,
        *,
        include_engine: bool = False,
        include_bias_head: bool = False,
    ) -> tuple[str, ...]:
        """Return an exact plasticity allowlist for one node only."""

        spec = self.spec(cjt_id)
        prefix = f"cells.{self._module_keys[cjt_id]}."
        operation_prefix = prefix + f"operations.modules_by_operation.{spec.operation_id}."
        allowed: list[str] = []
        for name, _ in self.named_parameters():
            if name.startswith(operation_prefix):
                allowed.append(name)
            elif include_bias_head and name.startswith(prefix + "bias_update_head."):
                allowed.append(name)
            elif include_engine and name.startswith(prefix + "engine."):
                allowed.append(name)
        if not allowed:
            raise NetworkError("node plasticity allowlist selected no parameters")
        return tuple(sorted(allowed))

    def topology_manifest(self) -> dict[str, object]:
        return {
            "schema_version": "cas.neural-cjt.topology/0.2",
            "nodes": [
                {"cjt_id": item.cjt_id, "operation_id": item.operation_id}
                for item in self.node_specs
            ],
            "edges": [
                {
                    "source_cjt_id": source,
                    "target_cjt_id": target,
                    "permitted": permitted,
                }
                for (source, target), permitted in sorted(self._topology.items())
            ],
        }


__all__ = [
    "CJTNodeSpec",
    "NetworkError",
    "NeuralCJTNetwork",
    "TopologyEdge",
]
