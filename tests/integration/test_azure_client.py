"""Integration tests of the Azure DevOps client against the stub server."""

from __future__ import annotations

import pytest

from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.infrastructure.azure_client import AzureDevOpsClient
from tests.integration.stub_server import StubAzureDevOps


@pytest.fixture
def client(stub: StubAzureDevOps) -> AzureDevOpsClient:
    """A client talking to the stub server."""
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        base_url=stub.base_url,
        timeout=5.0,
    )
    return AzureDevOpsClient(settings)


def test_the_work_items_are_listed(
    client: AzureDevOpsClient,
    stub: StubAzureDevOps,
) -> None:
    summaries = client.list_work_items()

    assert summaries
    assert all(isinstance(summary, WorkItemSummary) for summary in summaries)
    assert summaries[0].id.value == 42
    assert summaries[0].title == "Login fails on Safari"
    assert summaries[0].assigned_to == "Ada Lovelace"
    assert summaries[0].story_points == 3.0

    # The WIQL query was sent before the batch request.
    paths = [request.path for request in stub.requests]
    assert "/_apis/wit/wiql" in paths
    assert "/_apis/wit/workitems" in paths


def test_the_wiql_query_is_sent_to_the_server(
    client: AzureDevOpsClient,
    stub: StubAzureDevOps,
) -> None:
    client.list_work_items()

    wiql_requests = [request for request in stub.requests if request.path == "/_apis/wit/wiql"]
    assert wiql_requests

    query = wiql_requests[0].body["query"]
    assert "[System.AssignedTo] = @me" in query
    assert "ORDER BY [System.ChangedDate] DESC" in query


def test_a_work_item_is_fetched_with_its_details(
    client: AzureDevOpsClient,
) -> None:
    detail = client.get_workitem_by_id(42)

    assert isinstance(detail, WorkItemDetail)
    assert detail is not None
    assert detail.id.value == 42
    assert detail.title == "Login fails on Safari"
    assert detail.state.value == "Active"
    assert detail.type.value == "Bug"
    assert detail.area_path == "Acme/Frontend"
    assert detail.iteration_path == "Acme/Sprint 12"
    assert detail.description == "The form does not submit."
    assert detail.acceptance_criteria == "The user can log in"
    assert [tag.value for tag in detail.tags] == ["frontend", "p1"]


def test_an_unknown_work_item_returns_none(client: AzureDevOpsClient) -> None:
    assert client.get_workitem_by_id(999) is None


def test_the_related_pull_requests_are_found(client: AzureDevOpsClient) -> None:
    links = client.get_related_prs_and_branches(42)

    pull_requests = [link for link in links if link.kind is LinkKind.PULL_REQUEST]
    branches = [link for link in links if link.kind is LinkKind.BRANCH]

    assert pull_requests
    assert branches
    assert any(link.id == "feature/login" for link in branches)


def test_the_token_is_sent_with_the_requests(
    client: AzureDevOpsClient,
    stub: StubAzureDevOps,
) -> None:
    client.get_workitem_by_id(42)

    assert stub.requests
    authorization = stub.requests[0].headers.get("Authorization", "")
    assert authorization.startswith("Basic ")
