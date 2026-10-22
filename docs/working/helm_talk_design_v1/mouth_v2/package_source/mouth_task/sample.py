"""mouth_task/sample.py -- the mouth's decoding: the writing lock on every step, then top-p sampling with one seeded
generator per row (A-TALK-4 W4). GPU only (torch). top_p = 0 means greedy.

The seed of a row is sha256(input text + "|" + situation + "|" + turn) mod 2^63, so a replay gives the same words and two
different turns may word the same fact differently. The lock (mouth_task.lock.MouthAutomaton) decides which tokens may
come next; the model only chooses among them.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence


def seed_of(input_text: str, situation: str, turn: str) -> int:
    return int(hashlib.sha256(f"{input_text}|{situation}|{turn}".encode("utf-8")).hexdigest(), 16) % (2 ** 63)


def sample_locked(model, srcs: List[List[int]], automata: List[object], tok_of_id: Sequence[str],
                  id_of_tok: Dict[str, int], device, seeds: List[int], top_p: float = 0.9,
                  max_len: int = 64) -> List[Dict[str, object]]:
    import torch
    from helm_cas_translator.model import pad_batch
    model.eval()
    gens = []
    for s in seeds:
        g = torch.Generator(device=device)
        g.manual_seed(int(s))
        gens.append(g)
    with torch.no_grad():
        src = pad_batch(srcs, device)
        mem, src_pad = model.encode(src)
        b = len(srcs)
        tgt = torch.full((b, 1), 1, dtype=torch.long, device=device)            # [BOS]
        done = [False] * b
        out: List[List[str]] = [[] for _ in range(b)]
        cache: Dict[frozenset, torch.Tensor] = {}
        for _ in range(max_len):
            logp = model.decode_logp(src, mem, src_pad, tgt)[:, -1, :]
            nxt = torch.zeros((b,), dtype=torch.long, device=device)
            for i in range(b):
                if done[i]:
                    continue
                allowed = automata[i].allowed()
                if not allowed:
                    done[i] = True
                    continue
                m = cache.get(allowed)
                if m is None:
                    m = torch.full((model.vocab_size,), float("-inf"), device=device)
                    m[torch.tensor([id_of_tok[t] for t in allowed], device=device)] = 0.0
                    cache[allowed] = m
                scores = logp[i] + m
                if top_p <= 0:
                    k = int(torch.argmax(scores).item())
                else:
                    probs = torch.softmax(scores, dim=-1)
                    sp, si = torch.sort(probs, descending=True)
                    keep = torch.cumsum(sp, dim=-1) - sp < top_p
                    sp = sp * keep
                    sp = sp / sp.sum()
                    k = int(si[torch.multinomial(sp, 1, generator=gens[i])].item())
                tok = tok_of_id[k]
                automata[i].step(tok)
                nxt[i] = k
                if tok == "[EOS]":
                    done[i] = True
                else:
                    out[i].append(tok)
            tgt = torch.cat([tgt, nxt.unsqueeze(1)], dim=1)
            del logp
            torch.cuda.empty_cache()   # each step's (B, T, V) blocks grow with T and are not reused: without this the
                                       # pool grew ~0.55 GB a step and ran out of memory at step 47 (laptop smoke 2026-10-22)
            if all(done):
                break
    return [{"tokens": out[i], "complete": bool(getattr(automata[i], "ended", False))} for i in range(b)]
