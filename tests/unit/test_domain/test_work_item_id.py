"""Tests of the work item identifier value object."""

from __future__ import annotations

import pytest

from azure_cli.domain.exceptions import InvalidWorkItemIdError
from azure_cli.domain.value_objects.work_item_id import WorkItemId


def test_accepts_a_positive_integer() -> None:
    assert WorkItemId(42).value == 42


@pytest.mark.parametrize("invalid", [0, -1])
def test_rejects_non_positive_ids(invalid: int) -> None:
    with pytest.raises(InvalidWorkItemIdError):
        WorkItemId(invalid)


def test_rejects_booleans() -> None:
    with pytest.raises(InvalidWorkItemIdError):
        WorkItemId(True)


def test_parses_a_numeric_string() -> None:
    assert WorkItemId.parse(" 42 ").value == 42


def test_parses_an_integer() -> None:
    assert WorkItemId.parse(42) == WorkItemId(42)


def test_is_idempotent_when_parsing_an_existing_id() -> None:
    identifier = WorkItemId(42)
    assert WorkItemId.parse(identifier) is identifier


def test_rejects_a_non_numeric_string() -> None:
    with pytest.raises(InvalidWorkItemIdError, match="not a valid work item id"):
        WorkItemId.parse("abc")


def test_rejects_an_empty_string() -> None:
    with pytest.raises(InvalidWorkItemIdError):
        WorkItemId.parse("   ")


def test_renders_as_its_number() -> None:
    assert str(WorkItemId(42)) == "42"
