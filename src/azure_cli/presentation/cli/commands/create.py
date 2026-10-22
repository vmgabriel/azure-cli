"""Command: create a work item."""

from __future__ import annotations

import typer

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.presentation.cli.console import WorkItemRenderer
from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``create`` command."""

    @app.command("create", help="Create a new work item.")
    def create_work_item(
        ctx: typer.Context,
        title: str = typer.Option(..., "--title", help="Title of the work item."),
        work_item_type: str = typer.Option("Task", "--type", "-t", help="Type of the work item."),
        description: str | None = typer.Option(
            None,
            "--description",
            "-d",
            help="Description (HTML is accepted).",
        ),
        acceptance_criteria: str | None = typer.Option(
            None,
            "--acceptance-criteria",
            "-c",
            help="Acceptance criteria.",
        ),
        tag: list[str] = typer.Option([], "--tag", help="Tag of the work item (repeatable)."),
        story_points: float | None = typer.Option(
            None,
            "--story-points",
            "-p",
            help="Story points.",
        ),
        area_path: str | None = typer.Option(None, "--area", help="Area path."),
        iteration_path: str | None = typer.Option(None, "--iteration", help="Iteration path."),
        assigned_to: str | None = typer.Option(None, "--assigned-to", "-a", help="Assignee."),
    ) -> None:
        """Create a new work item."""
        with cli_errors():
            container = resolve_container(ctx)

            draft = WorkItemDraft(
                description=description,
                acceptance_criteria=acceptance_criteria,
                tags=tuple(tag),
                story_points=story_points,
                area_path=area_path,
                iteration_path=iteration_path,
                assigned_to=assigned_to,
            )

            work_item = container.create_work_item.execute(work_item_type, title, draft)
            renderer = WorkItemRenderer(container.settings.output_format)
            typer.echo(renderer.render_work_item(work_item))
