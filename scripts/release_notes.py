#!/usr/bin/env python3
"""Print the release notes of a version: its section in CHANGELOG.md, without the heading.

Fails if the changelog has no section for the version, or the section is empty.

Usage: scripts/release_notes.py 0.18.0 > notes.md
"""

from pathlib import Path
import sys

CHANGELOG = Path(__file__).parent.parent / "CHANGELOG.md"


def release_notes(changelog: str, version: str) -> str:
    """Return the section of the version in the changelog, without its heading, or "" if there is none."""
    lines = changelog.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(f"## [{version}]")]
    if not starts:
        return ""
    end = next(
        (i for i in range(starts[0] + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    return "\n".join(lines[starts[0] + 1 : end]).strip()


if __name__ == "__main__":
    version = sys.argv[1]
    notes = release_notes(CHANGELOG.read_text(encoding="utf-8"), version)
    if not notes:
        sys.exit(
            f"error: CHANGELOG.md has no release notes for version {version} "
            f"(expected a section '## [{version}] ...')"
        )
    print(notes)
