"""Use case: list work items matching a set of filters."""

from __future__ import annotations

from azure_cli.application.services.work_item_query import (
    WorkItemFilter,
    WorkItemQueryService,
)
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository


class ListWorkItems:
    """Runs a WIQL query and returns the matching work items."""

    def __init__(
        self,
        repository: WorkItemRepository,
        query_service: WorkItemQueryService | None = None,
    ) -> None:
        self._repository = repository
        self._query_service = query_service or WorkItemQueryService()

    def execute(
        self,
        work_item_filter: WorkItemFilter | None = None,
        *,
        top: int | None = None,
    ) -> list[WorkItemDetail]:
        """Return the work items matching the filter, newest first."""
        wiql = self._query_service.build_wiql(work_item_filter)
        return self._repository.list(wiql, top=top)
