"""Command: show the git artifacts related to a work item."""

from __future__ import annotations

import typer

from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``links`` command."""

    @app.command("links", help="Show the pull requests and branches related to a work item.")
    def show_links(
        ctx: typer.Context,
        work_item_id: int = typer.Argument(..., metavar="ID", help="Id of the work item."),
    ) -> None:
        """Show the pull requests and branches related to a work item."""
        with cli_errors():
            container = resolve_container(ctx)
            links = container.get_related_links.execute(work_item_id)
            renderer = WorkItemRenderer(container.settings.output_format)
            typer.echo(renderer.render_links(links))
