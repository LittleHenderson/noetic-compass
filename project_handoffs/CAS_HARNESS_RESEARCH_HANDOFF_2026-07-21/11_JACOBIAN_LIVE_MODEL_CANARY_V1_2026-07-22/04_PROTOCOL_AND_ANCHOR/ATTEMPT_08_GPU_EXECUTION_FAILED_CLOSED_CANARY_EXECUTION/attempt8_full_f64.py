import os, sys
from pathlib import Path
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research.jacobian_lens_canary_torch import _source_delta_target_capture, stable_top2_token_ids
from research.jacobian_lens_canary_executor import build_execution_plan
SOURCE_LAYERS=(3,6,9); TARGET_LAYER=11; SRC_POS=126; OUT_POS=127
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
def build(dtype):
    m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=dtype, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
    tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
    return jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R8}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(t,d): return torch.tensor([t], dtype=torch.long, device=d)
lens32=ExactTokenLensModel(build(torch.float32), manifest, tensor_factory=tf)
lens64=ExactTokenLensModel(build(torch.float64), manifest, tensor_factory=tf)
plan=build_execution_plan(manifest)
def relerr(lens, dtype, block_id, L):
    ids=lens.encode(block_id, max_length=128); width=lens.d_model
    vd=torch.zeros(width, dtype=dtype, device="cuda:0", requires_grad=True)
    full=torch.zeros((1,128,width), dtype=dtype, device="cuda:0"); full[:,SRC_POS,:]=vd
    with torch.enable_grad(), _source_delta_target_capture(lens, source_layer=L, target_layer=TARGET_LAYER, delta=full) as cap:
        lens.forward(ids)
    logits=lens.unembed(cap["target"][:,OUT_POS,:])[0]
    t=stable_top2_token_ids(logits.detach().float().cpu().tolist())
    functional=logits[t[0]]-logits[t[1]]
    grad=torch.autograd.grad(functional, vd, create_graph=False)[0]
    gnorm=float(grad.norm().item()); direction=(grad/grad.norm()).detach()
    def f(a):
        d2=torch.zeros((1,128,width), dtype=dtype, device="cuda:0"); d2[:,SRC_POS,:]=a*direction
        with _source_delta_target_capture(lens, source_layer=L, target_layer=TARGET_LAYER, delta=d2) as c2:
            lens.forward(ids)
        l2=lens.unembed(c2["target"][:,OUT_POS,:])[0]; return l2[t[0]]-l2[t[1]]
    z=torch.tensor(0.0, dtype=dtype, device="cuda:0"); _b,a=torch.autograd.functional.jvp(f, z, torch.ones_like(z), strict=True)
    return abs(float(a.item())-gnorm)/abs(gnorm)
r32=[]; r64=[]
for b in plan.blocks:
    for L in SOURCE_LAYERS:
        r32.append(relerr(lens32, torch.float32, b.block_id, L))
        r64.append(relerr(lens64, torch.float64, b.block_id, L))
def summ(name, xs):
    xs=sorted(xs); n=len(xs)
    print("%s: n=%d min=%.2e median=%.2e max=%.2e | >1e-4:%d >1e-3:%d" % (name,n,xs[0],xs[n//2],xs[-1], sum(1 for e in xs if e>1e-4), sum(1 for e in xs if e>1e-3)))
summ("float32", r32); summ("float64", r64)
