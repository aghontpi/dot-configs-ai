#!/usr/bin/env python3
"""
Store a new memory entry into ~/.skill-memory/.

Usage:
  python memory.store.py --type preference --title "Uses pnpm" --tags "pnpm,tooling" --content "User prefers pnpm over npm for all package management."
  python memory.store.py --type correction --title "Don't use git add ." --tags "git,workflow" --content "Always stage only modified files. Ask user before using git add ."
  python memory.store.py --type project --project "pomodoro-app" --title "Tech stack" --tags "swift,macos" --content "Native macOS app built with Swift. Has floating overlay and menu bar timer."
  python memory.store.py --type general --title "Some note" --content "Free-form memory entry."
"""

import argparse
import os
import sys
from datetime import datetime

MEMORY_ROOT = os.path.expanduser("~/.skill-memory")

TYPE_FILE_MAP = {
    "preference": "preferences.md",
    "correction": "corrections.md",
    "general": "general.md",
}


def get_target_file(memory_type, project=None):
    if memory_type == "project":
        if not project:
            print("❌ --project is required when --type is 'project'")
            sys.exit(1)
        projects_dir = os.path.join(MEMORY_ROOT, "projects")
        os.makedirs(projects_dir, exist_ok=True)
        return os.path.join(projects_dir, f"{project}.md")
    return os.path.join(MEMORY_ROOT, TYPE_FILE_MAP.get(memory_type, "general.md"))


def ensure_file_header(filepath, memory_type, project=None):
    """Create the file with a header if it doesn't exist yet."""
    if os.path.isfile(filepath):
        return

    if memory_type == "project":
        header = f"# Project: {project}\n\nContext and decisions for the {project} project.\n\n---\n"
    elif memory_type == "general":
        header = "# General Memories\n\nMiscellaneous notes and context.\n\n---\n"
    else:
        return  # preferences.md and corrections.md are created by init

    with open(filepath, "w") as f:
        f.write(header)


def store(memory_type, title, content, tags=None, project=None):
    if not os.path.isdir(MEMORY_ROOT):
        print("❌ Memory not initialized. Run memory.init.py first.")
        sys.exit(1)

    filepath = get_target_file(memory_type, project)
    ensure_file_header(filepath, memory_type, project)

    date_str = datetime.now().strftime("%Y-%m-%d")
    tag_str = ", ".join(f"`{t.strip()}`" for t in tags.split(",")) if tags else "`untagged`"

    entry = (
        f"\n### {title}\n"
        f"- **Date**: {date_str}\n"
        f"- **Tags**: {tag_str}\n"
        f"- **Memory**: {content}\n"
    )

    with open(filepath, "a") as f:
        f.write(entry)

    update_index(memory_type, title, filepath, project)

    print(f"✅ Stored → {filepath}")
    print(f"   Title: {title}")
    print(f"   Tags:  {tag_str}")


def update_index(memory_type, title, filepath, project=None):
    """Append a line to index.md tracking this entry."""
    index_path = os.path.join(MEMORY_ROOT, "index.md")
    if not os.path.isfile(index_path):
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    rel_path = os.path.relpath(filepath, MEMORY_ROOT)
    line = f"- `[{date_str}]` **{title}** → [{rel_path}]({rel_path})\n"

    # Avoid duplicate entries
    with open(index_path, "r") as f:
        existing = f.read()

    if title in existing:
        return

    with open(index_path, "a") as f:
        f.write(line)


def main():
    parser = argparse.ArgumentParser(description="Store a memory entry.")
    parser.add_argument("--type", required=True, choices=["preference", "correction", "project", "general"],
                        help="Type of memory.")
    parser.add_argument("--title", required=True, help="Short title for the memory.")
    parser.add_argument("--tags", default=None, help="Comma-separated tags (e.g., 'pnpm,tooling').")
    parser.add_argument("--content", required=True, help="The memory content.")
    parser.add_argument("--project", default=None, help="Project name (required if --type is 'project').")

    args = parser.parse_args()
    store(args.type, args.title, args.content, args.tags, args.project)


if __name__ == "__main__":
    main()
