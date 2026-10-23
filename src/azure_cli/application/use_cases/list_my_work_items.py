"""Use case: list the work items the current user is working on."""

from __future__ import annotations

import logging

from azure_cli.application.services.work_item_selection import WorkItemSelection
from azure_cli.domain.entities.work_item import WorkItemSummary
from azure_cli.domain.exceptions import AzureWiError
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway

logger = logging.getLogger(__name__)


class ListMyWorkItemsUseCase:
    """Returns the work items assigned to the current user.

    The use case orchestrates the workflow: it asks Azure DevOps, through the
    gateway port, for the work items assigned to the user behind the
    credentials, and applies the selection rules of the application layer.

    The identity of the user is never passed as an argument nor read from the
    configuration: the ``@me`` macro lets the server resolve it from the
    request, so this use case does not need to know it. It knows nothing about
    HTTP, nor of the terminal, nor of the way the configuration was loaded:
    everything it needs is injected.
    """

    def __init__(
        self,
        gateway: AzureDevOpsGateway,
        selection: WorkItemSelection | None = None,
    ) -> None:
        """Create the use case.

        Args:
            gateway: The port used to read the work items of Azure DevOps.
            selection: The rules deciding which work items are shown. A
                default one is created when it is not given.
        """
        self._gateway = gateway
        self._selection = selection or WorkItemSelection()

    def execute(self) -> list[WorkItemSummary]:
        """Return the work items the current user is working on.

        The work items are the active ones, the most recently changed first.

        Returns:
            The summaries of the work items, in that order.

        Raises:
            AuthenticationError: if Azure DevOps rejected the credentials.
            AzureApiError: if Azure DevOps returned an unexpected response.
            TransportError: if Azure DevOps could not be reached.
        """
        logger.debug("Listing the work items assigned to the current user")
        try:
            summaries = self._gateway.list_work_items()
        except AzureWiError as exc:
            logger.error("Could not list the work items of the current user: %s", exc)
            raise

        selected = self._selection.select(summaries)
        logger.info("%s active work items found for the current user", len(selected))
        return selected
