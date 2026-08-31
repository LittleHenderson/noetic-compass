"""candidate_encoding.py -- the FROZEN shared candidate-encoding rule.

Owner audit 2026-08-31 section 7: the old rule (mean of contextual hidden states
at the candidate's FIRST occurrence) encoded 18.6% of train answers and 20.4% of
val answers from an unrelated distractor clause -- an avoidable architecture
interaction. REPLACED (amendment A5) by the owner-preferred rule:

    CONTEXT-FREE FROZEN INPUT-EMBEDDING ENCODING
    enc(e) = mean over the frozen model's input-embedding rows of e's tokens,
             where e is tokenized STANDALONE with no special tokens.

One rule, applied identically by every arm. No contextual occurrence is chosen,
so no occurrence ambiguity exists. The corpus occurrence audit is still recorded
(tools/audit_candidate_occurrence.py) as a dataset characteristic.
"""
from __future__ import annotations


def encode_candidates(candidates, tokenize_ids, embedding_rows):
    """Return one vector per candidate string.

    tokenize_ids: callable str -> list[int]   (no special tokens)
    embedding_rows: callable list[int] -> 2-D tensor (len(ids), d_model)
        -- the FROZEN input-embedding lookup (model.get_input_embeddings()).
    """
    import torch
    out = []
    for e in candidates:
        ids = tokenize_ids(e)
        if not ids:
            raise ValueError(f"CANDIDATE_ENCODING_FAILURE: {e!r} tokenizes to 0 ids")
        out.append(embedding_rows(ids).float().mean(dim=0))
    return torch.stack(out, dim=0)
