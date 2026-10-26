"""Anchored precedence chain -- core forward/backward, exact residual metrics.

    h_{-1} = 0
    h_k    = tanh( E[assign[k]] @ W_k + h_{k-1} @ U_k + b_k )   k = 0..K-1
    out    = h_{K-1} @ Rd

No action mask. Shared readout Rd.
"""
import numpy as np

K, DE, H, ACT = 5, 5, 5, 4


def rand_params(seed, K=K, DE=DE, H=H, ACT=ACT, scale=1.0):
    r = np.random.default_rng(seed)
    W = scale * r.normal(size=(K, DE, H))
    U = scale * r.normal(size=(K, H, H))
    b = scale * r.normal(size=(K, H))
    Rd = r.normal(size=(H, ACT))
    return dict(W=W, U=U, b=b, Rd=Rd)


def forward(p, E, assign=None):
    """E: (N,K,DE) -> out: (N,ACT).  assign[k] = TYPE at chain POSITION k."""
    Kk = p["W"].shape[0]
    if assign is None:
        assign = np.arange(Kk)
    N = E.shape[0]
    h = np.zeros((N, p["W"].shape[2]))
    for k in range(Kk):
        a = E[:, assign[k], :] @ p["W"][k] + h @ p["U"][k] + p["b"][k]
        h = np.tanh(a)
    return h @ p["Rd"]


def fwd_cache(p, E, assign=None):
    Kk = p["W"].shape[0]
    if assign is None:
        assign = np.arange(Kk)
    N = E.shape[0]
    hs = [np.zeros((N, p["W"].shape[2]))]
    for k in range(Kk):
        a = E[:, assign[k], :] @ p["W"][k] + hs[-1] @ p["U"][k] + p["b"][k]
        hs.append(np.tanh(a))
    out = hs[-1] @ p["Rd"]
    return out, hs


def grads(p, E, target, assign=None):
    """MSE loss = mean over (N,ACT) of (out-target)^2. Returns loss, grad dict."""
    Kk = p["W"].shape[0]
    if assign is None:
        assign = np.arange(Kk)
    out, hs = fwd_cache(p, E, assign)
    N = E.shape[0]
    d = out - target
    loss = np.mean(d * d)
    c = 2.0 / (N * target.shape[1])
    gOut = c * d                                    # (N,ACT)
    g = dict(W=np.zeros_like(p["W"]), U=np.zeros_like(p["U"]),
             b=np.zeros_like(p["b"]), Rd=hs[-1].T @ gOut)
    gh = gOut @ p["Rd"].T                           # (N,H)
    for k in range(Kk - 1, -1, -1):
        ga = gh * (1.0 - hs[k + 1] ** 2)            # through tanh
        g["W"][k] = E[:, assign[k], :].T @ ga
        g["U"][k] = hs[k].T @ ga
        g["b"][k] = ga.sum(0)
        gh = ga @ p["U"][k].T
    return loss, g


def rel_rmse(a, b):
    """||a-b||_F / ||b||_F  -- scale-invariant residual."""
    return float(np.sqrt(np.sum((a - b) ** 2) / np.sum(b ** 2)))


def abs_rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))
