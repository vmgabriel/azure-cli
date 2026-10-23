"""Data transfer objects for the Azure DevOps REST payloads.

These models live in the infrastructure layer on purpose: the domain never
sees the wire format of Azure DevOps.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class IdentityDto(BaseModel):
    """An Azure DevOps identity (user or group)."""

    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = Field(default=None, alias="displayName")
    unique_name: str | None = Field(default=None, alias="uniqueName")


class RelationDto(BaseModel):
    """A relation attached to a work item (artifact links, hierarchy...)."""

    model_config = ConfigDict(populate_by_name=True)

    rel: str
    url: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class WorkItemDto(BaseModel):
    """A work item as returned by the work item tracking API."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    fields: dict[str, Any] = Field(default_factory=dict)
    url: str | None = None
    relations: list[RelationDto] = Field(default_factory=list)


class WorkItemListDto(BaseModel):
    """The envelope of a work item collection."""

    value: list[WorkItemDto] = Field(default_factory=list)


class WorkItemRelationDto(BaseModel):
    """An id-only reference to a work item (returned by the WIQL endpoint)."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    url: str | None = None


class WiqlResultDto(BaseModel):
    """The envelope of a WIQL query result."""

    model_config = ConfigDict(populate_by_name=True)

    work_item_relations: list[WorkItemRelationDto] = Field(
        default_factory=list,
        validation_alias=AliasChoices("workItems", "workItemRelations"),
        serialization_alias="workItems",
    )


class CommentDto(BaseModel):
    """A comment on a work item."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    text: str | None = None
    created_date: str | None = Field(default=None, alias="createdDate")
    created_by: IdentityDto | None = Field(default=None, alias="createdBy")
    url: str | None = None


class RepositoryDto(BaseModel):
    """A git repository."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    name: str | None = None
    url: str | None = None


class PullRequestDto(BaseModel):
    """A git pull request."""

    model_config = ConfigDict(populate_by_name=True)

    pull_request_id: int = Field(alias="pullRequestId")
    title: str | None = None
    description: str | None = None
    source_ref_name: str | None = Field(default=None, alias="sourceRefName")
    target_ref_name: str | None = Field(default=None, alias="targetRefName")
    url: str | None = None
    repository: RepositoryDto | None = None
    created_by: IdentityDto | None = Field(default=None, alias="createdBy")
