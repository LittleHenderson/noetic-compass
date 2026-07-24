import os, sys, tempfile
from pathlib import Path
R="/workspace/cas-jlcv1-official-6d676840-179fa0ff"; WK=f"{R}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf, jlens.fitting
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research.jacobian_lens_canary_executor import execute_canary_raw
import statistics
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(t,d): return torch.tensor([t], dtype=torch.long, device=d)
exact=ExactTokenLensModel(lens, manifest, tensor_factory=tf)
d=tempfile.mkdtemp(prefix="a9jvp-"); art=Path(d)/"art"
raw=execute_canary_raw(run_id="jlcv1-rfc3161-179fa0ff51dcef07db7f1b6627ba08a2285a1624849b843b098b9b2cabf28b82", lens_model=exact, manifest=manifest, artifact_directory=art, jacobian_for_prompt=jlens.fitting.jacobian_for_prompt)
jvp=[(r.selection_rank,r.source_layer,r.relative_error) for r in raw.jvp_records]
vjp=[(r.selection_rank,r.source_layer,r.relative_error) for r in raw.vjp_records]
jvp.sort(key=lambda x:-x[2]); vjp.sort(key=lambda x:-x[2])
print('=== JVP worst (rank,layer,relerr) ===')
for r,l,e in jvp[:8]: print(f'  r{r} l{l}: {e:.4e}')
print('=== VJP worst (rank,layer,relerr) ===')
for r,l,e in vjp[:10]: print(f'  r{r} l{l}: {e:.4e}')
print('JVP max %.4e  VJP max %.4e'%(jvp[0][2],vjp[0][2]))
