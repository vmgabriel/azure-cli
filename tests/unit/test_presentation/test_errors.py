"""Tests of the translation of the errors into CLI failures."""

from __future__ import annotations

from collections.abc import Mapping

from typer.testing import CliRunner

from azure_cli.application.use_cases.add_comment import AddComment
from azure_cli.application.use_cases.create_work_item import CreateWorkItem
from azure_cli.application.use_cases.get_related_links import GetRelatedLinks
from azure_cli.application.use_cases.get_work_item import GetWorkItem
from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.application.use_cases.update_work_item import UpdateWorkItem
from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.domain.entities.work_item import WorkItem
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.presentation.cli.container import Container
from azure_cli.presentation.cli.main import app
from tests.conftest import FakeAzureDevOpsGateway, FakeGitRepository


class FailingRepository(WorkItemRepository):
    """A repository whose every call fails with the given error."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def get(self, work_item_id: WorkItemId) -> WorkItem:
        raise self.error

    def list(self, query: str, *, top: int | None = None) -> list[WorkItem]:
        raise self.error

    def create(
        self,
        work_item_type: WorkItemType,
        title: str,
        fields: Mapping[str, str] | None = None,
    ) -> WorkItem:
        raise self.error

    def update(
        self,
        work_item_id: WorkItemId,
        changes: Mapping[str, str],
    ) -> WorkItem:
        raise self.error

    def add_comment(self, work_item_id: WorkItemId, text: str) -> WorkItemComment:
        raise self.error


def _container(error: Exception) -> Container:
    """Build a container whose repository always fails."""
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        default_email="ada@example.com",
    )
    repository = FailingRepository(error)
    git_repository = FakeGitRepository()
    gateway = FakeAzureDevOpsGateway(error=error)

    return Container(
        settings=settings,
        get_work_item=GetWorkItem(repository),
        list_work_items=ListWorkItems(repository),
        create_work_item=CreateWorkItem(repository),
        update_work_item=UpdateWorkItem(repository),
        add_comment=AddComment(repository),
        get_related_links=GetRelatedLinks(git_repository, repository),
        list_my_work_items=ListMyWorkItemsUseCase(gateway, settings),
        get_workitem_details=GetWorkItemDetailsUseCase(gateway),
    )


def test_an_authentication_error_is_explained(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        app,
        ["get", "42"],
        obj=_container(AuthenticationError("token rejected")),
    )

    assert result.exit_code == 1
    assert "token rejected" in result.output
    assert "AZURE_DEVOPS_PAT" in result.output


def test_a_transport_error_is_explained(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        app,
        ["get", "42"],
        obj=_container(TransportError("no route to host")),
    )

    assert result.exit_code == 1
    assert "no route to host" in result.output
    assert "network" in result.output


def test_an_api_error_is_reported(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        app,
        ["get", "42"],
        obj=_container(AzureApiError("HTTP 500", status_code=500)),
    )

    assert result.exit_code == 1
    assert "HTTP 500" in result.output


def test_a_missing_work_item_suggests_to_check_the_id(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        app,
        ["get", "42"],
        obj=_container(WorkItemNotFoundError("Work item 42 was not found")),
    )

    assert result.exit_code == 1
    assert "Check the work item id" in result.output


def test_the_git_repository_is_not_used_when_it_is_not_needed() -> None:
    git_repository = FakeGitRepository()

    assert git_repository.requested_ids == []
