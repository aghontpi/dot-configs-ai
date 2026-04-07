#!/usr/bin/env python3
"""
Initialize the ~/.skill-memory/ directory structure.
Safe to run multiple times — never overwrites existing data.
"""

import os
import sys
from datetime import datetime

MEMORY_ROOT = os.path.expanduser("~/.skill-memory")

SCAFFOLD = {
    "preferences.md": (
        "# Preferences\n\n"
        "User preferences, tool choices, and workflow patterns.\n\n"
        "---\n"
    ),
    "corrections.md": (
        "# Corrections\n\n"
        "Mistakes the AI made and the correct approach.\n\n"
        "---\n"
    ),
    "index.md": (
        "# Skill Memory Index\n\n"
        f"Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "## Files\n"
        "- [preferences.md](preferences.md) — User preferences and patterns\n"
        "- [corrections.md](corrections.md) — Learned corrections\n"
        "- `projects/` — Per-project context\n"
    ),
}

SUBDIRS = ["projects"]


def init():
    created = []
    skipped = []

    # Root directory
    if not os.path.isdir(MEMORY_ROOT):
        os.makedirs(MEMORY_ROOT)
        created.append(MEMORY_ROOT)
    else:
        skipped.append(MEMORY_ROOT)

    # Subdirectories
    for subdir in SUBDIRS:
        path = os.path.join(MEMORY_ROOT, subdir)
        if not os.path.isdir(path):
            os.makedirs(path)
            created.append(path)
        else:
            skipped.append(path)

    # Scaffold files
    for filename, content in SCAFFOLD.items():
        path = os.path.join(MEMORY_ROOT, filename)
        if not os.path.isfile(path):
            with open(path, "w") as f:
                f.write(content)
            created.append(path)
        else:
            skipped.append(path)

    # Report
    print("✅ Memory initialized at:", MEMORY_ROOT)
    if created:
        print("\n  Created:")
        for p in created:
            print(f"    + {p}")
    if skipped:
        print("\n  Already existed (untouched):")
        for p in skipped:
            print(f"    ~ {p}")


if __name__ == "__main__":
    init()
