import os, sys, contextlib
from pathlib import Path
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf
from research.jacobian_lens_canary_torch import _source_delta_target_capture, stable_top2_token_ids
SOURCE_LAYERS=(3,6,9); TARGET_LAYER=11; SRC_POS=126; OUT_POS=127
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
def build(dtype):
    m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=dtype, attn_implementation="eager", use_safetensors=True)
    m.to("cuda:0"); m.eval()
    tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
    return jlens.hf.from_hf(m, tok, compile=False, force_bos=False), tok
lens32,tok=build(torch.float32)
lens64,_=build(torch.float64)
# a real 128-token input: encode a wikitext-like passage
text=("In the early history of the region, settlements grew along the river valleys where "
      "agriculture flourished and trade routes connected distant communities across the plains. ")*6
def make_ids(tok):
    ids=tok(text, return_tensors="pt", truncation=True, max_length=128)["input_ids"]
    if ids.shape[1]<128:
        ids=torch.nn.functional.pad(ids,(0,128-ids.shape[1]),value=int(tok.eos_token_id or 0))
    return ids[:, :128].to("cuda:0")
ids32=make_ids(tok); ids64=ids32.clone()
def measure(lens, ids, dtype, src_layer):
    width=lens.d_model
    vd=torch.zeros(width, dtype=dtype, device="cuda:0", requires_grad=True)
    full=torch.zeros((1,128,width), dtype=dtype, device="cuda:0"); full[:,SRC_POS,:]=vd
    with torch.enable_grad(), _source_delta_target_capture(lens, source_layer=src_layer, target_layer=TARGET_LAYER, delta=full) as cap:
        lens.forward(ids)
    tgt=cap["target"]; logits=lens.unembed(tgt[:,OUT_POS,:])[0]
    t=stable_top2_token_ids(logits.detach().float().cpu().tolist())
    functional=logits[t[0]]-logits[t[1]]
    grad=torch.autograd.grad(functional, vd, create_graph=False)[0]
    gnorm=float(grad.norm().item()); direction=(grad/grad.norm()).detach()
    # forward jvp of functional(alpha) along direction at 0
    def f(alpha):
        d2=torch.zeros((1,128,width), dtype=dtype, device="cuda:0"); d2[:,SRC_POS,:]=alpha*direction
        with _source_delta_target_capture(lens, source_layer=src_layer, target_layer=TARGET_LAYER, delta=d2) as c2:
            lens.forward(ids)
        lg=lens.unembed(c2["target"][:,OUT_POS,:])[0]
        return lg[t[0]]-lg[t[1]]
    z=torch.tensor(0.0, dtype=dtype, device="cuda:0")
    _b,analytic=torch.autograd.functional.jvp(f, z, torch.ones_like(z), strict=True)
    a=float(analytic.item())
    relerr=abs(a-gnorm)/abs(gnorm)
    return gnorm, a, relerr
print("layer | relerr_float32 | relerr_float64 | improvement")
for L in SOURCE_LAYERS:
    _,_,r32=measure(lens32, ids32, torch.float32, L)
    _,_,r64=measure(lens64, ids64, torch.float64, L)
    print("  %2d  |   %.3e    |   %.3e    |  %.1fx" % (L, r32, r64, (r32/r64 if r64>0 else float('inf'))))
