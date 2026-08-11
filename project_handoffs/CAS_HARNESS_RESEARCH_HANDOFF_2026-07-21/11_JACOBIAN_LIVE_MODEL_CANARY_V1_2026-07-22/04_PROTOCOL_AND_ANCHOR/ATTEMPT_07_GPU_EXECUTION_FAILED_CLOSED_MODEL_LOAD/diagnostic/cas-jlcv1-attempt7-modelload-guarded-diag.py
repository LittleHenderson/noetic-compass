import os, sys, traceback
WK="/workspace/cas-jlcv1-official-88b59de9-09995d91/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
sys.path.insert(0, WK)
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_TELEMETRY":"1","CUBLAS_WORKSPACE_CONFIG":":4096:8","NVIDIA_TF32_OVERRIDE":"0","TOKENIZERS_PARALLELISM":"false"})
from research import jacobian_lens_network_guard as g
LIB="d60148325d84cab666b226676c5009a61eea24f3902598829fe714da87ef3587"
try:
    p1=g.install_phase_one_guard(expected_libseccomp_sha256=LIB)
    import torch, transformers
    b=g.initialize_cuda_bootstrap(torch, device_index=0)
    uvm=g.identify_sole_cuda_uvm_listener()
    p2=g.install_phase_two_guard(phase_one_observation=p1, uvm_listener=uvm, expected_libseccomp_sha256=p1.libseccomp_sha256)
    g.run_post_guard_cuda_proof(torch, bootstrap=b, phase_two_observation=p2)
    print("GUARD_OK phase_two+proof passed; now MODEL_LOAD under active deny...")
    m=transformers.AutoModelForCausalLM.from_pretrained("/workspace/cas-model-a8969eb7", local_files_only=True, trust_remote_code=False, dtype=torch.float32, attn_implementation="eager", use_safetensors=True)
    print("MODEL_LOAD_OK", type(m).__name__)
except BaseException as e:
    print("FAILED:", type(e).__name__, repr(str(e))[:500])
    traceback.print_exc()
