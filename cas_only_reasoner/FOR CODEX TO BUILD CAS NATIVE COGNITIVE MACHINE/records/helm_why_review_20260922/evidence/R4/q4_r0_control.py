"""R4: the repo's own R0 retrieval control (pure Python) on the same 16 dev inputs, fitted on the same
2048 visible train inputs; label = the train observation text, scored by parsing it (parser validated 16/16)."""
import sys, pathlib
sys.argv = sys.argv[:2]
src = open(pathlib.Path(__file__).with_name("q4_prior_analysis.py"), encoding="utf-8").read()
exec(src.split("# 2. training order")[0])
from learner_q4_representation import R0NearestNeighbor, encode_observation
r0 = R0NearestNeighbor((encode_observation(r["observation"]), r["observation"]) for r in train)
hits = 0; ties = []
for c in insp:
    got = r0.predict(encode_observation(c["input"]))
    hits += parse(got.label) == c["checker_reference_ast"]
    ties.append(len(got.tied_training_positions))
print("R0 retrieval control on dev16: exact %d/16 ; tie counts %s" % (hits, ties))
print("hand parser (no learning) on dev16: exact %d/16" % sum(parse(c["input"]) == c["checker_reference_ast"] for c in insp))
