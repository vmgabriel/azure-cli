"""Service: which work item fields to request from Azure DevOps."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.application.services.work_item_fields import WorkItemField


@dataclass(frozen=True, slots=True)
class WorkItemFieldSpec:
    """The set of fields requested for a given kind of work item query.

    Requesting only the needed fields keeps the responses small and the
    terminal output focused.
    """

    detail_fields: tuple[str, ...]
    summary_fields: tuple[str, ...]

    @classmethod
    def detail(cls) -> WorkItemFieldSpec:
        """Every field needed to render a single work item in full."""
        return cls(
            detail_fields=(
                WorkItemField.ID,
                WorkItemField.TITLE,
                WorkItemField.STATE,
                WorkItemField.TYPE,
                WorkItemField.DESCRIPTION,
                WorkItemField.ACCEPTANCE_CRITERIA,
                WorkItemField.TAGS,
                WorkItemField.STORY_POINTS,
                WorkItemField.AREA_PATH,
                WorkItemField.ITERATION_PATH,
                WorkItemField.ASSIGNED_TO,
                WorkItemField.CREATED_BY,
                WorkItemField.CHANGED_DATE,
            ),
            summary_fields=(
                WorkItemField.ID,
                WorkItemField.TITLE,
                WorkItemField.STATE,
                WorkItemField.TYPE,
                WorkItemField.ASSIGNED_TO,
                WorkItemField.CHANGED_DATE,
            ),
        )

    @classmethod
    def summary(cls) -> WorkItemFieldSpec:
        """The compact field set used by list queries."""
        return cls(detail_fields=(), summary_fields=cls.detail().summary_fields)
