"""Use case: create a work item."""

from __future__ import annotations

from azure_cli.application.services.work_item_draft import WorkItemDraft
from azure_cli.application.services.work_item_fields import WorkItemField
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_type import WorkItemType


class CreateWorkItem:
    """Creates a new work item of a given type."""

    def __init__(self, repository: WorkItemRepository) -> None:
        self._repository = repository

    def execute(
        self,
        work_item_type: str,
        title: str,
        draft: WorkItemDraft | None = None,
    ) -> WorkItemDetail:
        """Create the work item and return it.

        Raises:
            WorkItemValidationError: if the title is blank.
        """
        if not title.strip():
            raise WorkItemValidationError("A work item needs a non-empty title")

        draft = draft or WorkItemDraft()
        fields = draft.to_api_fields()
        # The title is mandatory, so it always wins over the draft.
        fields[WorkItemField.TITLE] = title.strip()
        return self._repository.create(WorkItemType(work_item_type), title.strip(), fields)
