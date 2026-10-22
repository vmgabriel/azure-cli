"""Integration tests of the repositories talking to the stub server."""

from __future__ import annotations

from azure_cli.application.services.work_item_field_spec import WorkItemFieldSpec
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.infrastructure.azure.html_cleaner import HtmlTextCleaner
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.git.git_api_client import AzureGitApiClient
from azure_cli.infrastructure.repositories.azure_git_repository import AzureGitRepository
from azure_cli.infrastructure.repositories.azure_work_item_repository import (
    AzureWorkItemRepository,
)
from tests.integration.stub_server import StubAzureDevOps


def _repository(client: AzureWorkItemApiClient) -> AzureWorkItemRepository:
    return AzureWorkItemRepository(client, WorkItemFieldSpec.detail(), HtmlTextCleaner())


def test_a_work_item_is_mapped_onto_the_domain(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    work_item = _repository(work_item_client).get(WorkItemId(42))

    assert work_item.id == WorkItemId(42)
    assert work_item.title == "Login fails on Safari"
    assert work_item.state.value == "Active"
    assert work_item.type.value == "Bug"
    assert work_item.story_points == 3.0
    assert work_item.assigned_to == "Ada Lovelace"
    assert work_item.created_by == "Alan Turing"
    assert work_item.area_path == "Acme/Frontend"
    assert work_item.iteration_path == "Acme/Sprint 12"


def test_the_html_is_stripped_from_the_rich_text_fields(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    work_item = _repository(work_item_client).get(WorkItemId(42))

    assert work_item.description == "The form does not submit."
    assert work_item.acceptance_criteria == "The user can log in"


def test_the_tags_are_parsed(work_item_client: AzureWorkItemApiClient) -> None:
    work_item = _repository(work_item_client).get(WorkItemId(42))

    assert [tag.value for tag in work_item.tags] == ["frontend", "p1"]
    assert work_item.has_tag("frontend") is True


def test_the_work_items_of_a_wiql_query_are_mapped(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    work_items = _repository(work_item_client).list("SELECT [System.Id] FROM WorkItems")

    assert [item.id.value for item in work_items] == [42]


def test_a_created_work_item_is_mapped(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    from azure_cli.domain.value_objects.work_item_type import WorkItemType

    work_item = _repository(work_item_client).create(
        WorkItemType("Bug"),
        "A brand new bug",
    )

    assert work_item.id == WorkItemId(43)
    assert work_item.title == "A brand new bug"


def test_an_updated_work_item_is_mapped(
    work_item_client: AzureWorkItemApiClient,
) -> None:
    work_item = _repository(work_item_client).update(
        WorkItemId(42),
        {"System.State": "Closed"},
    )

    assert work_item.state.value == "Closed"


def test_a_comment_is_mapped(work_item_client: AzureWorkItemApiClient) -> None:
    comment = _repository(work_item_client).add_comment(WorkItemId(42), "Looks good")

    assert comment.text == "Looks good"
    assert comment.author == "Ada Lovelace"


def test_the_explicit_relations_are_found(
    work_item_client: AzureWorkItemApiClient,
    git_client: AzureGitApiClient,
) -> None:
    repository = AzureGitRepository(
        work_item_client,
        git_client,
        web_base_url="https://dev.azure.com/acme/widgets",
    )

    links = repository.find_related_links(WorkItemId(42))

    pull_requests = [link for link in links if link.kind is LinkKind.PULL_REQUEST]
    assert pull_requests
    assert pull_requests[0].id == "7"
    assert pull_requests[0].url == "https://dev.azure.com/acme/widgets/_git/pullrequest/7"


def test_the_pull_requests_mentioning_the_work_item_are_found(
    work_item_client: AzureWorkItemApiClient,
    git_client: AzureGitApiClient,
) -> None:
    repository = AzureGitRepository(
        work_item_client,
        git_client,
        web_base_url="https://dev.azure.com/acme/widgets",
    )

    links = repository.find_related_links(WorkItemId(42))

    branch_links = [link for link in links if link.kind is LinkKind.BRANCH]
    assert [link.id for link in branch_links] == ["feature/login"]
    assert (
        branch_links[0].url
        == "https://dev.azure.com/acme/widgets/_git/branches?refname=feature/login"
    )


def test_the_pull_requests_are_fetched_from_the_git_api(
    work_item_client: AzureWorkItemApiClient,
    git_client: AzureGitApiClient,
    stub: StubAzureDevOps,
) -> None:
    repository = AzureGitRepository(
        work_item_client,
        git_client,
        web_base_url="https://dev.azure.com/acme/widgets",
    )

    repository.find_related_links(WorkItemId(42))

    assert any(request.path == "/_apis/git/pullrequests" for request in stub.requests)
