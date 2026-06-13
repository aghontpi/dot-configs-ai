---
name: qbittorrent
description: |
  Interact with a remote qBittorrent WebUI instance behind HTTP Basic Auth.
  Use this skill whenever the user asks to list, search, pause, resume, delete,
  add torrents (magnet/torrent file), or check transfer status — anything
  involving a qBittorrent server. Even if the user just mentions "torrents" or
  "qBittorrent" trigger this skill.
---

# qBittorrent Skill

Interact with a qBittorrent server via its Web API. Supports HTTP Basic Auth in
front of qBittorrent (nginx reverse proxy) and session-based qBittorrent auth.

## Prerequisites

The skill expects a config file at `~/.config/qbittorrent-skill/config.sh`
or environment variables:

```sh
# ~/.config/qbittorrent-skill/config.sh
QBIT_URL="https://example.com/qbittorrent/"
QBIT_USER="username"
QBIT_PASS="password"
# Optional: HTTP Basic Auth credentials (when nginx sits in front)
QBIT_HTTP_USER="username"
QBIT_HTTP_PASS="password"
```

The skill auto-loads this file. If it doesn't exist, ask the user for the
endpoint, credentials, and whether HTTP Basic Auth is needed — then write the
config for them.

## Connection flow

### Step 1: Load config

```
source ~/.config/qbittorrent-skill/config.sh 2>/dev/null || true
```

If `QBIT_URL` is empty, ask the user for the required values.

### Step 2: Authenticate (get session cookie)

qBittorrent requires a session cookie (`SID`) obtained by POSTing to
`/api/v2/auth/login`. If HTTP Basic Auth is configured, include it with `-u`.

```sh
source ~/.config/qbittorrent-skill/config.sh

# Create temp cookie jar
COOKIE_FILE=$(mktemp /tmp/qbit_cookies.XXXXXX)

# Login — use --data-urlencode for safe password encoding
LOGIN_RESP=$(curl -s -c "$COOKIE_FILE" \
  -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST \
  --data-urlencode "username=${QBIT_USER}" \
  --data-urlencode "password=${QBIT_PASS}" \
  "${QBIT_URL}api/v2/auth/login")

# Must return "Ok."
echo "Login: $LOGIN_RESP"
```

If the response is not `Ok.`, re-prompt for credentials.

After login, every API call takes:
```sh
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/..."
```

### Step 3: Use the API

All API paths are relative to `$QBIT_URL/api/v2/`. Every curl call needs the
cookie and HTTP Basic Auth:

```sh
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/..."
```

## API Reference

The skill bundles a Python helper at `scripts/qbit.py` for common tasks like
URL-encoding magnets, filtering/searching torrent JSON, and formatting tables.
Use it instead of inline `python3 -c` one-liners for reliability across shells.

### Torrent listing & search

```sh
# List all torrents (JSON)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/info"

# Filter by state: downloading, seeding, completed, paused, active, etc.
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/info?filter=downloading"

# Filter by category
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/info?category=movies"

# Search by name substring (uses scripts/qbit.py helper)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/info" | \
  python3 scripts/qbit.py search "<term>"

# Pretty-print as table
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/info" | \
  python3 scripts/qbit.py table
```

The `scripts/qbit.py` path is relative to the skill directory. If the current
working directory is not the skill root, resolve it with:
```sh
SKILL_DIR="$(dirname "$0")/skills/qbittorrent"  # adjust as needed
python3 "$SKILL_DIR/scripts/qbit.py" search "<term>"
```

**Key fields to show the user:**
- `name` — torrent name
- `state` — current state (pausedUP, downloading, seeding, etc.)
- `progress` — 0.0 to 1.0
- `size` / `total_size` — bytes
- `dlspeed` / `upspeed` — bytes/sec
- `eta` — seconds remaining
- `ratio` — upload ratio
- `category` — category tag
- `hash` — used for per-torrent actions

### Torrent actions (require hash)

All per-torrent actions take `hashes=<hash>` (or pipe-separated for multiple:
`hashes=hash1|hash2`).

```sh
# Pause
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/pause" -d "hashes=<hash>"

# Resume
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/resume" -d "hashes=<hash>"

# Delete (remove torrent + delete data — DESTRUCTIVE, always confirm)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/delete" -d "hashes=<hash>&deleteFiles=true"

# Delete (remove torrent only, keep files — DESTRUCTIVE, always confirm)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/delete" -d "hashes=<hash>&deleteFiles=false"

# Recheck
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/recheck" -d "hashes=<hash>"

# Reannounce (force tracker update)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/reannounce" -d "hashes=<hash>"

# Set category
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/setCategory" -d "hashes=<hash>&category=<category>"

# Increase / decrease priority
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/increasePrio" -d "hashes=<hash>"
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/decreasePrio" -d "hashes=<hash>"

# Force start (bypass queue)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/setForceStart" -d "hashes=<hash>&value=true"
```

### Adding torrents

```sh
# Add by magnet link (URL-encode with the bundled helper)
ENCODED_MAGNET=$(python3 scripts/qbit.py encode "<magnet-link>")
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/add" -d "urls=${ENCODED_MAGNET}"

# Add by torrent file
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/add" -F "torrents=@/path/to/file.torrent"

# Add with options
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/add" \
  -d "urls=${ENCODED_MAGNET}&savepath=/downloads/movies&category=movies&paused=false"
```

### Transfer / server info

```sh
# Server transfer info (speeds, DHT nodes, connection status)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/transfer/info"

# App version
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/app/version"

# Main data (server state — free disk space, etc.)
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/sync/maindata"
```

### Categories

```sh
# List all categories
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" "${QBIT_URL}api/v2/torrents/categories"

# Create category
curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
  -X POST "${QBIT_URL}api/v2/torrents/createCategory" -d "category=<name>&savePath=/path"
```

## Workflow patterns

### Pattern: Show torrent summary

1. Load config → authenticate → get cookie.
2. Call `/torrents/info` and pipe through the bundled helper:
   ```sh
   curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
     "${QBIT_URL}api/v2/torrents/info" | python3 scripts/qbit.py summary
   ```
3. This prints a formatted table plus state counts and total speeds.

### Pattern: Pause/resume a torrent

1. Load config → authenticate.
2. If the user says "pause X" or "resume X" without a hash, search torrents by
   name substring using the bundled helper: pipe `/torrents/info` into
   `python3 scripts/qbit.py search "<name>"`.
3. Confirm with the user which torrent (show name + hash).
4. Execute pause or resume.
5. Verify by fetching the torrent info and confirming state changed.

### Pattern: Add a magnet link

1. Load config → authenticate.
2. URL-encode the magnet URI with `python3 scripts/qbit.py encode "<magnet>"`.
3. POST to `/torrents/add` with the encoded magnet.
4. Confirm: "Added. Check status with 'list torrents'."

### Pattern: Search torrents

1. Load config → authenticate.
2. Fetch all torrents, then filter with the bundled helper:
   ```sh
   curl -s -b "$COOKIE_FILE" -u "${QBIT_HTTP_USER}:${QBIT_HTTP_PASS}" \
     "${QBIT_URL}api/v2/torrents/info" | python3 scripts/qbit.py search "<user-query>"
   ```

## Important notes

- **Always confirm destructive actions** (delete, delete+data) before executing.
  Show the torrent name and ask the user to confirm.
- **Cookie expires**: If you get a 403, re-authenticate (Step 2) and retry.
- **HTTP Basic Auth**: Use `QBIT_HTTP_USER`/`QBIT_HTTP_PASS` only when the
  server returns 401 without them. The skill config supports both scenarios.
  If no HTTP auth is needed, omit the `-u` flag.
- **Multiple hashes**: The API accepts pipe-separated hashes (`hash1|hash2`) for
  batch operations.
- **URL encoding**: Always URL-encode magnet URIs. Use `python3 scripts/qbit.py encode`
  instead of manual `urllib.parse.quote` — it's more reliable across shells.
- **Helper script**: The skill bundles `scripts/qbit.py` for search, table
  formatting, summary, and URL encoding. Always use it instead of inline
  `python3 -c` — it avoids shell quoting issues (especially in zsh).
- **Clean up**: Remove the temp cookie file at the end of the session:
  `rm -f "$COOKIE_FILE"`

## Config file template

When setting up for the first time, create `~/.config/qbittorrent-skill/config.sh`:

```sh
# qBittorrent skill configuration
QBIT_URL="https://example.com/qbittorrent/"
QBIT_USER="your-qbit-username"
QBIT_PASS="your-qbit-password"
QBIT_HTTP_USER="your-http-basic-auth-user"
QBIT_HTTP_PASS="your-http-basic-auth-password"
```

Only set `QBIT_HTTP_USER`/`QBIT_HTTP_PASS` if there's an nginx/auth proxy in
front of qBittorrent. Otherwise leave them empty.
