"""Integration tests of the use cases talking to the stub server.

The whole chain is exercised here: the use case asks the gateway port, the
infrastructure client turns it into HTTP requests, and the stub server
answers as Azure DevOps would.
"""

from __future__ import annotations

import pytest

from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.domain.exceptions import WorkItemNotFoundError
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


@pytest.fixture
def settings(stub: StubAzureDevOps) -> AzureDevOpsSettings:
    """Settings pointing at the stub server, with an e-mail address."""
    return AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="fake-token",
        base_url=stub.base_url,
        default_email="ada@acme.com",
        timeout=5.0,
    )


def test_my_work_items_are_listed(
    client: AzureDevOpsClient,
    settings: AzureDevOpsSettings,
) -> None:
    use_case = ListMyWorkItemsUseCase(client, settings)

    summaries = use_case.execute()

    assert [summary.id.value for summary in summaries] == [42]
    assert summaries[0].title == "Login fails on Safari"
    assert summaries[0].assigned_to == "Ada Lovelace"


def test_the_details_of_a_work_item_are_returned(client: AzureDevOpsClient) -> None:
    use_case = GetWorkItemDetailsUseCase(client)

    detail = use_case.execute(42)

    assert detail.id.value == 42
    assert detail.title == "Login fails on Safari"
    assert detail.description == "The form does not submit."
    assert detail.acceptance_criteria == "The user can log in"


def test_the_related_artifacts_are_returned(client: AzureDevOpsClient) -> None:
    use_case = GetWorkItemDetailsUseCase(client)

    detail = use_case.execute(42)

    assert [link.id for link in detail.pull_requests] == ["7"]
    assert [link.id for link in detail.branches] == ["feature/login"]


def test_an_unknown_work_item_is_not_found(client: AzureDevOpsClient) -> None:
    use_case = GetWorkItemDetailsUseCase(client)

    with pytest.raises(WorkItemNotFoundError):
        use_case.execute(999)
