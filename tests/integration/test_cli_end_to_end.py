"""End to end test: the CLI talking to the stub Azure DevOps over HTTP."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from azure_cli.application.services.work_item_field_spec import WorkItemFieldSpec
from azure_cli.application.use_cases.add_comment import AddComment
from azure_cli.application.use_cases.create_work_item import CreateWorkItem
from azure_cli.application.use_cases.get_related_links import GetRelatedLinks
from azure_cli.application.use_cases.get_work_item import GetWorkItem
from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.application.use_cases.update_work_item import UpdateWorkItem
from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.infrastructure.azure.html_cleaner import HtmlTextCleaner
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.azure_client import AzureDevOpsClient
from azure_cli.infrastructure.git.git_api_client import AzureGitApiClient
from azure_cli.infrastructure.http.session import build_session
from azure_cli.infrastructure.repositories.azure_git_repository import AzureGitRepository
from azure_cli.infrastructure.repositories.azure_work_item_repository import (
    AzureWorkItemRepository,
)
from azure_cli.presentation.cli.container import Container
from azure_cli.presentation.cli.main import app
from tests.integration.stub_server import StubAzureDevOps


def _container(stub: StubAzureDevOps) -> Container:
    """Build a container whose clients talk to the stub server."""
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        base_url=stub.base_url,
        default_email="ada@acme.com",
    )
    session = build_session(settings.pat.get_secret_value())

    work_item_client = AzureWorkItemApiClient(
        session,
        api_base_url=settings.api_base_url,
        api_version=settings.api_version,
        timeout=5.0,
    )
    git_client = AzureGitApiClient(
        session,
        api_base_url=settings.api_base_url,
        api_version=settings.api_version,
        timeout=5.0,
    )

    work_item_repository = AzureWorkItemRepository(
        work_item_client,
        WorkItemFieldSpec.detail(),
        HtmlTextCleaner(),
    )
    git_repository = AzureGitRepository(
        work_item_client,
        git_client,
        web_base_url=settings.web_base_url,
    )
    gateway = AzureDevOpsClient(settings)

    return Container(
        settings=settings,
        get_work_item=GetWorkItem(work_item_repository),
        list_work_items=ListWorkItems(work_item_repository),
        create_work_item=CreateWorkItem(work_item_repository),
        update_work_item=UpdateWorkItem(work_item_repository),
        add_comment=AddComment(work_item_repository),
        get_related_links=GetRelatedLinks(git_repository, work_item_repository),
        list_my_work_items=ListMyWorkItemsUseCase(gateway, settings),
        get_workitem_details=GetWorkItemDetailsUseCase(gateway),
    )


def test_the_cli_shows_a_work_item(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["get", "42"], obj=_container(stub))

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "The form does" in result.output


def test_the_cli_shows_the_related_links(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["get", "42", "--links"], obj=_container(stub))

    assert result.exit_code == 0
    assert "feature/login" in result.output


def test_the_cli_lists_the_work_items(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["list"], obj=_container(stub))

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output


def test_the_cli_reports_a_missing_work_item(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["get", "999"], obj=_container(stub))

    assert result.exit_code == 1
    assert "was not found" in result.output


def test_mine_lists_the_work_items_of_the_user(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mine"], obj=_container(stub))

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "Total: 3 points in 1 work item" in result.output


def test_mine_exposes_json_to_the_machines(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mine", "--format", "json"], obj=_container(stub))

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["count"] == 1
    assert payload["total_story_points"] == 3.0
    assert payload["work_items"][0]["id"] == 42


def test_detail_shows_the_work_item_and_its_artifacts(stub: StubAzureDevOps) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["detail", "42"], obj=_container(stub))

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "The form does" in result.output
    assert "feature/login" in result.output
