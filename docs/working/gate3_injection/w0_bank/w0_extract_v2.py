"""W0 hidden-state extractor for the prompt-injection detection Gate-2 run.

Runs ON THE POD (GPU, torch) against a local pythia-160m snapshot. For each
prompt in the hidden prompt-injection bank it takes the last-token residual
stream at a fixed pre-registered set of layers (3, 6, 9) and writes an .npz in
the schema the fair-comparison scorer consumes: features (N, n_layers, dim),
layers, labels_behavior (PRESENT/ABSENT), labels_payload_class, labels_domain,
prompts, scenario_ids, groups (prompt_group_id). Layers are fixed a priori so
the downstream permutation test can Bonferroni-correct across exactly them —
no post-hoc layer cherry-picking. Extraction is measurement only; it licenses
nothing. Bank path / snapshot path are pod-local.
"""

import argparse, os, sys, json, hashlib
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
BANK="/workspace/w0/hidden_prompt_injection_bank_v0_20260617.json"

# Attempt 1 defaults (last-token, layers 3/6/9) kept for reproducibility;
# Attempt 2 passes --pool mean --layers 0,3,6,9 --output ... explicitly.
# Layer 0 under mean pooling is the token-identity leakage control
# (bag-of-embeddings): a candidate layer must beat it, not be it.
ap = argparse.ArgumentParser()
ap.add_argument("--pool", choices=["last", "mean"], default="last")
ap.add_argument("--layers", default="3,6,9")
ap.add_argument("--output", default="/workspace/w0/w0_hidden_pi_v0.npz")
args = ap.parse_args()
LAYERS=[int(v) for v in args.layers.split(",")]
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True, output_hidden_states=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
scen=json.load(open(BANK))["scenarios"]
feats=[]; behavior=[]; payload=[]; domain=[]; prompts=[]; sids=[]; groups=[]
with torch.no_grad():
    for i,s in enumerate(scen):
        ids=tok(s["prompt"], return_tensors="pt", truncation=True, max_length=512).input_ids.to("cuda:0")
        hs=m(ids).hidden_states  # tuple (num_layers+1) each (1,seq,768)
        if args.pool == "mean":
            row=[hs[L][0,:,:].float().mean(dim=0).cpu().numpy() for L in LAYERS]  # mean over all tokens
        else:
            row=[hs[L][0,-1,:].float().cpu().numpy() for L in LAYERS]  # last-token state at each layer
        feats.append(np.stack(row,axis=0))  # (nlayers,768)
        behavior.append(str(s["prompt_injection_status"]).upper())
        payload.append(str(s.get("payload_class","")))
        domain.append(str(s.get("domain","")))
        prompts.append(s["prompt"]); sids.append(s["id"]); groups.append(str(s.get("prompt_group_id","")))
        if (i+1)%160==0: print("extracted", i+1, flush=True)
feats=np.stack(feats,axis=0).astype(np.float32)  # (640,nlayers,768)
out=args.output
np.savez(out, features=feats, layers=np.array(LAYERS), labels_behavior=np.array(behavior),
         labels_payload_class=np.array(payload), labels_domain=np.array(domain),
         prompts=np.array(prompts,dtype=object), scenario_ids=np.array(sids,dtype=object),
         groups=np.array(groups,dtype=object))
print("SAVED", out, "features", feats.shape, "PRESENT/ABSENT", {b:behavior.count(b) for b in set(behavior)})
print("npz_sha", hashlib.sha256(open(out,'rb').read()).hexdigest())
