"""Integration tests of the Azure DevOps work item API client."""

from __future__ import annotations

import base64

import pytest

from azure_cli.domain.exceptions import (
    AuthenticationError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.http.session import build_session
from tests.integration.stub_server import StubAzureDevOps


def test_a_work_item_is_fetched(work_item_client: AzureWorkItemApiClient) -> None:
    dto = work_item_client.get_work_item(42, ["System.Title"])

    assert dto.id == 42
    assert dto.fields["System.Title"] == "Login fails on Safari"


def test_the_requested_fields_are_sent(
    work_item_client: AzureWorkItemApiClient,
    stub: StubAzureDevOps,
) -> None:
    work_item_client.get_work_item(42, ["System.Title", "System.State"])

    request = stub.requests[-1]
    assert "fields=System.Title%2CSystem.State" in request.query
    assert "api-version=7.1" in request.query


def test_the_pat_is_sent_in_the_authorization_header(
    work_item_client: AzureWorkItemApiClient,
    stub: StubAzureDevOps,
) -> None:
    work_item_client.get_work_item(42, ["System.Id"])

    expected = base64.b64encode(b":fake-token").decode()
    assert stub.requests[-1].headers["Authorization"] == f"Basic {expected}"


def test_several_work_items_are_fetched_in_one_call(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    work_items = work_item_client.get_work_items([42], ["System.Title"])

    assert len(work_items) == 1
    assert work_items[0].id == 42


def test_an_empty_batch_does_not_call_the_api(
    work_item_client: AzureWorkItemApiClient,
    stub: StubAzureDevOps,
) -> None:
    assert work_item_client.get_work_items([], ["System.Title"]) == []
    assert stub.requests == []


def test_a_wiql_query_returns_the_work_items(
    work_item_client: AzureWorkItemApiClient,
    stub: StubAzureDevOps,
) -> None:
    work_items = work_item_client.query_by_wiql(
        "SELECT [System.Id] FROM WorkItems",
        ["System.Title"],
    )

    assert [item.id for item in work_items] == [42]
    assert stub.requests[0].method == "POST"
    assert stub.requests[0].body == {"query": "SELECT [System.Id] FROM WorkItems"}


def test_a_work_item_is_created(work_item_client: AzureWorkItemApiClient) -> None:
    dto = work_item_client.create_work_item("Bug", {"System.Title": "A brand new bug"})

    assert dto.id == 43
    assert dto.fields["System.Title"] == "A brand new bug"


def test_an_update_sends_a_json_patch(work_item_client: AzureWorkItemApiClient) -> None:
    dto = work_item_client.update_work_item(42, {"System.State": "Closed"})

    assert dto.fields["System.State"] == "Closed"


def test_a_comment_is_added(work_item_client: AzureWorkItemApiClient) -> None:
    comment = work_item_client.add_comment(42, "Looks good")

    assert comment.id == 5
    assert comment.text == "Looks good"
    assert comment.created_by is not None
    assert comment.created_by.display_name == "Ada Lovelace"


def test_a_missing_work_item_raises(work_item_client: AzureWorkItemApiClient) -> None:
    with pytest.raises(WorkItemNotFoundError):
        work_item_client.get_work_item(999, ["System.Id"])


def test_a_rejected_token_raises(work_item_client: AzureWorkItemApiClient) -> None:
    with pytest.raises(AuthenticationError):
        work_item_client.get_work_item(401, ["System.Id"])


def test_an_unreachable_server_raises(stub: StubAzureDevOps) -> None:
    session = build_session("fake-token")
    client = AzureWorkItemApiClient(
        session,
        api_base_url="http://127.0.0.1:1/_apis",
        timeout=1.0,
    )

    with pytest.raises(TransportError):
        client.get_work_item(42, ["System.Id"])
