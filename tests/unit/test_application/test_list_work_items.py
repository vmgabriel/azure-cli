"""Tests of the use case listing the work items matching a filter.

The repository is mocked: the use case only has to build the WIQL query, to
forward the limit and to return whatever the repository gives back (or to let
its failures bubble up unchanged).
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from azure_cli.application.services.work_item_query import WorkItemFilter
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.domain.entities.work_item import WorkItem
from azure_cli.domain.exceptions import TransportError, WorkItemNotFoundError
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from tests.conftest import FakeWorkItemRepository


def make_mocked_repository(work_items: list[WorkItem] | None = None) -> Mock:
    """Return a repository mock returning the given work items."""
    repository = Mock(spec=WorkItemRepository)
    repository.list.return_value = work_items if work_items is not None else []
    return repository


def test_the_work_items_of_the_repository_are_returned(work_item: WorkItem) -> None:
    repository = make_mocked_repository([work_item])

    work_items = ListWorkItems(repository).execute()

    assert work_items == [work_item]


def test_an_empty_result_is_returned_when_nothing_matches() -> None:
    repository = make_mocked_repository()

    assert ListWorkItems(repository).execute() == []


def test_the_query_is_sent_to_the_repository(work_item: WorkItem) -> None:
    repository = make_mocked_repository([work_item])

    ListWorkItems(repository).execute()

    repository.list.assert_called_once()
    query = repository.list.call_args.args[0]
    assert "FROM WorkItems" in query
    assert "[System.TeamProject] = @project" in query


def test_the_filter_is_translated_into_the_query(work_item: WorkItem) -> None:
    repository = make_mocked_repository([work_item])

    ListWorkItems(repository).execute(WorkItemFilter(state="Active", assigned_to="ada@acme.com"))

    query = repository.list.call_args.args[0]
    assert "[System.State] = 'Active'" in query
    assert "[System.AssignedTo] = 'ada@acme.com'" in query


def test_the_limit_is_forwarded_to_the_repository(work_item: WorkItem) -> None:
    repository = make_mocked_repository([work_item])

    ListWorkItems(repository).execute(top=5)

    assert repository.list.call_args.kwargs == {"top": 5}


def test_the_results_of_a_real_repository_are_paginated(work_item: WorkItem) -> None:
    repository = FakeWorkItemRepository(items={work_item.id.value: work_item})

    work_items = ListWorkItems(repository).execute(top=1)

    assert work_items == [work_item]
    assert repository.last_query is not None
    assert "FROM WorkItems" in repository.last_query


def test_the_errors_of_the_repository_are_propagated() -> None:
    repository = Mock(spec=WorkItemRepository)
    repository.list.side_effect = TransportError("network down")

    with pytest.raises(TransportError, match="network down"):
        ListWorkItems(repository).execute()


def test_a_missing_work_item_error_is_propagated() -> None:
    repository = Mock(spec=WorkItemRepository)
    repository.list.side_effect = WorkItemNotFoundError("gone")

    with pytest.raises(WorkItemNotFoundError):
        ListWorkItems(repository).execute()
