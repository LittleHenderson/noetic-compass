"""tier_c_cache_binding.py -- activation-cache binding law (G-C0-8).

Owner ruling section 5: caches must bind record CONTENT hashes, not passage
ids alone. Every activation cache carries a binding manifest with:
  canonical per-record SHA-256, passage id, dataset-manifest SHA-256,
  model SHA-256, tokenizer SHA-256, selected layer, extraction-code SHA-256,
  candidate-span digest.
The loader requires EXACT set equality between dataset records and cache
records plus per-record digest match. Any mismatch raises
CacheBindingViolation (fail closed) with the exact differences named.

This permanently blocks the PATH B P0 contamination class: a valid-looking
passage id can no longer retrieve another passage's neural state, and a
regenerated dataset can no longer silently reuse a stale cache.

Development-only, non-claim-bearing.
"""
from __future__ import annotations

import hashlib
import json

BINDING_VERSION = 1
REQUIRED_FIELDS = ("binding_version", "dataset_manifest_sha256",
                   "model_sha256", "tokenizer_sha256", "layer",
                   "extraction_code_sha256", "records")


class CacheBindingViolation(Exception):
    pass


def canonical_record_line(rec) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def record_sha(rec) -> str:
    return hashlib.sha256(canonical_record_line(rec).encode()).hexdigest()


def candidate_span_digest(rec) -> str:
    return hashlib.sha256(json.dumps(
        rec["candidates"], separators=(",", ":")).encode()).hexdigest()


def build_binding(records, dataset_manifest_sha256, model_sha256,
                  tokenizer_sha256, layer, extraction_code_sha256):
    return {"binding_version": BINDING_VERSION,
            "dataset_manifest_sha256": dataset_manifest_sha256,
            "model_sha256": model_sha256,
            "tokenizer_sha256": tokenizer_sha256,
            "layer": layer,
            "extraction_code_sha256": extraction_code_sha256,
            "records": {rec["passage_id"]:
                        {"record_sha256": record_sha(rec),
                         "candidate_span_digest": candidate_span_digest(rec)}
                        for rec in records}}


def verify_cache_binding(binding, cache_pids, records, *,
                         expected_manifest_sha=None, expected_layer=None,
                         expected_model_sha=None,
                         expected_tokenizer_sha=None,
                         expected_extraction_code_sha=None):
    """Fail-closed verification. Raises CacheBindingViolation naming every
    difference; returns a summary dict on success. Every bound header field
    is verifiable (C0 review fix: model/tokenizer/extraction shas were
    bound but previously unverifiable); duplicate pids in the cache or the
    dataset are violations in their own right (cardinality checks)."""
    errs = []
    for f in REQUIRED_FIELDS:
        if f not in binding:
            errs.append(f"missing binding field: {f}")
    if errs:
        raise CacheBindingViolation("; ".join(errs))
    for name, expected in (("dataset_manifest_sha256", expected_manifest_sha),
                           ("model_sha256", expected_model_sha),
                           ("tokenizer_sha256", expected_tokenizer_sha),
                           ("extraction_code_sha256",
                            expected_extraction_code_sha)):
        if expected is not None and binding[name] != expected:
            errs.append(f"{name} mismatch: cache bound to "
                        f"{str(binding[name])[:16]}..., expected "
                        f"{str(expected)[:16]}...")
    if expected_layer is not None and binding["layer"] != expected_layer:
        errs.append(f"layer mismatch: bound {binding['layer']}, "
                    f"requested {expected_layer}")
    cache_list = list(cache_pids)
    if len(cache_list) != len(set(cache_list)):
        errs.append(f"duplicate pids in cache: {len(cache_list)} rows, "
                    f"{len(set(cache_list))} unique")
    ds_pid_list = [r["passage_id"] for r in records]
    if len(ds_pid_list) != len(set(ds_pid_list)):
        errs.append(f"duplicate pids in dataset records: "
                    f"{len(ds_pid_list)} records, "
                    f"{len(set(ds_pid_list))} unique")
    if errs:
        raise CacheBindingViolation("CACHE_BINDING_VIOLATION: "
                                    + "; ".join(errs))
    rec_by_pid = {r["passage_id"]: r for r in records}
    ds_pids, b_pids = set(rec_by_pid), set(binding["records"])
    c_pids = set(cache_list)
    if ds_pids != b_pids:
        errs.append(f"binding/dataset pid sets differ: "
                    f"{len(b_pids - ds_pids)} only-in-binding, "
                    f"{len(ds_pids - b_pids)} only-in-dataset")
    if ds_pids != c_pids:
        errs.append(f"cache/dataset pid sets differ: "
                    f"{len(c_pids - ds_pids)} only-in-cache, "
                    f"{len(ds_pids - c_pids)} only-in-dataset")
    n_sha_bad = n_span_bad = 0
    for pid in (ds_pids & b_pids):
        b = binding["records"][pid]
        if b["record_sha256"] != record_sha(rec_by_pid[pid]):
            n_sha_bad += 1
        if b["candidate_span_digest"] != \
                candidate_span_digest(rec_by_pid[pid]):
            n_span_bad += 1
    if n_sha_bad:
        errs.append(f"{n_sha_bad} record content hashes differ (stale or "
                    "regenerated dataset)")
    if n_span_bad:
        errs.append(f"{n_span_bad} candidate-span digests differ")
    if errs:
        raise CacheBindingViolation("CACHE_BINDING_VIOLATION: "
                                    + "; ".join(errs))
    return {"verified_records": len(ds_pids), "pass": True}


def unit_tests():
    """G-C0-8: the pass case verifies; each violation class raises."""
    recs = [{"passage_id": f"p{i}", "candidates": ["a", "b"],
             "answer": "a", "x": i} for i in range(4)]
    b = build_binding(recs, "m" * 64, "mo" * 32, "tk" * 32, 6, "e" * 64)
    results = {}
    ok = verify_cache_binding(b, [r["passage_id"] for r in recs], recs,
                              expected_manifest_sha="m" * 64,
                              expected_layer=6,
                              expected_model_sha="mo" * 32,
                              expected_tokenizer_sha="tk" * 32,
                              expected_extraction_code_sha="e" * 64)
    results["clean_pass"] = ok["pass"]

    def expect_raise(name, fn):
        try:
            fn()
            results[name] = False
        except CacheBindingViolation as e:
            results[name] = True
            results[name + "_msg"] = str(e)[:120]
    expect_raise("missing_field", lambda: verify_cache_binding(
        {k: v for k, v in b.items() if k != "records"},
        [r["passage_id"] for r in recs], recs))
    expect_raise("pid_set_mismatch", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs[:-1]], recs))
    mutated = [dict(r, x=99) if r["passage_id"] == "p1" else r
               for r in recs]
    expect_raise("content_hash_mismatch", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], mutated))
    swapped = [dict(r, candidates=["b", "a"])
               if r["passage_id"] == "p2" else r for r in recs]
    expect_raise("candidate_span_mismatch", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], swapped))
    expect_raise("stale_manifest", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs,
        expected_manifest_sha="z" * 64))
    expect_raise("wrong_layer", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs, expected_layer=12))
    expect_raise("wrong_model_sha", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs,
        expected_model_sha="z" * 64))
    expect_raise("wrong_tokenizer_sha", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs,
        expected_tokenizer_sha="z" * 64))
    expect_raise("wrong_extraction_sha", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs,
        expected_extraction_code_sha="z" * 64))
    expect_raise("duplicate_cache_pid", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs] + ["p1"], recs))
    expect_raise("duplicate_dataset_pid", lambda: verify_cache_binding(
        b, [r["passage_id"] for r in recs], recs + [dict(recs[1], x=999)]))
    results["pass"] = all(v for k, v in results.items()
                          if not k.endswith("_msg"))
    return results
