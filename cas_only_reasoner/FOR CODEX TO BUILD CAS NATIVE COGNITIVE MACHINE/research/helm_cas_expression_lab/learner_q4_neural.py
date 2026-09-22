"""R1 bottleneck GRU encoder/decoder CODE; neural execution is a separate gate.

No torch import at module import. build_model explicitly requires CUDA; it
never falls back to CPU. The caller must establish resource authorization.
No model from this module was initialized, run, or trained during its code-only
implementation tests. No checkpoint or learned reconstruction result exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from learner_q4_decoder import BOS_ID, TOKENS, DecodeLimits, free_decode
from learner_q4_representation import Bottleneck, SequenceInput


@dataclass(frozen=True, slots=True)
class NeuralConfig:
    width: int = 64

    def __post_init__(self):
        if type(self.width) is not int or self.width not in (64, 128):
            raise ValueError("INVALID_INPUT: engineering widths are 64 or 128")


def build_model(config: NeuralConfig = NeuralConfig(), *, device: str):
    """Construct R1 only after the caller's resource gate; never called by tests.

All trainable tensors are created directly on CUDA. A weight checkpoint must
be bound to config + the input/output codec versions by the future run harness.
"""
    if type(device) is not str or re.fullmatch(r"cuda:[0-9]+", device) is None:
        raise RuntimeError("GPU_REQUIRED: explicit cuda:N device required")
    if type(config) is not NeuralConfig:
        raise ValueError("INVALID_INPUT: NeuralConfig required")
    import torch
    from torch import nn

    if not torch.cuda.is_available() or int(device.split(":")[1]) >= torch.cuda.device_count():
        raise RuntimeError("GPU_REQUIRED: selected CUDA device unavailable")
    selected = torch.device(device)

    class StrictR1(nn.Module):
        def __init__(self):
            super().__init__()
            self.config = config
            self.input_embedding = nn.Embedding(257, config.width, padding_idx=0, device=selected, dtype=torch.float32)
            self.encoder = nn.GRU(config.width, config.width, batch_first=True, device=selected, dtype=torch.float32)
            self.output_embedding = nn.Embedding(len(TOKENS) + 1, config.width, device=selected, dtype=torch.float32)
            self.decoder = nn.GRU(config.width, config.width, batch_first=True, device=selected, dtype=torch.float32)
            self.output_head = nn.Linear(config.width, len(TOKENS), device=selected, dtype=torch.float32)

        def _device(self):
            actual = self.input_embedding.weight.device
            if actual.type != "cuda":
                raise RuntimeError("GPU_REQUIRED: neural execution cannot run on CPU")
            if any(parameter.device != actual for parameter in self.parameters()):
                raise RuntimeError("GPU_REQUIRED: all model parameters must share one CUDA device")
            return actual

        def _encode_tensor(self, observation: SequenceInput):
            if type(observation) is not SequenceInput:
                raise ValueError("INVALID_INPUT: SequenceInput required")
            tensor = torch.tensor([observation.byte_ids], dtype=torch.long, device=self._device())
            _, hidden = self.encoder(self.input_embedding(tensor))
            return hidden

        def _prefix_tensor(self, prefix: tuple[int, ...]):
            if (type(prefix) is not tuple or len(prefix) >= DecodeLimits().max_tokens
                    or any(type(token) is not int or not 0 <= token < len(TOKENS) for token in prefix)):
                raise ValueError("INVALID_INPUT: bounded generated/supervised history required")
            return torch.tensor([(BOS_ID,) + prefix], dtype=torch.long, device=self._device())

        def encode(self, observation: SequenceInput) -> Bottleneck:
            self.eval()
            with torch.no_grad():
                vector = self._encode_tensor(observation)[0, 0]
                # CPU transfer is serialization of a completed result, not inference.
                return Bottleneck(tuple(float(x) for x in vector.detach().cpu().tolist()))

        def next_logits(self, bottleneck: Bottleneck, generated: tuple[int, ...]) -> tuple[float, ...]:
            """Strict decoder: never receives the source, AST, or gold history."""
            if type(bottleneck) is not Bottleneck or len(bottleneck.values) != config.width:
                raise ValueError("INVALID_INPUT: wrong bottleneck width/type")
            self.eval()
            with torch.no_grad():
                hidden = torch.tensor([[bottleneck.values]], dtype=self.input_embedding.weight.dtype,
                                      device=self._device())
                values, _ = self.decoder(self.output_embedding(self._prefix_tensor(generated)), hidden)
                logits = self.output_head(values[0, -1])
                return tuple(float(x) for x in logits.detach().cpu().tolist())

        def generate(self, observation: SequenceInput, limits: DecodeLimits = DecodeLimits()):
            return free_decode(self.encode(observation), self.next_logits, limits)

        def teacher_forced_logits(self, observation: SequenceInput, training_prefix: tuple[int, ...]):
            """TRAINING ONLY: supervised prefix, for external loss calculation.

For targets t0..tn (including EOS), call with targets[:-1]. Returned positions
predict t0..tn. This method is never called by generate/next_logits.
"""
            self.train()
            hidden = self._encode_tensor(observation)
            values, _ = self.decoder(self.output_embedding(self._prefix_tensor(training_prefix)), hidden)
            return self.output_head(values[0])

    return StrictR1()
