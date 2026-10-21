"""Read-only replay of U1b's frozen reader (merge_u1.py) on the sealed run folder. Writes ONLY into the scratchpad."""
import hashlib, json, sys, time
from pathlib import Path
D15 = Path(r"C:\Users\wakil\Documents\Codex\2026-10-15")
OUT = Path(sys.argv[1])
sys.path.insert(0, str(D15))
sys.dont_write_bytecode = True
t0 = time.time()
from u1b_unity_eye import merge_u1  # noqa: E402
res = merge_u1.merge()
data = json.dumps(res, indent=1, default=str, ensure_ascii=False)
OUT.write_text(data, "utf-8")
sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
sealed = D15 / "u1b_unity_eye" / "runs" / "MERGED_READING.json"
sealed_sha = hashlib.sha256(sealed.read_bytes()).hexdigest()
print(json.dumps({"verdict": res["test_verdict"], "words": res["status_words"],
                  "gates_failed": [g for g, v in res["hard_gates"].items() if v is not True],
                  "replay_sha256": sha, "sealed_sha256": sealed_sha, "byte_identical": sha == sealed_sha,
                  "seconds": round(time.time() - t0, 3)}, indent=1))
