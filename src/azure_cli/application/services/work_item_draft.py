"""Service: the editable values of a work item and their API field mapping."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.application.services.work_item_fields import WorkItemField


@dataclass(frozen=True, slots=True)
class WorkItemDraft:
    """The values a user can set when creating or updating a work item.

    Every field is optional; ``None`` means "leave untouched", which is what
    makes the same value object usable for both create and update.
    """

    title: str | None = None
    state: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    tags: tuple[str, ...] = ()
    story_points: float | None = None
    area_path: str | None = None
    iteration_path: str | None = None
    assigned_to: str | None = None

    def to_api_fields(self) -> dict[str, str]:
        """Return the API fields to send, skipping the untouched ones."""
        fields: dict[str, str] = {}

        if self.title is not None:
            fields[WorkItemField.TITLE] = self.title
        if self.state is not None:
            fields[WorkItemField.STATE] = self.state
        if self.description is not None:
            fields[WorkItemField.DESCRIPTION] = self.description
        if self.acceptance_criteria is not None:
            fields[WorkItemField.ACCEPTANCE_CRITERIA] = self.acceptance_criteria
        if self.tags:
            fields[WorkItemField.TAGS] = ";".join(self.tags)
        if self.story_points is not None:
            fields[WorkItemField.STORY_POINTS] = str(self.story_points)
        if self.area_path is not None:
            fields[WorkItemField.AREA_PATH] = self.area_path
        if self.iteration_path is not None:
            fields[WorkItemField.ITERATION_PATH] = self.iteration_path
        if self.assigned_to is not None:
            fields[WorkItemField.ASSIGNED_TO] = self.assigned_to

        return fields
