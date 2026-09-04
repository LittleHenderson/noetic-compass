"""Run one real CASformer language-model forward pass without training."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from casformer import (  # noqa: E402
    CASControl,
    CASformerConfig,
    CASformerLanguageModel,
    make_trace,
)


def main() -> None:
    torch.manual_seed(20260903)
    config = CASformerConfig(
        d_model=16,
        num_heads=4,
        num_relations=4,
        num_layers=2,
        d_ff=32,
    )
    model = CASformerLanguageModel(
        config, vocab_size=32, max_sequence_length=8
    ).eval()
    tokens = torch.tensor([[1, 7, 3, 9, 2]], dtype=torch.long)
    template = torch.zeros(1, tokens.shape[1], config.d_model)
    control = CASControl.uniform(
        template,
        num_heads=config.num_heads,
        causal=True,
        profile_id="minimal-forward-untrained",
        provenance="examples/minimal_forward.py",
        control_tick=1,
        feedback_source_tick=0,
    )
    with torch.no_grad():
        logits, telemetry = model(tokens, control)
    trace = make_trace(
        telemetry[0], control, layer_index=0, include_tensors=False
    )
    print(
        json.dumps(
            {
                "status": "FORWARD_PASS_ONLY",
                "trained": False,
                "logits_shape": list(logits.shape),
                "trace_detail": "SUMMARY_ONLY",
                "trace": trace.to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
