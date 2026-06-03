# SearXNG Troubleshooting

## Port 8888 already in use

```bash
# Find what's using the port
lsof -i :8888
# Kill it, or change port in .searxng/settings.yml
```

## Python not found or too old

SearXNG requires Python 3.9+. Check with `python3 --version`.

On macOS, install with `brew install python@3.12`.

## Build dependencies missing (Linux)

```bash
sudo apt install -y python3-venv python3-dev \
  libxml2-dev libxslt-dev libffi-dev libssl-dev zlib1g-dev
```

On macOS, install Xcode CLI tools: `xcode-select --install`

## pip install fails

Make sure you have an up-to-date pip:
```bash
python3 -m pip install --upgrade pip wheel
```

## Zip download fails

Check your network connection. If behind a proxy:
```bash
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

## Server starts but searches return empty

The upstream search engines may be unreachable from your network. Check `.searxng/searxng.log` for errors.

Configure specific engines in `.searxng/settings.yml`:
```yaml
engines:
  - name: duckduckgo
    disabled: false
  - name: wikipedia
    disabled: false
```

## Stale PID file

If `manage.py stop` didn't clean up: `rm .searxng/searxng.pid`

## 403 Forbidden on JSON API

The `json` format must be enabled in `search.formats` in `.searxng/settings.yml`.
