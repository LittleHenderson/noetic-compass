import os, sys, traceback
WK="/workspace/cas-jlcv1-official-88b59de9-09995d91/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
sys.path.insert(0, WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers
from research import jacobian_lens_canary_runtime as rt
root="/workspace/cas-model-a8969eb7"
m=transformers.AutoModelForCausalLM.from_pretrained(root, local_files_only=True, trust_remote_code=False, dtype=torch.float32, attn_implementation="eager", use_safetensors=True)
tok=transformers.AutoTokenizer.from_pretrained(root, local_files_only=True, trust_remote_code=False, use_fast=True)
m.to("cuda:0"); m.eval()
print("requires_grad BEFORE jlens:", m.get_parameter("gpt_neox.embed_in.weight").requires_grad)
jl=rt._import_jlens_from_hf()
lens=jl(m, tok, compile=False, force_bos=False)
print("requires_grad AFTER jlens:", m.get_parameter("gpt_neox.embed_in.weight").requires_grad)
try:
    rt._validate_exact_model_and_lens(model=m, tokenizer=tok, lens_model=lens, device=torch.device("cuda:0"), torch_module=torch)
    print("VALIDATE_OK -- model load path is clean")
except BaseException as e:
    print("VALIDATE_FAILED:", type(e).__name__, str(e))
    traceback.print_exc()
