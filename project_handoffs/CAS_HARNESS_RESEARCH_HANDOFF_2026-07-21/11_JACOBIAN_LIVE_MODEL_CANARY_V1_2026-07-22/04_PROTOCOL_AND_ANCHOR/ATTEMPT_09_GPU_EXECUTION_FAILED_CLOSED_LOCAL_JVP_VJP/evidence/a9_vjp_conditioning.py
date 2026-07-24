import sys, math
from pathlib import Path
import numpy as np
OFF="/workspace/cas-jlcv1-official-6d676840-179fa0ff"
WK=f"{OFF}/repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
sys.path.insert(0, WK)
from research.jacobian_lens_canary_artifacts import decode_float32_artifact
OUT=Path(f"{OFF}/output")
def vals(name):
    art,tup=decode_float32_artifact((OUT/name).read_bytes()); return np.array(tup,dtype=np.float64)
worst=[("r1","l3"),("r2","l9"),("r7","l6"),("r3","l3"),("r2","l6")]
print("VJP normalization-conditioning check (frozen A9 artifacts).")
print(f"{'meas':>7} {'|direct_vjp|':>12} {'abs_mtx_err':>12} {'||M.src-Jsrc||':>14} {'||Jsrc||':>10} {'M_cond':>10} {'|dvjp|/scale':>12}")
for r,l in worst:
    dj=vals(f"jvp-direct-{r}-{l}.casf32"); pj=vals(f"jvp-matrix-{r}-{l}.casf32")
    tgt=vals(f"vjp-direction-{r}-{l}.casf32")
    dvjp=vals(f"vjp-direct-{r}-{l}.casf32")[0]; pvjp=vals(f"vjp-matrix-{r}-{l}.casf32")[0]
    fj=float(tgt@dj)
    abs_mtx_err=abs(fj-pvjp)
    vec_abs_err=np.linalg.norm(dj-pj); jnorm=np.linalg.norm(dj)
    # scale of a typical random projection: ||Jsrc|| * ||tgt|| / sqrt(width)  (rademacher tgt has norm sqrt(width))
    scale = jnorm*np.linalg.norm(tgt)/math.sqrt(len(tgt))
    # matrix conditioning
    Mfull=vals(f"matrix-{r}-x0-{l}.casf32")
    w=int(round(math.sqrt(len(Mfull)))); M=Mfull.reshape(w,w)
    sv=np.linalg.svd(M,compute_uv=False); cond=sv[0]/sv[-1]
    print(f"{r}/{l:>3} {abs(dvjp):12.4e} {abs_mtx_err:12.4e} {vec_abs_err:14.4e} {jnorm:10.3e} {cond:10.3e} {abs(dvjp)/scale:12.3f}")
print()
print("Key: if abs_mtx_err is ~constant across rows while |direct_vjp| varies, the relative")
print("blowup is normalization amplification (random target nearly orthogonal to J.source =>")
print("small |direct_vjp| denominator). |dvjp|/scale << 1 confirms an atypically small projection.")
