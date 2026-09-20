"""Explicit command line; importing this module performs no work."""
import argparse
from .runtime import run


def main(argv=None):
    parser = argparse.ArgumentParser(description='Evaluate existing sealed v6 choices; never train or regenerate.')
    for flag in ('admission','admission-sha256','recovery-manifest','recovery-manifest-sha256',
                 'gpu-gate','gpu-gate-sha256','inputs','packet','output','job'):
        parser.add_argument('--'+flag,required=True)
    parser.add_argument('--max-seconds',type=int,default=2400)
    parser.add_argument('--enable-native-evaluation',action='store_true')
    args = parser.parse_args(argv)
    run(admission_path=args.admission,admission_sha256=args.admission_sha256,
        recovery_manifest_path=args.recovery_manifest,recovery_manifest_sha256=args.recovery_manifest_sha256,
        gpu_gate_path=args.gpu_gate,gpu_gate_sha256=args.gpu_gate_sha256,inputs=args.inputs,packet=args.packet,
        output=args.output,job=args.job,max_seconds=args.max_seconds,enabled=args.enable_native_evaluation)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
