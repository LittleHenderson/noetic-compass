import os, sys, tempfile, traceback
from pathlib import Path
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
torch.use_deterministic_algorithms(True); torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False; torch.set_float32_matmul_precision("highest")
import transformers, jlens.hf, jlens.fitting
from research.exact_token_lens import ExactTokenLensModel, load_manifest
from research.jacobian_lens_canary_executor import execute_canary_raw
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
manifest=load_manifest(Path(f"{R8}/frozen/tokens/jspace_wikitext_blocks_v1.json"))
def tf(token_ids, device): return torch.tensor([token_ids], dtype=torch.long, device=device)
exact=ExactTokenLensModel(lens, manifest, tensor_factory=tf)
print("adapter built; manifest_sha256 present:", bool(getattr(exact,'manifest_sha256','')))
d=tempfile.mkdtemp(prefix="faithful-"); art=Path(d)/"art"
try:
    raw=execute_canary_raw(run_id="jlcv1-rfc3161-77097e7bfb0d04a461e0db14a64a356cc5a300fbeffec86d1a2940802d2ef91e", lens_model=exact, manifest=manifest, artifact_directory=art, jacobian_for_prompt=jlens.fitting.jacobian_for_prompt)
    print("CANARY_EXECUTION_OK  artifacts:", len(list(art.iterdir())))
except BaseException as e:
    print("CANARY_EXEC_FAILED:", type(e).__name__, repr(str(e))[:500])
    print("artifacts produced before failure:", len(list(art.iterdir())) if art.exists() else 0)
    traceback.print_exc()
