"""Use case: fetch a single work item."""

from __future__ import annotations

from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_id import WorkItemId


class GetWorkItem:
    """Retrieves one work item by id."""

    def __init__(self, repository: WorkItemRepository) -> None:
        self._repository = repository

    def execute(self, work_item_id: WorkItemId | str | int) -> WorkItemDetail:
        """Return the work item with the given id.

        Raises:
            InvalidWorkItemIdError: if the id is not a positive integer.
            WorkItemNotFoundError: if the work item does not exist.
        """
        return self._repository.get(WorkItemId.parse(work_item_id))
