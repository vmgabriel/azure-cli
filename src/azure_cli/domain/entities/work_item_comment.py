"""Entity: a comment left on a work item."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.value_objects.work_item_id import WorkItemId


@dataclass(frozen=True, slots=True)
class WorkItemComment:
    """A comment attached to a work item."""

    id: int
    work_item_id: WorkItemId
    text: str
    author: str = ""
    created_at: str = ""
    url: str = ""

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise WorkItemValidationError("Comment text cannot be empty")
        object.__setattr__(self, "text", self.text.strip())
