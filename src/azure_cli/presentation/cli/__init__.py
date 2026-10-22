"""The Typer command line application.

``main.py`` holds the root application, ``container.py`` the composition root
and ``commands/`` one module per user action.
"""

from azure_cli.presentation.cli.main import app

__all__ = ["app"]
