"""The Azure DevOps work item fields this tool cares about.

Field reference names are stable, well-documented identifiers of the Azure
DevOps work item schema (``System.Title``, ``Microsoft.VSTS.Scheduling...``).
Keeping them in one place avoids scattering magic strings across the layers.
"""

from __future__ import annotations

from enum import StrEnum


class WorkItemField(StrEnum):
    """Reference names of the work item fields used by this CLI."""

    ID = "System.Id"
    TITLE = "System.Title"
    STATE = "System.State"
    TYPE = "System.WorkItemType"
    DESCRIPTION = "System.Description"
    ACCEPTANCE_CRITERIA = "Microsoft.VSTS.Common.AcceptanceCriteria"
    TAGS = "System.Tags"
    STORY_POINTS = "Microsoft.VSTS.Scheduling.StoryPoints"
    AREA_PATH = "System.AreaPath"
    ITERATION_PATH = "System.IterationPath"
    ASSIGNED_TO = "System.AssignedTo"
    CREATED_BY = "System.CreatedBy"
    CHANGED_DATE = "System.ChangedDate"
    REVISION = "System.Revision"
