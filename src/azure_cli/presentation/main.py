"""Entry point of the ``azure-cli`` command.

The application itself lives in :mod:`azure_cli.presentation.cli.main`: this
module is the stable path the console script points at, and the place where
the configuration is loaded, the dependencies are wired and the application is
run.

Usage::

    azure-cli --help
    azure-cli mine --format table
    azure-cli detail 42
"""

from __future__ import annotations

from azure_cli.presentation.cli.main import app

__all__ = ["app", "main"]


def main() -> None:
    """Run the command line application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
