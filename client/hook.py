"""Report uncaught Python exceptions to the local DevMentor service.

Usage:
    python -c "import client.hook; client.hook.install()"    # interactive
    or, at the top of a script:  import client.hook; client.hook.install()
"""
from __future__ import annotations

import sys
import traceback

import requests

from client.runner import fingerprint, should_notify
from core.parsers import parse_any
from sanitizer.sanitizer import assess_risk, sanitize

SERVICE_URL = "http://localhost:8765/analyze"


def report(raw_traceback: str) -> None:
    """Parse, sanitize, risk-gate, debounce, then POST. Never raises."""
    try:
        event = parse_any(raw_traceback)
        if event is None:
            return
        error_type = event.exception_type or ""
        message = sanitize(event.message)
        if assess_risk(message) == "review":
            return  # fail closed: send nothing
        fp = fingerprint(error_type, message)
        if not should_notify(fp):
            return
        requests.post(
            SERVICE_URL,
            json={"error_type": error_type, "message": message, "fingerprint": fp},
            timeout=3,
        )
    except Exception:
        pass  # the hook must never break the host program


def install() -> None:
    """Chain onto sys.excepthook so normal error output is unchanged."""
    previous = sys.excepthook

    def hook(exc_type, exc, tb):
        previous(exc_type, exc, tb)  # show the normal traceback first
        report("".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = hook