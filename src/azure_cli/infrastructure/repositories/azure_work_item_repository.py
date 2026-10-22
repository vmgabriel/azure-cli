"""Adapter: implements the work item port on top of the Azure DevOps API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_cli.application.services.work_item_field_spec import WorkItemFieldSpec
from azure_cli.application.services.work_item_fields import WorkItemField
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.infrastructure.azure.dto import WorkItemDto
from azure_cli.infrastructure.azure.html_cleaner import HtmlTextCleaner
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient


class AzureWorkItemRepository(WorkItemRepository):
    """Reads and writes work items through the Azure DevOps REST API."""

    def __init__(
        self,
        client: AzureWorkItemApiClient,
        field_spec: WorkItemFieldSpec,
        html_cleaner: HtmlTextCleaner,
    ) -> None:
        self._client = client
        self._field_spec = field_spec
        self._html_cleaner = html_cleaner

    def get(self, work_item_id: WorkItemId) -> WorkItemDetail:
        """Return a single work item."""
        dto = self._client.get_work_item(
            work_item_id.value,
            self._field_spec.detail_fields,
        )
        return self._to_domain(dto)

    def list(self, query: str, *, top: int | None = None) -> list[WorkItemDetail]:
        """Return the work items matching a WIQL query."""
        dtos = self._client.query_by_wiql(
            query,
            self._field_spec.summary_fields,
            top=top,
        )
        return [self._to_domain(dto) for dto in dtos]

    def create(
        self,
        work_item_type: WorkItemType,
        title: str,
        fields: Mapping[str, str] | None = None,
    ) -> WorkItemDetail:
        """Create a work item of the given type."""
        payload: dict[str, Any] = dict(fields or {})
        payload[WorkItemField.TITLE] = title
        dto = self._client.create_work_item(work_item_type.value, payload)
        return self._to_domain(dto)

    def update(
        self,
        work_item_id: WorkItemId,
        changes: Mapping[str, str],
    ) -> WorkItemDetail:
        """Apply field changes to a work item."""
        dto = self._client.update_work_item(work_item_id.value, changes)
        return self._to_domain(dto)

    def add_comment(self, work_item_id: WorkItemId, text: str) -> WorkItemComment:
        """Add a comment to a work item."""
        dto = self._client.add_comment(work_item_id.value, text)
        author = dto.created_by.display_name if dto.created_by else ""
        return WorkItemComment(
            id=dto.id,
            work_item_id=work_item_id,
            text=dto.text or "",
            author=author or "",
            created_at=dto.created_date or "",
            url=dto.url or "",
        )

    # -- mapping ------------------------------------------------------------
    def _to_domain(self, dto: WorkItemDto) -> WorkItemDetail:
        """Map an API payload onto the domain entity."""
        fields = dto.fields
        return WorkItemDetail(
            id=WorkItemId(dto.id),
            title=str(fields.get(WorkItemField.TITLE) or f"Work item {dto.id}"),
            state=WorkItemState(str(fields.get(WorkItemField.STATE) or "New")),
            type=WorkItemType(str(fields.get(WorkItemField.TYPE) or "Task")),
            description=self._html_cleaner.clean(_as_text(fields.get(WorkItemField.DESCRIPTION))),
            acceptance_criteria=self._html_cleaner.clean(
                _as_text(fields.get(WorkItemField.ACCEPTANCE_CRITERIA))
            ),
            tags=Tag.parse_many(_as_text(fields.get(WorkItemField.TAGS))),
            story_points=_as_float(fields.get(WorkItemField.STORY_POINTS)),
            area_path=_as_text(fields.get(WorkItemField.AREA_PATH)),
            iteration_path=_as_text(fields.get(WorkItemField.ITERATION_PATH)),
            assigned_to=_display_name(fields.get(WorkItemField.ASSIGNED_TO)),
            created_by=_display_name(fields.get(WorkItemField.CREATED_BY)),
            url=dto.url or "",
        )


def _as_text(value: Any) -> str:
    """Return an API value as text, ignoring ``None``."""
    if value is None:
        return ""
    return str(value)


def _as_float(value: Any) -> float | None:
    """Return an API value as a float, ignoring values that are not numbers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _display_name(value: Any) -> str:
    """Return the display name of an Azure DevOps identity.

    Identities come either as an object (``{"displayName": "Ada"}``) or as a
    plain string depending on the field and on the API version.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("displayName") or value.get("uniqueName") or "")
    return str(value)
