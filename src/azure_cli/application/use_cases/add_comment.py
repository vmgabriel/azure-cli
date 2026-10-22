"""Use case: add a comment to a work item."""

from __future__ import annotations

from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_id import WorkItemId


class AddComment:
    """Leaves a comment on a work item."""

    def __init__(self, repository: WorkItemRepository) -> None:
        self._repository = repository

    def execute(self, work_item_id: WorkItemId | str | int, text: str) -> WorkItemComment:
        """Add the comment and return it.

        Raises:
            WorkItemValidationError: if the comment is blank.
            WorkItemNotFoundError: if the work item does not exist.
        """
        if not text.strip():
            raise WorkItemValidationError("A comment cannot be empty")

        return self._repository.add_comment(WorkItemId.parse(work_item_id), text.strip())
