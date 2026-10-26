# Typed-Probe v5 Transformers bootstrap fix candidate

**Status:** CANDIDATE ONLY; not uploaded, executed, or authorized for an AWS launch.

The Stage S attempt `typed-probe-v5-stage-s-capacity-retry2-20261025` stopped before the runner because the PyTorch interpreter at `/opt/pytorch/bin/python` did not have `transformers`. The separate system interpreter had no `torch`. The failed attempt's source and receipts remain unchanged in `typed_probe_v5_20261025_capacity_retry2/`.

This candidate fixes the package setup in the same interpreter that already contains PyTorch:

1. Use only `/opt/pytorch/bin/python`; do not switch to system Python.
2. Require PyTorch 2.2 or newer and pip in that environment.
3. Install the exact pin in `transformers-requirements.txt` with that interpreter if the package is absent, broken, or at another version. The install is limited to 240 seconds, uses binary wheels, and allows two pip retries.
4. Import PyTorch, Transformers, `AutoModelForCausalLM`, and `AutoTokenizer`; confirm the exact Transformers version and confirm PyTorch's version did not change.
5. Stop before retrieving the Anthropic key or starting model work if any check fails.

The pin follows the official Transformers v4.57.1 installation page, which documents Python 3.9+ and PyTorch 2.2+. The failed run's interpreter path shows Python 3.12, but its exact PyTorch version was not captured; the candidate checks that version at runtime. Sources: [Transformers v4.57.1 installation](https://huggingface.co/docs/transformers/v4.57.1/en/installation) and [v4.57.1 release](https://github.com/huggingface/transformers/releases/tag/v4.57.1).

The bootstrap script intentionally exits with code 90 before doing any work. It retains the consumed run ID and S3 prefix for comparison with the failed source. Do not remove that guard, execute it, or upload it. A future Stage S attempt needs a new dated owner authorization, a fresh run ID/prefix, and a new launch plan. The one-attempt approval is consumed; Stage C remains unauthorized.

This is only a source correction candidate. It has not been installed or exercised on AWS, so package import and model loading remain unverified in the actual AWS image. No local model or GPU work was run.
