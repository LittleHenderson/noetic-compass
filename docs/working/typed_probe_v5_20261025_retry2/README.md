# Typed-Probe v5 Stage S execution kit

This directory contains the AWS runner and the external shutdown watchdog for the frozen v5 Stage S screen. The runner must execute on the approved us-west-2 g5.2xlarge. It has no CPU fallback and does not print reply text or the Anthropic key.

The runner uses the frozen 120-row prompt bank, Qwen revision 989aa7980e4cf806f80c7fef2b1adb7bc71aa306, Mistral revision c170c708c41dac9275d15a8fff4eca08d52bab71, Claude Sonnet 5.5, Claude Haiku 5.5, the frozen rubric, 16 samples per prompt, and the preregistered seed rule. It counts every Claude request before batch submission, stops above 1,900 input tokens, uses no judge retries, and enforces an 80-minute in-instance runtime guard. The independent EventBridge Scheduler watchdog will terminate only the instance with the exact run-id tag.

Do not run model inference or GPU tests on the laptop. The small calibration checker is for later use only after Wakil labels all 30 examples; it compares exact four-way labels and Stage C requires at least 24/30.

The runner writes raw output only to the private S3 evidence prefix and temporary AWS instance disk. It writes counts and hashes to logs, never reply text. The human calibration file omits all panel labels. Keep its answer key private until the owner submits labels.
