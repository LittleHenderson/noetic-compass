import os, sys, traceback
from pathlib import Path
WK="/workspace/cas-jlcv1-official-88b59de9-09995d91/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
sys.path.insert(0, WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch
from research import jacobian_lens_canary_runtime as rt
snap=Path("/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46")
man=open("/workspace/cas-jlcv1-official-88b59de9-09995d91/frozen/model/pythia_160m_model_manifest_v1.json","rb").read()
parsed=rt.load_model_manifest_bytes(man)
try:
    obs=rt.inventory_exact_model_snapshot(snap)
    print("inventory OK, files:", len(obs), "| matches manifest:", obs==parsed.get("files"), "| files_sha256 match:", rt.model_files_sha256(obs)==parsed.get("files_sha256"))
except BaseException as e:
    print("inventory FAILED:", type(e).__name__, e); traceback.print_exc()
# full from_pretrained from cache snapshot
try:
    import transformers
    m=transformers.AutoModelForCausalLM.from_pretrained(str(snap), local_files_only=True, trust_remote_code=False, dtype=torch.float32, attn_implementation="eager", use_safetensors=True)
    print("from_pretrained from cache snapshot OK:", type(m).__name__)
except BaseException as e:
    print("from_pretrained FAILED:", type(e).__name__, e)
