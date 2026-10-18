"""scribe_model.py -- CAS-Native Neural Proposer Architecture for Level L4 Scribe.

Architecture:
- CASNativeScribeTransformer: Lightweight Multi-Head Attention Sequence Encoder + Multi-Task Slot Classifier.
- Trained completely from scratch with seeded weights (ZERO foreign pretrained weights, per Rule in LADDER.md).
- Emits structured CASContent candidate dictionary for CCE round-trip verification:
    parse(render(C)) == C
"""
from __future__ import annotations

import math
from typing import Dict, List, Any, Tuple, Optional

# Slot class definitions
DOMAINS_LIST = ["P", "C", "E", "O"]
REGISTERS_LIST = ["T", "A", "f", "E"]
DRIVES_LIST = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]
VERBS_LIST = ["intakes", "processes", "stores", "outputs"]
SUBJECTS_LIST = ["Mind", "Positive", "Negative", "Male", "Female"]
OBJECTS_LIST = ["Idea", "Vibration", "Rhythm", "Above/Cause", "Below/Effect"]
TURN_TYPES = ["ANSWER", "CLARIFY"]

# Simple deterministic word vocabulary builder
SPECIAL_TOKENS = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]


class SimpleTokenizer:
    def __init__(self, vocab_list: Optional[List[str]] = None):
        self.vocab = {tok: idx for idx, tok in enumerate(SPECIAL_TOKENS)}
        self.inv_vocab = {idx: tok for tok, idx in self.vocab.items()}
        if vocab_list:
            for w in vocab_list:
                self.add_word(w)

    def add_word(self, word: str) -> int:
        w = word.lower().strip(".,:;!?()[]{}'\"")
        if not w:
            return 0
        if w not in self.vocab:
            idx = len(self.vocab)
            self.vocab[w] = idx
            self.inv_vocab[idx] = w
        return self.vocab[w]

    def encode(self, text: str, max_len: int = 32) -> List[int]:
        tokens = text.lower().replace("-", " ").replace("/", " ").split()
        ids = [self.vocab.get("<BOS>", 2)]
        for t in tokens:
            cleaned = t.strip(".,:;!?()[]{}'\"")
            if cleaned in self.vocab:
                ids.append(self.vocab[cleaned])
            else:
                ids.append(self.vocab.get("<UNK>", 1))
        ids.append(self.vocab.get("<EOS>", 3))
        # Pad or truncate
        if len(ids) < max_len:
            ids += [self.vocab.get("<PAD>", 0)] * (max_len - len(ids))
        else:
            ids = ids[:max_len]
        return ids

    def build_from_corpus(self, sentences: List[str]):
        for s in sentences:
            tokens = s.lower().replace("-", " ").replace("/", " ").split()
            for t in tokens:
                self.add_word(t)


# Model Hyperparameters
D_MODEL = 64
N_HEADS = 4
N_LAYERS = 2
D_FF = 128
MAX_SEQ_LEN = 32


def create_pytorch_model(vocab_size: int):
    """Factory for the PyTorch CUDA model when running on AWS GPU."""
    import torch
    import torch.nn as nn

    class PyTorchScribeTransformer(nn.Module):
        def __init__(self, vocab_sz: int, d_model: int = D_MODEL, nhead: int = N_HEADS, num_layers: int = N_LAYERS):
            super().__init__()
            self.embedding = nn.Embedding(vocab_sz, d_model, padding_idx=0)
            self.pos_encoder = nn.Parameter(torch.randn(1, MAX_SEQ_LEN, d_model) * 0.02)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=nhead, dim_feedforward=D_FF, dropout=0.1, batch_first=True
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

            # Multi-task classification heads
            self.head_turn_type = nn.Linear(d_model, len(TURN_TYPES))
            self.head_domain = nn.Linear(d_model, len(DOMAINS_LIST))
            self.head_register = nn.Linear(d_model, len(REGISTERS_LIST))
            self.head_drive = nn.Linear(d_model, len(DRIVES_LIST))
            self.head_verb = nn.Linear(d_model, len(VERBS_LIST))
            self.head_subject = nn.Linear(d_model, len(SUBJECTS_LIST))
            self.head_object = nn.Linear(d_model, len(OBJECTS_LIST))

        def forward(self, x):
            # x: [batch_size, seq_len]
            b, s = x.size()
            embed = self.embedding(x) + self.pos_encoder[:, :s, :]
            mask = (x == 0)  # padding mask
            feat = self.transformer(embed, src_key_padding_mask=mask)
            # Pool representation (mean pooling over non-padded tokens)
            mask_expanded = mask.unsqueeze(-1).expand_as(feat)
            feat_masked = feat.masked_fill(mask_expanded, 0.0)
            sum_feat = feat_masked.sum(dim=1)
            lens = torch.clamp((~mask).sum(dim=1, keepdim=True), min=1)
            pooled = sum_feat / lens

            return {
                "turn_type": self.head_turn_type(pooled),
                "domain": self.head_domain(pooled),
                "register": self.head_register(pooled),
                "drive": self.head_drive(pooled),
                "verb": self.head_verb(pooled),
                "subject": self.head_subject(pooled),
                "object": self.head_object(pooled)
            }

    return PyTorchScribeTransformer(vocab_size)
