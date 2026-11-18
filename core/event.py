from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ErrorEvent:
    """One error, in a language-agnostic shape."""
    language: str                      # "python", "javascript", ...
    tool: str                          # "cpython", "node", "tsc", ...
    exception_type: str | None         # "KeyError"
    message: str                       # raw until sanitized
    error_code: str | None = None      # "E0382", "TS2322", ...
    frames: list[str] = field(default_factory=list)

    @property
    def short_type(self) -> str:
        """Last dotted part: urllib3.exceptions.MaxRetryError -> MaxRetryError."""
        return (self.exception_type or "").split(".")[-1]

    @property
    def text(self) -> str:
        """The string the ML model sees (same format as before)."""
        return f"{self.exception_type or ''} {self.message}".strip()