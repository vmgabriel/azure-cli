"""Root of the ``azure-cli`` command line application."""

from __future__ import annotations

import typer

from azure_cli.presentation.cli.commands import comment, create, detail, get, links, mine, update
from azure_cli.presentation.cli.commands import config as config_command
from azure_cli.presentation.cli.commands import list as list_command
from azure_cli.presentation.cli.container import CliOptions, Container

app = typer.Typer(
    name="azure-cli",
    help="Interact with Azure DevOps work items and linked pull requests from the terminal. "
    "Slack integrations are planned.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main(
    ctx: typer.Context,
    organization: str | None = typer.Option(
        None,
        "--org",
        "--organization",
        help="Azure DevOps organization.",
    ),
    project: str | None = typer.Option(None, "--project", help="Azure DevOps project."),
    pat: str | None = typer.Option(
        None,
        "--pat",
        help="Personal access token (prefer the AZURE_DEVOPS_PAT variable).",
    ),
    api_version: str | None = typer.Option(None, "--api-version", help="REST API version."),
    timeout: float | None = typer.Option(None, "--timeout", help="HTTP timeout in seconds."),
    output_format: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: text (default) or json.",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Configuration profile to use (see the config.toml file).",
    ),
) -> None:
    """Interact with Azure DevOps work items from the terminal."""
    if isinstance(ctx.obj, Container):
        # A container was injected by the tests: keep it untouched.
        return

    ctx.obj = CliOptions(
        organization=organization,
        project=project,
        pat=pat,
        api_version=api_version,
        timeout=timeout,
        output_format=output_format,
        profile=profile,
    )


for _command in (
    get,
    list_command,
    create,
    update,
    comment,
    links,
    config_command,
    mine,
    detail,
):
    _command.register(app)
