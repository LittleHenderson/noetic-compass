"""activation_extraction.py -- frozen-model hidden-state extraction + cache I/O.

Gate 1B jobs only. Activations are extracted ONCE per split for ALL candidate
layers in a SINGLE forward pass per passage (not one pass per layer), cached
fp16, digest-pinned, and reused by every arm and seed (cache-once law). The
context-free CANDIDATE encodings are produced in the same pass from the frozen
INPUT embeddings (layer-independent), so no passage ever reaches training,
validation, or protected scoring with cand=None.

require_gpu() is enforced at the DRIVER entry (exec/campaign_driver
_load_frozen_model); extract_split itself takes an explicit `device` so the
REAL extraction logic is exercisable with fake tokenizers/embeddings on CPU in
the REAL-branch conformance tests without a model, GPU, or AWS -- while the real
campaign still fails closed on a CUDA-less box at the driver.

Model identity is verified BEFORE extraction (exec/identity.verify_model_identity)
against the signed approval; a model file outside the signed allow-list aborts.
"""
from __future__ import annotations

import hashlib

try:
    from exec.spans import build_input_text, clause_char_spans, token_spans
    from exec.candidate_encoding import encode_candidates
except ImportError:
    from spans import build_input_text, clause_char_spans, token_spans
    from candidate_encoding import encode_candidates

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


def extract_split(records, tokenizer, model, layers, device="cpu"):
    """{passage_id: {"layers": {L: (h_ideas (N,896) fp16, g (896,) fp16)},
                     "cand": (C, 896) fp16}}

    ONE forward pass per passage yields every candidate layer's per-Idea and
    question hidden states; `cand` is the context-free frozen-input-embedding
    encoding of the passage's closed candidate set (layer-independent). Caller
    has already verified model identity and (for the real path) the GPU."""
    import torch
    model = model.to(device).eval()
    embed = model.get_input_embeddings()

    def tokenize_ids(text):                             # standalone, no specials
        return tokenizer(text, add_special_tokens=False)["input_ids"]

    def embedding_rows(ids):
        return embed(torch.tensor(ids, device=device)).detach()

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
                    [h_all[torch.tensor(ix, device=h_all.device)].mean(dim=0)
                     for ix in idea_toks]).half()
                g = h_all[torch.tensor(q_toks, device=h_all.device)].mean(dim=0).half()
                per_layer[L] = (h_ideas.cpu(), g.cpu())
            cand = encode_candidates(rec["candidates"], tokenize_ids,
                                     embedding_rows).half().cpu()
            out[rec["passage_id"]] = {"layers": per_layer, "cand": cand}
    return out
