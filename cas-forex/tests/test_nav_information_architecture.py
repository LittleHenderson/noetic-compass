"""Navigation IA contract: the grouped nav must be a complete partition.

23 flat destinations became 7 groups plus a legal footer. The danger in a
grouped IA is silent unreachability - a page that exists but appears in no
group and no footer has no path to it except a typed URL. These tests make the
partition property load-bearing: every page is reachable in exactly one place,
and the router uses real history entries so the back button works.
"""

from __future__ import annotations

import json
import re

from ui_contract import ui_sources


def _page_config() -> str:
    return ui_sources()["pageConfig.ts"]


def _ids(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text)


def test_nav_groups_and_footer_partition_every_page():
    text = _page_config()
    all_pages = set(_ids(r'\{ id: "([\w-]+)", label: "[^"]+", ready:', text))
    assert len(all_pages) == 23, f"page registry changed size: {sorted(all_pages)}"

    groups_block = text[text.index("NAV_GROUPS") : text.index("FOOTER_PAGES")]
    grouped = _ids(r'\{ id: "([\w-]+)", label: "[^"]+" \}', groups_block)
    footer_block = text[text.index("FOOTER_PAGES") :]
    footer = _ids(r'\{ id: "([\w-]+)", label: "[^"]+" \}', footer_block)

    # exactly one placement per page: no duplicates within or across the two
    assert len(grouped) == len(set(grouped)), "a page appears in two nav groups"
    assert len(footer) == len(set(footer)), "a page appears twice in the footer"
    overlap = set(grouped) & set(footer)
    assert not overlap, f"pages both grouped and in footer: {sorted(overlap)}"

    placed = set(grouped) | set(footer)
    unreachable = all_pages - placed
    assert not unreachable, f"pages with no navigation path: {sorted(unreachable)}"
    phantom = placed - all_pages
    assert not phantom, f"nav references unknown pages: {sorted(phantom)}"


def test_legal_pages_live_in_the_footer_not_the_nav():
    text = _page_config()
    footer_block = text[text.index("FOOTER_PAGES") :]
    footer = set(_ids(r'\{ id: "([\w-]+)", label: "[^"]+" \}', footer_block))
    assert footer == {"risk", "terms", "privacy"}


def test_router_uses_real_history_entries():
    app = ui_sources()["App.tsx"]
    assert "pushState" in app, "navigation must create history entries"
    assert "popstate" in app, "back/forward must re-render the routed page"
    # The old replaceState-only pattern (dead back button) must not return for
    # in-app navigation. One replaceState remains legal for the pairing-token
    # scrub in ownerAuthApi; App.tsx itself must not use it for page changes.
    set_page_block = app[app.index("const setPage") : app.index("useEffect")]
    assert "replaceState" not in set_page_block


def test_shell_renders_groups_subnav_and_footer():
    shell = ui_sources()["components/Shell.tsx"]
    for marker in ("NAV_GROUPS", "shell-subnav", "shell-footer", "FOOTER_PAGES"):
        assert marker in shell, f"Shell lost its {marker}"
    # The overflow/zoom-advisory machinery must stay dead.
    for gone in ("ResizeObserver", "layoutAdvisory", "visualViewport"):
        assert gone not in shell, f"the retired nav machinery returned: {gone}"
