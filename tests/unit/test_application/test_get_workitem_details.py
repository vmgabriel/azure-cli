"""Tests of the use case returning the details of a work item."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.exceptions import (
    AuthenticationError,
    InvalidWorkItemIdError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from tests.conftest import FakeAzureDevOpsGateway


def make_detail(work_item_id: int = 42) -> WorkItemDetail:
    """Return a work item with its content."""
    return WorkItemDetail(
        id=WorkItemId(work_item_id),
        title="Login fails on Safari",
        state=WorkItemState("Active"),
        type=WorkItemType("Bug"),
        description="The login form does not submit.",
        assigned_to="Ada Lovelace",
    )


def test_the_work_item_is_returned() -> None:
    gateway = FakeAzureDevOpsGateway(details={42: make_detail()})

    use_case = GetWorkItemDetailsUseCase(gateway)

    detail = use_case.execute(42)

    assert isinstance(detail, WorkItemDetail)
    assert detail.id.value == 42
    assert detail.title == "Login fails on Safari"
    assert detail.description == "The login form does not submit."


def test_the_related_artifacts_are_added_to_the_work_item() -> None:
    link = RelatedLink(
        id="7",
        kind=LinkKind.PULL_REQUEST,
        url="https://dev.azure.com/acme/widgets/_git/pullrequest/7",
        title="Fix the login form",
    )
    gateway = FakeAzureDevOpsGateway(details={42: make_detail()}, links=[link])

    use_case = GetWorkItemDetailsUseCase(gateway)

    detail = use_case.execute(42)

    assert detail.related_links == (link,)
    assert detail.pull_requests == (link,)


def test_a_work_item_without_artifacts_has_no_link() -> None:
    gateway = FakeAzureDevOpsGateway(details={42: make_detail()})

    use_case = GetWorkItemDetailsUseCase(gateway)

    detail = use_case.execute(42)

    assert detail.related_links == ()


def test_the_work_item_and_its_artifacts_are_both_read() -> None:
    gateway = FakeAzureDevOpsGateway(details={42: make_detail()})

    use_case = GetWorkItemDetailsUseCase(gateway)

    use_case.execute(42)

    assert gateway.requested_ids == [42, 42]


def test_an_unknown_work_item_is_not_found() -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(WorkItemNotFoundError):
        use_case.execute(999)


@pytest.mark.parametrize("work_item_id", [0, -1, -42])
def test_an_invalid_identifier_is_refused(work_item_id: int) -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(InvalidWorkItemIdError):
        use_case.execute(work_item_id)

    assert gateway.requested_ids == []


def test_an_invalid_identifier_is_a_value_error() -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(ValueError):
        use_case.execute(0)


def test_a_boolean_is_not_an_identifier() -> None:
    gateway = FakeAzureDevOpsGateway()

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(InvalidWorkItemIdError):
        use_case.execute(True)


def test_the_failures_of_azure_devops_are_propagated() -> None:
    gateway = FakeAzureDevOpsGateway(error=AuthenticationError("bad token"))

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(AuthenticationError):
        use_case.execute(42)


def test_the_failure_of_the_artifacts_is_propagated() -> None:
    gateway = FakeAzureDevOpsGateway(
        details={42: make_detail()},
        links_error=TransportError("network down"),
    )

    use_case = GetWorkItemDetailsUseCase(gateway)

    with pytest.raises(TransportError):
        use_case.execute(42)


def test_the_gateway_is_asked_for_the_work_item_and_its_links() -> None:
    link = RelatedLink(id="7", kind=LinkKind.PULL_REQUEST)
    gateway = Mock(spec=AzureDevOpsGateway)
    gateway.get_workitem_by_id.return_value = make_detail()
    gateway.get_related_prs_and_branches.return_value = [link]

    detail = GetWorkItemDetailsUseCase(gateway).execute(42)

    gateway.get_workitem_by_id.assert_called_once_with(42)
    gateway.get_related_prs_and_branches.assert_called_once_with(42)
    assert detail.related_links == (link,)


def test_the_gateway_is_not_asked_for_links_of_a_missing_work_item() -> None:
    gateway = Mock(spec=AzureDevOpsGateway)
    gateway.get_workitem_by_id.return_value = None

    with pytest.raises(WorkItemNotFoundError):
        GetWorkItemDetailsUseCase(gateway).execute(42)

    gateway.get_related_prs_and_branches.assert_not_called()
