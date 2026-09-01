"""pathb_a0_probe.py -- PATH-B-A0: Frozen Representation and Hop Sufficiency
Probe (owner ruling). DEVELOPMENT-ONLY, NON-CLAIM-BEARING, diagnostic-routing
only. Decides whether the frozen Qwen representations carry enough information
to support multihop binding BEFORE any graph executor is built.

QB-ORD is DROPPED (frozen PRB-POS gate; QB_ORD_REJECTED_POSITION_SHORTCUT).
Retained families: QB_REL, QB_COMP, QB_INT.

Gold path (diagnostic ONLY, from the frozen solver's edge trace + formal ops;
never enters ordinary training or primary evaluation elsewhere):
    REL : selector ^3(m1,x)      -> bridge m1  -> final ^2   -> answer idea
    COMP: selector ^2(x,m1)      -> bridge m1  -> final ^8   -> answer idea
    INT : selector ^2(i2,m1)     -> bridge i2  -> finals ^6x2-> answer part

Probes (per cached layer 6/12/18/24, per family; tiny GPU decoders):
    A  bridge recovery:      D1(g, h_sel, E_sel)            -> bridge entity
    B  second-hop binding:   D2(g, h_fin, e_bridge, E_fin)  -> final answer
    C  full gold-path:       stage1(A-style) soft bridge -> stage2(B-style);
                             NO gold bridge supplied; trained end-to-end
    D  destructive controls on the trained C:
         shuffled clause path | swapped hop order |
         rewired candidate-clause membership | wrong bridge pointer (on B)

Pass law (owner): A/B/C train acc >= 0.95 (128 balanced examples);
C holdout clearly above candidate-uniform (registered: >= uniform + 0.10);
shuffled-path drop >= 0.30; rewired-membership drop >= 0.30.
Earliest passing layer -> GRAPH_EXECUTOR_EARNED (freeze it).
No layer passes -> FROZEN_REPRESENTATION_INSUFFICIENT_FOR_PATH_B.

Compute: ONE GPU, hard sub-cap $0.25; only ~280 records re-extracted (the P0
instance's caches died with it -- 'genuinely unavailable' per the ruling).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

from exec.activation_extraction import MODEL_ID, extract_split  # noqa: E402
from exec.spans import build_input_text, clause_char_spans  # noqa: E402

FAMS = ("QB_REL", "QB_COMP", "QB_INT")
LAYERS = (6, 12, 18, 24)
N_TRAIN_PER_FAM = 43                      # 129 total ~ "128 balanced"
N_HOLD_PER_FAM = 50
EPOCHS = 500
LR = 3e-3
D = 896
H = 256


def load_train():
    p = HERE / "data" / "train.jsonl"
    return [json.loads(l) for l in p.read_text("utf-8").splitlines() if l]


def gold_path(rec):
    """(sel_idx, bridge_entity, final_idxs) from the formal record."""
    tr = rec["edge_trace"]
    ops = rec["ops"]
    sel = tr[0]
    c, a = ops[sel][0], ops[sel][1]
    if rec["question_type"] == "QB_REL":
        bridge = a[0]                       # ^3 (m1, x) -> m1
        finals = [tr[1]]
    elif rec["question_type"] == "QB_COMP":
        bridge = a[1]                       # ^2 (x, m1) -> m1
        finals = [tr[1]]
    else:                                   # QB_INT: ^2 (i2, m1) -> i2
        bridge = a[0]
        finals = [tr[1], tr[2]]
    return sel, bridge, finals


def extract_clause_local(records, tok, model, device, layers):
    import torch
    out = {}
    with torch.no_grad():
        for rec in records:
            text = build_input_text(rec)
            enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
            offs = enc["offset_mapping"][0].tolist()
            hs = model(input_ids=enc["input_ids"].to(device),
                       attention_mask=enc["attention_mask"].to(device),
                       output_hidden_states=True).hidden_states
            spans, _ = clause_char_spans(rec)
            low = text.lower()
            occ = {}
            for j, cand in enumerate(rec["candidates"]):
                for m in re.finditer(rf"\b{re.escape(cand.lower())}\b", low):
                    for i, (cs, ce) in enumerate(spans):
                        if m.start() >= cs and m.end() <= ce:
                            occ.setdefault((i, j), []).extend(
                                [ti for ti, (a, b) in enumerate(offs)
                                 if b > a and a < m.end() and b > m.start()])
            per = {}
            for L in layers:
                h_all = hs[L][0].float()
                per[L] = {k: h_all[torch.tensor(sorted(set(t)))].mean(0)
                          .half().cpu() for k, t in occ.items()}
            out[rec["passage_id"]] = per
    return out


def build_tensors(recs, acts, loc, L, device, rewire_seed=None,
                  path_mode="gold"):
    """Per-record probe tensors at layer L. path_mode: gold | shuffled |
    swapped. rewire_seed: permute candidate-clause membership per record."""
    import torch
    items = []
    g_rw = torch.Generator().manual_seed(rewire_seed or 0)
    for rec in recs:
        pid = rec["passage_id"]
        n = len(rec["clauses"])
        C = len(rec["candidates"])
        sel, bridge, finals = gold_path(rec)
        if path_mode == "shuffled":
            perm = torch.randperm(n, generator=torch.Generator()
                                  .manual_seed(hash(pid) % (2**31))).tolist()
            sel = perm[sel]
            finals = [perm[f] for f in finals]
        elif path_mode == "swapped":
            sel, finals = finals[0], [sel]
        hg = acts[pid]["layers"][L]
        h = hg[0].float()                                  # (n, 896)
        g = hg[1].float()                                  # (896,)
        e = torch.zeros(n, C, D)
        m = torch.zeros(n, C, dtype=torch.bool)
        for (i, j), v in loc[pid][L].items():
            e[i, j] = v.float()
            m[i, j] = True
        if rewire_seed is not None:
            perm = torch.randperm(n, generator=g_rw)
            e = e[perm]
            m = m[perm]
        items.append({
            "qt": rec["question_type"], "n": n, "C": C,
            "g": g, "h": h, "e": e, "m": m,
            "sel": sel, "finals": finals,
            "bridge_idx": rec["candidates"].index(bridge),
            "answer_idx": rec["candidates"].index(rec["answer"]),
            "uniform": 1.0 / C})
    return items


def make_decoder(device):
    import torch.nn as nn
    return nn.Sequential(nn.Linear(4 * D, H), nn.GELU(),
                         nn.Linear(H, H), nn.GELU(),
                         nn.Linear(H, 1)).to(device)


def score_probe(dec, it, device, mode, bridge_vec=None, bridge_override=None):
    """Candidate scores for one item. mode A: selector clause; mode B: final
    clause(s) + bridge vector."""
    import torch
    g = it["g"].to(device)
    if mode == "A":
        hs = it["h"][it["sel"]].to(device)
        e = it["e"][it["sel"]].to(device)                  # (C, 896)
        msk = it["m"][it["sel"]].to(device)
        b = torch.zeros(D, device=device)
    else:
        hs = it["h"][it["finals"]].to(device).mean(0)
        e = it["e"][it["finals"]].to(device)
        msk_rows = it["m"][it["finals"]].to(device)
        e = (e * msk_rows.unsqueeze(-1)).sum(0) / \
            msk_rows.sum(0).clamp(min=1).unsqueeze(-1)
        msk = msk_rows.any(0)
        b = bridge_vec if bridge_vec is not None else \
            torch.zeros(D, device=device)
        if bridge_override is not None:
            b = bridge_override
    C = e.shape[0]
    feats = torch.cat([g.expand(C, D), hs.expand(C, D),
                       b.expand(C, D), e], dim=-1)
    s = dec(feats).squeeze(-1)
    return s.masked_fill(~msk, float("-inf")), msk


def bridge_vec_of(it, device, idx=None):
    import torch
    j = it["bridge_idx"] if idx is None else idx
    row = it["e"][it["sel"], j]
    if not bool(it["m"][it["sel"], j]):
        return torch.zeros(D, device=device)
    return row.to(device)


def soft_bridge_vec(it, r1, device):
    e_sel = it["e"][it["sel"]].to(device)
    return (r1.unsqueeze(-1) * e_sel).sum(0)


def train_probe(items, device, probe, epochs=EPOCHS):
    """probe in {A, B, C}. Returns trained decoder(s)."""
    import torch
    torch.manual_seed(11)
    d1 = make_decoder(device)
    d2 = make_decoder(device) if probe in ("B", "C") else None
    params = list(d1.parameters()) + (list(d2.parameters()) if d2 else [])
    opt = torch.optim.Adam(params, lr=LR)
    for ep in range(epochs):
        opt.zero_grad(set_to_none=True)
        loss = 0.0
        for it in items:
            if probe == "A":
                s, _ = score_probe(d1, it, device, "A")
                loss = loss + torch.nn.functional.cross_entropy(
                    s.unsqueeze(0),
                    torch.tensor([it["bridge_idx"]], device=device))
            elif probe == "B":
                bv = bridge_vec_of(it, device)
                s, _ = score_probe(d2, it, device, "B", bridge_vec=bv)
                loss = loss + torch.nn.functional.cross_entropy(
                    s.unsqueeze(0),
                    torch.tensor([it["answer_idx"]], device=device))
            else:                                          # C: end-to-end
                s1, _ = score_probe(d1, it, device, "A")
                r1 = torch.softmax(s1, dim=0)
                bv = soft_bridge_vec(it, r1, device)
                s2, _ = score_probe(d2, it, device, "B", bridge_vec=bv)
                loss = loss + torch.nn.functional.cross_entropy(
                    s2.unsqueeze(0),
                    torch.tensor([it["answer_idx"]], device=device))
        loss = loss / len(items)
        loss.backward()
        opt.step()
    return d1, d2


def eval_probe(decs, items, device, probe, wrong_bridge=False):
    import torch
    d1, d2 = decs
    cor = tot = 0
    bridge_cor = 0
    with torch.no_grad():
        for it in items:
            if probe == "A":
                s, _ = score_probe(d1, it, device, "A")
                cor += int(int(s.argmax()) == it["bridge_idx"])
            elif probe == "B":
                if wrong_bridge:
                    msk = it["m"][it["sel"]]
                    alts = [j for j in range(it["C"])
                            if bool(msk[j]) and j != it["bridge_idx"]]
                    j = alts[0] if alts else it["bridge_idx"]
                    bv = bridge_vec_of(it, device, idx=j)
                else:
                    bv = bridge_vec_of(it, device)
                s, _ = score_probe(d2, it, device, "B", bridge_vec=bv)
                cor += int(int(s.argmax()) == it["answer_idx"])
            else:
                s1, _ = score_probe(d1, it, device, "A")
                r1 = torch.softmax(s1, dim=0)
                bridge_cor += int(int(s1.argmax()) == it["bridge_idx"])
                bv = soft_bridge_vec(it, r1, device)
                s2, _ = score_probe(d2, it, device, "B", bridge_vec=bv)
                cor += int(int(s2.argmax()) == it["answer_idx"])
            tot += 1
    out = {"accuracy": round(cor / tot, 4)}
    if probe == "C":
        out["bridge_top1"] = round(bridge_cor / tot, 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_pathb_a0"))
    args = ap.parse_args()
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CPU neural fallback")
    device = args.device
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    allrec = load_train()
    train_sub, hold_sub = [], []
    for q in FAMS:
        fam = [r for r in allrec if r["question_type"] == q]
        train_sub += fam[:N_TRAIN_PER_FAM]
        hold_sub += fam[N_TRAIN_PER_FAM:N_TRAIN_PER_FAM + N_HOLD_PER_FAM]
    subset = train_sub + hold_sub
    print(f"[data] train {len(train_sub)}, holdout {len(hold_sub)} "
          f"(families {FAMS}; QB_ORD dropped: "
          f"QB_ORD_REJECTED_POSITION_SHORTCUT)")

    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    te = time.time()
    acts = extract_split(subset, tok, model, list(LAYERS), device)
    loc = extract_clause_local(subset, tok, model, device, list(LAYERS))
    print(f"[extract] {len(subset)} records, {time.time()-te:.0f}s")
    del model
    torch.cuda.empty_cache()
    # cache-integrity guard (post-collision law): one cache entry per record
    assert len(acts) == len(subset) and len(loc) == len(subset), \
        "PID_COLLISION: cache entries != records"

    # CLEAN PRB-POS measurement (REPORT-ONLY -- for the owner's QB-ORD
    # re-adjudication; the contaminated 0.8883 P0 value is void)
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    prb = {}
    for L in LAYERS:
        X, y = [], []
        for r in train_sub:
            h = acts[r["passage_id"]]["layers"][L][0].float().numpy()
            for i in range(h.shape[0]):
                X.append(h[i]); y.append(i)
        Xh, yh = [], []
        for r in hold_sub:
            h = acts[r["passage_id"]]["layers"][L][0].float().numpy()
            for i in range(h.shape[0]):
                Xh.append(h[i]); yh.append(i)
        pr = LogisticRegression(max_iter=1000).fit(np.array(X), np.array(y))
        prb[str(L)] = round(float(pr.score(np.array(Xh), np.array(yh))), 4)
    print(f"[PRB-POS clean] {prb}")

    report = {"probe": "PATH-B-A0", "non_claim_bearing": True,
              "prb_pos_clean_by_layer_report_only": prb,
              "qb_ord": "QB_ORD_REJECTED_POSITION_SHORTCUT (frozen PRB-POS "
              "gate 0.8883 < 0.90)",
              "families": list(FAMS), "layers": {},
              "pass_law": {"train_ge": 0.95,
                           "holdout_ge_uniform_plus": 0.10,
                           "destructive_drop_ge": 0.30}}
    earned_layer = None
    for L in LAYERS:
        tr = build_tensors(train_sub, acts, loc, L, device)
        ho = build_tensors(hold_sub, acts, loc, L, device)
        unif = sum(it["uniform"] for it in ho) / len(ho)
        dA = train_probe(tr, device, "A")
        dB = train_probe(tr, device, "B")
        dC = train_probe(tr, device, "C")
        res = {"A_train": eval_probe(dA, tr, device, "A"),
               "A_hold": eval_probe(dA, ho, device, "A"),
               "B_train": eval_probe(dB, tr, device, "B"),
               "B_hold": eval_probe(dB, ho, device, "B"),
               "C_train": eval_probe(dC, tr, device, "C"),
               "C_hold": eval_probe(dC, ho, device, "C"),
               "holdout_candidate_uniform": round(unif, 4)}
        # destructive controls on the trained C (and wrong-bridge on B)
        tr_shuf = build_tensors(train_sub, acts, loc, L, device,
                                path_mode="shuffled")
        tr_swap = build_tensors(train_sub, acts, loc, L, device,
                                path_mode="swapped")
        tr_rew = build_tensors(train_sub, acts, loc, L, device,
                               rewire_seed=20260901)
        res["D_shuffled_path"] = eval_probe(dC, tr_shuf, device, "C")
        res["D_swapped_hops"] = eval_probe(dC, tr_swap, device, "C")
        res["D_rewired_membership"] = eval_probe(dC, tr_rew, device, "C")
        res["D_wrong_bridge_on_B"] = eval_probe(dB, tr, device, "B",
                                                wrong_bridge=True)
        # per-family C holdout
        res["C_hold_per_family"] = {}
        for q in FAMS:
            sub = [it for it in ho if it["qt"] == q]
            res["C_hold_per_family"][q] = eval_probe(dC, sub, device, "C")
        cbase = res["C_train"]["accuracy"]
        gates = {
            "A_train_ge_95": res["A_train"]["accuracy"] >= 0.95,
            "B_train_ge_95": res["B_train"]["accuracy"] >= 0.95,
            "C_train_ge_95": cbase >= 0.95,
            "C_hold_above_uniform":
                res["C_hold"]["accuracy"] >= unif + 0.10,
            "shuffled_drop_ge_30":
                cbase - res["D_shuffled_path"]["accuracy"] >= 0.30,
            "rewired_drop_ge_30":
                cbase - res["D_rewired_membership"]["accuracy"] >= 0.30}
        res["gates"] = gates
        res["layer_pass"] = all(gates.values())
        report["layers"][str(L)] = res
        print(f"[L={L}] A={res['A_train']['accuracy']:.3f}/"
              f"{res['A_hold']['accuracy']:.3f} "
              f"B={res['B_train']['accuracy']:.3f}/"
              f"{res['B_hold']['accuracy']:.3f} "
              f"C={cbase:.3f}/{res['C_hold']['accuracy']:.3f} "
              f"(unif {unif:.3f}) shufD={res['D_shuffled_path']['accuracy']:.3f} "
              f"rewD={res['D_rewired_membership']['accuracy']:.3f} "
              f"pass={res['layer_pass']}")
        if res["layer_pass"] and earned_layer is None:
            earned_layer = L
    status = ("GRAPH_EXECUTOR_EARNED" if earned_layer is not None
              else "FROZEN_REPRESENTATION_INSUFFICIENT_FOR_PATH_B")
    report["earned_layer"] = earned_layer
    report["status"] = status
    report["total_wall_clock_seconds"] = round(time.time() - t0, 1)
    (out / "PATHB_A0_RESULTS.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nA0 STATUS: {status} (earned layer: {earned_layer})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
