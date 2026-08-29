"""Phase 4.1: the cortex adapter.

Loads the open-weight model DIRECTLY from its immutable local
snapshot (the refs/main repair), computes a full MODEL IDENTITY
RECEIPT (weight/tokenizer/config digests + library versions + dtype +
generation parameters), generates deterministically (greedy), and
emits ONLY CortexProposal records - raw output always preserved.

TEST-GATED lane: the model is a proposal generator under the frozen
authority contract; nothing here can commit, write, or act.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Dict, List, Optional

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
    "snapshots/7ae557604adf67be50417f59c2c2f167def9a775")

KNOWN_WORDS = ("the", "is", "not", "it", "cat", "dog", "gray", "brown",
               "quiet", "chases")

SYSTEM_PROMPT = (
    "You translate English sentences into JSON meaning packets. "
    "Output ONLY one JSON object, nothing else.\n"
    "Schemas:\n"
    '  statement: {"pred": "property", "args": ["<entity>", "<property>"]}\n'
    '  negation: {"pred": "negation", "args": [<inner packet>]}\n'
    '  relation: {"pred": "relation", "args": ["<verb-sense>", "<subject>", "<object>"]}\n'
    '  question: {"pred": "question", "args": [<inner packet>]}\n'
    "The verb sense of 'chases' is 'chase'.\n"
    "The ONLY known words are: " + ", ".join(KNOWN_WORDS) + ". "
    "If the sentence contains any other content word, output exactly "
    '{"error": "unknown word", "word": "<that word>"} and nothing else.'
)

FEWSHOT = (
    ("the sky is blue.",
     '{"pred": "property", "args": ["sky", "blue"]}'),
    ("the bird is not small.",
     '{"pred": "negation", "args": [{"pred": "property", '
     '"args": ["bird", "small"]}]}'),
    ("the fox chases the hen.",
     '{"pred": "relation", "args": ["chase", "fox", "hen"]}'),
    ("is the sun hot?",
     '{"pred": "question", "args": [{"pred": "property", '
     '"args": ["sun", "hot"]}]}'),
    ("the wug is tall.",
     '{"error": "unknown word", "word": "wug"}'),
)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def snapshot_receipt(snapshot: str = SNAPSHOT) -> Dict:
    """The immutable identity of the model - evidence binds to these
    digests, never to a cache path."""
    files = {}
    for name in ("config.json", "generation_config.json",
                 "tokenizer.json", "tokenizer_config.json",
                 "vocab.json", "merges.txt", "model.safetensors"):
        path = os.path.join(snapshot, name)
        if os.path.exists(path):
            files[name] = _sha256_file(path)
    import torch
    import transformers
    return {
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_revision": os.path.basename(snapshot),
        "file_digests": files,
        "tokenizer_digest": files.get("tokenizer.json", "absent"),
        "weights_digest": files.get("model.safetensors", "absent"),
        "runtime_digest": hashlib.sha256(json.dumps({
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "dtype": "float32", "device": "cpu",
            "generation": {"do_sample": False, "max_new_tokens": 96},
        }, sort_keys=True).encode()).hexdigest()[:16],
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "dtype": "float32",
        "device": "cpu",
        "generation_parameters": {"do_sample": False,
                                  "max_new_tokens": 96},
    }


def _extract_json(text: str) -> Optional[Dict]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


class CortexAdapter:
    """Resident model (loaded once, reused across turns), greedy
    generation, CortexProposal-only output."""

    def __init__(self, snapshot: str = SNAPSHOT) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.receipt = snapshot_receipt(snapshot)
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot)
        self.model = AutoModelForCausalLM.from_pretrained(
            snapshot, dtype=torch.float32)
        self.model.eval()
        self.latencies: List[float] = []

    def propose(self, sentence: str) -> Dict:
        """English in -> CortexProposal out. Never a committed answer."""
        from .proposal import make_proposal

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for example_in, example_out in FEWSHOT:
            messages.append({"role": "user",
                             "content": f'Sentence: "{example_in}"'})
            messages.append({"role": "assistant", "content": example_out})
        messages.append({"role": "user",
                         "content": f'Sentence: "{sentence}"'})
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt")
        start = time.time()
        with self.torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=96, do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id)
        self.latencies.append(round(time.time() - start, 2))
        raw = self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True).strip()

        packet = _extract_json(raw)
        unknown_tokens: List[str] = []
        candidate = None
        if packet is not None and "error" in packet:
            word = packet.get("word")
            if word:
                unknown_tokens.append(str(word))
        elif packet is not None:
            candidate = packet

        return make_proposal(
            model_receipt=self.receipt,
            raw_input=sentence,
            raw_model_output=raw,
            candidate_semantic_packet=candidate,
            unknown_tokens=unknown_tokens,
            claimed_confidence=None,   # the model supplies none honestly
            generation_mode="greedy",
            seed=0)
