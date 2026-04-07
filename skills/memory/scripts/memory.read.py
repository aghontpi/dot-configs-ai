#!/usr/bin/env python3
"""
Read and display memories from ~/.skill-memory/.

Modes:
  --all          Load and display ALL memories.
  --summary      Show only titles and tags (quick overview).
  --project X    Load memories for a specific project.
  --recent N     Show the N most recent entries across all files.

Usage:
  python memory.read.py --summary
  python memory.read.py --all
  python memory.read.py --project pomodoro-app
  python memory.read.py --recent 5
"""

import argparse
import os
import re
import sys
from datetime import datetime

MEMORY_ROOT = os.path.expanduser("~/.skill-memory")


def parse_entries_from_file(filepath):
    """Parse a memory markdown file into list of (title, date, tags, content, source) tuples."""
    if not os.path.isfile(filepath):
        return []

    with open(filepath, "r") as f:
        text = f.read()

    entries = []
    blocks = re.split(r"(?=^### )", text, flags=re.MULTILINE)

    for block in blocks:
        block = block.strip()
        if not block.startswith("### "):
            continue

        title = ""
        date = ""
        tags = []
        content = ""

        title_match = re.match(r"### (.+)", block)
        if title_match:
            title = title_match.group(1).strip()

        date_match = re.search(r"\*\*Date\*\*:\s*(.+)", block)
        if date_match:
            date = date_match.group(1).strip()

        tags_match = re.search(r"\*\*Tags\*\*:\s*(.+)", block)
        if tags_match:
            raw_tags = tags_match.group(1).strip()
            tags = [t.strip().strip("`") for t in raw_tags.split(",")]

        content_match = re.search(r"\*\*Memory\*\*:\s*(.+)", block, re.DOTALL)
        if content_match:
            content = content_match.group(1).strip()

        rel_source = os.path.relpath(filepath, MEMORY_ROOT)
        entries.append({
            "title": title,
            "date": date,
            "tags": tags,
            "content": content,
            "source": rel_source,
        })

    return entries


def collect_all():
    """Gather entries from every .md file in ~/.skill-memory/."""
    all_entries = []
    for root, dirs, files in os.walk(MEMORY_ROOT):
        for fname in files:
            if fname.endswith(".md") and fname != "index.md":
                filepath = os.path.join(root, fname)
                all_entries.extend(parse_entries_from_file(filepath))
    return all_entries


def display_summary(entries):
    """Show only titles, tags, and source — no content."""
    if not entries:
        print("📭 No memories found.")
        return

    print(f"📋 Memory Summary ({len(entries)} entries):\n")
    for e in entries:
        tag_str = ", ".join(f"`{t}`" for t in e["tags"]) if e["tags"] else "—"
        print(f"  • [{e['date']}] **{e['title']}** ({e['source']})")
        print(f"    Tags: {tag_str}")


def display_full(entries):
    """Show everything."""
    if not entries:
        print("📭 No memories found.")
        return

    print(f"📖 Full Memory Dump ({len(entries)} entries):\n")
    for e in entries:
        tag_str = ", ".join(f"`{t}`" for t in e["tags"]) if e["tags"] else "—"
        print(f"### {e['title']}")
        print(f"- **Date**: {e['date']}")
        print(f"- **Tags**: {tag_str}")
        print(f"- **Source**: {e['source']}")
        print(f"- **Memory**: {e['content']}")
        print()


def display_recent(entries, n):
    """Show the most recent N entries sorted by date."""
    # Sort by date descending, entries without dates go last
    def sort_key(e):
        try:
            return datetime.strptime(e["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.min

    sorted_entries = sorted(entries, key=sort_key, reverse=True)
    display_full(sorted_entries[:n])


def main():
    parser = argparse.ArgumentParser(description="Read memories from ~/.skill-memory/.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Display all memories with full content.")
    group.add_argument("--summary", action="store_true", help="Display only titles and tags.")
    group.add_argument("--project", type=str, help="Load memories for a specific project.")
    group.add_argument("--recent", type=int, metavar="N", help="Show the N most recent entries.")

    args = parser.parse_args()

    if not os.path.isdir(MEMORY_ROOT):
        print("📭 No memory store found. Run memory.init.py to initialize.")
        sys.exit(0)

    if args.project:
        filepath = os.path.join(MEMORY_ROOT, "projects", f"{args.project}.md")
        entries = parse_entries_from_file(filepath)
        if not entries:
            print(f"📭 No memories found for project '{args.project}'.")
        else:
            display_full(entries)
    elif args.recent:
        entries = collect_all()
        display_recent(entries, args.recent)
    elif args.summary:
        entries = collect_all()
        display_summary(entries)
    elif args.all:
        entries = collect_all()
        display_full(entries)


if __name__ == "__main__":
    main()
