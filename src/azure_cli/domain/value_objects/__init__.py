"""Value objects: the small, immutable and self-validating building blocks."""

from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType

__all__ = [
    "LinkKind",
    "Tag",
    "WorkItemId",
    "WorkItemState",
    "WorkItemType",
]
