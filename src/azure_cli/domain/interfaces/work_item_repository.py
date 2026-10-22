"""Port: everything the domain needs from a work item store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_type import WorkItemType


class WorkItemRepository(ABC):
    """A store of work items.

    Implemented by the infrastructure layer (``AzureWorkItemRepository``) and
    faked in the tests, so the use cases never talk to Azure DevOps directly.
    """

    @abstractmethod
    def get(self, work_item_id: WorkItemId) -> WorkItemDetail:
        """Return a single work item.

        Raises:
            WorkItemNotFoundError: if the work item does not exist.
        """

    @abstractmethod
    def list(self, query: str, *, top: int | None = None) -> list[WorkItemDetail]:
        """Return the work items matching a WIQL query."""

    @abstractmethod
    def create(
        self,
        work_item_type: WorkItemType,
        title: str,
        fields: Mapping[str, str] | None = None,
    ) -> WorkItemDetail:
        """Create a work item of the given type and return it."""

    @abstractmethod
    def update(
        self,
        work_item_id: WorkItemId,
        changes: Mapping[str, str],
    ) -> WorkItemDetail:
        """Apply the given field changes to a work item and return it."""

    @abstractmethod
    def add_comment(self, work_item_id: WorkItemId, text: str) -> WorkItemComment:
        """Add a comment to a work item and return it."""
