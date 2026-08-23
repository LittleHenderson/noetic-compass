# -*- coding: utf-8 -*-
import ast, json, hashlib
V4 = r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820\docs\working\detector_validation_20260821\detector_validation_v4_domain.py"
src = open(V4, encoding="utf-8").read()
mod = ast.parse(src)
TOPICS = None
for node in mod.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if getattr(t, "id", None) == "TOPICS":
                TOPICS = ast.literal_eval(node.value)
assert TOPICS is not None and len(TOPICS) == 8
fx = {"domains": ["P", "C", "E", "O"], "topics": TOPICS}
b = json.dumps(fx, sort_keys=True, indent=1).encode("utf-8")
print("fixture_sha256 " + hashlib.sha256(b).hexdigest())
print("n_topics " + str(len(TOPICS)))
