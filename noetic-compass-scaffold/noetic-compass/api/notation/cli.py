"""CLI and REPL for the executable CAS language."""

from __future__ import annotations

import argparse
import json
import sys

from .compiler import CAS_GRAMMAR_BNF, compile_expression, compile_file


def _print_json(payload: object) -> None:
    _write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_text(text: str) -> None:
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="backslashreplace"))


def _emit_stage(mode: str, artifact: dict) -> None:
    if mode == "lex":
        _print_json({"tokens": artifact["tokens"], "valid": artifact["valid"], "error": artifact["error"]})
        return
    if mode == "parse":
        _print_json({"ast": artifact["ast"], "valid": artifact["valid"], "error": artifact["error"]})
        return
    if mode == "check":
        _print_json({"type": artifact["type"], "warnings": artifact["warnings"], "valid": artifact["valid"], "error": artifact["error"]})
        return
    if mode == "run":
        _print_json(artifact)
        return
    raise ValueError(f"unknown mode {mode}")


def repl() -> int:
    print("CAS REPL. Type :quit to exit, :grammar to print the grammar.")
    while True:
        try:
            line = input("cas> ")
        except EOFError:
            print()
            return 0
        if not line.strip():
            continue
        if line.strip() in {":quit", ":q", "quit", "exit"}:
            return 0
        if line.strip() == ":grammar":
            _write_text(CAS_GRAMMAR_BNF + "\n")
            continue
        artifact = compile_expression(line)
        _print_json(artifact.to_dict())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m api.notation.cli", description="Compile and execute CAS notation")
    parser.add_argument("expression", nargs="?", help="CAS expression or program to compile")
    parser.add_argument("--file", dest="file_path", help="Read a CAS program from a file")
    parser.add_argument("--mode", choices=["lex", "parse", "check", "run"], default="run")
    parser.add_argument("--grammar", action="store_true", help="Print the CAS BNF grammar and exit")
    parser.add_argument("--repl", action="store_true", help="Launch an interactive CAS REPL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.grammar:
        _write_text(CAS_GRAMMAR_BNF + "\n")
        return 0
    if args.repl:
        return repl()
    if args.file_path:
        artifact = compile_file(args.file_path)
    elif args.expression:
        artifact = compile_expression(args.expression)
    else:
        print("usage: python -m api.notation.cli '<expression>' or --file path or --repl", file=sys.stderr)
        return 2
    payload = artifact.to_dict()
    _emit_stage(args.mode, payload)
    return 0 if artifact.valid else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
