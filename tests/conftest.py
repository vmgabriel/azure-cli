"""Shared fixtures of the test suite."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest
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
from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItem, WorkItemDetail, WorkItemSummary
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.exceptions import WorkItemNotFoundError
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway
from azure_cli.domain.interfaces.git_repository import GitRepository
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.presentation.cli.container import Container


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in flag of the tests that call the real API."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help=("run the live tests that call the real Azure DevOps API (requires AZURE_DEVOPS_PAT)"),
    )


@pytest.fixture(autouse=True)
def isolated_environment(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Make the configuration deterministic for every test.

    The environment variables of the developer machine, the ``.env`` file of
    the project and the user level TOML file must never leak into a test.

    The live tests are the exception: they need the real credentials, so the
    environment is left untouched for them. They still run from a temporary
    working directory so that a stray ``.env`` or a written file cannot leak
    into the repository.
    """
    monkeypatch.chdir(tmp_path)
    if request.node.get_closest_marker("live") is not None:
        return

    for name in list(os.environ):
        if name.startswith(("AZURE_DEVOPS_", "AZURE_CLI_")):
            monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv(
        "AZURE_CLI_CONFIG_PATH",
        str(tmp_path / "does-not-exist.toml"),
    )


@pytest.fixture
def settings() -> AzureDevOpsSettings:
    """Settings pointing at a fake organization."""
    return AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        default_email="ada@example.com",
    )


@pytest.fixture
def work_item() -> WorkItem:
    """A work item with every field filled in."""
    return WorkItem(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        description="The login form does not submit.",
        acceptance_criteria="The user can log in.",
        tags=(Tag("frontend"), Tag("p1")),
        story_points=3.0,
        area_path="Acme/Frontend",
        iteration_path="Acme/Sprint 12",
        assigned_to="Ada Lovelace",
        created_by="Alan Turing",
        url="https://dev.azure.com/acme/widgets/_workitems/edit/42",
    )


@dataclass
class FakeWorkItemRepository(WorkItemRepository):
    """An in-memory work item repository used by the tests."""

    items: dict[int, WorkItem] = field(default_factory=dict)
    last_query: str | None = None
    last_changes: dict[str, str] = field(default_factory=dict)
    last_create: tuple[str, str, dict[str, str]] | None = None
    comments: list[tuple[int, str]] = field(default_factory=list)

    def get(self, work_item_id: WorkItemId) -> WorkItem:
        try:
            return self.items[work_item_id.value]
        except KeyError as exc:
            raise WorkItemNotFoundError(f"Work item {work_item_id.value} was not found") from exc

    def list(self, query: str, *, top: int | None = None) -> list[WorkItem]:
        self.last_query = query
        items = list(self.items.values())
        return items[:top] if top is not None else items

    def create(
        self,
        work_item_type: WorkItemType,
        title: str,
        fields: Mapping[str, str] | None = None,
    ) -> WorkItem:
        payload = dict(fields or {})
        self.last_create = (work_item_type.value, title, payload)
        created = WorkItem(
            id=WorkItemId(max(self.items, default=0) + 1),
            title=title,
            state=WorkItemState("New"),
            type=work_item_type,
            description=payload.get("System.Description", ""),
            area_path=payload.get("System.AreaPath", ""),
        )
        self.items[created.id.value] = created
        return created

    def update(
        self,
        work_item_id: WorkItemId,
        changes: Mapping[str, str],
    ) -> WorkItem:
        self.last_changes = dict(changes)
        current = self.get(work_item_id)
        updated = WorkItem(
            id=current.id,
            title=changes.get("System.Title", current.title),
            state=WorkItemState(changes.get("System.State", current.state.value)),
            type=current.type,
            description=changes.get("System.Description", current.description),
            acceptance_criteria=current.acceptance_criteria,
            tags=current.tags,
            story_points=current.story_points,
            area_path=changes.get("System.AreaPath", current.area_path),
            iteration_path=current.iteration_path,
            assigned_to=changes.get("System.AssignedTo", current.assigned_to),
            created_by=current.created_by,
            url=current.url,
        )
        self.items[work_item_id.value] = updated
        return updated

    def add_comment(self, work_item_id: WorkItemId, text: str) -> WorkItemComment:
        self.comments.append((work_item_id.value, text))
        return WorkItemComment(
            id=len(self.comments),
            work_item_id=work_item_id,
            text=text,
            author="Ada Lovelace",
        )


@dataclass
class FakeGitRepository(GitRepository):
    """A git repository returning a fixed list of links."""

    links: list[RelatedLink] = field(default_factory=list)
    requested_ids: list[int] = field(default_factory=list)

    def find_related_links(self, work_item_id: WorkItemId) -> list[RelatedLink]:
        self.requested_ids.append(work_item_id.value)
        return list(self.links)


@dataclass
class FakeAzureDevOpsGateway(AzureDevOpsGateway):
    """An in-memory Azure DevOps gateway used by the tests."""

    summaries: list[WorkItemSummary] = field(default_factory=list)
    details: dict[int, WorkItemDetail] = field(default_factory=dict)
    links: list[RelatedLink] = field(default_factory=list)
    requested_emails: list[str] = field(default_factory=list)
    requested_ids: list[int] = field(default_factory=list)
    error: Exception | None = None
    links_error: Exception | None = None

    def list_work_items(self, email: str) -> list[WorkItemSummary]:
        self.requested_emails.append(email)
        if self.error is not None:
            raise self.error
        return list(self.summaries)

    def get_workitem_by_id(self, workitem_id: int) -> WorkItemDetail | None:
        self.requested_ids.append(workitem_id)
        if self.error is not None:
            raise self.error
        return self.details.get(workitem_id)

    def get_related_prs_and_branches(self, workitem_id: int) -> list[RelatedLink]:
        self.requested_ids.append(workitem_id)
        if self.links_error is not None:
            raise self.links_error
        if self.error is not None:
            raise self.error
        return list(self.links)


@pytest.fixture
def repository(work_item: WorkItem) -> FakeWorkItemRepository:
    """A repository holding a single work item."""
    return FakeWorkItemRepository(items={work_item.id.value: work_item})


@pytest.fixture
def git_repository() -> FakeGitRepository:
    """A git repository with one pull request and one branch."""
    return FakeGitRepository(
        links=[
            RelatedLink(
                id="7",
                kind=LinkKind.PULL_REQUEST,
                url="https://dev.azure.com/acme/widgets/_git/pullrequest/7",
                title="Fix the login form",
            ),
            RelatedLink(
                id="feature/login",
                kind=LinkKind.BRANCH,
                url="https://dev.azure.com/acme/widgets/_git/branches?refname=feature/login",
            ),
        ]
    )


@pytest.fixture
def gateway() -> FakeAzureDevOpsGateway:
    """A gateway holding a single work item and its artifacts."""
    summary = WorkItemSummary(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("User Story"),
        assigned_to="Ada Lovelace",
        story_points=3.0,
        url="https://dev.azure.com/acme/widgets/_workitems/edit/42",
    )
    detail = WorkItemDetail(
        id=summary.id,
        title=summary.title,
        state=summary.state,
        type=summary.type,
        assigned_to=summary.assigned_to,
        story_points=summary.story_points,
        url=summary.url,
        description="The login form does not submit.",
        acceptance_criteria="The user can log in.",
        tags=(Tag("frontend"), Tag("p1")),
        area_path="Acme/Frontend",
        iteration_path="Acme/Sprint 12",
    )
    return FakeAzureDevOpsGateway(
        summaries=[summary],
        details={42: detail},
        links=[
            RelatedLink(
                id="7",
                kind=LinkKind.PULL_REQUEST,
                url="https://dev.azure.com/acme/widgets/_git/pullrequest/7",
                title="Fix the login form",
            ),
            RelatedLink(
                id="feature/login",
                kind=LinkKind.BRANCH,
                url="https://dev.azure.com/acme/widgets/_git/branches?refname=feature/login",
            ),
        ],
    )


@pytest.fixture
def container(
    settings: AzureDevOpsSettings,
    repository: FakeWorkItemRepository,
    git_repository: FakeGitRepository,
    gateway: FakeAzureDevOpsGateway,
) -> Container:
    """A container wired with the fake repositories."""
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


@pytest.fixture
def cli_runner() -> CliRunner:
    """A Click runner capturing the output of the CLI."""
    return CliRunner()
