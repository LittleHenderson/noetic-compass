"""Route B: a pretrained open-weight language cortex (Qwen2.5-0.5B-
Instruct, run OFFLINE from the local cache, greedy decoding).

The cortex only PROPOSES meaning packets; the same unchanged kernel
judges them (doctrine: the Transformer may parse and propose - it may
not commit). This is the FLOOR of the doctrine's 1-3B cortex band: a
0.5B model on CPU. Results are a floor for Route B, not its ceiling.

TEST-ONLY per the standing rule: no foreign model enters production;
this module exists solely for the owner-ordered head-to-head.
"""

from __future__ import annotations

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

from .tasks import FEWSHOT_BREADTH, FEWSHOT_FRAGMENT, KNOWN_WORDS  # noqa: E402

FRAGMENT_SYSTEM = (
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

BREADTH_SYSTEM = (
    "You translate English sentences into flat JSON slot packets. "
    "Output ONLY one JSON object, nothing else. Use keys such as "
    "event, agent, object, recipient, object_property, relation, "
    "figure, ground, tense. Use base verb forms (gave -> give) and "
    "tense in {past, present, future}."
)


def _extract_json(text: str) -> Optional[Dict]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


class RouteB:
    name = "route_b_pretrained_cortex"
    description = ("Qwen/Qwen2.5-0.5B-Instruct (local cache, offline, "
                   "CPU, greedy) proposing packets; same kernel judges")

    def __init__(self, max_new_tokens: int = 96) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(SNAPSHOT)
        self.model = AutoModelForCausalLM.from_pretrained(
            SNAPSHOT, dtype=torch.float32)
        self.model.eval()
        self.max_new_tokens = max_new_tokens
        self.generation_seconds: List[float] = []

    # ------------------------------------------------------------------
    def _chat(self, system: str, examples: List[Dict],
              sentence: str) -> str:
        messages = [{"role": "system", "content": system}]
        for example in examples:
            messages.append({"role": "user",
                             "content": f'Sentence: "{example["sentence"]}"'})
            messages.append({"role": "assistant",
                             "content": json.dumps(example["packet"])})
        messages.append({"role": "user",
                         "content": f'Sentence: "{sentence}"'})
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt")
        start = time.time()
        with self.torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id)
        self.generation_seconds.append(time.time() - start)
        return self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True).strip()

    # ------------------------------------------------------------------
    def parse(self, sentence: str) -> Dict:
        """Fragment-schema packet proposal: {"ok"| "refused"| "invalid"}."""
        reply = self._chat(FRAGMENT_SYSTEM, FEWSHOT_FRAGMENT, sentence)
        packet = _extract_json(reply)
        if packet is None:
            return {"invalid": {"error": "invalid_json", "raw": reply[:200]}}
        if "error" in packet:
            return {"refused": packet}
        return {"ok": packet}

    def parse_breadth(self, sentence: str) -> Dict:
        reply = self._chat(BREADTH_SYSTEM, FEWSHOT_BREADTH, sentence)
        packet = _extract_json(reply)
        if packet is None:
            return {"invalid": {"error": "invalid_json", "raw": reply[:200]}}
        if "error" in packet:
            return {"refused": packet}
        return {"ok": packet}
