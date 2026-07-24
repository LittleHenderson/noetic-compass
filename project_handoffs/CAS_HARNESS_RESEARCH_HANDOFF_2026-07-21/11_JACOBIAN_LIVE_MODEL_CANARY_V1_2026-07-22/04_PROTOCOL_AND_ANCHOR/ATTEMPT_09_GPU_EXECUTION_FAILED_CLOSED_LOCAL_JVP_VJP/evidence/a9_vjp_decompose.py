import sys, math
from pathlib import Path
OFF="/workspace/cas-jlcv1-official-6d676840-179fa0ff"
WK=f"{OFF}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
sys.path.insert(0, WK)
from research.jacobian_lens_canary_artifacts import decode_float32_artifact
OUT=Path(f"{OFF}/output")
def vals(name):
    p=OUT/name
    art,tup=decode_float32_artifact(p.read_bytes())
    return list(tup)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm(a): return math.sqrt(sum(x*x for x in a))
worst=[("r1","l3"),("r2","l9"),("r7","l6"),("r3","l3"),("r2","l6")]
print("Decomposition of the LOCAL VJP relative error (frozen A9 float32 artifacts).")
print("VJP relerr = |direct_vjp - target^T M source| / |direct_vjp|")
print("  fr_gap    = |direct_vjp - target^T (true JVP)| / |direct_vjp|   [forward-vs-reverse autodiff gap, no matrix]")
print("  mtx_gap   = |target^T(true JVP) - target^T M source| / |direct_vjp| [matrix-estimation error on target]")
print("  jvp_relerr= ||true JVP - M source|| / ||true JVP||")
print()
print(f"{'meas':>7} {'vjp_relerr':>11} {'fr_gap':>11} {'mtx_gap':>11} {'jvp_relerr':>11}  dominant")
for r,l in worst:
    dj = vals(f"jvp-direct-{r}-{l}.casf32")     # true forward-mode JVP vector J.source
    pj = vals(f"jvp-matrix-{r}-{l}.casf32")     # M.source  (matrix-predicted JVP)
    tgt= vals(f"vjp-direction-{r}-{l}.casf32")  # target v
    dvjp = vals(f"vjp-direct-{r}-{l}.casf32")[0]   # true reverse-mode bilinear v^T J source
    pvjp = vals(f"vjp-matrix-{r}-{l}.casf32")[0]   # v^T M source
    fj = dot(tgt, dj)                           # v^T (true forward JVP)
    denom = abs(dvjp)
    vjp_relerr = abs(dvjp - pvjp)/denom
    fr_gap = abs(dvjp - fj)/denom               # reverse-mode vs forward-mode (both true)
    mtx_gap = abs(fj - pvjp)/denom              # forward true vs matrix prediction
    jvp_relerr = norm([a-b for a,b in zip(dj,pj)])/norm(dj)
    dom = "FWD-vs-REV" if fr_gap>mtx_gap else "MATRIX-EST"
    print(f"{r}/{l:>3} {vjp_relerr:11.3e} {fr_gap:11.3e} {mtx_gap:11.3e} {jvp_relerr:11.3e}  {dom}")
print()
print("Interpretation: if fr_gap dominates, the VJP gate is catching the forward-vs-reverse")
print("autodiff disagreement (A8 already showed float64 does NOT remove that floor). If mtx_gap")
print("dominates, it is matrix-estimation error (potentially float64/estimator-curable).")
