"""Tests of the work item entity and of its value objects."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any, cast

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


def test_a_work_item_requires_a_title() -> None:
    with pytest.raises(WorkItemValidationError):
        WorkItem(
            id=WorkItemId(1),
            title="   ",
            state=WorkItemState("New"),
            type=WorkItemType("Task"),
        )


def test_the_title_is_trimmed() -> None:
    work_item = WorkItem(
        id=WorkItemId(1),
        title="  Fix the build  ",
        state=WorkItemState("New"),
        type=WorkItemType("Task"),
    )
    assert work_item.title == "Fix the build"


def test_a_closed_work_item_is_reported_as_closed() -> None:
    work_item = WorkItem(
        id=WorkItemId(1),
        title="Done",
        state=WorkItemState("Closed"),
        type=WorkItemType("Task"),
    )
    assert work_item.is_closed is True
    assert work_item.is_active is False


def test_an_active_work_item_is_reported_as_active() -> None:
    work_item = WorkItem(
        id=WorkItemId(1),
        title="WIP",
        state=WorkItemState("Active"),
        type=WorkItemType("Task"),
    )
    assert work_item.is_active is True
    assert work_item.is_closed is False


def test_tags_are_matched_case_insensitively() -> None:
    work_item = WorkItem(
        id=WorkItemId(1),
        title="Tagged",
        state=WorkItemState("New"),
        type=WorkItemType("Task"),
        tags=(Tag("Frontend"),),
    )
    assert work_item.has_tag("frontend") is True
    assert work_item.has_tag(Tag("FRONTEND")) is True
    assert work_item.has_tag("backend") is False


def test_related_links_can_be_attached_without_mutating_the_work_item() -> None:
    work_item = WorkItem(
        id=WorkItemId(1),
        title="With links",
        state=WorkItemState("New"),
        type=WorkItemType("Task"),
    )
    links = (
        RelatedLink(id="3", kind=LinkKind.PULL_REQUEST, url="https://example.com/pr/3"),
        RelatedLink(id="feature/x", kind=LinkKind.BRANCH),
    )

    enriched = work_item.with_related_links(links)

    assert enriched.related_links == links
    assert work_item.related_links == ()
    assert enriched.pull_requests == links[:1]
    assert enriched.branches == links[1:]


def test_a_state_cannot_be_empty() -> None:
    with pytest.raises(WorkItemValidationError):
        WorkItemState("   ")


def test_a_type_cannot_be_empty() -> None:
    with pytest.raises(WorkItemValidationError):
        WorkItemType("  ")


def test_the_known_types_are_recognised() -> None:
    assert WorkItemType("Bug").is_known is True
    assert WorkItemType("Custom Process Item").is_known is False


# -- WorkItemSummary ----------------------------------------------------------


def make_summary(
    *,
    title: str = "Login fails on Safari",
    assigned_to: str = "Ada Lovelace",
    story_points: float | None = 3.0,
    url: str = "",
    changed_at: datetime | None = None,
) -> WorkItemSummary:
    """Return a summary built from the required fields and the given options."""
    return WorkItemSummary(
        id=WorkItemId(42),
        title=title,
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        assigned_to=assigned_to,
        story_points=story_points,
        url=url,
        changed_at=changed_at,
    )


def test_a_summary_can_be_created_with_only_the_required_fields() -> None:
    summary = WorkItemSummary(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
    )

    assert summary.assigned_to == ""
    assert summary.story_points is None
    assert summary.url == ""
    assert summary.changed_at is None


def test_a_summary_keeps_the_optional_values_empty() -> None:
    summary = make_summary(assigned_to="", story_points=None, url="")

    assert summary.assigned_to == ""
    assert summary.story_points is None
    assert summary.url == ""


def test_a_summary_keeps_a_zero_story_point_estimate() -> None:
    summary = make_summary(story_points=0.0)

    assert summary.story_points == 0.0
    assert summary.story_points is not None


@pytest.mark.parametrize(
    "title",
    [
        "",
        "   ",
        "\t\n",
    ],
)
def test_a_summary_rejects_a_blank_title(title: str) -> None:
    with pytest.raises(WorkItemValidationError):
        make_summary(title=title)


def test_a_summary_trims_the_surrounding_spaces_of_the_title() -> None:
    summary = make_summary(title="  Login fails on Safari  ")

    assert summary.title == "Login fails on Safari"


@pytest.mark.parametrize(
    "title",
    [
        "Corrección de la sesión: ñandú",
        "🚀 Deploy [beta] <urgent> & 'quoted'",
        'A "quoted" title / with \\ backslash',
        "Line one\nLine two",
    ],
)
def test_a_summary_preserves_the_special_characters_of_the_title(title: str) -> None:
    assert make_summary(title=title).title == title


def test_a_summary_keeps_the_time_of_the_last_change() -> None:
    changed_at = datetime(2024, 5, 6, 12, 33, 41, tzinfo=UTC)

    summary = make_summary(changed_at=changed_at)

    assert summary.changed_at == changed_at


def test_a_summary_cannot_be_mutated() -> None:
    summary = make_summary()

    with pytest.raises(FrozenInstanceError):
        summary.title = "Another title"  # type: ignore[misc]


# -- WorkItemDetail -----------------------------------------------------------


def test_a_detail_can_be_created_with_only_the_required_fields() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
    )

    assert detail.description == ""
    assert detail.acceptance_criteria == ""
    assert detail.tags == ()
    assert detail.area_path == ""
    assert detail.iteration_path == ""
    assert detail.created_by == ""
    assert detail.related_links == ()


@pytest.mark.parametrize(
    "title",
    [
        "",
        "   ",
        "\t\n",
    ],
)
def test_a_detail_rejects_a_blank_title(title: str) -> None:
    with pytest.raises(WorkItemValidationError):
        WorkItemDetail(
            id=WorkItemId(42),
            title=title,
            state=WorkItemState("Active"),
            type=WorkItemType("Bug"),
        )


def test_a_detail_preserves_the_special_characters_of_the_rich_text() -> None:
    description = "Corrección 🚀\nLa sesión <b>no</b> funciona & falla."
    acceptance_criteria = "El usuario puede entrar [sin errores]."

    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        description=description,
        acceptance_criteria=acceptance_criteria,
    )

    assert detail.description == description
    assert detail.acceptance_criteria == acceptance_criteria


def test_a_detail_converts_the_tags_and_the_links_to_tuples() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        tags=cast(Any, [Tag("Frontend")]),
        related_links=cast(
            Any,
            [RelatedLink(id="7", kind=LinkKind.PULL_REQUEST)],
        ),
    )

    assert detail.tags == (Tag("Frontend"),)
    assert detail.related_links == (RelatedLink(id="7", kind=LinkKind.PULL_REQUEST),)
    assert isinstance(detail.tags, tuple)
    assert isinstance(detail.related_links, tuple)


def test_a_detail_cannot_be_mutated() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
    )

    with pytest.raises(FrozenInstanceError):
        detail.description = "Changed"  # type: ignore[misc]


def test_the_summary_projection_keeps_every_summary_field() -> None:
    changed_at = datetime(2024, 5, 6, 12, 33, 41, tzinfo=UTC)
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        assigned_to="Ada Lovelace",
        story_points=3.0,
        url="https://dev.azure.com/acme/widgets/_workitems/edit/42",
        changed_at=changed_at,
        description="The login form does not submit.",
        tags=(Tag("frontend"),),
    )

    summary = detail.to_summary()

    assert summary.id == detail.id
    assert summary.title == detail.title
    assert summary.state == detail.state
    assert summary.type == detail.type
    assert summary.assigned_to == detail.assigned_to
    assert summary.story_points == detail.story_points
    assert summary.url == detail.url
    assert summary.changed_at == changed_at


def test_a_detail_without_related_links_has_no_pull_requests_or_branches() -> None:
    detail = WorkItemDetail(
        id=WorkItemId(42),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
    )

    assert detail.pull_requests == ()
    assert detail.branches == ()
