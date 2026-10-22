"""Entities: the work items of a project.

Two levels of detail are modelled:

* :class:`WorkItemSummary` — what a list query returns: enough to identify a
  work item and to show it in a table.
* :class:`WorkItemDetail` — the same work item with its full content
  (description, acceptance criteria, tags, related links...).

Both are frozen dataclasses written with the standard library only: the domain
depends on neither Pydantic nor Azure DevOps, so they are trivial to build and
to assert on in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.exceptions import WorkItemValidationError
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType


@dataclass(frozen=True, slots=True)
class WorkItemSummary:
    """The essential facts of a work item.

    This is the projection a list query returns. It only carries the fields
    that Azure DevOps is asked for in a summary query, which keeps the
    responses small and the tables readable.
    """

    id: WorkItemId
    title: str
    state: WorkItemState
    type: WorkItemType
    assigned_to: str = ""
    story_points: float | None = None
    url: str = ""
    changed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise WorkItemValidationError(f"Work item {self.id} must have a non-empty title")
        object.__setattr__(self, "title", self.title.strip())

    @property
    def work_item_type(self) -> WorkItemType:
        """The type of the work item (alias of ``type``)."""
        return self.type

    @property
    def is_closed(self) -> bool:
        """Whether the work item reached a terminal state."""
        return self.state.is_closed

    @property
    def is_active(self) -> bool:
        """Whether the work item is currently being worked on."""
        return self.state.is_active


@dataclass(frozen=True, slots=True)
class WorkItemDetail(WorkItemSummary):
    """A work item with its full content.

    Rich-text fields (description, acceptance criteria) are stored already
    rendered as plain text: stripping the HTML is an infrastructure concern,
    the domain only cares about the content.
    """

    description: str = ""
    acceptance_criteria: str = ""
    tags: tuple[Tag, ...] = ()
    area_path: str = ""
    iteration_path: str = ""
    created_by: str = ""
    related_links: tuple[RelatedLink, ...] = ()

    def __post_init__(self) -> None:
        # The base class is called explicitly: a slotted dataclass rebuilt by
        # ``dataclasses`` cannot rely on the zero-argument ``super()``.
        WorkItemSummary.__post_init__(self)
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "related_links", tuple(self.related_links))

    def has_tag(self, tag: str | Tag) -> bool:
        """Whether the work item carries the given tag (case-insensitive)."""
        needle = tag.value if isinstance(tag, Tag) else Tag(tag).value
        return any(existing.value == needle for existing in self.tags)

    def with_related_links(self, links: tuple[RelatedLink, ...]) -> WorkItemDetail:
        """Return a copy of this work item carrying the given related links."""
        return replace(self, related_links=tuple(links))

    def to_summary(self) -> WorkItemSummary:
        """Return the summary projection of this work item."""
        return WorkItemSummary(
            id=self.id,
            title=self.title,
            state=self.state,
            type=self.type,
            assigned_to=self.assigned_to,
            story_points=self.story_points,
            url=self.url,
            changed_at=self.changed_at,
        )

    @property
    def pull_requests(self) -> tuple[RelatedLink, ...]:
        """Related links that point at pull requests."""
        return tuple(link for link in self.related_links if link.kind is LinkKind.PULL_REQUEST)

    @property
    def branches(self) -> tuple[RelatedLink, ...]:
        """Related links that point at source branches."""
        return tuple(link for link in self.related_links if link.kind is LinkKind.BRANCH)


#: The work item entity used to be called ``WorkItem``. The alias keeps the
#: old name working while the domain speaks of summaries and details.
WorkItem = WorkItemDetail
