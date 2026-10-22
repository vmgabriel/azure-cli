"""Port: everything the application needs to read from Azure DevOps.

The port is deliberately *read only*: it exposes the work items and the git
artifacts related to them, and nothing else. Writing to Azure DevOps goes
through the repository port
(:class:`~azure_cli.domain.interfaces.work_item_repository.WorkItemRepository`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary


class AzureDevOpsGateway(ABC):
    """A read-only view of Azure DevOps.

    Implemented by the infrastructure layer
    (``azure_cli.infrastructure.azure_client.AzureDevOpsClient``) and faked
    in the tests, so the use cases never talk to the HTTP client directly.

    The methods return domain objects: the mapping of the payloads of Azure
    DevOps onto those objects is the responsibility of the infrastructure.
    """

    @abstractmethod
    def list_work_items(self, email: str) -> list[WorkItemSummary]:
        """Return the active work items assigned to the given e-mail address.

        The work items come in the order given by Azure DevOps (the most
        recently changed first).
        """

    @abstractmethod
    def get_workitem_by_id(self, workitem_id: int) -> WorkItemDetail | None:
        """Return a work item with its full content.

        Returns:
            The work item, or ``None`` when it does not exist.
        """

    @abstractmethod
    def get_related_prs_and_branches(self, workitem_id: int) -> list[RelatedLink]:
        """Return the pull requests and branches related to a work item."""
