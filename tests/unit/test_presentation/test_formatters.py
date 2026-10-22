"""Tests of the formatters: tables, JSON and colours."""

from __future__ import annotations

import json
import sys

import pytest

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItem, WorkItemSummary
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.presentation.cli.formatters import (
    STATE_MARKER,
    colorize,
    colors_enabled,
    detail_to_dict,
    format_json,
    format_story_points,
    format_table,
    link_to_dict,
    state_style,
    summary_to_dict,
    total_story_points,
    wants_json,
    work_items_summary,
    work_items_table,
    work_items_urls,
)

#: The escape that starts an ANSI colour.
ANSI_START = "\x1b["


def _summary(work_item_id: int = 42, **overrides: object) -> WorkItemSummary:
    """Build a summary with sensible defaults."""
    defaults: dict[str, object] = {
        "id": WorkItemId(work_item_id),
        "title": "Login fails on Safari",
        "state": WorkItemState("Active"),
        "type": WorkItemType("User Story"),
        "assigned_to": "Ada Lovelace",
        "story_points": 3.0,
        "url": f"https://dev.azure.com/acme/widgets/_workitems/edit/{work_item_id}",
    }
    return WorkItemSummary(**{**defaults, **overrides})  # type: ignore[arg-type]


# -- colours -----------------------------------------------------------------
def test_a_terminal_gets_colours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert colors_enabled()


def test_a_pipe_gets_no_colours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    assert not colors_enabled()


def test_no_color_wins_over_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert not colors_enabled()


def test_the_state_decides_the_colour() -> None:
    assert state_style("Active") == "green"
    assert state_style("New") == "cyan"
    assert state_style("Ready for testing") == "yellow"
    assert state_style("Closed") == "grey62"
    assert state_style("Something else") == "white"


def test_the_text_is_coloured_when_the_terminal_allows_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert colorize("Active", "green") == f"{ANSI_START}32mActive\033[0m"


def test_an_unknown_style_leaves_the_text_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert colorize("Active", "unknown") == "Active"


def test_the_text_is_plain_when_the_colours_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")

    assert colorize("Active", "green") == "Active"


def test_the_unknown_states_are_still_rendered() -> None:
    output = work_items_table([_summary(state=WorkItemState("Weird"))])

    assert "Weird" in output


def test_the_brackets_of_a_title_are_plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "200")
    title = "[WIP] Fix [bold]crash[/bold] on [x]"

    output = work_items_table([_summary(title=title)])

    assert title in output


# -- story points -------------------------------------------------------------
def test_the_story_points_lose_the_trailing_zero() -> None:
    assert format_story_points(3.0) == "3"
    assert format_story_points(2.5) == "2.5"


def test_the_missing_story_points_are_explicit() -> None:
    assert format_story_points(None) == "N/A"


def test_the_total_ignores_the_work_items_without_points() -> None:
    summaries = [_summary(42, story_points=3.0), _summary(43, story_points=None)]

    assert total_story_points(summaries) == 3.0


def test_the_total_of_an_empty_list_is_zero() -> None:
    assert total_story_points([]) == 0.0


def test_the_summary_counts_the_work_items() -> None:
    summaries = [_summary(42, story_points=3.0), _summary(43, story_points=2.0)]

    assert work_items_summary(summaries) == "Total: 5 points in 2 work items"


def test_the_summary_uses_the_singular_for_one_work_item() -> None:
    assert work_items_summary([_summary()]) == "Total: 3 points in 1 work item"


# -- tables -------------------------------------------------------------------
def test_the_work_items_are_rendered_as_a_table() -> None:
    output = work_items_table([_summary()])

    for column in ("ID", "Points", "State", "Title"):
        assert column in output
    assert "42" in output
    assert "Login fails on Safari" in output
    assert STATE_MARKER in output


def test_the_table_does_not_render_the_url() -> None:
    output = work_items_table([_summary()])

    assert "URL" not in output
    assert "https://" not in output


def test_the_urls_are_rendered_as_a_separate_list() -> None:
    output = work_items_urls([_summary()])

    assert output.startswith("URLs:")
    assert "42: https://dev.azure.com/acme/widgets/_workitems/edit/42" in output


def test_the_urls_of_an_empty_list_are_empty() -> None:
    assert work_items_urls([]) == ""


def test_the_table_colours_the_state_when_it_can(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert ANSI_START in work_items_table([_summary()])


def test_the_table_is_plain_when_the_colours_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")

    assert ANSI_START not in work_items_table([_summary()])


def test_the_long_values_are_folded_not_cut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "40")
    value = "x" * 100

    output = format_table(("Value",), [(value,)])

    assert "…" not in output
    assert "".join(output.split()).count("x") == 100


def test_a_long_url_is_kept_whole_out_of_the_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLUMNS", "80")
    summary = _summary(title="Short title", url="https://dev.azure.com/" + "x" * 80)

    output = work_items_urls([summary])

    assert output.count("x") == 80


def test_a_table_can_be_built_by_hand() -> None:
    output = format_table(("A", "B"), [("1", "2")])

    assert "A" in output
    assert "B" in output
    assert "1" in output
    assert "2" in output


# -- JSON ---------------------------------------------------------------------
def test_the_json_is_indented_and_readable() -> None:
    output = format_json({"a": 1})

    assert output == '{\n  "a": 1\n}'


def test_the_json_keeps_the_non_ascii_characters() -> None:
    assert "café" in format_json({"name": "café"})


def test_a_summary_becomes_a_dictionary() -> None:
    payload = summary_to_dict(_summary())

    assert payload["id"] == 42
    assert payload["state"] == "Active"
    assert payload["story_points"] == 3.0
    assert payload["changed_at"] is None


def test_a_detail_becomes_a_dictionary(work_item: WorkItem) -> None:
    payload = detail_to_dict(work_item)

    assert payload["id"] == 42
    assert payload["tags"] == ["frontend", "p1"]
    assert payload["description"] == "The login form does not submit."
    assert payload["related_links"] == []


def test_a_link_becomes_a_dictionary() -> None:
    link = RelatedLink(id="7", kind=LinkKind.PULL_REQUEST, url="https://example.com/pr/7")

    payload = link_to_dict(link)

    assert payload == {
        "id": "7",
        "kind": "pull_request",
        "url": "https://example.com/pr/7",
        "title": "",
    }


def test_a_json_payload_can_be_parsed_back() -> None:
    output = format_json({"work_items": [summary_to_dict(_summary())]})

    assert json.loads(output)["work_items"][0]["title"] == "Login fails on Safari"


# -- output format ------------------------------------------------------------
def test_the_command_format_wins_over_the_configuration() -> None:
    assert wants_json("json", "text")
    assert not wants_json("table", "json")


def test_the_configuration_is_used_when_the_command_is_silent() -> None:
    assert wants_json(None, "json")
    assert not wants_json(None, "text")
