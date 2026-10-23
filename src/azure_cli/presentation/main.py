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

import logging
import sys
from importlib.metadata import PackageNotFoundError, version

import typer

from azure_cli.presentation.cli.main import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

__all__ = ["app", "get_app_version", "main", "version_callback"]


def get_app_version() -> str:
    """Return the installed version of ``azure-cli``.

    Falls back to a development version when the package metadata is not
    available (for example, when running straight from a source checkout).
    """
    try:
        return version("azure-cli")
    except PackageNotFoundError:
        return "0.1.0-dev"


def version_callback(value: bool) -> None:
    """Print the application version and exit when ``--version`` is used."""
    if value:
        typer.echo(f"azure-cli version {get_app_version()}")
        raise typer.Exit()


def main() -> None:
    """Run the command line application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
