import os, sys, math
from pathlib import Path
R="/workspace/cas-jlcv1-official-6d676840-179fa0ff"
WK=f"{R}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf, jlens.fitting
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research.jacobian_lens_canary_executor import build_execution_plan, DIM_BATCH, SEQUENCE_LENGTH
from research.jacobian_lens_canary_core import (SOURCE_LAYERS, TARGET_LAYER, VALID_POSITION_START, VALID_POSITION_END,
    JVP_SOURCE_CHECK, VJP_TARGET_CHECK, rademacher_direction)
from research.jacobian_lens_canary_torch import target_summary_with_delta, _direction_delta
snap=f"/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(t,d): return torch.tensor([t], dtype=torch.long, device=d)
exact=ExactTokenLensModel(lens, manifest, tensor_factory=tf)
plan=build_execution_plan(manifest)
dev="cuda:0"
def metrics_for(block, layer, Mgpu, corrupt=1.0):
    ids=exact.encode(block.block_id, max_length=SEQUENCE_LENGTH)
    d=ids.device
    src=torch.tensor(rademacher_direction(check_name=JVP_SOURCE_CHECK,block_id=block.block_id,layer=layer),dtype=torch.float32,device=d)
    tgt=torch.tensor(rademacher_direction(check_name=VJP_TARGET_CHECK,block_id=block.block_id,layer=layer),dtype=torch.float32,device=d)
    tangent=_direction_delta(direction=src,sequence_length=SEQUENCE_LENGTH,width=768,valid_start=VALID_POSITION_START,valid_end=VALID_POSITION_END,device=d)
    zero=torch.zeros_like(tangent)
    def summary(delta): return target_summary_with_delta(exact,ids,source_layer=layer,target_layer=TARGET_LAYER,valid_start=VALID_POSITION_START,valid_end=VALID_POSITION_END,delta=delta)
    with torch.enable_grad():
        _b,direct_jvp=torch.autograd.functional.jvp(summary,zero,tangent,create_graph=False,strict=True)
        vd=torch.zeros_like(tangent,requires_grad=True); s=summary(vd); scal=torch.dot(tgt,s)
        grad=torch.autograd.grad(scal,vd,create_graph=False,retain_graph=False)[0]
    g_red=grad[0,VALID_POSITION_START:VALID_POSITION_END+1,:].sum(dim=0)   # = A^T target
    M=(Mgpu*corrupt).to(d)
    pred_jvp=M@src; Mt_tgt=M.t()@tgt
    dvjp=float(torch.dot(g_red,src)); pvjp=float(torch.dot(tgt,pred_jvp))
    jvp_relerr=float(torch.linalg.vector_norm(direct_jvp-pred_jvp)/torch.linalg.vector_norm(direct_jvp))
    vjp_old=abs(dvjp-pvjp)/max(abs(dvjp),abs(pvjp),1e-8)
    vjp_natural=abs(dvjp-pvjp)/(float(torch.linalg.vector_norm(tgt))*float(torch.linalg.vector_norm(direct_jvp)))
    vjp_vector=float(torch.linalg.vector_norm(g_red-Mt_tgt)/torch.linalg.vector_norm(g_red))
    return jvp_relerr,vjp_old,vjp_natural,vjp_vector
# estimate M per block (all 3 layers, repeat 0), then metrics per (block,layer)
rows=[]; corrupt_rows=[]
for block in plan.blocks:
    res,seq,nv=jlens.fitting.jacobian_for_prompt(exact,block.block_id,SOURCE_LAYERS,target_layer=TARGET_LAYER,dim_batch=DIM_BATCH,max_seq_len=SEQUENCE_LENGTH,skip_first=VALID_POSITION_START)
    for layer in SOURCE_LAYERS:
        M=res[layer].float()
        rows.append((block.selection_rank,layer,*metrics_for(block,layer,M,1.0)))
        # strictness: corrupt M by +0.5% and confirm the well-conditioned metrics blow up
        corrupt_rows.append((block.selection_rank,layer,*metrics_for(block,layer,M,1.005)))
def summ(name,idx,rs):
    v=[r[idx] for r in rs]; return f"{name}: max={max(v):.3e} median={sorted(v)[len(v)//2]:.3e} >1e-4={sum(1 for x in v if x>1e-4)} >1e-3={sum(1 for x in v if x>1e-3)}"
print("=== CLEAN matrix (24 measurements): jvp_relerr | vjp_old(current) | vjp_natural | vjp_vector ===")
for r in sorted(rows,key=lambda x:-x[3]):
    print(f"  r{r[0]} l{r[1]}: jvp={r[2]:.3e}  vjp_old={r[3]:.3e}  vjp_nat={r[4]:.3e}  vjp_vec={r[5]:.3e}")
print(summ("JVP",2,rows)); print(summ("VJP_old",3,rows)); print(summ("VJP_natural",4,rows)); print(summ("VJP_vector",5,rows))
print()
print("=== CORRUPTED matrix (M*1.005, +0.5% error) — must blow past gate to stay strict ===")
print(summ("JVP",2,corrupt_rows)); print(summ("VJP_old",3,corrupt_rows)); print(summ("VJP_natural",4,corrupt_rows)); print(summ("VJP_vector",5,corrupt_rows))
