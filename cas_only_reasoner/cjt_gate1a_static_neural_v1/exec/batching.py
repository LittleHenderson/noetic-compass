"""batching.py -- the FROZEN batch-32 seeded sampler (GATE 1A.2R section 5).

The run schedule freezes batch_size=32, exactly 3000 updates, and a seed that
governs DATA ORDER as well as parameter init. This builds batch-32 tensor
batches over the FULL training corpus with a deterministic seeded permutation,
padded to MAX_IDEAS Ideas and the batch's max candidate count. run_training
consumes the batches, cycling through the corpus for exactly UPDATES steps.

Pure tensor assembly over cached activations; no model, GPU, or AWS -- so the
REAL batching contract is exercisable with fake features in the REAL-branch
conformance tests. The audited defect (one batch per record, batch dim 1, only
the first 3000 records, no shuffle) is closed here.
"""
from __future__ import annotations

try:
    from exec.arms import MAX_IDEAS
    from exec.dataset_assembly import assemble_examples
except ImportError:
    from arms import MAX_IDEAS
    from dataset_assembly import assemble_examples

BATCH_SIZE = 32


def seeded_permutation(n: int, seed: int):
    """Deterministic index permutation from the seed (Fisher-Yates on a
    torch.Generator; replay-identical for a given seed on a given torch build)."""
    import torch
    g = torch.Generator().manual_seed(seed)
    return torch.randperm(n, generator=g).tolist()


def build_batches(records, arm, features, verb_to_class, seed: int,
                  batch_size: int = BATCH_SIZE):
    """Full-corpus, seeded, batch-`batch_size` batches for run_training.
    Every example carries a REAL candidate tensor (features[pid]["cand"])."""
    import torch
    exs = assemble_examples(records, arm, verb_to_class=verb_to_class)
    order = seeded_permutation(len(exs), seed)
    ordered = [exs[i] for i in order]
    batches = []
    for start in range(0, len(ordered), batch_size):
        chunk = ordered[start:start + batch_size]
        b = len(chunk)
        max_c = max(features[ex["passage_id"]]["cand"].shape[0] for ex in chunk)
        h = torch.zeros(b, MAX_IDEAS, 896)
        g = torch.zeros(b, 896)
        idea_mask = torch.zeros(b, MAX_IDEAS, dtype=torch.bool)
        cand_enc = torch.zeros(b, max_c, 896)
        cand_mask = torch.zeros(b, max_c, dtype=torch.bool)
        answer_index = torch.zeros(b, dtype=torch.long)
        has_profiles = chunk[0]["profiles"] is not None
        p = torch.zeros(b, MAX_IDEAS, 4) if has_profiles else None
        for j, ex in enumerate(chunk):
            f = features[ex["passage_id"]]
            n, c = f["h"].shape[0], f["cand"].shape[0]
            h[j, :n] = f["h"].float()
            g[j] = f["g"].float()
            idea_mask[j, :n] = True
            cand_enc[j, :c] = f["cand"].float()
            cand_mask[j, :c] = True
            answer_index[j] = ex["answer_index"]
            if p is not None:
                p[j, :n] = torch.tensor(ex["profiles"], dtype=torch.float32)
        batches.append({"split": "train", "h": h, "g": g, "p": p,
                        "idea_mask": idea_mask, "cand_enc": cand_enc,
                        "cand_mask": cand_mask, "answer_index": answer_index})
    return batches
