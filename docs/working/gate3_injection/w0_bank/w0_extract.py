import os, sys, json, hashlib
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
BANK="/workspace/w0/hidden_prompt_injection_bank_v0_20260617.json"
LAYERS=[3,6,9]
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True, output_hidden_states=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
scen=json.load(open(BANK))["scenarios"]
feats=[]; behavior=[]; payload=[]; domain=[]; prompts=[]; sids=[]; groups=[]
with torch.no_grad():
    for i,s in enumerate(scen):
        ids=tok(s["prompt"], return_tensors="pt", truncation=True, max_length=512).input_ids.to("cuda:0")
        hs=m(ids).hidden_states  # tuple (num_layers+1) each (1,seq,768)
        row=[hs[L][0,-1,:].float().cpu().numpy() for L in LAYERS]  # last-token state at each layer
        feats.append(np.stack(row,axis=0))  # (nlayers,768)
        behavior.append(str(s["prompt_injection_status"]).upper())
        payload.append(str(s.get("payload_class","")))
        domain.append(str(s.get("domain","")))
        prompts.append(s["prompt"]); sids.append(s["id"]); groups.append(str(s.get("prompt_group_id","")))
        if (i+1)%160==0: print("extracted", i+1, flush=True)
feats=np.stack(feats,axis=0).astype(np.float32)  # (640,nlayers,768)
out="/workspace/w0/w0_hidden_pi_v0.npz"
np.savez(out, features=feats, layers=np.array(LAYERS), labels_behavior=np.array(behavior),
         labels_payload_class=np.array(payload), labels_domain=np.array(domain),
         prompts=np.array(prompts,dtype=object), scenario_ids=np.array(sids,dtype=object),
         groups=np.array(groups,dtype=object))
print("SAVED", out, "features", feats.shape, "PRESENT/ABSENT", {b:behavior.count(b) for b in set(behavior)})
print("npz_sha", hashlib.sha256(open(out,'rb').read()).hexdigest())
