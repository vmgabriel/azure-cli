"""Global debug switch shared by the infrastructure clients.

The SQL-ish diagnostics are meant for the terminal, so they are printed to
``stdout`` instead of going through :mod:`logging`. The switch is toggled by
the ``--debug`` option of the command line application.
"""

from __future__ import annotations

import sys
from typing import Any

_DEBUG = False


def set_debug(enabled: bool) -> None:
    """Enable or disable the verbose HTTP diagnostics."""
    global _DEBUG
    _DEBUG = bool(enabled)


def is_debug() -> bool:
    """Whether the verbose HTTP diagnostics are enabled."""
    return _DEBUG


def debug_print(message: Any = "") -> None:
    """Print a diagnostic line when the debug mode is enabled."""
    if _DEBUG:
        print(message, file=sys.stdout)


def truncate_body(text: str, limit: int = 4000) -> str:
    """Shorten a response body so a sign-in page does not flood the terminal."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text) - limit} more characters]"
