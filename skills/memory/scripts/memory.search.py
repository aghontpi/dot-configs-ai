#!/usr/bin/env python3
"""
Search across all memories in ~/.skill-memory/.

Supports:
  - Free-text keyword search (case-insensitive, ranked by hit count)
  - Tag filtering (exact match)
  - Project filtering
  - Type filtering (preference, correction, project, general)
  - Combining multiple filters

Usage:
  python memory.search.py --query "pnpm"
  python memory.search.py --tags "git,workflow"
  python memory.search.py --query "overlay" --project "pomodoro-app"
  python memory.search.py --type correction
  python memory.search.py --query "swift" --type project --tags "macos"
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

MEMORY_ROOT = os.path.expanduser("~/.skill-memory")


@dataclass
class MemoryEntry:
    title: str = ""
    date: str = ""
    tags: list = field(default_factory=list)
    content: str = ""
    source_file: str = ""
    raw_block: str = ""
    relevance: int = 0


def parse_entries(filepath):
    """Parse a memory markdown file into structured entries."""
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

        entry = MemoryEntry()
        entry.source_file = os.path.relpath(filepath, MEMORY_ROOT)
        entry.raw_block = block

        # Title
        title_match = re.match(r"### (.+)", block)
        if title_match:
            entry.title = title_match.group(1).strip()

        # Date
        date_match = re.search(r"\*\*Date\*\*:\s*(.+)", block)
        if date_match:
            entry.date = date_match.group(1).strip()

        # Tags
        tags_match = re.search(r"\*\*Tags\*\*:\s*(.+)", block)
        if tags_match:
            raw_tags = tags_match.group(1).strip()
            entry.tags = [t.strip().strip("`") for t in raw_tags.split(",")]

        # Content (Memory field)
        content_match = re.search(r"\*\*Memory\*\*:\s*(.+)", block, re.DOTALL)
        if content_match:
            entry.content = content_match.group(1).strip()

        entries.append(entry)

    return entries


def collect_all_entries():
    """Gather entries from every .md file in ~/.skill-memory/."""
    all_entries = []

    for root, dirs, files in os.walk(MEMORY_ROOT):
        for fname in files:
            if fname.endswith(".md") and fname != "index.md":
                filepath = os.path.join(root, fname)
                all_entries.extend(parse_entries(filepath))

    return all_entries


def filter_entries(entries, query=None, tags=None, project=None, memory_type=None):
    """Apply all filters and rank by relevance."""
    results = []

    for entry in entries:
        score = 0
        passed = True

        # Tag filter (all specified tags must be present)
        if tags:
            filter_tags = [t.strip().lower() for t in tags.split(",")]
            entry_tags_lower = [t.lower() for t in entry.tags]
            if not all(ft in entry_tags_lower for ft in filter_tags):
                passed = False

        # Project filter
        if project and passed:
            if f"projects/{project}.md" not in entry.source_file:
                passed = False

        # Type filter
        if memory_type and passed:
            type_file_map = {
                "preference": "preferences.md",
                "correction": "corrections.md",
                "general": "general.md",
                "project": "projects/",
            }
            expected = type_file_map.get(memory_type, "")
            if expected not in entry.source_file:
                passed = False

        # Keyword search (additive scoring)
        if query and passed:
            query_lower = query.lower()
            keywords = query_lower.split()
            searchable = f"{entry.title} {entry.content} {' '.join(entry.tags)}".lower()

            hits = sum(1 for kw in keywords if kw in searchable)
            if hits == 0:
                passed = False
            else:
                score += hits
                # Boost for title match
                if query_lower in entry.title.lower():
                    score += 5
                # Boost for tag match
                if any(query_lower in t.lower() for t in entry.tags):
                    score += 3

        if not query:
            score = 1  # All non-filtered entries are equally relevant

        if passed:
            entry.relevance = score
            results.append(entry)

    results.sort(key=lambda e: e.relevance, reverse=True)
    return results


def display_results(results, verbose=False):
    if not results:
        print("🔍 No memories found matching your query.")
        return

    print(f"🔍 Found {len(results)} matching memor{'y' if len(results) == 1 else 'ies'}:\n")

    for i, entry in enumerate(results, 1):
        tag_str = ", ".join(f"`{t}`" for t in entry.tags) if entry.tags else "none"
        print(f"  [{i}] **{entry.title}**")
        print(f"      Date: {entry.date}  |  Tags: {tag_str}")
        print(f"      Source: {entry.source_file}")
        if verbose or len(results) <= 10:
            print(f"      Memory: {entry.content}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search memories.")
    parser.add_argument("--query", "-q", default=None, help="Free-text search query.")
    parser.add_argument("--tags", "-t", default=None, help="Comma-separated tags to filter by.")
    parser.add_argument("--project", "-p", default=None, help="Filter by project name.")
    parser.add_argument("--type", default=None, choices=["preference", "correction", "project", "general"],
                        help="Filter by memory type.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Always show full memory content.")

    args = parser.parse_args()

    if not os.path.isdir(MEMORY_ROOT):
        print("❌ Memory not initialized. Run memory.init.py first.")
        sys.exit(1)

    if not any([args.query, args.tags, args.project, args.type]):
        print("❌ Provide at least one filter: --query, --tags, --project, or --type")
        sys.exit(1)

    entries = collect_all_entries()
    results = filter_entries(entries, args.query, args.tags, args.project, args.type)
    display_results(results, args.verbose)


if __name__ == "__main__":
    main()
