import os, sys, tempfile, traceback
from pathlib import Path
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf, jlens.fitting
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research import jacobian_lens_canary_core as core
from research import jacobian_lens_canary_torch as jtorch
from research.jacobian_lens_canary_executor import execute_canary_raw
# instrument: capture every scalar_relative_error(analytic, gradient_norm) comparison near the limit
orig=core.scalar_relative_error
hits=[]
def spy(observed, predicted):
    e=orig(observed, predicted)
    hits.append((float(observed), float(predicted), e))
    return e
core.scalar_relative_error=spy; jtorch.scalar_relative_error=spy
print("LIMIT:", core.GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT)
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R8}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(t,device): return torch.tensor([t], dtype=torch.long, device=device)
exact=ExactTokenLensModel(lens, manifest, tensor_factory=tf)
d=tempfile.mkdtemp(prefix="instr-")
try:
    execute_canary_raw(run_id="jlcv1-rfc3161-77097e7bfb0d04a461e0db14a64a356cc5a300fbeffec86d1a2940802d2ef91e", lens_model=exact, manifest=manifest, artifact_directory=Path(d)/"art", jacobian_for_prompt=jlens.fitting.jacobian_for_prompt)
    print("OK")
except BaseException as e:
    print("FAILED:", type(e).__name__, str(e)[:120])
print("last 3 scalar_relative_error (analytic, gradient_norm, relerr):")
for h in hits[-3:]: print("  analytic=%.10g gradient_norm=%.10g relerr=%.6g" % h)
