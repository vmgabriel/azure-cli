"""Integration test of the composition root against the stub server."""

from __future__ import annotations

from typer.testing import CliRunner

from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.presentation.cli.container import Container
from azure_cli.presentation.cli.main import app
from tests.integration.stub_server import StubAzureDevOps


def test_the_container_is_built_from_the_settings(stub: StubAzureDevOps) -> None:
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        base_url=stub.base_url,
    )

    container = Container.build(settings)

    assert container.settings.organization == "acme"
    assert container.get_work_item.execute(42).title == "Login fails on Safari"


def test_the_cli_works_with_a_container_built_by_the_composition_root(
    stub: StubAzureDevOps,
) -> None:
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        base_url=stub.base_url,
    )
    runner = CliRunner()

    result = runner.invoke(app, ["get", "42"], obj=Container.build(settings))

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
