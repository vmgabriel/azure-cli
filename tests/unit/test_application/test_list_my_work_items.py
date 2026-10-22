"""Tests of the use case listing the work items of the current user."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.domain.entities.work_item import WorkItemSummary
from azure_cli.domain.exceptions import (
    AuthenticationError,
    TransportError,
)
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from tests.conftest import FakeAzureDevOpsGateway


def make_summary(
    work_item_id: int,
    *,
    title: str = "A work item",
    state: str = "Active",
    changed_at: datetime | None = None,
) -> WorkItemSummary:
    """Return a summary of a work item."""
    return WorkItemSummary(
        id=WorkItemId(work_item_id),
        title=title,
        state=WorkItemState(state),
        type=WorkItemType("User Story"),
        assigned_to="Ada Lovelace",
        changed_at=changed_at,
    )


def test_the_work_items_of_the_user_are_returned() -> None:
    gateway = FakeAzureDevOpsGateway(summaries=[make_summary(42), make_summary(43)])

    use_case = ListMyWorkItemsUseCase(gateway)

    summaries = use_case.execute()

    assert [summary.id.value for summary in summaries] == [42, 43]
    assert all(isinstance(summary, WorkItemSummary) for summary in summaries)


def test_the_gateway_is_asked_for_the_work_items_of_the_user() -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = ListMyWorkItemsUseCase(gateway)

    use_case.execute()

    assert gateway.list_calls == 1


def test_the_closed_work_items_are_dropped() -> None:
    gateway = FakeAzureDevOpsGateway(
        summaries=[
            make_summary(42, state="Active"),
            make_summary(43, state="Closed"),
        ]
    )

    use_case = ListMyWorkItemsUseCase(gateway)

    summaries = use_case.execute()

    assert [summary.id.value for summary in summaries] == [42]


def test_the_work_items_are_sorted_by_their_last_change() -> None:
    gateway = FakeAzureDevOpsGateway(
        summaries=[
            make_summary(42, changed_at=datetime(2024, 5, 6, 12, 0, tzinfo=UTC)),
            make_summary(43, changed_at=datetime(2024, 5, 8, 12, 0, tzinfo=UTC)),
            make_summary(44, changed_at=datetime(2024, 5, 7, 12, 0, tzinfo=UTC)),
        ]
    )

    use_case = ListMyWorkItemsUseCase(gateway)

    summaries = use_case.execute()

    assert [summary.id.value for summary in summaries] == [43, 44, 42]


def test_the_work_items_without_a_change_date_come_last() -> None:
    gateway = FakeAzureDevOpsGateway(
        summaries=[
            make_summary(42),
            make_summary(43, changed_at=datetime(2024, 5, 6, 12, 0, tzinfo=UTC)),
        ]
    )

    use_case = ListMyWorkItemsUseCase(gateway)

    summaries = use_case.execute()

    assert [summary.id.value for summary in summaries] == [43, 42]


def test_an_empty_list_is_returned_when_there_is_nothing_to_do() -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = ListMyWorkItemsUseCase(gateway)

    assert use_case.execute() == []


def test_the_failures_of_azure_devops_are_propagated() -> None:
    gateway = FakeAzureDevOpsGateway(error=AuthenticationError("bad token"))

    use_case = ListMyWorkItemsUseCase(gateway)

    with pytest.raises(AuthenticationError):
        use_case.execute()


def test_an_unreachable_azure_devops_is_propagated() -> None:
    gateway = FakeAzureDevOpsGateway(error=TransportError("network down"))

    use_case = ListMyWorkItemsUseCase(gateway)

    with pytest.raises(TransportError):
        use_case.execute()
