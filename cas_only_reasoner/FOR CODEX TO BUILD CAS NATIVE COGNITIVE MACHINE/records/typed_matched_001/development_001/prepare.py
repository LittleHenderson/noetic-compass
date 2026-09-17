"""Bounded public-only development preparation with import sentinels."""
from hashlib import sha256
import builtins
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "research/CAS_META_2_COMPOSITION")]
attempts = []
original = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer", "requests", "httpx"} or name.endswith((".checker", ".loss_plan", ".final_panel", ".face_tasks", ".face_corpus", ".reference", ".development_data")):
        attempts.append(name)
        raise AssertionError("PUBLIC_DEVELOPMENT_PROHIBITED_IMPORT:" + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guard
started = time.perf_counter()
try:
    from cas_meta2.typed_teaching import development
    before = development.profile()
    doc = development.build_development(root=ROOT)
    raw = (json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)+"\n").encode()
    with (OUT / "public_development.json").open("xb") as stream: stream.write(raw)
    receipt = {"status":"PUBLIC_DEVELOPMENT_PREPARATION_PASS", "counts":doc["counts"],"max_token_count":doc["max_token_count"],
        "artifact":{"path":"public_development.json","bytes":len(raw),"sha256":sha256(raw).hexdigest()},
        "profile_before_after_equal":development.profile()==before,"profile":before,
        "prohibited_import_attempts":attempts,"seconds":time.perf_counter()-started,
        "boundary":"Public development preparation only; no answers, model, provider or final questions."}
    assert receipt["profile_before_after_equal"] and not attempts
    with (OUT / "preparation_receipt.json").open("x",encoding="utf-8") as stream: json.dump(receipt,stream,sort_keys=True,indent=2)
    print(json.dumps({k:v for k,v in receipt.items() if k!='profile'},sort_keys=True))
except Exception as exc:
    failure={"status":"PUBLIC_DEVELOPMENT_PREPARATION_FAILED","type":type(exc).__name__,"detail":str(exc),"seconds":time.perf_counter()-started,"prohibited_import_attempts":attempts}
    with (OUT / "failure_001.json").open("x",encoding="utf-8") as stream: json.dump(failure,stream,sort_keys=True,indent=2)
    raise
finally:
    builtins.__import__ = original
