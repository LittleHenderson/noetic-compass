"""Versioned, instance-local observation of the pinned HELM learner.

The original source file/module/class is never patched. The three compiled
definitions below keep its computation and add only calls whose return is the
original value. This is not a replacement learner or an intervention engine.
"""
import ast
import hashlib
from pathlib import Path

SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
LEARNER_SHA256 = "0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8"


def instrumented_graph(learner, emit):
    original = type(learner)._graph
    namespace = dict(original.__globals__)
    path = Path(original.__code__.co_filename)
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != LEARNER_SHA256:
        raise ValueError("UNSUPPORTED_LEARNER_SOURCE")
    tree = ast.parse(source, filename=str(path))
    wanted = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_rounds":
            wanted["_rounds"] = ast.get_source_segment(source.decode(), node)
        elif isinstance(node, ast.ClassDef) and node.name == "GraphForward":
            wanted["GraphForward"] = ast.get_source_segment(source.decode(), node)
        elif isinstance(node, ast.ClassDef) and node.name == "PointerCourseLearner":
            graph = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "_graph")
            import textwrap
            wanted["_graph"] = textwrap.dedent("    " + ast.get_source_segment(source.decode(), graph))
    if set(wanted) != {"_rounds", "GraphForward", "_graph"}:
        raise ValueError("CAPTURE_SOURCE_LAYOUT")

    def replace(which, before, after):
        if wanted[which].count(before) != 1:
            raise ValueError("CAPTURE_SOURCE_SEAM:" + which + ":" + before)
        wanted[which] = wanted[which].replace(before, after)

    replace("_rounds", "hidden = _rms_unit(torch, model.node_encode(raw))",
            "hidden = _rms_unit(torch, model.node_encode(raw))\n    _hh_emit('graph.initial_state', hidden)")
    # Reuse _rounds' real observe seam; preserve any incumbent callback.
    replace("_rounds", "if observe is not None:\n            observe(round_index, hidden_input)",
            "if observe is not None:\n            observe(round_index, hidden_input)\n        _hh_emit('graph.round_input', hidden_input, round_index)")
    replace("_rounds", "update = model.core_block(hidden_input)",
            "update = model.core_block(hidden_input)\n        _hh_emit('graph.round_update', update, round_index)")
    replace("_rounds", "hidden = _rms_unit(torch, hidden + PER_ROUND_UPDATE_CAP * torch.tanh(model.round_rate) * update)",
            "hidden = _rms_unit(torch, hidden + PER_ROUND_UPDATE_CAP * torch.tanh(model.round_rate) * update)\n        _hh_emit('graph.round_state', hidden, round_index)")
    for member, expression in [("hidden", "_rounds(torch, model, self.blocks, charge=charge)"),
                               ("query_value", "self._encode_query()"),
                               ("pointer_query", "model.pointer_key(self.query_value)"),
                               ("node_rows", "model.node_head(node_input)")]:
        site = {"hidden":"graph.node_state", "query_value":"graph.query_state",
                "pointer_query":"graph.pointer_query", "node_rows":"head.node"}[member]
        line = "self." + member + " = " + expression
        replace("GraphForward", line, line + "\n        _hh_emit('" + site + "', self." + member + ")")
    replace("GraphForward", "return model.reach_option_head(value).reshape(-1)",
            "return _hh_emit('head.reach', model.reach_option_head(value).reshape(-1))")
    replace("GraphForward", "return states.matmul(self.pointer_query)",
            "return _hh_emit('head.node_pointer', states.matmul(self.pointer_query))")
    replace("GraphForward", "return self.hidden.new_zeros(0)",
            "return _hh_emit('head.node_pointer', self.hidden.new_zeros(0))")
    replace("_graph", "reading[\"_device\"] = self.device",
            "_hh_emit('input.mapping', reading)\n    reading[\"_device\"] = self.device")
    for site, line, value in [
        ("answer.scores", "scores = _logit_rows(torch, plan, values)", "scores"),
        ("answer.decisions", "decisions = slots.score_decisions(packet, scores)", "decisions"),
        ("answer.assembly", "answer = slots.assemble_answer(packet, decisions)", "answer")]:
        replace("_graph", line, line + "\n    _hh_emit('" + site + "', " + value + ")")
    namespace["_hh_emit"] = emit
    for key in ("_rounds", "GraphForward", "_graph"):
        exec(compile(wanted[key], str(path) + "::HH_CAPTURE_V1", "exec"), namespace)
    return namespace["_graph"], namespace["CORE_ROUNDS"], {
        "source_sha256": LEARNER_SHA256,
        "instrumented_definitions_sha256": hashlib.sha256("\n".join(wanted.values()).encode()).hexdigest(),
        "source_edit": False, "global_monkeypatch": False,
    }
