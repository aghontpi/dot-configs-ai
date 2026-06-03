#!/usr/bin/env python3
"""Manage a local SearXNG instance for the searxng skill.

Usage:
  python manage.py setup [--force]
  python manage.py start
  python manage.py stop
  python manage.py restart
  python manage.py status [--json]
  python manage.py health [--json]
  python manage.py logs [--lines N]

All paths are relative to the skill directory.
"""

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SEARXNG_HOME = SKILL_DIR / ".searxng"
SRC_DIR = SEARXNG_HOME / "src"
VENV_DIR = SEARXNG_HOME / "venv"
SETTINGS_FILE = SEARXNG_HOME / "settings.yml"
PID_FILE = SEARXNG_HOME / "searxng.pid"
LOG_FILE = SEARXNG_HOME / "searxng.log"
CONFIG_TEMPLATE = SKILL_DIR / "config" / "settings.yml"

SEARXNG_ZIP_URL = "https://github.com/searxng/searxng/archive/refs/heads/master.zip"
SEARXNG_PORT = 8888
STARTUP_TIMEOUT = 15
STOP_TIMEOUT = 10
HEALTH_POLL_INTERVAL = 0.5

PYTHON = sys.executable


# ─── helpers ────────────────────────────────────────────────────────────────


def _emit(data):
    """Print JSON line to stdout."""
    print(json.dumps(data))


def _die(msg, code=1):
    """Print error to stderr and exit."""
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _venv_python():
    """Return path to the venv python binary."""
    return str(VENV_DIR / "bin" / "python3")


def _check_python():
    """Ensure Python 3.9+."""
    if sys.version_info < (3, 9):
        _die(f"Python 3.9+ required, found {sys.version_info.major}.{sys.version_info.minor}")


def _pid_running(pid):
    """Check if a process with the given PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _read_pid():
    """Read PID from pidfile. Returns (pid, stale) tuple."""
    if not PID_FILE.exists():
        return None, False
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None, True
    if _pid_running(pid):
        return pid, False
    return pid, True


def _uptime(pid):
    """Return process uptime in seconds, or None."""
    try:
        # macOS / BSD
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "etime="],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _do_health():
    """Check if SearXNG is healthy. Returns (healthy: bool, detail: dict)."""
    url = f"http://127.0.0.1:{SEARXNG_PORT}/search?q=ping&format=json"
    try:
        req = urllib.request.Request(url)
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            if resp.status != 200:
                return False, {"error": f"http_{resp.status}", "response_status": resp.status}
            body = json.loads(resp.read().decode())
            if "results" not in body:
                return False, {"error": "no_results_key", "response_status": 200}
            return True, {
                "results_count": len(body.get("results", [])),
                "response_time_ms": elapsed_ms,
            }
    except urllib.error.URLError as e:
        return False, {"error": "connection_refused", "detail": str(e.reason)}
    except Exception as e:
        return False, {"error": "unexpected", "detail": str(e)}


# ─── commands ───────────────────────────────────────────────────────────────


def cmd_setup(args):
    """Download, extract, create venv, install, configure SearXNG."""
    _check_python()

    steps = []
    steps_skipped = []

    # --- download ---
    if SRC_DIR.exists() and not args.force:
        steps_skipped.append("download")
    else:
        if SRC_DIR.exists():
            shutil.rmtree(SRC_DIR)
        SEARXNG_HOME.mkdir(parents=True, exist_ok=True)
        zip_path = SEARXNG_HOME / "master.zip"
        try:
            print("Downloading SearXNG...", file=sys.stderr)
            urllib.request.urlretrieve(SEARXNG_ZIP_URL, zip_path)
        except Exception as e:
            _die(f"Failed to download SearXNG: {e}\nCheck your network connection.")
        print("Extracting...", file=sys.stderr)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(SEARXNG_HOME)
        zip_path.unlink()
        extracted = next(SEARXNG_HOME.glob("searxng-*"))
        extracted.rename(SRC_DIR)
        steps.append("download")

    # --- venv ---
    if VENV_DIR.exists() and not args.force:
        steps_skipped.append("venv")
    else:
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)
        print("Creating virtual environment...", file=sys.stderr)
        subprocess.run([PYTHON, "-m", "venv", str(VENV_DIR)], check=True)
        steps.append("venv")

    # --- config (before install, so it exists even if install fails) ---
    if SETTINGS_FILE.exists() and not args.force:
        steps_skipped.append("config")
    else:
        secret = secrets.token_hex(32)
        template = CONFIG_TEMPLATE.read_text()
        settings = template.replace("__SECRET_KEY__", secret)
        SEARXNG_HOME.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(settings)
        steps.append("config")

    # --- install (deps first, then editable install with fallback) ---
    pip_marker = VENV_DIR / ".pip_installed"
    if pip_marker.exists() and not args.force:
        steps_skipped.append("install")
    else:
        pip = str(VENV_DIR / "bin" / "pip3")
        print("Installing dependencies (this may take a minute)...", file=sys.stderr)

        # Upgrade pip first
        subprocess.run([pip, "install", "--upgrade", "pip"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Pre-install build deps and runtime deps to avoid chicken-and-egg imports
        req_file = SRC_DIR / "requirements.txt"
        if req_file.exists():
            print("  → pre-installing requirements.txt...", file=sys.stderr)
            subprocess.run([pip, "install", "-r", str(req_file)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Editable install — try normal first, fall back to --no-build-isolation
        try:
            print("  → installing SearXNG (editable)...", file=sys.stderr)
            subprocess.run([pip, "install", "-e", str(SRC_DIR)], check=True)
        except subprocess.CalledProcessError:
            print("  → retrying with --no-build-isolation...", file=sys.stderr)
            subprocess.run(
                [pip, "install", "-e", str(SRC_DIR), "--no-build-isolation"],
                check=True,
            )

        pip_marker.touch()
        steps.append("install")

    if args.json:
        if steps_skipped and not steps:
            _emit({"status": "already_setup", "steps_skipped": steps_skipped})
        else:
            _emit({"status": "ok", "steps": steps, "steps_skipped": steps_skipped})
    else:
        if steps:
            print(f"Setup complete: {', '.join(steps)}")
        if steps_skipped:
            print(f"Already done: {', '.join(steps_skipped)}")


def cmd_start(args):
    """Start SearXNG in the background and wait for it to become healthy."""
    _check_python()

    pid, stale = _read_pid()
    if pid and not stale:
        healthy, detail = _do_health()
        if healthy:
            print(f"SearXNG is already running (PID {pid})")
            return
        else:
            print(f"PID {pid} exists but SearXNG is not responding. Restarting...", file=sys.stderr)
            cmd_stop(args)

    if stale:
        print("Stale PID file removed.", file=sys.stderr)
        PID_FILE.unlink(missing_ok=True)

    if not SRC_DIR.exists() or not VENV_DIR.exists():
        _die("SearXNG is not set up. Run: python manage.py setup")

    if not SETTINGS_FILE.exists():
        _die("settings.yml not found. Run: python manage.py setup")

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
    print(f"Started SearXNG (PID {process.pid}). Waiting for health check...", file=sys.stderr)

    # Poll until healthy or timeout
    deadline = time.monotonic() + STARTUP_TIMEOUT
    last_status = None
    while time.monotonic() < deadline:
        time.sleep(HEALTH_POLL_INTERVAL)
        if process.poll() is not None:
            _die(f"SearXNG exited immediately (code {process.returncode}). Check logs: {LOG_FILE}")
        healthy, detail = _do_health()
        if healthy:
            print(f"SearXNG running on http://127.0.0.1:{SEARXNG_PORT}")
            return
        # Show what's happening during the wait
        err = detail.get("error", "unknown")
        if err != last_status:
            print(f"  → {err}", file=sys.stderr)
            last_status = err

    _die(f"SearXNG did not become healthy within {STARTUP_TIMEOUT}s "
         f"(last status: {last_status}). Check logs: {LOG_FILE}")


def cmd_stop(args):
    """Stop SearXNG gracefully."""
    pid, stale = _read_pid()

    if pid is None:
        print("SearXNG is not running.")
        return

    if stale:
        print("Stale PID file cleaned up.")
        PID_FILE.unlink(missing_ok=True)
        return

    # Graceful shutdown
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print("Process already gone. Cleaning up PID file.")
        PID_FILE.unlink(missing_ok=True)
        return

    # Wait for graceful exit
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline:
        if not _pid_running(pid):
            print("SearXNG stopped.")
            PID_FILE.unlink(missing_ok=True)
            return
        time.sleep(0.2)

    # Force kill
    print("SearXNG did not stop gracefully. Force-killing...", file=sys.stderr)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(0.5)
    PID_FILE.unlink(missing_ok=True)
    print("SearXNG force-stopped.")


def cmd_restart(args):
    """Restart SearXNG."""
    pid, _ = _read_pid()
    if pid:
        cmd_stop(args)
    cmd_start(args)


def cmd_status(args):
    """Report SearXNG status."""
    pid, stale = _read_pid()

    if pid and not stale:
        uptime_str = _uptime(pid)
        if args.json:
            out = {"running": True, "pid": pid, "port": SEARXNG_PORT}
            if uptime_str:
                out["uptime"] = uptime_str
            _emit(out)
        else:
            line = f"RUNNING — PID {pid} on http://127.0.0.1:{SEARXNG_PORT}"
            if uptime_str:
                line += f" (uptime {uptime_str})"
            print(line)
        sys.exit(0)
    elif pid and stale:
        if args.json:
            _emit({"running": False, "stale_pid": True, "stale_pid_number": pid})
        else:
            print(f"STALE — PID file exists but process {pid} is dead")
        sys.exit(1)
    else:
        if args.json:
            _emit({"running": False, "stale_pid": False})
        else:
            print("STOPPED — SearXNG is not running")
        sys.exit(1)


def cmd_health(args):
    """Check SearXNG health via the JSON API."""
    healthy, detail = _do_health()
    if args.json:
        _emit({"healthy": healthy, **detail})
    else:
        if healthy:
            print(f"SearXNG is healthy — {detail['results_count']} results "
                  f"({detail['response_time_ms']}ms)")
        elif detail.get("error") == "connection_refused":
            print(f"SearXNG is not reachable on http://127.0.0.1:{SEARXNG_PORT}")
        else:
            print(f"Unexpected response from SearXNG: {detail}")
    sys.exit(0 if healthy else 1)


def cmd_logs(args):
    """Print recent SearXNG logs."""
    if not LOG_FILE.exists():
        print(f"No log file found at {LOG_FILE}")
        return
    lines = LOG_FILE.read_text().strip().split("\n")
    tail = lines[-args.lines:] if len(lines) > args.lines else lines
    print("\n".join(tail))


# ─── main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Manage local SearXNG instance")
    sub = parser.add_subparsers(dest="command")

    p_setup = sub.add_parser("setup", help="Download, install, and configure SearXNG")
    p_setup.add_argument("--force", action="store_true", help="Force re-run all steps")
    p_setup.add_argument("--json", action="store_true", help="JSON output for agents")

    sub.add_parser("start", help="Start SearXNG in the background")

    sub.add_parser("stop", help="Stop SearXNG gracefully")

    p_restart = sub.add_parser("restart", help="Stop then start SearXNG")

    p_status = sub.add_parser("status", help="Check if SearXNG is running")
    p_status.add_argument("--json", action="store_true", help="JSON output for agents")

    p_health = sub.add_parser("health", help="Verify SearXNG API is responding")
    p_health.add_argument("--json", action="store_true", help="JSON output for agents")

    p_logs = sub.add_parser("logs", help="Show recent SearXNG logs")
    p_logs.add_argument("--lines", type=int, default=50, help="Number of lines (default: 50)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "setup": cmd_setup,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "health": cmd_health,
        "logs": cmd_logs,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
