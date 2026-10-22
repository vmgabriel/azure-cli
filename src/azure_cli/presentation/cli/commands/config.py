"""Command: show the resolved configuration."""

from __future__ import annotations

import typer

from azure_cli.presentation.cli.container import resolve_container
from azure_cli.presentation.cli.errors import cli_errors


def register(app: typer.Typer) -> None:
    """Register the ``config`` command."""

    @app.command("config", help="Show the resolved configuration (the PAT is masked).")
    def show_config(ctx: typer.Context) -> None:
        """Show the resolved configuration (the PAT is masked)."""
        with cli_errors():
            container = resolve_container(ctx)
            settings = container.settings

            lines = [
                "⚙️  Configuración resuelta",
                f"   Organización: {settings.organization}",
                f"   Proyecto:     {settings.project}",
                f"   PAT:          {settings.masked_pat}",
                f"   API version:  {settings.api_version}",
                f"   Timeout:      {settings.timeout}s",
                f"   Formato:      {settings.output_format}",
                f"   API base URL: {settings.api_base_url}",
                f"   Perfil:       {settings.profile}",
                f"   Email:        {settings.default_email or 'N/A'}",
                f"   Slack canal:  {settings.slack_channel or 'N/A'}",
                f"   Slack token:  {settings.masked_slack_token or 'N/A'}",
            ]
            typer.echo("\n".join(lines))
