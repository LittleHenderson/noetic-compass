"""Provenance renderer contract: values cannot render without a trust label.

The canonical Metric (ui/src/components/Metric.tsx) REQUIRES a provenance prop
- live / cached / unproven - so an unlabelled value is a TypeScript compile
error, not a review comment. These tests pin that contract and ratchet the
legacy per-file Metric copies downward: each page the nav rebuild touches must
adopt the canonical component, and a new local copy anywhere fails the suite.
"""

from __future__ import annotations

import re

from ui_contract import ui_sources

# The per-file Metric copies that predate the canonical component. Files may
# ONLY leave this list (adopting components/Metric.tsx); additions fail.
LEGACY_METRIC_COPIES = {
    "components/DashboardEvidencePanels.tsx",
    "components/DashboardOperationsWorkbench.tsx",
    "components/DashboardSweepOpsPanel.tsx",
    "components/LiveOperabilityPanel.tsx",
    "components/LiveReadinessSummaryPanel.tsx",
    "components/ProofControlPanel.tsx",
    "pages/AdaptivePage.tsx",
    "pages/HistoryPage.tsx",
    "pages/LedgerPage.tsx",
    "pages/OptimizerPage.tsx",
    "pages/PcbaPage.tsx",
    "pages/ProofPage.tsx",
}

_LOCAL_METRIC_DEF = re.compile(r"^function Metric\(", re.M)


def _files_with_local_metric() -> set[str]:
    return {
        name
        for name, text in ui_sources().items()
        if name != "components/Metric.tsx" and _LOCAL_METRIC_DEF.search(text)
    }


def test_canonical_metric_requires_provenance():
    source = ui_sources()["components/Metric.tsx"]
    # The prop must be REQUIRED (no `?`) and typed to the closed union.
    assert re.search(r"^\s*provenance: MetricProvenance;", source, re.M), (
        "provenance must be a required prop - making it optional reopens the "
        "unlabelled-value path this component exists to close"
    )
    assert '"live" | "cached" | "unproven"' in source
    # Both non-live states must render a visible tag.
    assert "metric-tag-cached" in source
    assert "metric-tag-unproven" in source


def test_local_metric_copies_only_ratchet_down():
    current = _files_with_local_metric()
    new_copies = current - LEGACY_METRIC_COPIES
    assert not new_copies, (
        f"new local Metric definitions are forbidden - use components/Metric.tsx: {sorted(new_copies)}"
    )
    # Files that migrated should be removed from LEGACY_METRIC_COPIES so the
    # ratchet keeps tightening (stale entries hide regressions).
    stale = LEGACY_METRIC_COPIES - current
    assert not stale, (
        f"update LEGACY_METRIC_COPIES - these files no longer define a local Metric: {sorted(stale)}"
    )


def test_dashboard_first_paint_surfaces_use_canonical_metric():
    sources = ui_sources()
    for name in ("pages/DashboardPage.tsx", "components/DashboardInstantShell.tsx"):
        text = sources[name]
        assert 'from "../components/Metric"' in text or 'from "./Metric"' in text, (
            f"{name} must import the canonical Metric"
        )
        assert not _LOCAL_METRIC_DEF.search(text), f"{name} must not define a local Metric"
        # Every call site carries provenance (single- or multi-line JSX).
        for match in re.finditer(r"<Metric\b(?P<attrs>[^>]*)>", text, re.S):
            assert "provenance=" in match.group("attrs"), (
                f"unlabelled <Metric> in {name}: {match.group(0)[:80]}"
            )


def test_dashboard_fallback_panels_are_marked_unproven():
    """The fallback panels render hardcoded strings ('OWNER GATED', targets)
    before any data arrives - the exact overclaim this work exists to stop.
    They must declare provenance="unproven", never live."""
    text = ui_sources()["pages/DashboardPage.tsx"]
    for fallback in (
        "OperatorBriefingCardFallback",
        "ObjectiveSupportCardsFallback",
        "DashboardDeferredSectionsNotice",
    ):
        match = re.search(rf"function {fallback}\(\).*?(?=\nfunction |\Z)", text, re.S)
        assert match, f"{fallback} not found"
        body = match.group(0)
        metrics = re.findall(r"<Metric\b[^>]*>", body, re.S)
        assert metrics, f"{fallback} renders no Metric rows?"
        for site in metrics:
            assert 'provenance="unproven"' in site, (
                f"{fallback} renders a value not marked unproven: {site[:90]}"
            )
