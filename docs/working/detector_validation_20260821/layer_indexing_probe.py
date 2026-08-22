import sys,pathlib
R=pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
W=R/"noetic-compass-scaffold"/"noetic-compass"/"live-trace-worker"
sys.path.insert(0,str(W))
from app.runtime.open_weight.engine import RuntimeLoadConfig, load_open_weight_runtime
from app.runtime.open_weight.identity import LocalModelSnapshot
SP=pathlib.Path(__file__).resolve().parent
STORE=SP/"models"/"alias--pythia-160m-reserialized"; REV="d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"
rt=load_open_weight_runtime(RuntimeLoadConfig(
 snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized",revision=REV,snapshot_root=STORE/"snapshots"/REV,model_storage_root=STORE),
 adapter_source_path=W.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
 entrypoint_source_path=pathlib.Path(__file__).resolve(),
 device="cpu",dtype="auto",minimum_available_memory_bytes=268435456,minimum_capture_available_bytes=134217728))
print("layer_count =",rt.layer_count)
for i in [0,1,2,rt.layer_count-1]:
    print(f"  residual_paths[{i}] = {rt.adapter.residual_paths[i]}")
print()
print("=> L0 hooks:",rt.adapter.residual_paths[0])
