"""Error handling of the CLI: domain errors become readable messages."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import typer

from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    AzureWiError,
    ConfigurationError,
    DomainError,
    TransportError,
    WorkItemNotFoundError,
)

#: Exit code used for every failure caused by the tool itself.
EXIT_ERROR = 1

#: Exit code used by Typer/Click for a wrong usage (unknown flag, bad id...).
EXIT_USAGE = 2


@contextmanager
def cli_errors() -> Iterator[None]:
    """Translate the exceptions of the inner layers into CLI failures.

    Every error is printed on ``stderr`` and turns into exit code ``1``; the
    usage errors keep the exit code ``2`` given by Click.
    """
    try:
        yield
    except WorkItemNotFoundError as exc:
        _fail(exc, hint="Check the work item id and the configured project.")
    except AuthenticationError as exc:
        _fail(exc, hint="Verify AZURE_DEVOPS_PAT and its 'Work Items' scope.")
    except ConfigurationError as exc:
        _fail(exc, hint="Run `azure-cli config` to see what is resolved.")
    except TransportError as exc:
        _fail(exc, hint="Check your network connection and the base URL.")
    except AzureApiError as exc:
        _fail(exc)
    except DomainError as exc:
        _fail(exc)
    except AzureWiError as exc:
        _fail(exc)


def _fail(exc: Exception, *, hint: str | None = None) -> None:
    """Print an error and stop the command with the error exit code."""
    typer.secho(f"✖ {exc}", err=True, fg=typer.colors.RED)
    if hint:
        typer.secho(f"  {hint}", err=True, fg=typer.colors.YELLOW)
    raise typer.Exit(code=EXIT_ERROR) from exc
