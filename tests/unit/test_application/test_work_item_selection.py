"""Tests of the service selecting the work items shown to the user."""

from __future__ import annotations

from datetime import UTC, datetime

from azure_cli.application.services.work_item_selection import WorkItemSelection
from azure_cli.domain.entities.work_item import WorkItemSummary
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType


def make_summary(
    work_item_id: int,
    *,
    state: str = "Active",
    changed_at: datetime | None = None,
) -> WorkItemSummary:
    """Return a summary of a work item."""
    return WorkItemSummary(
        id=WorkItemId(work_item_id),
        title="A work item",
        state=WorkItemState(state),
        type=WorkItemType("User Story"),
        changed_at=changed_at,
    )


def test_the_closed_work_items_are_dropped() -> None:
    selection = WorkItemSelection()

    summaries = selection.active_only(
        [
            make_summary(42, state="Active"),
            make_summary(43, state="Closed"),
            make_summary(44, state="Done"),
        ]
    )

    assert [summary.id.value for summary in summaries] == [42]


def test_the_work_items_are_ordered_by_their_last_change() -> None:
    selection = WorkItemSelection()

    summaries = selection.most_recent_first(
        [
            make_summary(42, changed_at=datetime(2024, 5, 6, 12, 0, tzinfo=UTC)),
            make_summary(43, changed_at=datetime(2024, 5, 8, 12, 0, tzinfo=UTC)),
        ]
    )

    assert [summary.id.value for summary in summaries] == [43, 42]


def test_the_work_items_without_a_change_date_keep_their_order() -> None:
    selection = WorkItemSelection()

    summaries = selection.most_recent_first([make_summary(42), make_summary(43)])

    assert [summary.id.value for summary in summaries] == [42, 43]


def test_the_selection_drops_the_closed_items_and_orders_the_others() -> None:
    selection = WorkItemSelection()

    summaries = selection.select(
        [
            make_summary(42, changed_at=datetime(2024, 5, 6, 12, 0, tzinfo=UTC)),
            make_summary(43, state="Closed", changed_at=datetime(2024, 5, 9, 12, 0, tzinfo=UTC)),
            make_summary(44, changed_at=datetime(2024, 5, 8, 12, 0, tzinfo=UTC)),
        ]
    )

    assert [summary.id.value for summary in summaries] == [44, 42]


def test_an_empty_selection_is_empty() -> None:
    selection = WorkItemSelection()

    assert selection.select([]) == []
