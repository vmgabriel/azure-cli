"""Command: add a comment to a work item."""

from __future__ import annotations

import typer

from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``comment`` command."""

    @app.command("comment", help="Add a comment to a work item.")
    def add_comment(
        ctx: typer.Context,
        work_item_id: int = typer.Argument(..., metavar="ID", help="Id of the work item."),
        text: str = typer.Argument(..., help="Text of the comment."),
    ) -> None:
        """Add a comment to a work item."""
        with cli_errors():
            container = resolve_container(ctx)
            comment = container.add_comment.execute(work_item_id, text)
            renderer = WorkItemRenderer(container.settings.output_format)
            typer.echo(renderer.render_comment(comment))
