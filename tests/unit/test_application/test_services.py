"""Tests of the application services: WIQL builder, field spec and draft."""

from __future__ import annotations

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.application.services.work_item_field_spec import WorkItemFieldSpec
from azure_cli.application.services.work_item_fields import WorkItemField
from azure_cli.application.services.work_item_query import (
    WorkItemFilter,
    WorkItemQueryService,
)


def test_an_empty_filter_selects_the_open_work_items() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter())

    assert "FROM WorkItems" in wiql
    assert "[System.State] NOT IN ('Closed', 'Done', 'Resolved', 'Removed')" in wiql
    assert "[System.TeamProject] = @project" in wiql


def test_a_state_filter_replaces_the_closed_state_exclusion() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter(state="Active"))

    assert "[System.State] = 'Active'" in wiql
    assert "NOT IN" not in wiql


def test_the_filters_are_combined_with_and() -> None:
    wiql = WorkItemQueryService().build_wiql(
        WorkItemFilter(
            state="Active",
            assigned_to="Ada Lovelace",
            work_item_type="Bug",
            area_path="Acme/Frontend",
            iteration_path="Acme/Sprint 12",
        )
    )

    assert "[System.AssignedTo] = 'Ada Lovelace'" in wiql
    assert "[System.WorkItemType] = 'Bug'" in wiql
    assert "[System.AreaPath] = 'Acme/Frontend'" in wiql
    assert "[System.IterationPath] = 'Acme/Sprint 12'" in wiql
    assert wiql.count(" AND ") == 5


def test_every_tag_becomes_a_contains_clause() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter(tags=("frontend", "p1")))

    assert "[System.Tags] CONTAINS 'frontend'" in wiql
    assert "[System.Tags] CONTAINS 'p1'" in wiql


def test_a_single_quote_is_escaped() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter(state="O'Brien"))

    assert "[System.State] = 'O''Brien'" in wiql


def test_the_search_looks_at_the_title_and_the_description() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter(contains="login"))

    assert "[System.Title] CONTAINS 'login'" in wiql
    assert "[System.Description] CONTAINS 'login'" in wiql


def test_the_closed_work_items_can_be_included() -> None:
    wiql = WorkItemQueryService().build_wiql(WorkItemFilter(include_closed=True))

    assert "NOT IN" not in wiql


def test_the_detail_spec_contains_every_useful_field() -> None:
    spec = WorkItemFieldSpec.detail()

    assert WorkItemField.TITLE in spec.detail_fields
    assert WorkItemField.ACCEPTANCE_CRITERIA in spec.detail_fields
    assert WorkItemField.STORY_POINTS in spec.detail_fields


def test_the_summary_spec_is_smaller_than_the_detail_one() -> None:
    spec = WorkItemFieldSpec.detail()

    assert len(spec.summary_fields) < len(spec.detail_fields)
    assert WorkItemField.DESCRIPTION not in spec.summary_fields


def test_a_draft_maps_its_values_to_api_fields() -> None:
    fields = WorkItemDraft(
        title="A title",
        state="Active",
        description="A description",
        tags=("frontend", "p1"),
        story_points=5.0,
    ).to_api_fields()

    assert fields[WorkItemField.TITLE] == "A title"
    assert fields[WorkItemField.STATE] == "Active"
    assert fields[WorkItemField.DESCRIPTION] == "A description"
    assert fields[WorkItemField.TAGS] == "frontend;p1"
    assert fields[WorkItemField.STORY_POINTS] == "5.0"


def test_a_draft_skips_the_untouched_values() -> None:
    fields = WorkItemDraft(state="Active").to_api_fields()

    assert fields == {WorkItemField.STATE: "Active"}
