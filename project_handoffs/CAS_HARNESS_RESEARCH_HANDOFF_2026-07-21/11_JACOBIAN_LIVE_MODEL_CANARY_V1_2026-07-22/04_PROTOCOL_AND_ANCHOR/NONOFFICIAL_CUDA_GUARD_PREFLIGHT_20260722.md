# Nonofficial A40 CUDA / seccomp preflight

Date: 2026-07-22 PDT

Status: `PREFLIGHT_ONLY / NOT_THE_OFFICIAL_CANARY / NOT_LICENSED`

Research pod: `tto1s8rgz3ixvg`  
GPU: `NVIDIA A40`  
libseccomp SHA-256:
`d60148325d84cab666b226676c5009a61eea24f3902598829fe714da87ef3587`

## Finding

Installing the full socket/io_uring/pidfd seccomp guard before CUDA
initialization caused `cudaGetDeviceCount()` to fail with CUDA error 304:
`OS call failed or operation not supported on this OS`.

An unguarded diagnostic showed that CUDA initialization creates and retains
one AF_UNIX `SOCK_SEQPACKET` descriptor bound to an abstract path of the form:

`@cuda-uvmfd-<namespace-id>-<process-id>@`

The provider container also has listening network sockets owned by other
processes, but they were not inherited by the diagnostic process.

## Narrow successful diagnostic

The following order succeeded:

1. Import the pinned PyTorch environment and initialize CUDA with a one-element
   tensor before loading any model or frozen prompt/token input.
2. Verify that the process owns exactly one socket descriptor and that it is
   the expected CUDA UVM abstract socket.
3. Close that descriptor.
4. Install the unchanged full seccomp policy.
5. Re-run all eight guard self-tests; every prohibited operation returned
   `EPERM`.
6. Perform and synchronize a second CUDA tensor computation.

The post-guard computation succeeded on `NVIDIA A40` and returned the expected
sum `357389824.0` for the diagnostic tensor.

The installed guard observation reported:

- `no_new_privs=true`;
- seccomp mode `2`;
- filter count increase `1`;
- inherited socket count `0`;
- inherited io_uring count `0`;
- AF_INET, AF_INET6, AF_UNIX, socketpair, all three io_uring operations, and
  `pidfd_getfd` returning `EPERM`.

## Required implementation correction

The official launcher cannot install the guard and then `execve` a fresh
Python runner, because `execve` discards the initialized CUDA context and the
fresh process must repeat the blocked CUDA initialization. The corrected
launcher must sanitize its environment, initialize CUDA before any model or
input load, strictly identify and close only the expected CUDA UVM socket,
install the full guard, and enter the pinned bootstrap in the same isolated
process. The receipt must disclose this pre-guard CUDA-bootstrap boundary.

This preflight does not establish the 1,248-call canary result, J-Space
validity, CAS-Ohm utility, prompt-injection detection, output control,
universality, cross-architecture transfer, or 300B execution.
