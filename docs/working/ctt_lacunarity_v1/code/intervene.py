"""Rank 5 intervention: three 500-step arms from A4-s1 step 1,000 (targeted / undirected / placebo labels)."""
import json, random, sys, time
from pathlib import Path

HERE = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1")
sys.path.insert(0, str(HERE))
import torch
import torch.nn.functional as F
from cube_task import mix, target
from helm_cas_translator import model as M, param_count
from helm_cas_translator.vocab import BOS, PAD, context_units
from mouth_task import vocab_m

STEPS = 500
CKPT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\results\out\A4-s1\step_01000.pt")
ARMS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\arms"); ARMS.mkdir(exist_ok=True)
NOETIC = tuple("^%d" % i for i in range(10))
LOW = ("^2", "^3", "^4", "^5", "^8")

device = M.require_cuda()
fz = json.loads((HERE / "FROZEN_MOUTH.json").read_text(encoding="utf-8"))
cfg = param_count.CONFIGS["A4_9p6M"]
data = HERE / "data"
vm = vocab_m.load(str(data / "vocab.json"))

def load(name):
    return [json.loads(l) for l in open(data / name, encoding="utf-8") if l.strip()]

mouth, cube, cas, ear_m = load("mouth_train.jsonl"), load("train_cube.jsonl"), load("cas_keep.jsonl"), load("ear_m.jsonl")
enc = {
    "MOUTH": [(vm.encode_mouth_source(r["situation"], tuple(r["tone"]), r["input_text"],
                                      tuple(r["style"]) if r.get("style") else None), vm.encode_mouth_target(r["target"]))
              for r in mouth],
    "EAR_M": [(vm.base.encode_source(target.DIRECTION, r["text"], [])[0], vm.base.encode_target(r["target"])) for r in ear_m],
    "CUBE": [(vm.base.encode_source(target.DIRECTION, r["text"], [])[0], vm.base.encode_target(r["target"])) for r in cube],
}
cas_enc_full = [(vm.base.encode_source(r["direction"], r["text"], context_units(r["context"]))[0], vm.base.encode_target(r["target"])) for r in cas]

low_idx = [i for i, r in enumerate(cas) if any(t in LOW for t in (r["target"] or []))]
rng = random.Random(20261024)
rand_idx = rng.sample(range(len(cas)), len(low_idx))

def placebo_target(toks, rng):
    out = []
    for t in toks:
        if t in NOETIC:
            out.append(rng.choice([n for n in NOETIC if n != t]) if rng.random() < 1.0 else t)
        else:
            out.append(t)
    return out

arm_pools = {
    "targeted":  [cas_enc_full[i] for i in low_idx],
    "undirected":[cas_enc_full[i] for i in rand_idx],
    "placebo":   [(cas_enc_full[i][0], vm.base.encode_target(placebo_target(cas[i]["target"], random.Random(9000 + i)))) for i in low_idx],
}

for arm, extra in arm_pools.items():
    dest = ARMS / f"{arm}.pt"
    if dest.exists():
        print(arm, "exists, skip", flush=True); continue
    torch.manual_seed(777); random.seed(777)
    net = M.CTTModel.from_config(len(vm), cfg, dropout=fz["dropout"]).to(device)
    net.load_state_dict(torch.load(CKPT, map_location=device, weights_only=True))
    net.train()
    enc_arm = dict(enc); enc_arm["CAS"] = cas_enc_full + extra
    sizes = {k: len(v) for k, v in enc_arm.items()}
    plan = mix.batch_plan(STEPS, fz["batch"], sizes, fz["mix"], 7001)
    opt = torch.optim.AdamW(net.parameters(), lr=fz["lr"], weight_decay=fz["weight_decay"])
    t0 = time.time()
    for step, batch in enumerate(plan):
        for g in opt.param_groups:
            g["lr"] = fz["lr"]
        chunks = [batch[i:i + 64] for i in range(0, len(batch), 64)]
        opt.zero_grad(set_to_none=True)
        total = 0.0
        for chunk in chunks:
            pairs = [enc_arm[k][i] for k, i in chunk]
            src = M.pad_batch([s for s, _t in pairs], device)
            tgt_out = M.pad_batch([t for _s, t in pairs], device)
            tgt_in = M.pad_batch([[BOS] + t[:-1] for _s, t in pairs], device)
            logp = net(src, tgt_in)
            loss = F.nll_loss(logp.reshape(-1, logp.size(-1)), tgt_out.reshape(-1), ignore_index=PAD)
            (loss / len(chunks)).backward()
            total += float(loss.item())
        torch.nn.utils.clip_grad_norm_(net.parameters(), fz["grad_clip"])
        opt.step()
        if (step + 1) % 100 == 0:
            print(arm, step + 1, round(total / len(chunks), 5), round(time.time() - t0, 1), flush=True)
    torch.save(net.state_dict(), dest)
    print(arm, "saved", dest, flush=True)
print("INTERVENE_DONE")

