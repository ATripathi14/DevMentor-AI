from __future__ import annotations

from client.runner import parse_error
from core.event import ErrorEvent


class PythonParser:
    language = "python"
    tool = "cpython"

    def matches(self, raw: str) -> bool:
        return "Traceback (most recent call last)" in raw or _looks_like_py_exception(raw)

    def parse(self, raw: str) -> ErrorEvent | None:
        parsed = parse_error(raw)
        if not parsed:
            return None
        exception_type, message = parsed
        frames = [ln.strip() for ln in raw.splitlines() if ln.lstrip().startswith("File ")]
        return ErrorEvent(language=self.language, tool=self.tool,
                          exception_type=exception_type, message=message, frames=frames)


def _looks_like_py_exception(raw: str) -> bool:
    last = raw.strip().splitlines()[-1] if raw.strip() else ""
    head = last.split(":", 1)[0].split(".")[-1]
    return head.endswith(("Error", "Exception", "Warning"))