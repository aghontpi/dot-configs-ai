---
name: searxng
description: |
  Self-hosted private web search via a local SearXNG metasearch engine. Provides up-to-date information from multiple search engines without tracking or rate limits.
  WHEN TO USE: Trigger this skill whenever the user asks to search the web, look up current information, find recent news/docs/papers, or asks questions that require information beyond Claude's knowledge cutoff. Also trigger for any query about recent events, latest releases, current documentation, or real-world facts that may have changed. Err on the side of triggering — if the answer might benefit from fresh web data, use this skill.
---

# SearXNG Skill

Self-hosted, privacy-respecting web search via a local SearXNG instance. No Docker, no cloud dependencies — just Python.

## How it works

SearXNG runs as a lazy daemon: it starts on first use and stays running for subsequent searches. You stop it only when explicitly asked.

## Search flow

### Step 1: Search

Try the search first. The common case is that SearXNG is already running:

```
curl -s "http://127.0.0.1:8888/search?q=<url-encoded-query>&format=json"
```

If the response contains `"results"` → parse, summarize, and return to the user. Done.

If curl fails with "Connection refused" (or returns no valid JSON) → go to **Step 2**.

### Step 2: Lazy start (only when search fails)

The server is down. Check if `.searxng/` directory exists in the skill folder. If not, run setup first:

```
python manage.py setup
```

Then start the server:

```
python manage.py start
```

This starts SearXNG in the background, waits for it to become healthy (up to 15s), and returns. If it fails, check logs:

```
python manage.py logs
```

Once started, retry the search from **Step 1**.

## Stopping SearXNG

Only stop when the user explicitly asks:

```
python manage.py stop
```

## Commands reference

| Command | Purpose |
|---------|---------|
| `python manage.py setup [--force]` | First-time install: download, venv, pip install, configure |
| `python manage.py start` | Start SearXNG in background, wait for healthy |
| `python manage.py stop` | Graceful shutdown |
| `python manage.py restart` | Stop + start |
| `python manage.py status [--json]` | Show running/stopped status |
| `python manage.py health [--json]` | Verify API is responding correctly |
| `python manage.py logs [--lines N]` | Show recent server logs |

All commands are run from the skill directory: `skills/searxng/scripts/manage.py`.

## Troubleshooting

If something goes wrong, read `references/troubleshooting.md` for common issues and fixes.
