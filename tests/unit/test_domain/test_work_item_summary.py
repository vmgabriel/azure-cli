"""Tests of the summary and detail projections of a work item."""

from __future__ import annotations

import pytest

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import (
    WorkItem,
    WorkItemDetail,
    WorkItemSummary,
)
from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType


def make_summary() -> WorkItemSummary:
    """Return a summary with every field filled in."""
    return WorkItemSummary(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        assigned_to="Ada Lovelace",
        story_points=3.0,
        url="https://dev.azure.com/acme/widgets/_workitems/edit/42",
    )


def test_a_summary_carries_the_essential_facts() -> None:
    summary = make_summary()

    assert summary.id.value == 42
    assert summary.title == "Login fails on Safari"
    assert summary.state.value == "Active"
    assert summary.assigned_to == "Ada Lovelace"
    assert summary.story_points == 3.0
    assert summary.type.value == "Bug"
    assert summary.url.endswith("/42")


def test_a_summary_knows_its_work_item_type() -> None:
    summary = make_summary()

    assert summary.work_item_type is summary.type


def test_a_summary_requires_a_title() -> None:
    with pytest.raises(WorkItemValidationError):
        WorkItemSummary(
            id=WorkItemId(1),
            title="   ",
            state=WorkItemState("New"),
            type=WorkItemType("Task"),
        )


def test_a_summary_reports_the_state_of_the_work_item() -> None:
    assert make_summary().is_active is True
    assert make_summary().is_closed is False


def test_a_detail_extends_the_summary() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        assigned_to="Ada Lovelace",
        story_points=3.0,
        url="https://dev.azure.com/acme/widgets/_workitems/edit/42",
        description="The login form does not submit.",
        acceptance_criteria="The user can log in.",
        tags=(Tag("frontend"),),
        area_path="Acme/Frontend",
        iteration_path="Acme/Sprint 12",
        related_links=(RelatedLink(id="7", kind=LinkKind.PULL_REQUEST),),
    )

    # The fields of the summary are still there.
    assert detail.id.value == 42
    assert detail.state.value == "Active"
    # And the ones of the detail too.
    assert detail.description == "The login form does not submit."
    assert detail.acceptance_criteria == "The user can log in."
    assert detail.tags == (Tag("frontend"),)
    assert detail.area_path == "Acme/Frontend"
    assert detail.iteration_path == "Acme/Sprint 12"
    assert detail.related_links[0].id == "7"


def test_a_detail_is_a_summary() -> None:
    assert issubclass(WorkItemDetail, WorkItemSummary)
    assert isinstance(make_summary(), WorkItemSummary)


def test_a_detail_can_be_reduced_to_a_summary() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        assigned_to="Ada Lovelace",
        story_points=3.0,
        description="The login form does not submit.",
        tags=(Tag("frontend"),),
    )

    summary = detail.to_summary()

    assert isinstance(summary, WorkItemSummary)
    assert not isinstance(summary, WorkItemDetail)
    assert summary.id == detail.id
    assert summary.title == detail.title
    assert summary.story_points == detail.story_points


def test_the_old_name_of_the_entity_still_works() -> None:
    assert WorkItem is WorkItemDetail


def test_the_related_link_exposes_its_type() -> None:
    link = RelatedLink(id="7", kind=LinkKind.PULL_REQUEST)

    assert link.type is LinkKind.PULL_REQUEST
