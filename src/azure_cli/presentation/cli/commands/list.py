"""Command: list the work items of the project."""

from __future__ import annotations

from typing import Literal

import typer

from azure_cli.application.services.work_item_query import WorkItemFilter
from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors
from azure_cli.presentation.cli.formatters import wants_json


def register(app: typer.Typer) -> None:
    """Register the ``list`` command."""

    @app.command("list", help="List the work items of the project.")
    def list_work_items(
        ctx: typer.Context,
        state: str | None = typer.Option(
            None,
            "--state",
            "-s",
            help="Filter by state (Active, Closed...).",
        ),
        assigned_to: str | None = typer.Option(
            None,
            "--assigned-to",
            "-a",
            help="Filter by assignee.",
        ),
        area_path: str | None = typer.Option(
            None,
            "--area",
            help="Filter by area path.",
        ),
        iteration_path: str | None = typer.Option(
            None,
            "--iteration",
            help="Filter by iteration path.",
        ),
        work_item_type: str | None = typer.Option(
            None,
            "--type",
            "-t",
            help="Filter by type (Bug, Task...).",
        ),
        tag: list[str] = typer.Option([], "--tag", help="Filter by tag (repeatable)."),
        search: str | None = typer.Option(
            None,
            "--search",
            help="Search in the title and the description.",
        ),
        top: int | None = typer.Option(
            None,
            "--top",
            "-n",
            help="Maximum number of work items to show.",
        ),
        closed: bool = typer.Option(False, "--closed", help="Include the closed work items."),
        output_format: Literal["table", "json"] | None = typer.Option(
            None,
            "--format",
            "-f",
            help="Output format: table (default) or json.",
        ),
    ) -> None:
        """List the work items of the project."""
        with cli_errors():
            container = resolve_container(ctx)

            work_item_filter = WorkItemFilter(
                state=state,
                # The configured email is the default filter: the work items
                # of the user, unless another assignee is asked for.
                assigned_to=assigned_to or container.settings.default_email,
                area_path=area_path,
                iteration_path=iteration_path,
                work_item_type=work_item_type,
                tags=tuple(tag),
                contains=search,
                include_closed=closed,
            )

            work_items = container.list_work_items.execute(work_item_filter, top=top)
            as_json = wants_json(output_format, container.settings.output_format)
            renderer = WorkItemRenderer("json" if as_json else "text", colored=not as_json)
            typer.echo(renderer.render_work_items(work_items))
