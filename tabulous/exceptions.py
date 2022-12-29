from __future__ import annotations
import sys
from typing import Any, Callable
from types import TracebackType

__all__ = ["SelectionRangeError", "ExceptionHandler"]


class SelectionRangeError(ValueError):
    """Raised when the exception is caused by wrong selection range(s)."""


class TableImmutableError(ValueError):
    """Raised when immutable table was being tried to edit."""


class TriggerParent(RuntimeError):
    """Should try to trigger parent's keybinding instead of the current one"""


class ExceptionHandler:
    """Handle exceptions in the GUI thread."""

    def __init__(
        self, hook: Callable[[type[Exception], Exception, TracebackType], Any]
    ):
        self._excepthook = hook

    def __enter__(self):
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._excepthook
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.excepthook = self._original_excepthook
        return None
