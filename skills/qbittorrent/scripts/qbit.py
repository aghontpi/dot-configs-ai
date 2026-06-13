#!/usr/bin/env python3
"""qBittorrent helper utilities for use within the qbittorrent skill.

These helpers handle common tasks like URL-encoding magnet links, filtering
torrent JSON by name, and pretty-printing torrent summaries. They are designed
to be called inline from shell scripts (via python3 -c or piped stdin) so the
skill's curl-based workflow stays simple and debuggable.

Usage examples:

    # URL-encode a magnet link
    python3 scripts/qbit.py encode "<magnet-link>"

    # Filter torrent list by name substring
    curl ... /torrents/info | python3 scripts/qbit.py search "<query>"

    # Pretty-print torrent list as a table
    curl ... /torrents/info | python3 scripts/qbit.py table

    # Show summary with transfer info
    curl ... /torrents/info | python3 scripts/qbit.py summary
"""

import json
import sys
import urllib.parse
from pathlib import Path


def encode_magnet(magnet: str) -> str:
    """URL-encode a magnet link for the qBittorrent add API."""
    return urllib.parse.quote(magnet, safe="")


def search_torrents(data: list[dict], query: str) -> list[dict]:
    """Filter torrent list by case-insensitive name substring match."""
    q = query.lower()
    return [t for t in data if q in t["name"].lower()]


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PiB"


def format_speed(bytes_per_sec: int) -> str:
    """Format bytes/sec into human-readable speed."""
    if bytes_per_sec == 0:
        return "0 B/s"
    return format_size(bytes_per_sec) + "/s"


def print_search(data: list[dict], query: str) -> None:
    """Print filtered torrent search results."""
    matches = search_torrents(data, query)
    if not matches:
        print(f"No torrents matching '{query}'")
        return
    for t in matches:
        progress = t.get("progress", 0) * 100
        print(
            f"{t['name']} [{t.get('state', '?')}] "
            f"{progress:.0f}% — hash: {t['hash']}"
        )


def print_table(data: list[dict]) -> None:
    """Pretty-print torrent list as a formatted table."""
    if not data:
        print("No torrents found.")
        return

    # Header
    header = f"{'Name':<40} {'Size':>10} {'Progress':>8} {'State':<14} {'DL':>10} {'UL':>10} {'Ratio':>6}"
    print(header)
    print("-" * len(header))

    for t in data:
        name = t["name"][:38] + (".." if len(t["name"]) > 40 else "")
        size = format_size(t.get("total_size", t.get("size", 0)))
        progress = f"{t.get('progress', 0) * 100:.0f}%"
        state = t.get("state", "?")
        dlspeed = format_speed(t.get("dlspeed", 0))
        upspeed = format_speed(t.get("upspeed", 0))
        ratio = f"{t.get('ratio', 0):.2f}"

        print(
            f"{name:<40} {size:>10} {progress:>8} {state:<14} "
            f"{dlspeed:>10} {upspeed:>10} {ratio:>6}"
        )


def print_summary(data: list[dict]) -> None:
    """Print a summary of all torrents with counts by state."""
    print_table(data)
    print()

    # Count by state
    states: dict[str, int] = {}
    total_dl = 0
    total_ul = 0
    for t in data:
        state = t.get("state", "unknown")
        states[state] = states.get(state, 0) + 1
        total_dl += t.get("dlspeed", 0)
        total_ul += t.get("upspeed", 0)

    print(f"Total: {len(data)} torrents")
    for state, count in sorted(states.items()):
        print(f"  {state}: {count}")
    print(f"Total DL: {format_speed(total_dl)}")
    print(f"Total UL: {format_speed(total_ul)}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: qbit.py <encode|search|table|summary> [args...]", file=sys.stderr)
        sys.exit(1)

    # Resolve skill root for relative script paths
    command = sys.argv[1]

    if command == "encode":
        if len(sys.argv) < 3:
            print("Usage: qbit.py encode <magnet-link>", file=sys.stderr)
            sys.exit(1)
        print(encode_magnet(sys.argv[2]))

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: qbit.py search <query>", file=sys.stderr)
            sys.exit(1)
        data = json.load(sys.stdin)
        print_search(data, sys.argv[2])

    elif command == "table":
        data = json.load(sys.stdin)
        print_table(data)

    elif command == "summary":
        data = json.load(sys.stdin)
        print_summary(data)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Commands: encode, search, table, summary", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
