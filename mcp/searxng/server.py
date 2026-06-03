#!/usr/bin/env python3
"""MCP server for private web search via a self-contained SearXNG instance.

Manages its own SearXNG lifecycle — lazy setup on first launch, starts the
engine in the background, and tears it down on exit. No Docker, no shared
state with the searxng skill.
"""

import asyncio
import os
import secrets
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ── paths & constants ──────────────────────────────────────────────────────────

MCP_DIR = Path(__file__).resolve().parent
SEARXNG_HOME = MCP_DIR / ".searxng"
SRC_DIR = SEARXNG_HOME / "src"
VENV_DIR = SEARXNG_HOME / "venv"
SETTINGS_FILE = SEARXNG_HOME / "settings.yml"
PID_FILE = SEARXNG_HOME / "searxng.pid"
LOG_FILE = SEARXNG_HOME / "searxng.log"
CONFIG_TEMPLATE = MCP_DIR / "config" / "settings.yml"

SEARXNG_ZIP_URL = "https://github.com/searxng/searxng/archive/refs/heads/master.zip"
SEARXNG_PORT = 8889
SEARXNG_URL = f"http://127.0.0.1:{SEARXNG_PORT}"
STARTUP_TIMEOUT = 15
STOP_TIMEOUT = 10

_searxng_process: Optional[subprocess.Popen] = None


# ── sync helpers ───────────────────────────────────────────────────────────────

def _venv_python() -> str:
    return str(VENV_DIR / "bin" / "python3")


def _check_python():
    if sys.version_info < (3, 10):
        print(f"error: Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}", file=sys.stderr)
        sys.exit(1)


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None
    return pid if _pid_running(pid) else None


def _is_setup() -> bool:
    return SRC_DIR.exists() and VENV_DIR.exists() and SETTINGS_FILE.exists()


def _setup_searxng():
    """One-time: download, extract, venv, install, configure SearXNG."""
    _check_python()

    SEARXNG_HOME.mkdir(parents=True, exist_ok=True)

    # download & extract
    if not SRC_DIR.exists():
        zip_path = SEARXNG_HOME / "master.zip"
        print("Downloading SearXNG...", file=sys.stderr)
        try:
            urllib.request.urlretrieve(SEARXNG_ZIP_URL, zip_path)
        except Exception as e:
            print(f"error: Failed to download SearXNG: {e}", file=sys.stderr)
            sys.exit(1)
        print("Extracting...", file=sys.stderr)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(SEARXNG_HOME)
        zip_path.unlink()
        extracted = next(SEARXNG_HOME.glob("searxng-*"))
        extracted.rename(SRC_DIR)

    # venv
    if not VENV_DIR.exists():
        print("Creating virtual environment...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    # config
    if not SETTINGS_FILE.exists():
        secret = secrets.token_hex(32)
        template = CONFIG_TEMPLATE.read_text()
        SETTINGS_FILE.write_text(template.replace("__SECRET_KEY__", secret))

    # install
    pip_marker = VENV_DIR / ".pip_installed"
    if not pip_marker.exists():
        pip = str(VENV_DIR / "bin" / "pip3")
        print("Installing dependencies (this may take a minute)...", file=sys.stderr)

        subprocess.run([pip, "install", "--upgrade", "pip"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # setuptools is needed for editable installs (not bundled in venvs by default)
        subprocess.run([pip, "install", "setuptools", "wheel"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        req_file = SRC_DIR / "requirements.txt"
        if req_file.exists():
            subprocess.run([pip, "install", "-r", str(req_file)], check=True)

        try:
            subprocess.run([pip, "install", "-e", str(SRC_DIR)], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(
                [pip, "install", "-e", str(SRC_DIR), "--no-build-isolation"],
                check=True,
            )

        pip_marker.touch()

    print("SearXNG setup complete.", file=sys.stderr)


# ── async lifecycle ────────────────────────────────────────────────────────────

async def _health_check() -> bool:
    """Return True if SearXNG on SEARXNG_PORT responds with valid JSON."""
    url = f"{SEARXNG_URL}/search?q=ping&format=json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            if resp.status_code != 200:
                return False
            body = resp.json()
            return "results" in body
    except Exception:
        return False


async def _start_searxng():
    """Start SearXNG as a subprocess and wait until healthy. Returns the Popen object."""
    existing_pid = _read_pid()
    if existing_pid and await _health_check():
        print(f"SearXNG already running (PID {existing_pid})", file=sys.stderr)
        return None  # caller won't own it

    if existing_pid:
        print("Stale PID file — cleaning up.", file=sys.stderr)
        PID_FILE.unlink(missing_ok=True)

    if not _is_setup():
        _setup_searxng()

    env = os.environ.copy()
    env["SEARXNG_SETTINGS_PATH"] = str(SETTINGS_FILE)

    log_fh = open(LOG_FILE, "a")
    python_bin = _venv_python()

    process = subprocess.Popen(
        [python_bin, "-m", "searx.webapp"],
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=str(SRC_DIR),
        start_new_session=True,
    )

    PID_FILE.write_text(str(process.pid))
    print(f"Started SearXNG (PID {process.pid}), waiting for health check...", file=sys.stderr)

    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(f"error: SearXNG exited immediately (code {process.returncode}). "
                  f"Check logs: {LOG_FILE}", file=sys.stderr)
            sys.exit(1)
        if await _health_check():
            print(f"SearXNG ready on {SEARXNG_URL}", file=sys.stderr)
            return process
        await asyncio.sleep(0.5)

    print(f"error: SearXNG did not become healthy within {STARTUP_TIMEOUT}s. "
          f"Check logs: {LOG_FILE}", file=sys.stderr)
    sys.exit(1)


async def _stop_searxng(process: Optional[subprocess.Popen]):
    """Gracefully stop the SearXNG subprocess."""
    if process is None:
        return
    pid = process.pid
    print("Stopping SearXNG...", file=sys.stderr)
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        PID_FILE.unlink(missing_ok=True)
        return

    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline:
        if not _pid_running(pid):
            print("SearXNG stopped.", file=sys.stderr)
            PID_FILE.unlink(missing_ok=True)
            return
        await asyncio.sleep(0.2)

    print("Force-killing SearXNG...", file=sys.stderr)
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass
    PID_FILE.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(app):
    global _searxng_process
    _searxng_process = await _start_searxng()
    try:
        yield
    finally:
        await _stop_searxng(_searxng_process)


# ── server & tool ──────────────────────────────────────────────────────────────

mcp = FastMCP("searxng_mcp", lifespan=lifespan)


class SearchInput(BaseModel):
    """Input for web search."""
    model_config = {"str_strip_whitespace": True, "extra": "forbid"}

    query: str = Field(
        ...,
        description="Search query string",
        min_length=1,
        max_length=500,
    )
    time_range: Optional[str] = Field(
        default=None,
        description="Filter by time: 'day', 'week', 'month', or 'year'",
        pattern=r"^(day|week|month|year)$",
    )
    language: str = Field(
        default="auto",
        description="Language code (e.g. 'en-US', 'de') or 'auto'",
    )
    safesearch: int = Field(
        default=0,
        description="Safe search level: 0=none, 1=moderate, 2=strict",
        ge=0,
        le=2,
    )


@mcp.tool(
    name="search",
    annotations={
        "title": "Web Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search(params: SearchInput) -> str:
    """Search the web using SearXNG metasearch engine.

    Returns results from multiple search engines (Google, DuckDuckGo, Bing, etc.)
    with no tracking. Supports time filtering, language selection, and safe search.

    Args:
        params: SearchInput with query and optional filters.

    Returns:
        Markdown-formatted search results with title, URL, snippet, and source engine.
    """
    url = f"{SEARXNG_URL}/search"
    req_params = {
        "q": params.query,
        "format": "json",
        "language": params.language,
        "safesearch": str(params.safesearch),
        "pageno": "1",
    }
    if params.time_range:
        req_params["time_range"] = params.time_range

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=req_params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        return "Error: SearXNG is not running. The search engine may still be starting up — try again in a few seconds."
    except httpx.TimeoutException:
        return "Error: Search request timed out. The search engine may be overloaded — try again."
    except Exception as e:
        return f"Error: Search request failed: {e}"

    results = data.get("results", [])
    if not results:
        return f"No results found for \"{params.query}\"."

    lines = [f"## Search: \"{params.query}\"", ""]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled").strip()
        url_str = r.get("url", "")
        snippet = r.get("content", "").strip()
        engine = r.get("engine", "")
        published = r.get("publishedDate") or r.get("pubdate") or ""

        lines.append(f"**{i}. [{title}]({url_str})**")
        if snippet:
            lines.append(f"> {snippet}")
        meta = engine
        if published:
            meta += f" · {published}"
        lines.append(f"*{meta}*")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
