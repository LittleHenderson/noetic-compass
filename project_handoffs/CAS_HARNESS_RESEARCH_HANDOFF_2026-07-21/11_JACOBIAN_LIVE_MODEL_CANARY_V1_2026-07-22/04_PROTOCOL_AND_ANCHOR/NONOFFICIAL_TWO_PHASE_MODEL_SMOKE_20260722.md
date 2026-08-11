# Non-official two-phase CUDA/Pythia preflight — 2026-07-22

Captured locally at 2026-07-22T09:12:09.3572871-07:00 against the dedicated
research RunPod tto1s8rgz3ixvg (NVIDIA A40). This was a disposable engineering
preflight. It is not the anchored 1,248-call canary and creates no scientific,
semantic, prompt-injection, output-control, universality, or 300B claim.

Controlling labels:

- execution_mode: NONCLAIM_PREFLIGHT
- verdict: NONE
- claim_status: NOT_LICENSED

The smoke used the exact local Pythia-160M snapshot revision
50f5173d932e8e61f858120bcb800b97af589f46 with weight SHA-256
29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270.
It installed phase one before Torch import, inherited it across execve, loaded
the exact ML stack, initialized one fixed CUDA tensor, matched the sole CUDA
UVM listener, installed the full phase-two filter with TSYNC before closing
that listener, proved post-guard CUDA operation, and only then loaded the model
and tokenized a prompt. A real gradient from an output logit to layer-6 hidden
state was finite.

The first two attempts failed closed and discovered two Linux representation
bugs before model loading:

1. getsockname returned the abstract phase-one listener name as exact bytes,
   not a string.
2. CUDA returned the UVM address as leading-and-trailing-NUL bytes, while
   /proc/net/unix renders those NULs as leading-and-trailing @ characters.

Both comparisons were corrected with exact equality/framing checks and direct
regression tests. The successful observation was:

    {"claim_status":"NOT_LICENSED","execution_mode":"NONCLAIM_PREFLIGHT","gpu_name":"NVIDIA A40","gradient_sha256":"6366fe75d6dd0127466a537815e4e07d3ceefef74a5aba2f1a664825e40d93f3","gradient_shape":[1,4,768],"guard_schema_version":"cas_harness_research_shadow.jacobian_lens_seccomp_network_guard.v2","hidden_shape":[1,4,768],"phase_one_filter_count":2,"phase_two_all_thread_count":66,"phase_two_filter_count":3,"post_guard_cuda_proof_sha256":"688dbc0f5663deb25069c702e308b570f65ce3016ab4f189e0b21f01089d1197","socket_fd_count_after":0,"verdict":"NONE"}

Interpretation: this closes the narrow compatibility question of whether the
two-phase guard can retain CUDA and real Pythia hidden-state autograd after
full isolation on this A40 runtime. It does not replace the anchored protocol,
the exact 1,248-call run, numerical acceptance gates, or independent receiver.
