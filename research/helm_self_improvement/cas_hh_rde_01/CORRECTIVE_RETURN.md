# Corrective passive validation: test-helper failure, no model execution

Job **helm-hh-rde-parity-20260929-a2**, instance **i-0df68da5f2cb9ab74**, executing source **ae2482fc93bc562c855037e90273da794a33b1f9**.

The original native-PCBA fixture passes without checker changes. AWS recorded Pydantic **2.12.5**, pydantic-core **2.41.5**, pytest **9.0.2**, and all **44** exact dependency pins.

| Contract group | Executed | Passed | Failed | Errors/skips |
|---|---:|---:|---:|---:|
| Codex observation and producer-to-converter |21|21|0|0|
| Claude configuration/readout |24|23|1|0|
| Claude synthetic intervention contracts |17|17|0|0|
| Total |62|61|1|0|

Actual collection was also62. The failure is test_hh05_capture_refuses_relabeled_coordinate_meaning_nonfinite_values_and_wrong_counts. Its helper indexes SITE_SEMANTICS['mlp.layer3'] and throws KeyError at line28, called from line82, before raw_capture can return SITE_UNKNOWN. The smallest source-only fix is to supply an explicit meaning on that unknown-site call. [Claude owns that exclusive test-file correction](https://github.com/LittleHenderson/noetic-compass/pull/245#issuecomment-5881938722); it is **NOT_RUN**.

**Real HELM forwards: 0. Optimizer updates: 0. Real site coverage, neutral scores/answers/state and fresh-process reload: NOT_RUN.** The dependent stage stopped. All three current Codex producer-to-converter/refusal cases passed using actual Capture.emit, host retention and anchored conversion; this does not establish real-model capture.

Scientific source: **c45f775f225dd06cc20cdf313f0a0398486e0d61**. Parent: **5b37699d52e530a9ecd3563e235f0884630225da2fbe27489767a196c0f7a109**. Freeze: **cfb2c8bc4a0f370570d09aff1422f2e5057aac5bc3f235f05b7b7ba988d348a5**.

**Cleanup independently verified:** instance terminated; owned volume, network interface, security group, shutdown schedule, profile and both roles absent. All **58/58** receiver artifacts match. Original termination-confirmation timeout and cleanup_complete=false preserved; separate recovery/final closeout record the newer result. Private archive retained: **6 objects, 9,491,794 bytes**. Production resources unchanged.

**Costs:** both original and corrective **USD2 reservations retained**, inside the unchanged **USD12** allocation2/2/4/2/2. Compute upper estimate through confirmed termination **USD0.433234** at USD2.52/hour; actual billing unavailable. The earlier operator-only estimate stops before provider termination. Frozen all-services forecast maximum **USD1.76**, including **USD0.50** other-services allowance, is not an invoice. Protected cleanup remains **USD2**; no other campaign funds used; retained storage continues.

DeepSeek reviewed ae2482fc in report deepseek-cas-hh-rde-corrective-successor-20260929-14. Its three packaging conditions were reconciled before admission. Actual AWS imports now establish the dependency result. D-RDE-10 was closed as a pinned Parts-slot source fact. Same-operator external anchors and the shared OBSERVE_ONLY/NO_OP_CONTROL path remain limitations.

Next eligible action: Claude's narrow source correction. **Both initial model-job slots are consumed; no third paid job or automatic retry is authorized.**

Post-run source disposition: Claude returned the exact helper correction at **b054dee4352fbbad5a35d2eead033365b0635fd9**, acknowledged in [comment5881954949](https://github.com/LittleHenderson/noetic-compass/pull/245#issuecomment-5881954949). Codex integrated only that call correction and its comment; the 21+24+17 inventory remains unchanged by static inspection. **Correction NOT_RUN.** The executed61-pass/1-failure result and frozen payload remain unchanged. No third job or rerun was launched.
