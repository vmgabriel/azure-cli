"""Command: show a single work item."""

from __future__ import annotations

import typer

from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``get`` command."""

    @app.command("get", help="Show a single work item.")
    def get_work_item(
        ctx: typer.Context,
        work_item_id: int = typer.Argument(..., metavar="ID", help="Id of the work item."),
        links: bool = typer.Option(
            False,
            "--links",
            "-l",
            help="Also show the related branches and pull requests.",
        ),
    ) -> None:
        """Show a single work item."""
        with cli_errors():
            container = resolve_container(ctx)
            work_item = container.get_work_item.execute(work_item_id)

            if links:
                related_links = tuple(container.get_related_links.execute(work_item.id))
                work_item = work_item.with_related_links(related_links)

            renderer = WorkItemRenderer(container.settings.output_format)
            typer.echo(renderer.render_work_item(work_item))
