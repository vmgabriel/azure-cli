"""Command: update the fields of a work item."""

from __future__ import annotations

import typer

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``update`` command."""

    @app.command("update", help="Update the fields of a work item.")
    def update_work_item(
        ctx: typer.Context,
        work_item_id: int = typer.Argument(..., metavar="ID", help="Id of the work item."),
        title: str | None = typer.Option(None, "--title", help="New title."),
        state: str | None = typer.Option(None, "--state", "-s", help="New state."),
        description: str | None = typer.Option(
            None,
            "--description",
            "-d",
            help="New description.",
        ),
        acceptance_criteria: str | None = typer.Option(
            None,
            "--acceptance-criteria",
            "-c",
            help="New acceptance criteria.",
        ),
        tag: list[str] = typer.Option([], "--tag", help="Replace the tags (repeatable)."),
        story_points: float | None = typer.Option(
            None,
            "--story-points",
            "-p",
            help="New story points.",
        ),
        area_path: str | None = typer.Option(None, "--area", help="New area path."),
        iteration_path: str | None = typer.Option(None, "--iteration", help="New iteration path."),
        assigned_to: str | None = typer.Option(None, "--assigned-to", "-a", help="New assignee."),
    ) -> None:
        """Update the fields of a work item."""
        with cli_errors():
            container = resolve_container(ctx)

            draft = WorkItemDraft(
                title=title,
                state=state,
                description=description,
                acceptance_criteria=acceptance_criteria,
                tags=tuple(tag),
                story_points=story_points,
                area_path=area_path,
                iteration_path=iteration_path,
                assigned_to=assigned_to,
            )

            work_item = container.update_work_item.execute(work_item_id, draft)
            renderer = WorkItemRenderer(container.settings.output_format)
            typer.echo(renderer.render_work_item(work_item))
