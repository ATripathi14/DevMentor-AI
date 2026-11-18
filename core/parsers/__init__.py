from __future__ import annotations

from core.event import ErrorEvent
from core.parsers.python_parser import PythonParser

# Add new parsers here as languages ship. Order matters: first match wins.
PARSERS = [PythonParser()]


def parse_any(raw: str) -> ErrorEvent | None:
    """Pick the first parser that recognizes the text and return its event."""
    for parser in PARSERS:
        if parser.matches(raw):
            event = parser.parse(raw)
            if event:
                return event
    return None