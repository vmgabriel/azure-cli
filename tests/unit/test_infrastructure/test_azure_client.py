"""Unit tests of the Azure DevOps REST client.

The HTTP session is mocked: the tests exercise the mapping of the payloads
onto the domain objects, the queries that are built and the way the failures
are translated into exceptions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
import requests
from requests.auth import HTTPBasicAuth

from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary
from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.infrastructure.azure_client import (
    MAX_BATCH_SIZE,
    MAX_LIST_ITEMS,
    SUMMARY_FIELDS,
    AzureDevOpsClient,
)

WIQL_RESPONSE: dict[str, Any] = {
    "queryType": "flat",
    "workItemRelations": [{"id": 42}, {"id": 43}],
}

WORK_ITEMS_RESPONSE: dict[str, Any] = {
    "value": [
        {
            "id": 42,
            "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/42",
            "fields": {
                "System.Id": 42,
                "System.Title": "Login fails on Safari",
                "System.State": "Active",
                "System.WorkItemType": "User Story",
                "System.AssignedTo": {
                    "displayName": "Ada Lovelace",
                    "uniqueName": "ada@acme.com",
                },
                "Microsoft.VSTS.Scheduling.StoryPoints": 3,
            },
        },
        {
            "id": 43,
            "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/43",
            "fields": {
                "System.Id": 43,
                "System.Title": "A brand new story",
                "System.State": "New",
                "System.WorkItemType": "User Story",
                "System.AssignedTo": "Ada Lovelace",
            },
        },
    ]
}

WORK_ITEM_DETAIL: dict[str, Any] = {
    "id": 42,
    "url": "https://dev.azure.com/acme/widgets/_apis/wit/workItems/42",
    "fields": {
        "System.Id": 42,
        "System.Title": "Login fails on Safari",
        "System.State": "Active",
        "System.WorkItemType": "Bug",
        "System.Description": "<div>The form does <b>not</b> submit.</div>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>The user can log in</li></ul>",
        "System.Tags": "frontend; p1",
        "Microsoft.VSTS.Scheduling.StoryPoints": 3,
        "System.AreaPath": "Acme/Frontend",
        "System.IterationPath": "Acme/Sprint 12",
        "System.AssignedTo": {"displayName": "Ada Lovelace"},
    },
}


def make_client(**overrides: Any) -> AzureDevOpsClient:
    """Return a client pointing at a fake organization."""
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="a-token",
        **overrides,
    )
    return AzureDevOpsClient(settings)


def make_response(
    payload: Any,
    status_code: int = 200,
) -> requests.Response:
    """Return a fake ``requests`` response."""
    response = requests.Response()
    response.status_code = status_code
    response._content = b"{}"
    response.url = "https://dev.azure.com/acme/widgets/_apis/wit/workitems"
    if payload is not None:
        import json

        response._content = json.dumps(payload).encode("utf-8")
    return response


# -- list_work_items ---------------------------------------------------------


def test_list_work_items_returns_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response(WIQL_RESPONSE)
        return make_response(WORK_ITEMS_RESPONSE)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert len(summaries) == 2
    assert all(isinstance(summary, WorkItemSummary) for summary in summaries)
    assert summaries[0].id.value == 42
    assert summaries[0].title == "Login fails on Safari"
    assert summaries[0].state.value == "Active"
    assert summaries[0].type.value == "User Story"
    assert summaries[0].assigned_to == "Ada Lovelace"
    assert summaries[0].story_points == 3.0
    assert summaries[0].url.endswith("/42")


def test_list_work_items_queries_the_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            captured["wiql"] = kwargs["json"]["query"]
            return make_response(WIQL_RESPONSE)
        captured["fields"] = kwargs["params"]["fields"]
        return make_response(WORK_ITEMS_RESPONSE)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.list_work_items()

    assert "System.Id" in captured["fields"]
    assert "System.Title" in captured["fields"]
    assert "System.State" in captured["fields"]
    assert "System.AssignedTo" in captured["fields"]
    assert "System.WorkItemType" in captured["fields"]
    assert "Microsoft.VSTS.Scheduling.StoryPoints" in captured["fields"]
    assert captured["fields"] == ",".join(SUMMARY_FIELDS)


def test_the_wiql_query_filters_on_the_current_user_and_the_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            captured["wiql"] = kwargs["json"]["query"]
            return make_response(WIQL_RESPONSE)
        return make_response(WORK_ITEMS_RESPONSE)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.list_work_items()

    query = captured["wiql"]
    assert "[System.AssignedTo] = @me" in query
    assert "ada@acme.com" not in query
    assert "'Closed'" in query
    assert "'Done'" in query
    assert "'Removed'" in query
    assert "[System.State] NOT IN" in query
    assert "[System.WorkItemType] IN ('User Story')" in query
    assert "ORDER BY [System.ChangedDate] DESC" in query


def test_list_work_items_returns_at_most_fifty_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    relations = [{"id": index} for index in range(1, 121)]

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": relations})
        return make_response({"value": []})

    monkeypatch.setattr(client.session, "request", fake_request)

    client.list_work_items()

    assert MAX_LIST_ITEMS == 50


def test_the_story_points_are_fetched_in_batches_of_two_hundred_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    relations = [{"id": index} for index in range(1, 451)]
    requested_ids: list[list[str]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": relations})
        requested_ids.append(kwargs["params"]["ids"].split(","))
        return make_response({"value": []})

    monkeypatch.setattr(client.session, "request", fake_request)

    client.list_work_items()

    # Only the first 50 ids survive the WIQL cap, but each batch respects the
    # 200 ids limit of the Azure DevOps API.
    assert MAX_BATCH_SIZE == 200
    assert all(len(chunk) <= MAX_BATCH_SIZE for chunk in requested_ids)


def test_list_work_items_without_a_match_returns_an_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        return make_response({"workItemRelations": []})

    monkeypatch.setattr(client.session, "request", fake_request)

    assert client.list_work_items() == []


def test_the_change_date_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    payload = {
        "value": [
            {
                "id": 42,
                "fields": {
                    "System.Title": "Login fails on Safari",
                    "System.State": "Active",
                    "System.WorkItemType": "User Story",
                    "System.AssignedTo": {
                        "displayName": "Ada Lovelace",
                        "uniqueName": "ada@acme.com",
                    },
                    "System.ChangedDate": "2024-05-06T12:33:41.0000000Z",
                },
            }
        ]
    }

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": [{"id": 42}]})
        return make_response(payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert summaries[0].changed_at == datetime(2024, 5, 6, 12, 33, 41, tzinfo=UTC)


def test_an_unreadable_change_date_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    payload = {
        "value": [
            {
                "id": 42,
                "fields": {
                    "System.Title": "Login fails on Safari",
                    "System.State": "Active",
                    "System.WorkItemType": "User Story",
                    "System.AssignedTo": {
                        "displayName": "Ada Lovelace",
                        "uniqueName": "ada@acme.com",
                    },
                    "System.ChangedDate": "not a date",
                },
            }
        ]
    }

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": [{"id": 42}]})
        return make_response(payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert summaries[0].changed_at is None


def test_the_assignee_is_not_filtered_client_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ``@me`` makes Azure DevOps answer with the right work items: whatever
    # the payload says about the assignee, the client keeps it.
    client = make_client()
    payload = {
        "value": [
            {
                "id": 42,
                "fields": {
                    "System.Title": "Resolved by the server",
                    "System.State": "Active",
                    "System.WorkItemType": "User Story",
                    "System.AssignedTo": {
                        "displayName": "Alan Turing",
                        "uniqueName": "alan@acme.com",
                    },
                },
            }
        ]
    }

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": [{"id": 42}]})
        return make_response(payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42]
    assert summaries[0].assigned_to == "Alan Turing"


def test_the_work_items_of_the_user_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    payload = {
        "value": [
            {
                "id": 42,
                "fields": {
                    "System.Title": "Mine",
                    "System.State": "Active",
                    "System.WorkItemType": "User Story",
                    "System.AssignedTo": {
                        "displayName": "Ada Lovelace",
                        "uniqueName": "ada@acme.com",
                    },
                },
            }
        ]
    }

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": [{"id": 42}]})
        return make_response(payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42]


# -- get_workitem_by_id ------------------------------------------------------


def test_get_workitem_by_id_returns_a_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(WORK_ITEM_DETAIL),
    )

    detail = client.get_workitem_by_id(42)

    assert isinstance(detail, WorkItemDetail)
    assert detail is not None
    assert detail.id.value == 42
    assert detail.title == "Login fails on Safari"
    assert detail.state.value == "Active"
    assert detail.type.value == "Bug"
    assert detail.area_path == "Acme/Frontend"
    assert detail.iteration_path == "Acme/Sprint 12"
    assert detail.story_points == 3.0
    assert [tag.value for tag in detail.tags] == ["frontend", "p1"]


def test_get_workitem_by_id_cleans_the_html(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(WORK_ITEM_DETAIL),
    )

    detail = client.get_workitem_by_id(42)

    assert detail is not None
    assert detail.description == "The form does not submit."
    assert detail.acceptance_criteria == "The user can log in"


def test_get_workitem_by_id_returns_none_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "not found"}, status_code=404),
    )

    assert client.get_workitem_by_id(999) is None


# -- get_related_prs_and_branches --------------------------------------------


def test_the_related_pull_requests_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    pull_requests = {
        "value": [
            {
                "pullRequestId": 7,
                "title": "Fix the login form",
                "description": "Closes #42",
                "sourceRefName": "refs/heads/feature/login",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/7",
            },
            {
                "pullRequestId": 8,
                "title": "Unrelated change",
                "description": "Nothing here",
                "sourceRefName": "refs/heads/main",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/8",
            },
        ]
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(pull_requests),
    )

    links = client.get_related_prs_and_branches(42)

    pull_request_links = [link for link in links if link.kind is LinkKind.PULL_REQUEST]
    branch_links = [link for link in links if link.kind is LinkKind.BRANCH]

    # Only the pull request mentioning the work item in its description.
    assert [link.id for link in pull_request_links] == ["7"]
    assert branch_links
    assert any(link.id == "feature/login" for link in branch_links)


def test_the_related_links_are_empty_when_the_search_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def boom(*args: Any, **kwargs: Any) -> requests.Response:
        raise requests.RequestException("network down")

    monkeypatch.setattr(client.session, "request", boom)

    assert client.get_related_prs_and_branches(42) == []


# -- error handling ----------------------------------------------------------


def test_an_unauthorized_response_raises_an_authentication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "nope"}, status_code=401),
    )

    with pytest.raises(AuthenticationError):
        client.list_work_items()


def test_an_api_error_raises_an_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "boom"}, status_code=500),
    )

    with pytest.raises(AzureApiError):
        client.list_work_items()


def test_an_unreachable_api_raises_a_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def boom(*args: Any, **kwargs: Any) -> requests.Response:
        raise requests.RequestException("network down")

    monkeypatch.setattr(client.session, "request", boom)

    with pytest.raises(TransportError):
        client.list_work_items()


def test_the_requests_use_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(timeout=12.0)
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        captured["timeout"] = kwargs.get("timeout")
        return make_response({"workItemRelations": []})

    monkeypatch.setattr(client.session, "request", fake_request)

    client.list_work_items()

    assert captured["timeout"] == 12.0


def test_the_pat_is_sent_with_basic_auth() -> None:
    client = make_client()

    auth = client.session.auth
    assert isinstance(auth, HTTPBasicAuth)

    assert auth.username == ""
    assert auth.password == "a-token"


def test_the_client_is_a_gateway() -> None:
    assert isinstance(make_client(), AzureDevOpsGateway)


def stub_responses(
    monkeypatch: pytest.MonkeyPatch,
    client: AzureDevOpsClient,
    wiql: dict[str, Any],
    work_items: dict[str, Any],
) -> None:
    """Make the client answer the WIQL query and the batch fetch."""

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response(wiql)
        return make_response(work_items)

    monkeypatch.setattr(client.session, "request", fake_request)


# -- error handling (continued) ----------------------------------------------


def test_a_forbidden_response_raises_an_authentication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "denied"}, status_code=403),
    )

    with pytest.raises(AuthenticationError, match="Work Items"):
        client.list_work_items()


def test_the_error_detail_is_included_in_the_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "quota exceeded"}, status_code=500),
    )

    with pytest.raises(AzureApiError, match="quota exceeded") as excinfo:
        client.list_work_items()

    assert excinfo.value.status_code == 500


def test_a_404_on_the_list_query_is_a_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"message": "missing"}, status_code=404),
    )

    with pytest.raises(WorkItemNotFoundError):
        client.list_work_items()


def test_a_non_json_error_body_is_still_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    response = requests.Response()
    response.status_code = 502
    response._content = b"<html>bad gateway</html>"
    response.url = "https://dev.azure.com/acme/widgets/_apis/wit/wiql"

    monkeypatch.setattr(client.session, "request", lambda *args, **kwargs: response)

    with pytest.raises(AzureApiError):
        client.list_work_items()


def test_a_dropped_connection_is_a_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def boom(*args: Any, **kwargs: Any) -> requests.Response:
        raise requests.ConnectionError("connection reset")

    monkeypatch.setattr(client.session, "request", boom)

    with pytest.raises(TransportError, match="Could not reach Azure DevOps"):
        client.get_workitem_by_id(42)


def test_the_default_timeout_is_used_when_the_settings_do_not_define_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(timeout=15.0)
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        captured["timeout"] = kwargs.get("timeout")
        return make_response(WORK_ITEM_DETAIL)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_workitem_by_id(42)

    assert captured["timeout"] == 15.0


# -- degraded payloads -------------------------------------------------------


def test_a_batch_response_without_a_value_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    stub_responses(
        monkeypatch,
        client,
        wiql={"workItemRelations": [{"id": 42}]},
        work_items={"unexpected": "shape"},
    )

    assert client.list_work_items() == []


def test_a_list_response_with_non_mapping_entries_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    stub_responses(
        monkeypatch,
        client,
        wiql={"workItemRelations": [{"id": 42}]},
        work_items={"value": ["not-a-dict", WORK_ITEMS_RESPONSE["value"][0]]},
    )

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42]


def test_a_list_response_with_non_mapping_fields_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    payload = {
        "value": [
            {"id": 42, "fields": "not-a-mapping"},
        ]
    }
    stub_responses(
        monkeypatch,
        client,
        wiql={"workItemRelations": [{"id": 42}]},
        work_items=payload,
    )

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42]
    assert summaries[0].title == "Work item 42"
    assert summaries[0].state.value == "New"


def test_a_work_item_without_a_readable_id_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    payload = {
        "value": [
            {"fields": dict(WORK_ITEMS_RESPONSE["value"][0]["fields"], **{"System.Id": "x"})},
            WORK_ITEMS_RESPONSE["value"][0],
        ]
    }
    stub_responses(
        monkeypatch,
        client,
        wiql={"workItemRelations": [{"id": 42}]},
        work_items=payload,
    )

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42]


def test_an_unparseable_wiql_response_is_an_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(["not", "an", "object"]),
    )

    assert client.list_work_items() == []


def test_a_wiql_response_with_relations_without_an_id_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def fake_request(method: str, url: str, **kwargs: Any) -> requests.Response:
        if url.endswith("/wit/wiql"):
            return make_response({"workItemRelations": [{"href": "…"}, {"id": 42}]})
        return make_response(WORK_ITEMS_RESPONSE)

    monkeypatch.setattr(client.session, "request", fake_request)

    summaries = client.list_work_items()

    assert [summary.id.value for summary in summaries] == [42, 43]


def test_a_detail_with_an_unexpected_payload_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(["not", "an", "object"]),
    )

    assert client.get_workitem_by_id(42) is None


def test_a_detail_with_non_mapping_fields_uses_the_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"id": 42, "fields": ["not", "a", "mapping"]}),
    )

    detail = client.get_workitem_by_id(42)

    assert detail is not None
    assert detail.title == "Work item 42"
    assert detail.state.value == "New"
    assert detail.type.value == "Task"


def test_a_detail_without_a_title_gets_a_readable_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"id": 42, "fields": {}}),
    )

    detail = client.get_workitem_by_id(42)

    assert detail is not None
    assert detail.title == "Work item 42"
    assert detail.state.value == "New"
    assert detail.type.value == "Task"
    assert detail.url.endswith("/42")


def test_a_detail_without_an_url_gets_the_browser_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    payload = {
        "id": 42,
        "fields": {
            "System.Title": "Login fails on Safari",
            "System.State": "Active",
            "System.WorkItemType": "Bug",
        },
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(payload),
    )

    detail = client.get_workitem_by_id(42)

    assert detail is not None
    assert detail.url == "https://dev.azure.com/acme/widgets/_workitems/edit/42"


# -- pull requests and branches (continued) ----------------------------------


def test_a_pull_request_without_a_url_gets_a_browser_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    pull_requests = {
        "value": [
            {
                "pullRequestId": 7,
                "title": "Fixes 42",
            }
        ]
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(pull_requests),
    )

    links = client.get_related_prs_and_branches(42)

    pull_request_links = [link for link in links if link.kind is LinkKind.PULL_REQUEST]
    assert [link.id for link in pull_request_links] == ["7"]
    assert pull_request_links[0].url.endswith("/_git/pullrequest/7")


def test_a_pull_request_without_a_source_branch_has_no_branch_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    pull_requests = {
        "value": [
            {
                "pullRequestId": 7,
                "title": "Fixes 42",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/7",
            }
        ]
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(pull_requests),
    )

    links = client.get_related_prs_and_branches(42)

    assert [link.kind for link in links] == [LinkKind.PULL_REQUEST]


def test_several_pull_requests_share_the_same_branch_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    pull_requests = {
        "value": [
            {
                "pullRequestId": 7,
                "title": "Fixes 42",
                "sourceRefName": "refs/heads/feature/login",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/7",
            },
            {
                "pullRequestId": 8,
                "title": "Also fixes 42",
                "sourceRefName": "refs/heads/feature/login",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/8",
            },
        ]
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(pull_requests),
    )

    links = client.get_related_prs_and_branches(42)

    branch_links = [link for link in links if link.kind is LinkKind.BRANCH]
    assert [link.id for link in branch_links] == ["feature/login"]
    assert len(branch_links) == 1


def test_a_pull_request_without_a_title_or_description_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    pull_requests = {
        "value": [
            {
                "pullRequestId": 7,
                "sourceRefName": "refs/heads/feature/login",
                "url": "https://dev.azure.com/acme/widgets/_git/pullrequest/7",
            }
        ]
    }

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response(pull_requests),
    )

    assert client.get_related_prs_and_branches(42) == []


def test_an_empty_pull_request_search_gives_no_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response({"value": []}),
    )

    assert client.get_related_prs_and_branches(42) == []


def test_a_pull_request_search_without_a_usable_payload_gives_no_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: make_response("not json"),
    )

    assert client.get_related_prs_and_branches(42) == []
