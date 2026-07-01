#!/usr/bin/env python3
"""build_bundle.py - rebuild antipatterns.skill from the runtime source files.

The bundle is a zip of the runtime files (no README, LICENSE, tests, or
tooling), nested under antipatterns/ to match the original package layout.
It is a build artifact, not a committed file: the release workflow
(.github/workflows/release.yml) builds and publishes it to a GitHub Release
on v* tags, so it is gitignored (see .gitignore). Run this locally to
inspect the bundle a release would ship.

Usage:
    python tools/build_bundle.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "antipatterns.skill"
RUNTIME = ["SKILL.md", "ANTIPATTERNS.md", "scan.py", "catalog.py", "add_pattern.py"]


def main() -> int:
    missing = [f for f in RUNTIME if not (REPO / f).exists()]
    if missing:
        print(f"::error::missing source files: {missing}")
        return 1
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in RUNTIME:
            z.write(REPO / f, arcname=f"antipatterns/{f}")
    print(f"built {OUT.relative_to(REPO)} ({OUT.stat().st_size} bytes, {len(RUNTIME)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
