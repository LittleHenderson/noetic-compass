import os, sys, traceback
R8="/workspace/cas-jlcv1-official-88b59de9-77097e7b"; WK=f"{R8}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"; DEP=f"{R8}/dependency"
sys.path.insert(0,DEP); sys.path.insert(0,WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers, jlens.hf, jlens.fitting
from research.jacobian_lens_canary_executor import TaggedAutogradGradCounter, MATRIX_SCOPE, SOURCE_LAYERS, TARGET_LAYER, SEQUENCE_LENGTH
snap="/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
m=transformers.AutoModelForCausalLM.from_pretrained(snap, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True); m.to("cuda:0"); m.eval()
tok=transformers.AutoTokenizer.from_pretrained(snap, local_files_only=True, use_fast=True)
lens=jlens.hf.from_hf(m, tok, compile=False, force_bos=False)
print("SOURCE_LAYERS", SOURCE_LAYERS, "TARGET_LAYER", TARGET_LAYER)
# is torch.autograd.grad the same object jlens sees?
import jlens.fitting as jf
print("jf module torch is torch:", jf.torch is torch)
prompt="The quick brown fox jumps over the lazy dog. " * 40  # long enough for 128 tokens
try:
    with TaggedAutogradGradCounter(torch) as counter:
        print("inside counter: torch.autograd.grad is patched:", torch.autograd.grad.__name__)
        with counter.scope(MATRIX_SCOPE):
            res = jf.jacobian_for_prompt(lens, prompt, SOURCE_LAYERS, target_layer=TARGET_LAYER)
        print("counts after one jacobian_for_prompt:", counter.counts)
except BaseException as e:
    print("PROBE_FAILED:", type(e).__name__, repr(str(e))[:300]); traceback.print_exc()
