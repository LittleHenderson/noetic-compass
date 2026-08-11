import os, sys, tempfile, math
from pathlib import Path
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf, jlens.fitting
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research import jacobian_lens_canary_torch as jtorch
from research.jacobian_lens_canary_executor import execute_canary_raw
# SHADOW: raise the analytic-vs-gradient limit so the check records instead of fail-closing; collect all relerrs
funcerrs=[]
orig=jtorch.scalar_relative_error
def spy(o,p):
    e=orig(o,p); 
    return e
jtorch.GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT=1.0  # shadow: never fail this gate, collect the distribution
# wrap to record the specific analytic-vs-gradient comparisons: patch at the call site by recording in scalar_relative_error when both args are floats ~O(0.1-2)
import research.jacobian_lens_canary_core as core
core_orig=core.scalar_relative_error
def core_spy(o,p):
    e=core_orig(o,p); funcerrs.append((float(o),float(p),e)); return e
core.scalar_relative_error=core_spy; jtorch.scalar_relative_error=core_spy
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R8}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(t,d): return torch.tensor([t], dtype=torch.long, device=d)
exact=ExactTokenLensModel(lens, manifest, tensor_factory=tf)
d=tempfile.mkdtemp(prefix="dist-")
try:
    execute_canary_raw(run_id="jlcv1-rfc3161-77097e7bfb0d04a461e0db14a64a356cc5a300fbeffec86d1a2940802d2ef91e", lens_model=exact, manifest=manifest, artifact_directory=Path(d)/"art", jacobian_for_prompt=jlens.fitting.jacobian_for_prompt)
    print("FULL RUN COMPLETED under shadow tolerance")
except BaseException as e:
    print("still failed (non-tolerance):", type(e).__name__, str(e)[:150])
# functional analytic-vs-gradient comparisons: values O(0.05..3), identify by both args finite & >1e-3
fe=[h for h in funcerrs if abs(h[0])>1e-3 and abs(h[1])>1e-3]
errs=sorted(h[2] for h in fe)
print("functional-like comparisons:", len(fe))
if errs:
    print("relerr min=%.3e median=%.3e max=%.3e" % (errs[0], errs[len(errs)//2], errs[-1]))
    print("count > 1e-4:", sum(1 for e in errs if e>1e-4), "| > 5e-4:", sum(1 for e in errs if e>5e-4), "| > 1e-3:", sum(1 for e in errs if e>1e-3))
    print("all relerrs:", ["%.2e"%e for e in errs])
