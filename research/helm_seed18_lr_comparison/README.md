# Seed18 LR-only fixed comparison v2

Source package is implemented. No tests or model execution ran locally; AWS acceptance and per-condition admission remain open. This package never launches automatically.

Two separately identified children start from clean seed18 parent SHA256 5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341 at update2940. Baseline stays LR0.003; the changed arm uses constant LR0.001. Each ends at5880 with readouts2940/4410/5880. No growth, CAS, selection threshold or automatic extension.

The loader first authenticates the complete original parent. Adoption preserves its object graph. A versioned LR policy changes only the existing optimizer group's LR and matching config metadata; an optimizer-state identity check requires every other field equal. Cumulative counters and elapsed parent history remain recorded. The schedule digest enters the new plan and run identity. Every scientific file, scoring path, parent and previous experiment stays unchanged.

Next acceptance commands, only inside separately admitted AWS worker:

    python -B -m pytest -q -p no:cacheprovider --junitxml=<out>/focused.xml research/helm_seed18_lr_comparison/test_continuation.py
    python -B -m helm_seed18_lr_comparison.worker --root /opt/cas-graph6curr/package --parent <copied-seed18-parent> --plan <fresh-admitted-baseline-child-plan.json> --out <fresh-out>/baseline-proof --mode proof
    python -B -m helm_seed18_lr_comparison.worker --root /opt/cas-graph6curr/package --parent <separate-identical-seed18-parent-copy> --plan <fresh-admitted-lr001-child-plan.json> --out <fresh-out>/lr001-proof --mode proof

The worker requires Linux and HELM_SEED18_LR_VENUE=ADMITTED_AWS, the original source manifest and venue root. The focused tests additionally need SEED18_LR_PARENT_METADATA and SEED18_LR_LEGACY_ROOT from that admitted package. These checks are venue guards, not authorization; only the sole Codex runner may bind them to actual ledger and source receipts.

The frozen-model/CAS interface at facba18 is separate and is not imported by this LR package.
