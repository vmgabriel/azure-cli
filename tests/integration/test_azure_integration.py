"""Live integration tests against the real Azure DevOps API.

These tests are opt-in: they only run when ``--run-live`` is passed **and**
``AZURE_DEVOPS_PAT`` is present. They are read-only — they never create,
update or delete anything — so there is no test data to clean up.

Run them with::

    make test-integration

The known work items are configured with ``AZURE_DEVOPS_TEST_WORK_ITEM_IDS``
and the user whose work items are listed with ``AZURE_DEVOPS_DEFAULT_EMAIL``
(or ``AZURE_DEVOPS_TEST_EMAIL``).
"""

from __future__ import annotations

import pytest

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.infrastructure.azure_client import MAX_LIST_ITEMS, AzureDevOpsClient

pytestmark = [pytest.mark.integration, pytest.mark.live]


def test_list_work_items_returns_domain_summaries(
    live_client: AzureDevOpsClient,
) -> None:
    summaries = live_client.list_work_items()

    assert isinstance(summaries, list)
    assert len(summaries) <= MAX_LIST_ITEMS
    for summary in summaries:
        assert isinstance(summary, WorkItemSummary)
        assert summary.id.value > 0
        assert summary.title.strip()
        assert summary.state.value.strip()
        assert summary.type.value.strip()
        assert isinstance(summary.assigned_to, str)
        if summary.story_points is not None:
            assert summary.story_points >= 0
        if summary.changed_at is not None:
            assert summary.changed_at.tzinfo is not None


def test_list_work_items_does_not_return_duplicates(
    live_client: AzureDevOpsClient,
) -> None:
    summaries = live_client.list_work_items()

    ids = [summary.id.value for summary in summaries]

    assert len(ids) == len(set(ids))


def test_get_workitem_by_id_returns_the_full_detail(
    live_client: AzureDevOpsClient,
    test_work_item_id: int,
) -> None:
    detail = live_client.get_workitem_by_id(test_work_item_id)

    assert detail is not None
    assert isinstance(detail, WorkItemDetail)
    assert detail.id.value == test_work_item_id
    assert detail.title.strip()
    assert detail.state.value.strip()
    assert detail.type.value.strip()
    assert detail.url
    assert isinstance(detail.tags, tuple)
    assert all(tag.value for tag in detail.tags)
    assert isinstance(detail.related_links, tuple)
    if detail.story_points is not None:
        assert detail.story_points >= 0
    if detail.changed_at is not None:
        assert detail.changed_at.tzinfo is not None


def test_get_workitem_by_id_returns_none_for_an_unknown_id(
    live_client: AzureDevOpsClient,
) -> None:
    assert live_client.get_workitem_by_id(999_999_999) is None


def test_get_related_prs_and_branches_returns_domain_links(
    live_client: AzureDevOpsClient,
    test_work_item_id: int,
) -> None:
    links = live_client.get_related_prs_and_branches(test_work_item_id)

    assert isinstance(links, list)
    for link in links:
        assert isinstance(link, RelatedLink)
        assert link.id
        assert link.kind in (LinkKind.PULL_REQUEST, LinkKind.BRANCH)
        assert isinstance(link.url, str)
        assert isinstance(link.title, str)


def test_get_related_prs_and_branches_does_not_return_duplicates(
    live_client: AzureDevOpsClient,
    test_work_item_id: int,
) -> None:
    links = live_client.get_related_prs_and_branches(test_work_item_id)

    keys = [(link.kind.value, link.id) for link in links]

    assert len(keys) == len(set(keys))


def test_a_detail_can_be_reduced_to_a_summary(
    live_client: AzureDevOpsClient,
    test_work_item_id: int,
) -> None:
    detail = live_client.get_workitem_by_id(test_work_item_id)

    assert detail is not None
    summary = detail.to_summary()

    assert isinstance(summary, WorkItemSummary)
    assert not isinstance(summary, WorkItemDetail)
    assert summary.id == detail.id
    assert summary.title == detail.title
