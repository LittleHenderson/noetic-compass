"""activation_extraction.py -- frozen-model hidden-state extraction + cache I/O.

Gate 1B jobs only: require_gpu() is the first statement of the extraction entry.
Activations are extracted ONCE per split at the candidate layers (train/val in
step 4; protected only inside step 7's single pass), cached fp16, digest-pinned,
and reused by every arm and seed (cache-once law).

The model identity is verified BEFORE extraction: the resolved HuggingFace
revision SHA and weight-file digests must equal the owner-signed approval's
values, else MODEL_IDENTITY_MISMATCH and abort.
"""
from __future__ import annotations

import hashlib

try:
    from exec.gpu_guard import require_gpu
    from exec.spans import build_input_text, clause_char_spans, token_spans
except ImportError:
    from gpu_guard import require_gpu
    from spans import build_input_text, clause_char_spans, token_spans

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"


def write_cache(path, obj) -> str:
    """torch.save the cache object; return the file's sha256 (receipt-pinned)."""
    import torch
    torch.save(obj, path)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def read_cache(path, expected_sha256: str = None):
    import torch
    if expected_sha256 is not None:
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if got != expected_sha256:
            raise RuntimeError(f"CACHE_INTEGRITY_FAILURE: {path} sha {got} != "
                               f"pinned {expected_sha256}")
    return torch.load(path, map_location="cpu", weights_only=True)


def extract_split(records, tokenizer, model, layers, batch_size: int = 16):
    """{passage_id: {"layers": {L: (h_ideas (N,896) fp16, g (896,) fp16)}}}
    -- mean-pooled per-Idea and question hidden states at each candidate layer.
    Caller has already verified model identity against the signed approval."""
    device = require_gpu()                              # FIRST -- fail closed
    import torch
    model = model.to(device).eval()
    out = {}
    with torch.no_grad():
        for rec in records:
            text = build_input_text(rec)
            enc = tokenizer(text, return_offsets_mapping=True, return_tensors="pt")
            spans, qspan = clause_char_spans(rec)
            idea_toks, q_toks = token_spans(spans, qspan,
                                            enc["offset_mapping"][0].tolist())
            hs = model(input_ids=enc["input_ids"].to(device),
                       attention_mask=enc["attention_mask"].to(device),
                       output_hidden_states=True).hidden_states
            per_layer = {}
            for L in layers:                            # 1-indexed block OUTPUT
                h_all = hs[L][0].float()
                h_ideas = torch.stack(
                    [h_all[t].mean(dim=0) for t in
                     [torch.tensor(ix) for ix in idea_toks]]).half()
                g = h_all[torch.tensor(q_toks)].mean(dim=0).half()
                per_layer[L] = (h_ideas.cpu(), g.cpu())
            out[rec["passage_id"]] = {"layers": per_layer}
    return out
