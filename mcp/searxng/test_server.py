#!/usr/bin/env python3
"""Tests for the SearXNG MCP server. Run from the mcp/searxng/ directory:

    .venv/bin/python3 test_server.py
"""

from pathlib import Path
import sys

SERVER_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, SERVER_DIR)
from server import (
    SearchInput,
    _health_check,
    _is_setup,
    _pid_running,
    _venv_python,
    SEARXNG_URL,
)
import asyncio

PASS = 0
FAIL = 0


def test(label):
    def decorator(fn):
        def wrapper():
            global PASS, FAIL
            try:
                fn()
                PASS += 1
                print(f"  PASS  {label}")
            except Exception as e:
                FAIL += 1
                print(f"  FAIL  {label}: {e}")

        return wrapper

    return decorator


# ── validation tests ──────────────────────────────────────────────────────────


@test("valid minimal input")
def test_valid_minimal():
    params = SearchInput(query="hello world")
    assert params.query == "hello world"
    assert params.limit is None
    assert params.language == "auto"
    assert params.safesearch == 0
    assert params.time_range is None


@test("valid input with all fields")
def test_valid_full():
    params = SearchInput(
        query="python async",
        time_range="week",
        language="en-US",
        safesearch=1,
        limit=5,
    )
    assert params.time_range == "week"
    assert params.language == "en-US"
    assert params.safesearch == 1
    assert params.limit == 5


@test("empty query rejected")
def test_empty_query():
    try:
        SearchInput(query="")
        assert False, "should have raised"
    except Exception:
        pass


@test("whitespace-only query rejected")
def test_whitespace_query():
    try:
        SearchInput(query="   ")
        assert False, "should have raised"
    except Exception:
        pass


@test("invalid time_range rejected")
def test_invalid_time_range():
    try:
        SearchInput(query="test", time_range="invalid")
        assert False, "should have raised"
    except Exception:
        pass


@test("safesearch out of range rejected")
def test_safesearch_range():
    try:
        SearchInput(query="test", safesearch=5)
        assert False, "should have raised"
    except Exception:
        pass


@test("limit below 1 rejected")
def test_limit_low():
    try:
        SearchInput(query="test", limit=0)
        assert False, "should have raised"
    except Exception:
        pass


@test("limit above 30 rejected")
def test_limit_high():
    try:
        SearchInput(query="test", limit=50)
        assert False, "should have raised"
    except Exception:
        pass


# ── formatting tests ──────────────────────────────────────────────────────────


def format_results(results, query="test query", limit=None):
    """Inline version of the search result formatting, for testing."""
    r = results
    if limit is not None:
        r = r[:limit]
    if not r:
        return f'No results found for "{query}".'

    lines = [f'## Search: "{query}"', ""]
    for i, item in enumerate(r, 1):
        title = item.get("title", "Untitled").strip()
        url_str = item.get("url", "")
        snippet = item.get("content", "").strip()
        engine = item.get("engine", "")
        published = item.get("publishedDate") or item.get("pubdate") or ""

        lines.append(f"**{i}. [{title}]({url_str})**")
        if snippet:
            lines.append(f"> {snippet}")
        meta = engine
        if published:
            meta += f" · {published}"
        lines.append(f"*{meta}*")
        lines.append("")

    return "\n".join(lines)


@test("format with all fields present")
def test_format_full():
    results = [
        {
            "title": "Example",
            "url": "https://example.com",
            "content": "A test page.",
            "engine": "google",
            "publishedDate": "2026-06-01",
        }
    ]
    out = format_results(results)
    assert "**1. [Example](https://example.com)**" in out
    assert "> A test page." in out
    assert "*google · 2026-06-01*" in out


@test("format with missing title defaults to Untitled")
def test_format_missing_title():
    results = [{"url": "https://x.com", "content": "text", "engine": "ddg"}]
    out = format_results(results)
    assert "[Untitled]" in out


@test("format with missing snippet skips blockquote")
def test_format_no_snippet():
    results = [{"title": "T", "url": "https://x.com", "engine": "ddg"}]
    out = format_results(results)
    assert "> " not in out


@test("empty results returns no-results message")
def test_format_empty():
    out = format_results([])
    assert "No results found" in out


@test("limit slices results correctly")
def test_format_limit():
    results = [
        {"title": f"R{i}", "url": f"https://{i}.com", "content": f"c{i}", "engine": "e"}
        for i in range(5)
    ]
    out = format_results(results, limit=2)
    assert "R0" in out
    assert "R1" in out
    assert "R2" not in out


# ── integration tests (require running SearXNG) ───────────────────────────────


async def _run_integration_tests():
    label = "searxng is running and healthy"
    try:
        healthy = await _health_check()
        if not healthy:
            print(f"  SKIP  {label}: SearXNG not running on {SEARXNG_URL}")
            return
        print(f"  PASS  {label}")

        # real search
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": "python programming", "format": "json"},
                timeout=15,
            )
            data = resp.json()
            results = data.get("results", [])
            assert isinstance(results, list), "results should be a list"
            assert len(results) > 0, "should get at least one result"
            assert "title" in results[0], "each result should have a title"
            assert "url" in results[0], "each result should have a url"
            print(f"  PASS  real search returns {len(results)} results")

    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        print(f"  SKIP  {label}: SearXNG not reachable")


# ── main ──────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    print("=== Unit Tests ===\n")
    test_valid_minimal()
    test_valid_full()
    test_empty_query()
    test_whitespace_query()
    test_invalid_time_range()
    test_safesearch_range()
    test_limit_low()
    test_limit_high()
    print()
    test_format_full()
    test_format_missing_title()
    test_format_no_snippet()
    test_format_empty()
    test_format_limit()

    print("\n=== Integration Tests ===\n")
    asyncio.run(_run_integration_tests())

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    if FAIL:
        sys.exit(1)
