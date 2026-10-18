"""rpa_creative_searchlight.py -- Bounded Creative Radius Search over the REAL RPA Atlas.

BOUND TO REAL RPA MODEL:
Directly imports and operates over real_atlas.rpa_model (AtlasNode, AtlasSnapshot,
AtlasContext, AtlasLink, NodeStatus, NodeKind, LinkType).

Implements the owner's "5 points ahead/behind/left/right" verified reconstruction loop:
When the verifier refuses at target station S0, HELM activates the Creative Radius
searchlight, geometrically widening across radii 1 -> 2 -> 4 -> 8 (bounded to 15 candidates total).

Ahead/Behind: Traversal along the 7 Archetypes (1:Unity .. 7:Rhythm)
Left/Right  : Traversal across the 4 Planes (Spiritual, Mental, Emotional, Physical)

Every candidate is created as an official AtlasNode in state NodeStatus.HYPOTHETICAL.
Only an exact match by an authoritative verifier promotes it to NodeStatus.VERIFIED.
"""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Tuple, Any

# Ensure real_atlas is discoverable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from real_atlas.rpa_model import (
    AtlasNode, AtlasContext, AtlasLink, AtlasSnapshot,
    NodeStatus, NodeKind, LinkType
)

PLANES = ["Spiritual", "Mental", "Emotional", "Physical"]
PLANE_KEYS = ["a", "b", "c", "d"]
ARCHETYPES = [
    "Divine Purpose", "Wisdom / Law", "Vitality / Life",
    "Love / Value", "Power / Will", "Creation / Form", "Rest / Sabbath"
]


@dataclass
class SearchlightTrace:
    anchor_node_id: str
    radii_traversed: List[int] = field(default_factory=list)
    candidates_evaluated: int = 0
    accepted_node: Optional[AtlasNode] = None
    final_verdict: str = "SEARCHING"
    reason: str = ""
    updated_snapshot: Optional[AtlasSnapshot] = None


class RPACreativeSearchlight:
    """The Searchlight: Bounded widening over the real RPA Atlas graph."""

    def __init__(self, max_radius_cap: int = 8):
        self.max_radius_cap = max_radius_cap
        self.allowed_radii = [1, 2, 4, 8]

    @staticmethod
    def parse_tks_from_node(node: AtlasNode) -> Tuple[int, int]:
        """Extract (plane_idx, archetype_idx) from an AtlasNode's fields or node_id."""
        node_fields = dict(node.fields)
        if "plane_idx" in node_fields and "archetype_idx" in node_fields:
            return int(node_fields["plane_idx"]), int(node_fields["archetype_idx"])
        # Fallback parse from node_id or idea_id like 'TKS_2b' -> (1, 2)
        code = node_fields.get("tks_code") or node.idea_id.replace("TKS_", "")
        if len(code) >= 2 and code[0].isdigit() and code[1] in PLANE_KEYS:
            arch = int(code[0])
            plane = PLANE_KEYS.index(code[1])
            return plane, arch
        # Default anchor: Mental Wisdom (1, 2)
        return 1, 2

    def generate_candidate_nodes(self, 
                                 anchor: AtlasNode, 
                                 radius: int) -> List[Tuple[AtlasNode, AtlasLink]]:
        """Generate real AtlasNode and AtlasLink candidates within the bounded radius around anchor.
        Budget per radius R matches POLICY_v0_2_FROZEN.md (1 at R=1, 2 at R=2, 4 at R=4, 8 at R=8 -> total 15).
        """
        plane_idx, arch_idx = self.parse_tks_from_node(anchor)
        context = anchor.context

        # Ahead / Behind (Archetype axis):
        ahead_arch = ((arch_idx - 1 + radius) % 7) + 1
        behind_arch = ((arch_idx - 1 - radius) % 7) + 1

        # Left / Right (Plane axis):
        left_plane = (plane_idx - radius) % 4
        right_plane = (plane_idx + radius) % 4

        moves = [
            ("AHEAD", plane_idx, ahead_arch, 0, radius),
            ("BEHIND", plane_idx, behind_arch, 0, -radius),
            ("LEFT", left_plane, arch_idx, -radius, 0),
            ("RIGHT", right_plane, arch_idx, radius, 0),
            ("AHEAD_LEFT", left_plane, ahead_arch, -radius, radius),
            ("AHEAD_RIGHT", right_plane, ahead_arch, radius, radius),
            ("BEHIND_LEFT", left_plane, behind_arch, -radius, -radius),
            ("BEHIND_RIGHT", right_plane, behind_arch, radius, -radius),
        ]

        candidates = []
        for name, p_i, a_i, dx, dy in moves[:radius]:
            code = f"{a_i}{PLANE_KEYS[p_i]}"
            node_id = f"hypo_{code}_r{radius}_{name.lower()}"
            idea_id = f"idea_{code}"
            label = f"Hypothesis {code} ({PLANES[p_i]} {ARCHETYPES[a_i - 1]}) at radius {radius} via {name}"
            
            node_fields = (
                ("archetype_idx", str(a_i)),
                ("direction", name),
                ("plane_idx", str(p_i)),
                ("radius", str(radius)),
                ("tks_code", code),
            )
            
            cand_node = AtlasNode(
                node_id=node_id,
                idea_id=idea_id,
                label=label,
                context=context,
                status=NodeStatus.HYPOTHETICAL,
                fields=node_fields,
                kind=NodeKind.STATE
            )
            
            link = AtlasLink(
                link_id=f"link_{anchor.node_id}_to_{node_id}",
                source_id=anchor.node_id,
                target_id=node_id,
                relation=LinkType.REACHABLE_VIA,
                action_id=f"act_traverse_r{radius}_{name.lower()}",
                transition_status="candidate"
            )
            candidates.append((cand_node, link))

        return candidates

    def search_atlas(self,
                     snapshot: AtlasSnapshot,
                     verifier: Callable[[AtlasNode], bool],
                     anchor_node_id: Optional[str] = None,
                     max_cap: Optional[int] = None) -> SearchlightTrace:
        """Execute the verified widening search over the real AtlasSnapshot."""
        cap = min(self.max_radius_cap, max_cap or self.max_radius_cap)
        anchor_id = anchor_node_id or snapshot.focus_node_id
        nodes_dict = {n.node_id: n for n in snapshot.nodes}
        anchor = nodes_dict[anchor_id]

        trace = SearchlightTrace(anchor_node_id=anchor_id)
        all_new_nodes = list(snapshot.nodes)
        all_new_links = list(snapshot.links)

        for r in self.allowed_radii:
            if r > cap:
                break
            trace.radii_traversed.append(r)
            stage_cands = self.generate_candidate_nodes(anchor, r)

            for cand_node, link in stage_cands:
                trace.candidates_evaluated += 1
                all_new_nodes.append(cand_node)
                all_new_links.append(link)

                # Authoritative verifier check: exact match required
                is_match = verifier(cand_node)
                if is_match:
                    # Promote candidate from HYPOTHETICAL to VERIFIED
                    verified_node = AtlasNode(
                        node_id=cand_node.node_id,
                        idea_id=cand_node.idea_id,
                        label=cand_node.label,
                        context=cand_node.context,
                        status=NodeStatus.VERIFIED,
                        fields=cand_node.fields,
                        kind=cand_node.kind
                    )
                    # Replace hypothetical node with verified node
                    all_new_nodes[-1] = verified_node
                    trace.accepted_node = verified_node
                    trace.final_verdict = "MATCH_ADMITTED"
                    trace.reason = f"Exact match verified at radius {r}: {verified_node.label}"

                    trace.updated_snapshot = AtlasSnapshot(
                        nodes=tuple(all_new_nodes),
                        links=tuple(all_new_links),
                        current_state_id=verified_node.node_id,
                        focus_node_id=verified_node.node_id,
                        hypothesis_branch_id=None
                    )
                    return trace

        trace.final_verdict = "REFUSE_SEARCH_CAP_REACHED"
        trace.reason = f"No candidate satisfied verifier within radius cap {cap} (evaluated {trace.candidates_evaluated} candidates)"
        trace.updated_snapshot = AtlasSnapshot(
            nodes=tuple(all_new_nodes),
            links=tuple(all_new_links),
            current_state_id=snapshot.current_state_id,
            focus_node_id=snapshot.focus_node_id,
            hypothesis_branch_id=None
        )
        return trace


def self_test():
    print("Testing RPACreativeSearchlight directly on real_atlas.rpa_model...")
    context = AtlasContext(
        context_id="ctx_helm_search",
        model_version="rpa/0.1",
        observation_id="obs_001",
        observation_time="2026-10-17T20:00:00Z",
        record_version=1
    )
    anchor_node = AtlasNode(
        node_id="station_s0",
        idea_id="TKS_2b",
        label="Station S0 (Mental Wisdom / Law 2b)",
        context=context,
        status=NodeStatus.VERIFIED,
        fields=(("archetype_idx", "2"), ("plane_idx", "1"), ("tks_code", "2b")),
        kind=NodeKind.STATE
    )
    initial_snapshot = AtlasSnapshot(
        nodes=(anchor_node,),
        links=(),
        current_state_id="station_s0",
        focus_node_id="station_s0"
    )

    searchlight = RPACreativeSearchlight(max_radius_cap=8)

    # Test 1: Verifier matches target at radius 2 (Mental Love 4b)
    def test_verifier_match_at_r2(node: AtlasNode) -> bool:
        node_fields = dict(node.fields)
        return node_fields.get("radius") == "2" and node_fields.get("tks_code") == "4b"

    trace1 = searchlight.search_atlas(initial_snapshot, test_verifier_match_at_r2)
    assert trace1.final_verdict == "MATCH_ADMITTED"
    assert trace1.accepted_node is not None
    assert trace1.accepted_node.status == NodeStatus.VERIFIED
    assert trace1.updated_snapshot is not None
    assert trace1.updated_snapshot.current_state_id == trace1.accepted_node.node_id
    print(f"[PASS] Scenario 1 verified with real AtlasNode: {trace1.reason}")

    # Test 2: Verifier refuses all -> Bounded clean halt at cap 8
    def test_verifier_refuse_all(node: AtlasNode) -> bool:
        return False

    trace2 = searchlight.search_atlas(initial_snapshot, test_verifier_refuse_all)
    assert trace2.final_verdict == "REFUSE_SEARCH_CAP_REACHED"
    assert trace2.candidates_evaluated == 15, f"Expected exactly 15 candidates, got {trace2.candidates_evaluated}"
    print(f"[PASS] Scenario 2 verified (Clean halt after exactly 15 candidates): {trace2.reason}")
    print("ALL RPA CREATIVE SEARCHLIGHT TESTS PASSED (BOUND TO REAL RPA MODEL).")


if __name__ == "__main__":
    self_test()
