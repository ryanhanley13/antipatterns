#!/usr/bin/env python3
"""check_bundle_sync.py - fail if antipatterns.skill is out of sync with source.

The committed .skill bundle is a zip of the runtime files. It must always match
the loose source so a Claude.ai import and a Claude Code checkout behave
identically. This check enforces that automatically in CI - replacing the
manual "rebuild and hope you remember" discipline.

It compares each bundled file's CONTENT against the source file. It deliberately
does NOT compare raw zip bytes, because zips store a per-entry mtime, so two
zips of identical content produced at different times differ at the byte level
(false drift). Content comparison is deterministic and correct.

Exit 0 if in sync, 1 if drift (with a message naming the offending file).

Usage:
    python tools/check_bundle_sync.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "antipatterns.skill"
RUNTIME = ["SKILL.md", "ANTIPATTERNS.md", "scan.py", "catalog.py", "add_pattern.py"]


def main() -> int:
    if not BUNDLE.exists():
        print(f"::error::{BUNDLE.name} not found", file=sys.stderr)
        return 1

    z = zipfile.ZipFile(BUNDLE)
    expected = {f"antipatterns/{f}" for f in RUNTIME}
    actual = set(z.namelist())

    problems = []
    extra = actual - expected
    missing = expected - actual
    if extra:
        problems.append(f"bundle has unexpected files: {sorted(extra)}")
    if missing:
        problems.append(f"bundle is missing files: {sorted(missing)}")

    for f in RUNTIME:
        arc = f"antipatterns/{f}"
        if arc not in actual:
            continue  # already reported as missing
        bundled = z.read(arc)
        source = (REPO / f).read_bytes()
        if bundled != source:
            problems.append(f"{f}: bundled content differs from source")

    if problems:
        print("::error::antipatterns.skill is out of sync with source files.")
        print("Rebuild and commit:  python tools/build_bundle.py")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"antipatterns.skill in sync ({len(RUNTIME)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
