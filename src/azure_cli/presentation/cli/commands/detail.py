"""Command: show the details of a work item."""

from __future__ import annotations

from typing import Literal

import typer

from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors
from azure_cli.presentation.cli.formatters import wants_json


def register(app: typer.Typer) -> None:
    """Register the ``detail`` command."""

    @app.command("detail", help="Show the details of a work item.")
    def show_work_item(
        ctx: typer.Context,
        workitem_id: int = typer.Argument(..., metavar="ID", help="Id of the work item."),
        output_format: Literal["table", "json"] | None = typer.Option(
            None,
            "--format",
            "-f",
            help="Output format: table (default) or json.",
        ),
    ) -> None:
        """Show the details of a work item.

        The work item is shown with its description, its acceptance criteria
        and the pull requests and branches related to it.
        """
        with cli_errors():
            container = resolve_container(ctx)
            work_item = container.get_workitem_details.execute(workitem_id)

            as_json = wants_json(output_format, container.settings.output_format)
            renderer = WorkItemRenderer("json" if as_json else "text", colored=not as_json)
            typer.echo(renderer.render_work_item(work_item))
