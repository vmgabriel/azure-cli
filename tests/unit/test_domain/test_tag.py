"""Tests of the tag value object."""

from __future__ import annotations

import pytest

from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.value_objects.tag import Tag


def test_a_tag_is_normalised() -> None:
    assert Tag("  FrontEnd  ").value == "frontend"


def test_the_internal_whitespace_is_collapsed() -> None:
    assert Tag("release   blocker").value == "release blocker"


def test_an_empty_tag_is_rejected() -> None:
    with pytest.raises(WorkItemValidationError):
        Tag("   ")


def test_the_azure_devops_tag_string_is_split() -> None:
    tags = Tag.parse_many("frontend; backend ;frontend")
    assert [tag.value for tag in tags] == ["frontend", "backend"]


def test_an_empty_tag_string_yields_no_tag() -> None:
    assert Tag.parse_many(None) == ()
    assert Tag.parse_many("") == ()
