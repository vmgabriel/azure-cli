"""Use case: get the complete details of a work item."""

from __future__ import annotations

import logging

from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.exceptions import (
    AzureWiError,
    InvalidWorkItemIdError,
    WorkItemNotFoundError,
)
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway

logger = logging.getLogger(__name__)


class GetWorkItemDetailsUseCase:
    """Returns a work item with its content and its related artifacts.

    Azure DevOps splits the information of a work item in two: the work item
    itself, and the git artifacts connected to it. The use case gathers both
    and returns a single, complete :class:`WorkItemDetail`.
    """

    def __init__(self, gateway: AzureDevOpsGateway) -> None:
        """Create the use case.

        Args:
            gateway: The port used to read the work item from Azure DevOps.
        """
        self._gateway = gateway

    def execute(self, workitem_id: int) -> WorkItemDetail:
        """Return the work item and the artifacts related to it.

        Args:
            workitem_id: The identifier of the work item. It must be a
                positive integer.

        Returns:
            The work item, with its pull requests and branches.

        Raises:
            InvalidWorkItemIdError: if the identifier is not a positive
                integer. It is a ``ValueError`` as well.
            WorkItemNotFoundError: if the work item does not exist.
            AuthenticationError: if Azure DevOps rejected the credentials.
            AzureApiError: if Azure DevOps returned an unexpected response.
            TransportError: if Azure DevOps could not be reached.
        """
        self._validate(workitem_id)

        logger.info("Getting the details of work item %s", workitem_id)
        try:
            detail = self._gateway.get_workitem_by_id(workitem_id)
        except AzureWiError as exc:
            logger.error("Could not read work item %s: %s", workitem_id, exc)
            raise

        if detail is None:
            logger.warning("Work item %s was not found", workitem_id)
            raise WorkItemNotFoundError(f"Work item {workitem_id} was not found")

        try:
            links = self._gateway.get_related_prs_and_branches(workitem_id)
        except AzureWiError as exc:
            logger.error("Could not read the artifacts of work item %s: %s", workitem_id, exc)
            raise

        logger.info("Work item %s is linked to %s artifacts", workitem_id, len(links))
        return detail.with_related_links(tuple(links))

    @staticmethod
    def _validate(workitem_id: int) -> None:
        """Refuse an identifier that cannot designate a work item.

        Raises:
            InvalidWorkItemIdError: if the identifier is not a positive integer.
        """
        if isinstance(workitem_id, bool) or not isinstance(workitem_id, int) or workitem_id <= 0:
            raise InvalidWorkItemIdError(
                f"Work item id must be a positive integer, got {workitem_id!r}"
            )
