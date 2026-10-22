"""Use case: update the fields of an existing work item."""

from __future__ import annotations

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_id import WorkItemId


class UpdateWorkItem:
    """Applies field changes to an existing work item."""

    def __init__(self, repository: WorkItemRepository) -> None:
        self._repository = repository

    def execute(
        self,
        work_item_id: WorkItemId | str | int,
        draft: WorkItemDraft,
    ) -> WorkItemDetail:
        """Apply the changes and return the updated work item.

        Raises:
            WorkItemValidationError: if there is nothing to update.
            WorkItemNotFoundError: if the work item does not exist.
        """
        changes = draft.to_api_fields()
        if not changes:
            raise WorkItemValidationError("Nothing to update: no field was provided")

        return self._repository.update(WorkItemId.parse(work_item_id), changes)
