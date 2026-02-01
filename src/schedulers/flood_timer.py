"""Subprocess-based flood timer - immune to Python thread suspension on macOS."""

import subprocess
import sys
from typing import Optional


def start_flood_timer(
    duration_seconds: float,
    api_url: str = "http://localhost:8000",
    logger=None,
) -> subprocess.Popen:
    """
    Start a subprocess that sleeps then POSTs to /api/device/off.
    Uses OS process scheduling, not Python threads, so timing is reliable.
    """
    script = f"""
import time
import urllib.request
import urllib.error
import sys

duration = float(sys.argv[1])
api_url = sys.argv[2]
url = api_url.rstrip("/") + "/api/device/off"

time.sleep(duration)
try:
    req = urllib.request.Request(url, method="POST")
    urllib.request.urlopen(req, timeout=10)
except Exception:
    sys.exit(1)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(duration_seconds), api_url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if logger:
        logger.debug(f"Flood timer subprocess started (pid={process.pid}) for {duration_seconds}s")
    return process


def cancel_flood_timer(process: Optional[subprocess.Popen], logger=None) -> bool:
    """Terminate the subprocess if still running. Returns True if cancelled."""
    if process is None:
        return False
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        if logger:
            logger.debug("Flood timer subprocess cancelled")
        return True
    return False
