"""Offline CAS compiler terminal.

Pure Python stdlib. No dashboard, server, database, network, or installs.
The goal is to mirror the online compiler's terminal workflow while adding
offline terminal diagrams plus standalone SVG/HTML exports.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import webbrowser
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
SOURCE_COMPILER_ROOT = ROOT.parent / "noetic-compass-scaffold" / "noetic-compass"
if not (ROOT / "api").exists() and SOURCE_COMPILER_ROOT.exists():
    sys.path.insert(0, str(SOURCE_COMPILER_ROOT))

from api.notation.compiler import CAS_GRAMMAR_BNF, compile_expression  # noqa: E402
from cas_svg import render_svg  # noqa: E402
from cas_terminal import (  # noqa: E402
    EXAMPLES,
    U,
    ansi,
    banner_text,
    compiler_shell_html,
    dictionary_text,
    example_by_index,
    examples_text,
    highlight_ansi,
    learning_text,
    palette_text,
    play_banner_wave,
    play_compiling_spinner,
    reference_text,
    set_color_enabled,
    startup_hint_text,
    terminal_diagram,
)


ALIASES = [
    (r"\bnotin\b", U["notin"]),
    (r"\bsubseteq\b", U["subseteq"]),
    (r"\bsubset\b", U["subset"]),
    (r"\bsupseteq\b", U["supseteq"]),
    (r"\bsupset\b", U["supset"]),
    (r"\bemptyset\b", U["empty"]),
    (r"\bin\b", U["in"]),
    (r"\bTheta\b", U["theta"]),
    (r"\bOmega(?=_|\b)", U["omega"]),
    (r"\bLambda(?=_|\b)", U["lambda"]),
    (r"\bkappa(?=_|\b)", U["kappa"]),
    (r"\biota(?=_|\b)", U["iota"]),
    (r"\beta\b", U["eta"]),
    (r"\bPhi\b", U["phi"]),
]


HELP = f"""\
Commands:
  :help          Show this message
  :grammar       Print the BNF grammar
  :examples      Show the same grouped examples as the online compiler
  :natural       Show examples in natural language
  :mirror        Show (CAS expression) natural-language mirror pairs
  :dict [TERM]   Show the CAS dictionary, optionally filtered
  :learn         Show the guided compiler learning path
  :example N     Compile example number N
  :demo          Compile every example and write demo SVG/HTML files
  :palette       Show hard-to-type CAS symbols
  :ref           Show Noetics, Domains, Drives, and Registers
  :history       Show command history
  :clear         Clear terminal output
  :diagram       Print the last diagram JSON
  :svg PATH      Save the last diagram as SVG
  :html PATH     Save the last diagram as standalone HTML
  :open          Open the last diagram in your default browser
  :preview       Alias for :open
  :json on/off   Toggle full JSON output
  :files on/off  Toggle automatic cas_diagram.svg/html writes
  :quit          Exit

Editing:
  Blank line     -> ; statement separator
  Single newline -> continuation
  Or write ; yourself at line ends.

ASCII aliases:
  in / notin / subset / subseteq / supset / supseteq / emptyset
  Theta / Omega / Lambda / kappa / iota / eta / Phi

Visual output:
  The terminal prints a compact diagram preview every time the compiler emits
  one. The full static visual is written to SVG/HTML offline.
  In the REPL you can append save flags directly:
    Product(Noetics, Domains) --svg product.svg --html product.html
"""


def expand(text: str) -> str:
    text = re.sub(r"\n[ \t]*\n+", "; ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    for pattern, replacement in ALIASES:
        text = re.sub(pattern, replacement, text)
    return text


def write_text(path: str | Path, text: str) -> Path:
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def render_outputs(
    artifact: Any,
    *,
    svg_path: str | Path | None = None,
    html_path: str | Path | None = None,
    title: str = "CAS Diagram",
) -> tuple[Path | None, Path | None]:
    diagram = artifact.diagram()
    if not diagram or (not diagram.get("nodes") and not diagram.get("containers")):
        return None, None
    result = artifact.to_dict().get("result")
    svg = render_svg(diagram, result=result, title=title)
    saved_svg = write_text(svg_path, svg) if svg_path else None
    if html_path:
        data = artifact.to_dict()
        data["diagram"] = diagram
        preview = terminal_diagram(diagram, result, title=title)
        html = compiler_shell_html(
            source=title,
            artifact_data=data,
            svg=svg,
            terminal_preview=preview,
            title="CAS Offline Compiler",
        )
        saved_html = write_text(html_path, html)
    else:
        saved_html = None
    return saved_svg, saved_html


def result_line(result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    kind = result.get("kind")
    if kind == "state":
        return f"{result.get('dominant_operator', '?')} in {result.get('dominant_domain', '?')} domain"
    if kind == "fractal":
        seq = ":".join(str(x) for x in result.get("sequence", []))
        return f"Fractal [{seq}] -> {result.get('composed_operator', '?')}"
    if kind == "rpm":
        completeness = result.get("completeness", 0)
        return f"{result.get('drive', '?')} prerequisite chain ({completeness:.0%})"
    if kind == "meta_assertion":
        mark = U["check"] if result.get("holds") is True else U["cross"] if result.get("holds") is False else "?"
        return f"{result.get('message', result.get('operator', 'assertion'))} {mark}"
    if kind == "meta_set":
        card = result.get("cardinality")
        return f"{result.get('name', 'set')} ({card} elements)" if isinstance(card, int) else str(result.get("name", "set"))
    if kind == "recipe":
        target = result.get("target", "?")
        count = len(result.get("prerequisites") or [])
        return f"Recipe -> {U['omega']}_{target} from {count} prerequisite(s)"
    if kind == "program":
        return "Multi-statement program"
    return json.dumps(result, ensure_ascii=False)[:160]


def summarize(
    artifact: Any,
    *,
    source: str,
    full_json: bool = False,
    show_terminal_diagram: bool = True,
) -> None:
    data = artifact.to_dict()
    if not artifact.valid:
        print(f"  {ansi('INVALID', 'red', bold=True)}: {artifact.error}")
        return

    print(
        f"  {ansi('valid', 'green', bold=True)} (engine={artifact.engine}, "
        f"tokens={len(artifact.tokens)}, bytecode={len(artifact.bytecode)})"
    )
    if data.get("type"):
        type_info = data["type"]
        singular = " singular" if type_info.get("singular") else ""
        print(f"  type: {ansi(type_info['kind'], 'violet')}{singular}")

    short = result_line(data.get("result"))
    if short:
        print(f"  meaning: {short}")

    diagram = artifact.diagram()
    if diagram and (diagram.get("nodes") or diagram.get("containers")):
        print(
            f"  diagram: layouts={diagram.get('layouts')} "
            f"nodes={len(diagram.get('nodes', []))} "
            f"edges={len(diagram.get('edges', []))} "
            f"containers={len(diagram.get('containers', []))}"
        )
        if show_terminal_diagram:
            print(terminal_diagram(diagram, data.get("result"), title=source))

    if full_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def compile_with_spinner(expanded: str) -> Any:
    """Run compile_expression(expanded) with a background "compiling" spinner.

    Spinner only renders after a short delay (handled inside
    play_compiling_spinner) so fast compiles do not flicker. Compile runs
    synchronously on the main thread; the spinner is a daemon thread that is
    signaled via threading.Event when the compile returns. On Ctrl+C the
    spinner is still stopped and its line cleared.
    """
    stop_event = threading.Event()
    spinner_thread = threading.Thread(
        target=play_compiling_spinner,
        args=(stop_event,),
        daemon=True,
    )
    spinner_thread.start()
    try:
        artifact = compile_expression(expanded)
    finally:
        stop_event.set()
        spinner_thread.join(timeout=1.0)
    return artifact


def compile_and_show(
    source: str,
    *,
    full_json: bool = False,
    show_terminal_diagram: bool = True,
    svg_path: str | Path | None = None,
    html_path: str | Path | None = None,
    auto_files: bool = False,
    echo_source: bool = True,
) -> tuple[Any, Path | None, Path | None]:
    expanded = expand(source.strip())
    if echo_source:
        print(f"{ansi('cas>', 'accent_light', bold=True)} {highlight_ansi(expanded)}")
    artifact = compile_with_spinner(expanded)
    summarize(
        artifact,
        source=expanded,
        full_json=full_json,
        show_terminal_diagram=show_terminal_diagram,
    )
    saved_svg = saved_html = None
    if artifact.valid:
        if auto_files:
            svg_path = svg_path or "cas_diagram.svg"
            html_path = html_path or "cas_diagram.html"
        saved_svg, saved_html = render_outputs(
            artifact,
            svg_path=svg_path,
            html_path=html_path,
            title=expanded,
        )
        if saved_svg:
            print(f"  svg: {saved_svg}")
        if saved_html:
            print(f"  html: {saved_html}")
    return artifact, saved_svg, saved_html


def parse_repl_inline_options(raw: str) -> tuple[str, dict[str, Any], list[str]]:
    """Parse one-shot-style save flags typed inside the REPL."""
    opts: dict[str, Any] = {
        "svg_path": None,
        "html_path": None,
        "auto_files": None,
        "full_json": None,
        "show_terminal_diagram": None,
        "color": None,
    }
    errors: list[str] = []
    text = raw

    def pull_path(flag: str, key: str) -> None:
        nonlocal text
        pattern = re.compile(rf"(^|\s){re.escape(flag)}\s+(\"[^\"]+\"|'[^']+'|\S+)")
        match = pattern.search(text)
        if not match:
            if re.search(rf"(^|\s){re.escape(flag)}(\s|$)", text):
                errors.append(f"{flag} requires a path")
            return
        opts[key] = match.group(2).strip("\"'")
        text = text[: match.start()] + " " + text[match.end() :]

    pull_path("--svg", "svg_path")
    pull_path("--html", "html_path")

    for flag, key, value in (
        ("--auto-files", "auto_files", True),
        ("--json", "full_json", True),
        ("--no-terminal-diagram", "show_terminal_diagram", False),
        ("--color", "color", True),
        ("--no-color", "color", False),
    ):
        pattern = re.compile(rf"(^|\s){re.escape(flag)}(?=\s|$)")
        if pattern.search(text):
            opts[key] = value
            text = pattern.sub(" ", text)

    expr = text.strip()
    if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
        expr = expr[1:-1].strip()
    return expr, opts, errors


def demo(output_dir: str | Path = "examples") -> int:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    print(f"Writing example diagrams to {out}")
    for i, example in enumerate(EXAMPLES, 1):
        source = expand(example["expr"])
        artifact = compile_expression(source)
        status = "valid" if artifact.valid else f"INVALID: {artifact.error}"
        print(f"{i:02d}. {example['label']}: {status}")
        if not artifact.valid:
            failures += 1
            continue
        stem = f"{i:02d}_{slug(example['label'])}"
        render_outputs(
            artifact,
            svg_path=out / f"{stem}.svg",
            html_path=out / f"{stem}.html",
            title=source,
        )
    print(f"done: {len(EXAMPLES) - failures} valid, {failures} invalid")
    return 1 if failures else 0


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "example"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# Cache paths used by the :open / :preview REPL commands.
# After every successful compile in the REPL we write the rendered diagram
# to these paths so :open always has something fresh to show. If the user
# explicitly saves via :svg PATH or :html PATH that path takes precedence.
CACHE_HTML_PATH = Path(tempfile.gettempdir()) / "cas_last_diagram.html"
CACHE_SVG_PATH = Path(tempfile.gettempdir()) / "cas_last_diagram.svg"

# Most-recent explicit path, set by :svg PATH or :html PATH. Preferred by :open.
_LAST_EXPLICIT_PATH: Path | None = None


def _cache_last_diagram(artifact: Any, title: str) -> Path | None:
    """Write the artifact's diagram to the OS-temp cache so :open can find it.

    Returns the cached HTML path on success, or None if the artifact has no
    renderable diagram. Failures (permission, disk full, etc.) are swallowed
    silently so they never disrupt the REPL flow.
    """
    try:
        diagram = artifact.diagram()
        if not diagram or (not diagram.get("nodes") and not diagram.get("containers")):
            return None
        return render_outputs(
            artifact,
            svg_path=CACHE_SVG_PATH,
            html_path=CACHE_HTML_PATH,
            title=title,
        )[1]
    except Exception:
        return None


def _open_last_diagram() -> bool:
    """Open the most recent diagram in the default browser.

    Preference order: explicit user-saved path (from :svg/:html) > cached HTML.
    Returns True if a diagram was opened, False if nothing was available.
    """
    candidate: Path | None = None
    if _LAST_EXPLICIT_PATH is not None and _LAST_EXPLICIT_PATH.exists():
        candidate = _LAST_EXPLICIT_PATH
    elif CACHE_HTML_PATH.exists():
        candidate = CACHE_HTML_PATH
    elif CACHE_SVG_PATH.exists():
        candidate = CACHE_SVG_PATH
    if candidate is None:
        return False
    url = "file://" + str(candidate.resolve()).replace("\\", "/")
    webbrowser.open(url)
    return True


def repl() -> int:
    global _LAST_EXPLICIT_PATH
    play_banner_wave()
    print(f"\n{startup_hint_text()}\n")
    last_artifact: Any | None = None
    last_source = "CAS Diagram"
    full_json = False
    auto_files = True
    history: list[str] = []

    while True:
        try:
            raw = input("cas> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue

        if raw in {":quit", ":q", "exit"}:
            return 0
        if raw == ":help":
            print(HELP)
            continue
        if raw == ":examples":
            print(examples_text())
            continue
        if raw == ":natural":
            print(examples_text("natural"))
            continue
        if raw == ":mirror":
            print(examples_text("mirror"))
            continue
        if raw == ":dict" or raw.startswith(":dict "):
            query = raw.split(maxsplit=1)[1] if " " in raw else ""
            print(dictionary_text(query))
            continue
        if raw == ":learn":
            print(learning_text())
            continue
        if raw.startswith(":example "):
            try:
                idx = int(raw.split(maxsplit=1)[1])
            except ValueError:
                print("  usage: :example N")
                continue
            expr = example_by_index(idx)
            if not expr:
                print(f"  example {idx} does not exist")
                continue
            print(f"{ansi('cas>', 'accent_light', bold=True)} {highlight_ansi(expr)}")
            history.insert(0, expr)
            last_artifact, _, _ = compile_and_show(
                expr,
                full_json=full_json,
                show_terminal_diagram=True,
                auto_files=auto_files,
                echo_source=False,
            )
            last_source = expand(expr)
            if last_artifact is not None and last_artifact.valid:
                _cache_last_diagram(last_artifact, last_source)
            continue
        if raw == ":demo":
            demo()
            continue
        if raw == ":palette":
            print(palette_text())
            continue
        if raw == ":ref":
            print(reference_text())
            continue
        if raw == ":history":
            if not history:
                print("  (empty)")
            else:
                for i, item in enumerate(history[:50], 1):
                    print(f"  {i:>2}. {item}")
            continue
        if raw == ":clear":
            clear_screen()
            print(banner_text())
            continue
        if raw == ":grammar":
            print(CAS_GRAMMAR_BNF)
            continue
        if raw == ":diagram":
            if last_artifact is None:
                print("  no previous diagram")
                continue
            print(json.dumps(last_artifact.diagram(), ensure_ascii=False, indent=2))
            continue
        if raw.startswith(":json"):
            full_json = raw.endswith("on")
            print(f"  json {'on' if full_json else 'off'}")
            continue
        if raw.startswith(":files"):
            auto_files = raw.endswith("on")
            print(f"  files {'on' if auto_files else 'off'}")
            continue
        if raw.startswith(":svg ") or raw.startswith(":html "):
            if last_artifact is None or not last_artifact.valid:
                print("  no valid previous diagram")
                continue
            cmd, path = raw.split(maxsplit=1)
            saved_svg, saved_html = render_outputs(
                last_artifact,
                svg_path=path if cmd == ":svg" else None,
                html_path=path if cmd == ":html" else None,
                title=last_source,
            )
            saved = saved_svg or saved_html
            if saved is not None:
                _LAST_EXPLICIT_PATH = Path(saved).resolve()
            print(f"  saved: {saved}")
            continue
        if raw in {":open", ":preview"}:
            if _open_last_diagram():
                target = _LAST_EXPLICIT_PATH if _LAST_EXPLICIT_PATH else CACHE_HTML_PATH
                print(f"  opening {target} in default browser")
            else:
                print("  (no diagram yet — compile something first)")
            continue

        expr, opts, errors = parse_repl_inline_options(raw)
        if errors:
            print("  " + "; ".join(errors))
            continue
        if opts["color"] is not None:
            set_color_enabled(opts["color"])
            print(f"  color {'on' if opts['color'] else 'off'}")
        if not expr:
            if last_artifact is None or not last_artifact.valid:
                print(
                    "  no valid previous diagram; enter an expression first or use: "
                    "Product(Noetics, Domains) --svg product.svg --html product.html"
                )
                continue
            saved_svg, saved_html = render_outputs(
                last_artifact,
                svg_path=opts["svg_path"],
                html_path=opts["html_path"],
                title=last_source,
            )
            if saved_svg or saved_html:
                print(f"  saved: {saved_svg or saved_html}")
            else:
                print("  no output path supplied; use --svg PATH and/or --html PATH")
            continue

        history.insert(0, expr)
        last_artifact, inline_svg, inline_html = compile_and_show(
            expr,
            full_json=opts["full_json"] if opts["full_json"] is not None else full_json,
            show_terminal_diagram=opts["show_terminal_diagram"] if opts["show_terminal_diagram"] is not None else True,
            svg_path=opts["svg_path"],
            html_path=opts["html_path"],
            auto_files=opts["auto_files"] if opts["auto_files"] is not None else auto_files,
            echo_source=False,
        )
        last_source = expand(expr)
        if last_artifact is not None and last_artifact.valid:
            _cache_last_diagram(last_artifact, last_source)
            # An inline --svg/--html save also counts as an explicit path for :open.
            explicit = inline_html or inline_svg
            if explicit is not None:
                _LAST_EXPLICIT_PATH = Path(explicit).resolve()


def compile_once(args: argparse.Namespace) -> int:
    if args.examples:
        print(examples_text())
        return 0
    if args.natural:
        print(examples_text("natural"))
        return 0
    if args.mirror:
        print(examples_text("mirror"))
        return 0
    if args.dictionary is not None:
        print(dictionary_text(args.dictionary))
        return 0
    if args.learn:
        print(learning_text())
        return 0
    if args.palette:
        print(palette_text())
        return 0
    if args.reference:
        print(reference_text())
        return 0
    if args.demo:
        return demo(args.demo_dir)
    if args.example is not None:
        expr = example_by_index(args.example)
        if not expr:
            print(f"example {args.example} does not exist")
            return 2
        source = expr
    else:
        source = " ".join(args.expression).strip()
    if not source:
        print("No expression supplied. Run without arguments for REPL mode.")
        return 2

    auto_files = args.auto_files or args.auto_svg or args.auto_html
    svg_path = args.svg
    html_path = args.html
    if args.auto_svg and not svg_path:
        svg_path = "cas_diagram.svg"
    if args.auto_html and not html_path:
        html_path = "cas_diagram.html"

    artifact, _, _ = compile_and_show(
        source,
        full_json=args.json,
        show_terminal_diagram=not args.no_terminal_diagram,
        svg_path=svg_path,
        html_path=html_path,
        auto_files=auto_files,
    )
    return 0 if artifact.valid else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline CAS compiler terminal with diagrams.")
    parser.add_argument("expression", nargs="*", help="CAS expression. Omit for REPL mode.")
    parser.add_argument("--json", action="store_true", help="Print full artifact JSON.")
    parser.add_argument("--svg", help="Write diagram SVG to this path.")
    parser.add_argument("--html", help="Write standalone diagram HTML to this path.")
    parser.add_argument("--auto-svg", action="store_true", help="Write cas_diagram.svg when --svg is omitted.")
    parser.add_argument("--auto-html", action="store_true", help="Write cas_diagram.html when --html is omitted.")
    parser.add_argument("--auto-files", action="store_true", help="Write both cas_diagram.svg and cas_diagram.html.")
    parser.add_argument("--no-terminal-diagram", action="store_true", help="Suppress terminal diagram preview.")
    parser.add_argument("--examples", action="store_true", help="Print grouped examples.")
    parser.add_argument("--natural", action="store_true", help="Print examples in natural language.")
    parser.add_argument("--mirror", action="store_true", help="Print (CAS expression) natural-language mirror pairs.")
    parser.add_argument("--dict", nargs="?", const="", dest="dictionary", help="Print the CAS dictionary, optionally filtered by term.")
    parser.add_argument("--learn", action="store_true", help="Print the guided compiler learning path.")
    parser.add_argument("--example", type=int, help="Compile example number N.")
    parser.add_argument("--demo", action="store_true", help="Compile every example and write SVG/HTML demo files.")
    parser.add_argument("--demo-dir", default="examples", help="Output folder for --demo.")
    parser.add_argument("--palette", action="store_true", help="Print symbol palette.")
    parser.add_argument("--reference", action="store_true", help="Print reference panel.")
    parser.add_argument("--color", action="store_true", help="Force ANSI color output.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    set_color_enabled(True if args.color else False if args.no_color else None)
    direct = (
        args.expression
        or args.examples
        or args.natural
        or args.mirror
        or args.dictionary is not None
        or args.learn
        or args.example is not None
        or args.demo
        or args.palette
        or args.reference
    )
    if not direct:
        return repl()
    return compile_once(args)


if __name__ == "__main__":
    raise SystemExit(main())
