#!/usr/bin/env python3
from __future__ import annotations
import re
import argparse
import fnmatch
import sys
from pathlib import Path
from typing import Iterable

"""
win2nix_paths.py — Convert Windows-style path slashes to POSIX slashes.

Modes:
- Default: only inside quoted strings (safer for code/escapes).
- --aggressive: also convert *unquoted* Windows-like paths using heuristics.

Heuristics try to avoid touching escape sequences (e.g., "\n") and code tokens.
"""

# Quoted string regex (single or double), handling escaped chars inside.
_QUOTED = re.compile(
    r"""
    (?P<quote>['"])
    (?P<content>
        (?:
            \\\\ .
          | [^\\'"]
        )*
    )
    (?P=quote)
    """,
    re.VERBOSE,
)

_PATHY_SEG = r"[A-Za-z0-9_\- .]"
_DRIVE = re.compile(r"(?i)^[A-Z]:[\\/]|^[A-Z]:\\\\")
_HAS_BACKSLASH_SEG = re.compile(rf"{_PATHY_SEG}+\\{_PATHY_SEG}+")
_TYPICAL_FILE = re.compile(rf"{_PATHY_SEG}+\\{_PATHY_SEG}+\.([A-Za-z0-9]{{1,6}})$")

def looks_like_path(s: str) -> bool:
    if "\\" not in s or len(s) < 3:
        return False
    if _DRIVE.search(s):
        return True
    if _HAS_BACKSLASH_SEG.search(s):
        return True
    if _TYPICAL_FILE.search(s):
        return True
    return False

def slashify(content: str) -> str:
    out = []
    i = 0
    while i < len(content):
        c = content[i]
        if c == "\\":
            if i + 1 < len(content) and content[i + 1] == "\\":
                out.append("/")
                i += 2
                continue
            if i + 1 < len(content) and content[i + 1] in ['"', "'", "n", "r", "t", "b", "f"]:
                out.append("\\")
                out.append(content[i + 1])
                i += 2
                continue
            if i + 1 < len(content) and re.match(r"[A-Za-z0-9_\- .]", content[i + 1]):
                out.append("/")
                i += 1
                continue
            out.append("\\")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)

def transform_quoted(text: str) -> tuple[str, int]:
    replacements = 0
    result = []
    last_end = 0
    for m in _QUOTED.finditer(text):
        start, end = m.span()
        quote = m.group("quote")
        content = m.group("content")
        result.append(text[last_end:start])
        new_inner = content
        if looks_like_path(content):
            new_inner = slashify(content)
            if new_inner != content:
                replacements += 1
        result.append(f"{quote}{new_inner}{quote}")
        last_end = end
    result.append(text[last_end:])
    return "".join(result), replacements

# Aggressive mode: also catch unquoted path-like tokens.
# We search for Windows-drive and backslash sequences outside quotes.
_UNQUOTED_PATH = re.compile(
    r"""
    (?<!['"])                # not immediately after a quote
    (?P<p>
        [A-Za-z]:\\[^\s'"]+  # C:\something\else (no spaces/quotes)
        |
        (?:[A-Za-z0-9_.-]+\\)+[A-Za-z0-9_.-]+  # foo\bar\baz
    )
    (?!['"])                 # not immediately before a quote
    """,
    re.VERBOSE,
)

def transform_aggressive(text: str) -> tuple[str, int]:
    # First do the quoted transform
    text_after, reps = transform_quoted(text)

    # Then replace unquoted matches, but only if they "look like a path"
    # and are not part of typical escape sequences or code escapes.
    def repl(m: re.Match) -> str:
        s = m.group("p")
        if looks_like_path(s):
            return slashify(s)
        return s

    new_text, n2 = _UNQUOTED_PATH.subn(repl, text_after)
    return new_text, reps + n2

DEFAULT_EXTS = [
    ".uplugin", ".uproject",
    ".Build.cs", ".Target.cs", ".cs",
    ".ini", ".txt", ".json", ".props", ".xml", ".bat", ".cmd",
    ".cpp", ".h", ".hpp"
]

def match_any(path: Path, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(str(path.as_posix()), pat) for pat in patterns)

def process_file(f: Path, aggressive: bool) -> int:
    try:
        text = f.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        try:
            text = f.read_text(encoding="latin-1")
        except Exception:
            print(f"[SKIP] Cannot decode {f}", file=sys.stderr)
            return 0
    new_text, nrep = (transform_aggressive(text) if aggressive else transform_quoted(text))
    if nrep > 0:
        f.write_text(new_text, encoding="utf-8")
    return nrep

def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Windows path slashes to POSIX slashes.")
    ap.add_argument("root", help="Root directory to scan")
    ap.add_argument("--dry-run", action="store_true", help="Report changes but do not modify files")
    ap.add_argument("--ext", nargs="*", default=DEFAULT_EXTS, help="File extensions to process")
    ap.add_argument("--include", nargs="*", default=["**/*"], help="Glob(s) to include (relative to root)")
    ap.add_argument("--exclude", nargs="*", default=["**/Binaries/**", "**/Intermediate/**", "**/.git/**"], help="Glob(s) to exclude")
    ap.add_argument("--aggressive", action="store_true", help="Also convert unquoted Windows-like paths (use with care)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERROR] Root not found: {root}", file=sys.stderr)
        return 1

    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if args.ext and p.suffix not in args.ext:
            continue
        rel = p.relative_to(root)
        if not match_any(rel, args.include):
            continue
        if match_any(rel, args.exclude):
            continue
        files.append(p)

    total_changed_files = 0
    total_replacements = 0
    for f in files:
        try:
            if args.dry_run:
                # simulate
                try:
                    text = f.read_text(encoding="utf-8", errors="strict")
                except UnicodeDecodeError:
                    try:
                        text = f.read_text(encoding="latin-1")
                    except Exception:
                        print(f"[SKIP] Cannot decode {f}", file=sys.stderr)
                        continue
                _, nrep = (transform_aggressive(text) if args.aggressive else transform_quoted(text))
                if nrep > 0:
                    print(f"[DRY] {f} — {nrep} path string(s) updated")
                    total_changed_files += 1
                    total_replacements += nrep
            else:
                nrep = process_file(f, args.aggressive)
                if nrep > 0:
                    print(f"[FIX] {f} — {nrep} path string(s) updated")
                    total_changed_files += 1
                    total_replacements += nrep
        except Exception as e:
            print(f"[ERROR] {f}: {e}", file=sys.stderr)

    print(f"[SUMMARY] Files changed: {total_changed_files}, path strings updated: {total_replacements}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
