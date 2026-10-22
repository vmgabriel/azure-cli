"""Tests of the use cases."""

from __future__ import annotations

import pytest

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.application.use_cases.add_comment import AddComment
from azure_cli.application.use_cases.create_work_item import CreateWorkItem
from azure_cli.application.use_cases.get_related_links import GetRelatedLinks
from azure_cli.application.use_cases.get_work_item import GetWorkItem
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.application.use_cases.update_work_item import UpdateWorkItem
from azure_cli.domain.entities.work_item import WorkItem
from azure_cli.domain.exceptions import (
    InvalidWorkItemIdError,
    WorkItemNotFoundError,
    WorkItemValidationError,
)
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from tests.conftest import FakeGitRepository, FakeWorkItemRepository


def test_get_work_item_returns_the_work_item(repository: FakeWorkItemRepository) -> None:
    use_case = GetWorkItem(repository)

    work_item = use_case.execute(42)

    assert work_item.id == WorkItemId(42)


def test_get_work_item_accepts_a_string_id(repository: FakeWorkItemRepository) -> None:
    assert GetWorkItem(repository).execute("42").id == WorkItemId(42)


def test_get_work_item_rejects_a_wrong_id(repository: FakeWorkItemRepository) -> None:
    with pytest.raises(InvalidWorkItemIdError):
        GetWorkItem(repository).execute("not-a-number")


def test_get_work_item_reports_a_missing_work_item(
    repository: FakeWorkItemRepository,
) -> None:
    with pytest.raises(WorkItemNotFoundError):
        GetWorkItem(repository).execute(999)


def test_list_work_items_runs_a_wiql_query(repository: FakeWorkItemRepository) -> None:
    use_case = ListWorkItems(repository)

    work_items = use_case.execute(top=10)

    assert len(work_items) == 1
    assert repository.last_query is not None
    assert "FROM WorkItems" in repository.last_query


def test_create_work_item_sends_the_title(repository: FakeWorkItemRepository) -> None:
    use_case = CreateWorkItem(repository)

    created = use_case.execute("Bug", "  Something is broken  ")

    assert created.title == "Something is broken"
    assert repository.last_create is not None
    work_item_type, title, fields = repository.last_create
    assert work_item_type == "Bug"
    assert title == "Something is broken"
    assert fields["System.Title"] == "Something is broken"


def test_create_work_item_rejects_a_blank_title(
    repository: FakeWorkItemRepository,
) -> None:
    with pytest.raises(WorkItemValidationError):
        CreateWorkItem(repository).execute("Bug", "   ")


def test_update_work_item_applies_the_changes(repository: FakeWorkItemRepository) -> None:
    use_case = UpdateWorkItem(repository)

    updated = use_case.execute(42, WorkItemDraft(state="Closed"))

    assert updated.state.value == "Closed"
    assert repository.last_changes == {"System.State": "Closed"}


def test_update_work_item_without_any_change_is_rejected(
    repository: FakeWorkItemRepository,
) -> None:
    with pytest.raises(WorkItemValidationError):
        UpdateWorkItem(repository).execute(42, WorkItemDraft())


def test_add_comment_stores_the_comment(repository: FakeWorkItemRepository) -> None:
    comment = AddComment(repository).execute(42, "  Looks good  ")

    assert comment.text == "Looks good"
    assert repository.comments == [(42, "Looks good")]


def test_add_comment_rejects_a_blank_comment(repository: FakeWorkItemRepository) -> None:
    with pytest.raises(WorkItemValidationError):
        AddComment(repository).execute(42, "   ")


def test_get_related_links_returns_the_links(
    repository: FakeWorkItemRepository,
    git_repository: FakeGitRepository,
) -> None:
    use_case = GetRelatedLinks(git_repository, repository)

    links = use_case.execute(42)

    assert len(links) == 2
    assert git_repository.requested_ids == [42]


def test_get_related_links_checks_the_work_item_first(
    repository: FakeWorkItemRepository,
    git_repository: FakeGitRepository,
) -> None:
    use_case = GetRelatedLinks(git_repository, repository)

    with pytest.raises(WorkItemNotFoundError):
        use_case.execute(999)

    assert git_repository.requested_ids == []


def test_get_related_links_works_without_the_work_item_repository(
    git_repository: FakeGitRepository,
) -> None:
    links = GetRelatedLinks(git_repository).execute(42)

    assert len(links) == 2


def test_the_work_item_is_not_mutated_by_a_use_case(
    repository: FakeWorkItemRepository,
    work_item: WorkItem,
) -> None:
    UpdateWorkItem(repository).execute(42, WorkItemDraft(state="Closed"))

    assert work_item.state.value == "Active"
