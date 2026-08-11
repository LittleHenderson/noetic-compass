"""Static UI layout and zoom contract checks for CAS Forex.

The contract catches the layout regressions that made owner controls hard to
reach under enlarged browser zoom: nav overflow, fixed panels clipped by the
viewport, missing page routes, and CSS patterns that commonly create horizontal
overflow. It is read-only and does not use a browser or broker connection.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_ui_layout_zoom_contract"
CLAIM_BOUNDARY = (
    "UI layout contract is a read-only static source check for navigation, "
    "dropdown, viewport, wrapping, and zoom-resilience evidence. It does not "
    "render pages, place orders, close positions, move money, change settings, "
    "authorize live trading, or promise returns."
)


@dataclass(frozen=True)
class UILayoutCheck:
    check_id: str
    status: str
    detail: str
    evidence: tuple[str, ...] = ()
    next_action: str = ""


@dataclass(frozen=True)
class UILayoutContractReport:
    report_kind: str
    status: str
    ok_count: int
    attention_count: int
    check_count: int
    checks: tuple[UILayoutCheck, ...]
    route_count: int
    missing_page_routes: tuple[str, ...]
    css_zoom_violations: tuple[str, ...]
    top_attention_items: tuple[str, ...]
    claim_boundary: str


def build_ui_layout_contract(root: Path | str | None = None) -> dict[str, Any]:
    """Return the static layout/zoom readiness contract as plain JSON data."""
    base = Path(root) if root is not None else REPO_ROOT
    checks = tuple(_build_checks(base))
    ok_count = sum(1 for check in checks if check.status == "OK")
    attention = tuple(check for check in checks if check.status != "OK")
    page_ids, routed_ids = _route_ids(base)
    css_violations = tuple(_css_zoom_violations(base))
    report = UILayoutContractReport(
        report_kind=REPORT_KIND,
        status="OK" if not attention else "ATTENTION",
        ok_count=ok_count,
        attention_count=len(attention),
        check_count=len(checks),
        checks=checks,
        route_count=len(page_ids),
        missing_page_routes=tuple(sorted(page_ids - routed_ids)),
        css_zoom_violations=css_violations,
        top_attention_items=tuple(
            check.next_action or check.detail for check in attention
        )[:8],
        claim_boundary=CLAIM_BOUNDARY,
    )
    return _report_to_dict(report)


def ui_registered_page_ids(root: Path | str | None = None) -> tuple[str, ...]:
    """Return page ids registered in the owner-facing nav config."""
    base = Path(root) if root is not None else REPO_ROOT
    page_ids, _ = _route_ids(base)
    return tuple(sorted(page_ids))


def _build_checks(base: Path) -> Iterable[UILayoutCheck]:
    page_ids, routed_ids = _route_ids(base)
    missing_routes = tuple(sorted(page_ids - routed_ids))
    yield _check(
        "registered_pages_have_routes",
        ok=not missing_routes and len(page_ids) >= 20,
        detail=(
            f"{len(page_ids)} nav page(s) have lazy route coverage."
            if not missing_routes
            else f"Missing route(s): {', '.join(missing_routes)}"
        ),
        evidence=("ui/src/pageConfig.ts", "ui/src/App.tsx"),
        next_action="Wire every NAV_ITEMS entry to PAGE_COMPONENTS so zoom-hidden pages are not mistaken for missing pages.",
    )

    index_html = _read(base, "ui/index.html")
    index_css = _read(base, "ui/src/index.css")
    yield _check(
        "global_viewport_box_model",
        ok=all(
            needle in index_html or needle in index_css
            for needle in (
                'name="viewport"',
                "box-sizing: border-box",
                "overflow-x: hidden",
            )
        ),
        detail="Viewport meta, border-box sizing, and horizontal overflow clamp are present.",
        evidence=("ui/index.html", "ui/src/index.css"),
        next_action="Keep global box sizing and horizontal overflow handling in the base stylesheet.",
    )

    app_css = _read(base, "ui/src/App.css")
    yield _check(
        "shell_main_width_contract",
        ok=_block_has(
            app_css,
            ".shell-main",
            ("width: 100%", "max-width: 1280px", "min-width: 0", "box-sizing: border-box"),
        )
        and _block_has(app_css, ".app-shell", ("min-width: 0",)),
        detail="Shell and main content have bounded width and min-width zero for zoomed layouts.",
        evidence=("ui/src/App.css",),
        next_action="Add min-width: 0 and border-box constraints to app shell containers.",
    )

    shell_tsx = _read(base, "ui/src/components/Shell.tsx")
    yield _check(
        "shell_nav_zoom_collapse",
        ok=all(
            needle in shell_tsx or needle in app_css
            for needle in (
                "ResizeObserver",
                "requiredLinkWidth > inlineAvailableWidth",
                "navOverflowed",
                "shell-layout-advisory",
                ".shell-nav.overflowed",
                ".shell-nav-links.open",
                "@media (max-width: 860px)",
            )
        ),
        detail="Navigation measures available width, collapses when zoomed, exposes a wrapping drawer, and warns when desktop layout drops into compact mode.",
        evidence=("ui/src/components/Shell.tsx", "ui/src/App.css"),
        next_action="Keep the measured nav collapse path covered; fixed breakpoint-only nav is not enough at browser zoom.",
    )

    operator_tsx = _read(base, "ui/src/components/OperatorBadge.tsx")
    operator_css = _read(base, "ui/src/components/OperatorBadge.css")
    yield _check(
        "operator_dropdown_viewport_guard",
        ok=all(
            needle in operator_tsx or needle in operator_css
            for needle in (
                "createPortal",
                "useLayoutEffect",
                "getBoundingClientRect",
                "viewportWidth",
                "panelWidth",
                'addEventListener("resize"',
                'addEventListener("scroll"',
                "position: fixed",
                "z-index: 5000",
                "calc(100vw - 16px)",
                "calc(100vh - var(--operator-panel-top",
                "overflow-y: auto",
            )
        ),
        detail="Operator dropdown is portaled, fixed, viewport-clamped, scroll-aware, and internally scrollable.",
        evidence=("ui/src/components/OperatorBadge.tsx", "ui/src/components/OperatorBadge.css"),
        next_action="Keep operator panels portaled and viewport-clamped so header stacking cannot block the dropdown.",
    )

    yield _check(
        "operator_chat_opens_at_composer",
        ok=all(
            needle in operator_tsx or needle in operator_css
            for needle in (
                "panelRef",
                "panelTitleRef",
                "chatRef",
                "panel.scrollTop",
                "chat.offsetTop",
                'aria-label="AI Operator controls and chat"',
                'aria-label="Message to the AI operator"',
                "position: sticky",
            )
        ),
        detail="Operator opens at the chat composer while its identity header remains visible above the scrollable evidence report.",
        evidence=("ui/src/components/OperatorBadge.tsx", "ui/src/components/OperatorBadge.css"),
        next_action="Keep the Operator composer immediately visible on open; do not bury it below the evidence/status report.",
    )

    yield _check(
        "data_tables_scroll_instead_of_break_layout",
        ok=".positions-table-wrap" in app_css
        and ".leads-table-wrap" in app_css
        and "overflow-x: auto" in app_css,
        detail="Wide trading/account tables use horizontal scroll wrappers.",
        evidence=("ui/src/App.css",),
        next_action="Wrap any new wide ledger or trading table in the shared scroll wrapper.",
    )

    violations = tuple(_css_zoom_violations(base))
    yield _check(
        "no_viewport_scaled_type_or_negative_tracking",
        ok=not violations,
        detail=(
            "CSS avoids viewport-scaled font sizes and negative letter-spacing."
            if not violations
            else f"Zoom-sensitive CSS found: {', '.join(violations[:5])}"
        ),
        evidence=("ui/src/**/*.css",),
        next_action="Remove viewport-scaled type and negative letter-spacing from app CSS.",
    )

    yield _check(
        "headless_browser_screenshot_runner_available",
        ok=(base / "cas_forex" / "ui_browser_zoom_smoke.py").exists()
        and (base / "scripts" / "run_ui_browser_zoom_smoke.py").exists(),
        detail="Headless Chrome/Edge screenshot smoke runner is available for desktop, zoomed, and phone viewports.",
        evidence=("cas_forex/ui_browser_zoom_smoke.py", "scripts/run_ui_browser_zoom_smoke.py"),
        next_action="Add and run the browser screenshot smoke runner after UI build.",
    )

    yield _check(
        "visual_baseline_diff_runner_available",
        ok=(base / "cas_forex" / "ui_visual_baseline.py").exists()
        and (base / "scripts" / "run_ui_visual_baseline.py").exists()
        and (base / "ui" / "visual_baselines" / "README.md").exists(),
        detail="Visual baseline diff runner and refresh workflow are available for screenshot drift review.",
        evidence=(
            "cas_forex/ui_visual_baseline.py",
            "scripts/run_ui_visual_baseline.py",
            "ui/visual_baselines/README.md",
        ),
        next_action="Add the visual baseline diff runner and documented refresh workflow.",
    )


def _check(
    check_id: str,
    *,
    ok: bool,
    detail: str,
    evidence: Iterable[str] = (),
    next_action: str = "",
) -> UILayoutCheck:
    return UILayoutCheck(
        check_id=check_id,
        status="OK" if ok else "ATTENTION",
        detail=detail,
        evidence=tuple(evidence),
        next_action="" if ok else next_action,
    )


def _route_ids(base: Path) -> tuple[set[str], set[str]]:
    page_config = _read(base, "ui/src/pageConfig.ts")
    app_tsx = _read(base, "ui/src/App.tsx")
    page_ids = set(re.findall(r'id:\s*"([^"]+)"', page_config))
    routed_ids: set[str] = set()
    match = re.search(
        r"const\s+PAGE_COMPONENTS\s*:\s*Record<Page,\s*LazyExoticComponent<RoutedPage>>\s*=\s*\{(?P<body>.*?)\n\};",
        app_tsx,
        re.S,
    )
    body = match.group("body") if match else ""
    for line in body.splitlines():
        key_match = re.match(r'\s*(?:"([^"]+)"|([A-Za-z_][\w-]*))\s*:', line)
        if key_match:
            routed_ids.add(key_match.group(1) or key_match.group(2))
    return page_ids, routed_ids


def _css_zoom_violations(base: Path) -> list[str]:
    violations: list[str] = []
    css_paths = sorted((base / "ui" / "src").glob("**/*.css"))
    viewport_font = re.compile(r"font-size\s*:[^;]*(?:vw|vmin|vmax)", re.I)
    negative_tracking = re.compile(r"letter-spacing\s*:\s*-\d", re.I)
    for path in css_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(base).as_posix()
        if viewport_font.search(text):
            violations.append(f"{rel}: viewport-scaled font-size")
        if negative_tracking.search(text):
            violations.append(f"{rel}: negative letter-spacing")
    return violations


def _block_has(text: str, selector: str, needles: Iterable[str]) -> bool:
    block = _css_block(text, selector)
    return bool(block) and all(needle in block for needle in needles)


def _css_block(text: str, selector: str) -> str:
    escaped = re.escape(selector)
    match = re.search(escaped + r"\s*\{(?P<body>.*?)\}", text, re.S)
    return match.group("body") if match else ""


def _read(base: Path, rel_path: str) -> str:
    path = base / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _report_to_dict(report: UILayoutContractReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["checks"] = [asdict(check) for check in report.checks]
    for check in payload["checks"]:
        check["evidence"] = list(check.get("evidence") or [])
    payload["missing_page_routes"] = list(report.missing_page_routes)
    payload["css_zoom_violations"] = list(report.css_zoom_violations)
    payload["top_attention_items"] = list(report.top_attention_items)
    return payload
