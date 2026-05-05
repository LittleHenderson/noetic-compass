"""Helper run via pytest for capturing a sample /trace output for the
report. Not asserting anything load-bearing; the load-bearing tests are
in ``test_live_capture.py`` and ``test_sample_trace_output.py``.
"""

from __future__ import annotations

import io
import sys

import torch

from cas_native.inference import chat as chat_mod
from cas_native.inference.predict_cas import Predictor
from cas_native.model import (
    StructuredPredictionHead,
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.tokenizer.lexicon.schema import load_seed_lexicon
from cas_native.training.structured_token_adapter import (
    tokens_to_structured_token_batch,
)


def test_emit_sample_trace_for_report(capsys):
    sequences = [tokenize("I feel drawn to the idea of structure")]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    embedding = StructuredTokenEmbedding(
        vocab_size=len(vocab), d_model=128, dropout=0.0
    )
    head = StructuredPredictionHead(d_model=128, bottleneck_dim=64)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.eval()
    predictor = Predictor(
        model=model,
        vocabulary=vocab,
        lexicon=load_seed_lexicon(),
        device=torch.device("cpu"),
        max_length=32,
    )

    pred, trace = predictor(
        "I feel drawn to the idea of structure", with_trace=True
    )

    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        chat_mod._show_trace(trace, console=None, raw=False)
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = saved
    print("=== SAMPLE /trace OUTPUT ===")
    print(out)
    print("=== END SAMPLE ===")
