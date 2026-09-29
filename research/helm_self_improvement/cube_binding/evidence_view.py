"""Filtered read-only projection over incumbent host/Harness evidence."""
from copy import deepcopy

from ..observation import reload_observation, reload_configuration_inputs
from .contracts import PUBLIC_PROFILE, SCIENTIFIC_SOURCE, digest, public_runtime, require


def binding_evidence_view(host, event_digest, packet):
    """Reload immutable evidence. No model, callback, hook, launch or promotion."""
    checked = public_runtime()["course"].validate_model_packet(packet)
    require(checked["record"]["query"]["kind"] == "parts" and checked["record"]["supports"] == []
            and checked["record"]["cue"] is None and len(checked["source"]["worlds"]) == 1,
            "CB1_VIEW_PACKET_PROFILE")
    loaded = reload_observation(host, event_digest)
    receipt = loaded["observation"]
    require(receipt["input_sha256"] == digest(checked)
            and receipt["scientific_source"] == SCIENTIFIC_SOURCE, "CB1_VIEW_SOURCE_INPUT")
    converted = reload_configuration_inputs(host, event_digest)
    world = next(w for w in checked["source"]["worlds"]
                 if w["world_id"] == checked["source"]["focus_world_id"])
    return {"schema": "helm.binding-evidence-view/1", "readonly": True,
        "profile": PUBLIC_PROFILE, "source": SCIENTIFIC_SOURCE,
        "checkpoint_sha256": receipt["checkpoint_sha256"], "input_sha256": receipt["input_sha256"],
        "anchor": deepcopy(loaded["rpa_projection"]),
        "authored_structure": {"origin": "PUBLIC_SUPPLIED_GRAPH_NOT_INFERRED",
            "nodes": [{"ref": n["ref"], "label": n["label"]} for n in world["nodes"]],
            "semantic_edges": [{"source": e["source"], "target": e["target"], "predicate": "contains"}
                               for e in world["contains"]]},
        "measurement": {"complete": converted["complete"], "coverage": deepcopy(converted["coverage"]),
                        "errors": list(receipt["errors"])},
        "model_inferred_binding": None, "reconstruction": None, "counterfactual": None,
        "evaluation": None, "missing": ["FITTED_BINDING", "RECONSTRUCTION", "COUNTERFACTUAL", "EVALUATION"],
        "execute_action": None, "promotion": False}
