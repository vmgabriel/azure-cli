"""Command: list the work items assigned to the current user."""

from __future__ import annotations

from typing import Literal

import typer

from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors
from azure_cli.presentation.cli.formatters import (
    format_json,
    summary_to_dict,
    total_story_points,
    wants_json,
    work_items_summary,
    work_items_table,
)

#: The name of the command.
COMMAND_NAME = "mine"

#: An alias of the command, kept for the habits of other CLIs.
COMMAND_ALIAS = "workitems"


def register(app: typer.Typer) -> None:
    """Register the ``mine`` command."""

    def list_my_work_items(
        ctx: typer.Context,
        output_format: Literal["table", "json"] | None = typer.Option(
            None,
            "--format",
            "-f",
            help="Output format: table (default) or json.",
        ),
        limit: int | None = typer.Option(
            None,
            "--limit",
            "-n",
            help="Show at most that many work items.",
        ),
    ) -> None:
        """List the work items assigned to you.

        The work items are the active ones, the most recently changed first.
        """
        with cli_errors():
            container = resolve_container(ctx)

            if limit is not None and limit <= 0:
                raise typer.BadParameter("--limit must be a positive number.")

            summaries = container.list_my_work_items.execute()
            if limit is not None:
                summaries = summaries[:limit]

            if wants_json(output_format, container.settings.output_format):
                typer.echo(
                    format_json(
                        {
                            "count": len(summaries),
                            "total_story_points": total_story_points(summaries),
                            "work_items": [summary_to_dict(item) for item in summaries],
                        }
                    )
                )
                return

            if not summaries:
                typer.echo("No tienes work items activos asignados.")
                return

            typer.echo(work_items_table(summaries))
            typer.echo(work_items_summary(summaries))

    app.command(COMMAND_NAME, help="List the work items assigned to you.")(list_my_work_items)
    app.command(COMMAND_ALIAS, help="Alias of 'mine'.")(list_my_work_items)
