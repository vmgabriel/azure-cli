"""Tests of the terminal rendering."""

from __future__ import annotations

import dataclasses
import json

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItem
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.presentation.cli.console import WorkItemRenderer


def test_a_work_item_is_rendered_as_text(work_item: WorkItem) -> None:
    output = WorkItemRenderer("text").render_work_item(work_item)

    assert "ID: 42" in output
    assert "Login fails on Safari" in output
    assert "The login form does not submit." in output
    assert "frontend, p1" in output


def test_the_story_points_have_no_trailing_zero(work_item: WorkItem) -> None:
    output = WorkItemRenderer("text").render_work_item(work_item)

    assert "⭐ Puntos: 3" in output


def test_a_work_item_without_story_points_says_not_available(work_item: WorkItem) -> None:
    output = WorkItemRenderer("text").render_work_item(
        dataclasses.replace(work_item, story_points=None)
    )

    assert "Puntos: N/A" in output


def test_a_work_item_is_rendered_as_json(work_item: WorkItem) -> None:
    output = WorkItemRenderer("json").render_work_item(work_item)

    payload = json.loads(output)
    assert payload["id"] == 42
    assert payload["state"] == "Active"
    assert payload["tags"] == ["frontend", "p1"]


def test_the_work_items_are_rendered_as_a_table(work_item: WorkItem) -> None:
    output = WorkItemRenderer("text").render_work_items([work_item])

    assert "ID" in output
    assert "42" in output
    assert "Login fails on Safari" in output


def test_an_empty_list_is_explicit() -> None:
    output = WorkItemRenderer("text").render_work_items([])

    assert "No se encontraron work items." in output


def test_the_work_items_are_rendered_as_json(work_item: WorkItem) -> None:
    payload = json.loads(WorkItemRenderer("json").render_work_items([work_item]))

    assert payload[0]["id"] == 42


def test_the_links_are_rendered_as_json() -> None:
    links = [RelatedLink(id="7", kind=LinkKind.PULL_REQUEST, url="https://example.com/pr/7")]

    payload = json.loads(WorkItemRenderer("json").render_links(links))

    assert payload[0]["kind"] == "pull_request"
    assert payload[0]["id"] == "7"


def test_the_links_are_rendered_as_text() -> None:
    links = [RelatedLink(id="feature/x", kind=LinkKind.BRANCH)]

    output = WorkItemRenderer("text").render_links(links)

    assert "feature/x" in output


def test_no_link_is_explicit() -> None:
    assert "No se encontraron" in WorkItemRenderer("text").render_links([])


def test_a_comment_is_rendered() -> None:
    comment = WorkItemComment(
        id=5,
        work_item_id=WorkItemId(42),
        text="Looks good",
        author="Ada Lovelace",
    )

    output = WorkItemRenderer("text").render_comment(comment)

    assert "Comentario #5" in output
    assert "Ada Lovelace" in output


def test_a_comment_is_rendered_as_json() -> None:
    comment = WorkItemComment(id=5, work_item_id=WorkItemId(42), text="Looks good")

    payload = json.loads(WorkItemRenderer("json").render_comment(comment))

    assert payload["work_item_id"] == 42
    assert payload["text"] == "Looks good"
