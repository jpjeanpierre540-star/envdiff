#!/usr/bin/env python3
"""
envdiff - Compare two .env-style files and report key differences
without ever printing secret values.

Usage:
    python3 envdiff.py <file_a> <file_b> [--show-values]

Why this exists:
    Developers constantly compare a local .env against .env.example,
    or a staging config against production, to spot missing or extra
    variables. Diffing the raw files leaks secrets into terminal
    scrollback, CI logs, or screen-shares. envdiff parses only the
    *keys* and reports which keys are missing, added, or have
    different (but masked) values -- safe to paste into a PR
    description, Slack, or a CI log.

Exit codes:
    0 - no differences in keys (values may still differ, see output)
    1 - differences found
    2 - usage / file error
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file into a dict.

    Rules (kept intentionally simple and dependency-free):
      - Blank lines and lines starting with '#' are ignored.
      - 'export KEY=VALUE' is treated the same as 'KEY=VALUE'.
      - The first '=' separates key from value.
      - Surrounding single or double quotes on the value are stripped.
      - Duplicate keys: last one wins (matches shell `source` semantics).
    """
    result: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key:
            continue
        result[key] = value
    return result


def mask(value: str) -> str:
    """Return a masked representation of a value, never the real secret."""
    if value == "":
        return "<empty>"
    return f"<set, {len(value)} chars>"


@dataclass
class DiffResult:
    only_in_a: list[str] = field(default_factory=list)
    only_in_b: list[str] = field(default_factory=list)
    differing: list[str] = field(default_factory=list)
    identical: list[str] = field(default_factory=list)

    def has_differences(self) -> bool:
        return bool(self.only_in_a or self.only_in_b or self.differing)


def diff_env(a: dict[str, str], b: dict[str, str]) -> DiffResult:
    result = DiffResult()
    keys_a = set(a)
    keys_b = set(b)

    result.only_in_a = sorted(keys_a - keys_b)
    result.only_in_b = sorted(keys_b - keys_a)

    for key in sorted(keys_a & keys_b):
        if a[key] == b[key]:
            result.identical.append(key)
        else:
            result.differing.append(key)

    return result


def format_report(
    result: DiffResult,
    name_a: str,
    name_b: str,
    a: dict[str, str],
    b: dict[str, str],
    show_values: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"Comparing {name_a} -> {name_b}")
    lines.append("=" * 40)

    if result.only_in_a:
        lines.append(f"\nOnly in {name_a} ({len(result.only_in_a)}):")
        for key in result.only_in_a:
            lines.append(f"  - {key}")

    if result.only_in_b:
        lines.append(f"\nOnly in {name_b} ({len(result.only_in_b)}):")
        for key in result.only_in_b:
            lines.append(f"  + {key}")

    if result.differing:
        lines.append(f"\nDifferent values ({len(result.differing)}):")
        for key in result.differing:
            if show_values:
                lines.append(f"  ~ {key}: {a[key]!r} -> {b[key]!r}")
            else:
                lines.append(f"  ~ {key}: {mask(a[key])} -> {mask(b[key])}")

    lines.append(f"\nIdentical keys: {len(result.identical)}")

    if not result.has_differences():
        lines.append("\nNo key differences found. Files declare the same variables.")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envdiff",
        description="Compare two .env files by key, without leaking secret values.",
    )
    parser.add_argument("file_a", type=Path, help="Path to the first .env file (e.g. .env.example)")
    parser.add_argument("file_b", type=Path, help="Path to the second .env file (e.g. .env)")
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="DANGEROUS: print actual values for differing keys instead of masking them. "
        "Only use on non-secret files.",
    )
    args = parser.parse_args(argv)

    for p in (args.file_a, args.file_b):
        if not p.is_file():
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2

    try:
        a = parse_env_file(args.file_a)
        b = parse_env_file(args.file_b)
    except OSError as exc:
        print(f"error: could not read file: {exc}", file=sys.stderr)
        return 2

    result = diff_env(a, b)
    report = format_report(result, str(args.file_a), str(args.file_b), a, b, args.show_values)
    print(report)

    return 1 if result.has_differences() else 0


if __name__ == "__main__":
    raise SystemExit(main())
