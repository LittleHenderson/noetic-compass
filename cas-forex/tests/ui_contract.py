"""Location-independent assertions about the UI source.

Most UI assertions in this suite are written as "this exact string appears in
this exact file":

    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text()
    assert "<SecurityPosturePanel />" in settings_page
    assert "function SecurityPosturePanel()" in settings_page

That couples the test to where the code lives rather than to what the app does.
SettingsPage.tsx is 6,501 lines and is scheduled to be split into per-concern
sub-pages; every assertion of the shape above breaks on that split even though
the panel still exists and still renders. A test that fails when nothing broke
trains people to edit tests instead of reading them.

The invariant these assertions were reaching for is real and worth keeping:
*this panel is defined somewhere, and something renders it*. The helpers here
express that against the whole of ui/src, so a refactor that moves a panel
between files is silent while deleting or orphaning one still fails.

Scope note: this is still text matching, not behaviour. It cannot tell you the
panel renders correctly, only that it is wired in. Prefer an API-contract test
when the thing under test is data, and keep these for structural wiring.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UI_SRC = REPO_ROOT / "ui" / "src"

_SOURCE_SUFFIXES = {".ts", ".tsx", ".css"}


@lru_cache(maxsize=1)
def ui_sources() -> dict[str, str]:
    """Every UI source file, keyed by path relative to ui/src."""
    out: dict[str, str] = {}
    for path in sorted(UI_SRC.rglob("*")):
        if path.suffix not in _SOURCE_SUFFIXES or not path.is_file():
            continue
        out[path.relative_to(UI_SRC).as_posix()] = path.read_text(encoding="utf-8")
    return out


@lru_cache(maxsize=1)
def ui_source_text() -> str:
    """All UI source concatenated. Use for "appears anywhere" checks."""
    return "\n".join(ui_sources().values())


def files_containing(needle: str) -> list[str]:
    return [name for name, text in ui_sources().items() if needle in text]


def assert_panel_wired(panel: str) -> None:
    """The panel is defined somewhere in ui/src and something renders it.

    Accepts any definition style (function declaration, const arrow component)
    and any render form (self-closing or with props/children), so neither a
    reformat nor a move between files can fail this.
    """
    sources = ui_sources()
    defined = [
        name for name, text in sources.items()
        if re.search(rf"(function\s+{panel}\s*\(|const\s+{panel}\s*[:=])", text)
    ]
    assert defined, f"{panel} is not defined anywhere under ui/src"

    rendered = [
        name for name, text in sources.items()
        if re.search(rf"<{panel}[\s/>]", text)
    ]
    assert rendered, (
        f"{panel} is defined in {defined} but nothing renders it - "
        "it is orphaned and unreachable in the app"
    )


def assert_ui_contains(needle: str, *, why: str = "") -> None:
    """`needle` appears somewhere in the UI source."""
    if needle in ui_source_text():
        return
    raise AssertionError(f"{needle!r} appears nowhere under ui/src" + (f" - {why}" if why else ""))


def assert_ui_omits(needle: str, *, why: str = "") -> None:
    """`needle` appears nowhere in the UI source.

    This is the shape worth keeping most: a claim the product must never make.
    Checking the whole tree is strictly stronger than checking one file, since
    a forbidden string cannot be smuggled in by moving it elsewhere.
    """
    hits = files_containing(needle)
    if not hits:
        return
    raise AssertionError(
        f"{needle!r} must not appear in the UI, found in: {hits}" + (f" - {why}" if why else "")
    )
