"""Service: build WIQL queries out of human friendly filters."""

from __future__ import annotations

from dataclasses import dataclass, field

#: States excluded from queries unless the user explicitly asks for them.
CLOSED_STATES = ("Closed", "Done", "Resolved", "Removed")


@dataclass(frozen=True, slots=True)
class WorkItemFilter:
    """The filters a user can combine to narrow down work items."""

    state: str | None = None
    assigned_to: str | None = None
    area_path: str | None = None
    iteration_path: str | None = None
    work_item_type: str | None = None
    tags: tuple[str, ...] = ()
    contains: str | None = None
    include_closed: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether the filter selects every work item of the project."""
        return not any(
            (
                self.state,
                self.assigned_to,
                self.area_path,
                self.iteration_path,
                self.work_item_type,
                self.tags,
                self.contains,
            )
        )


@dataclass(frozen=True, slots=True)
class WorkItemQueryService:
    """Turns a `WorkItemFilter` into a WIQL statement.

    WIQL is Azure DevOps' own query language; keeping the escaping rules in
    one place avoids injection issues and quoting mistakes.
    """

    _default_order: str = field(default="[System.ChangedDate] DESC", init=False)

    def build_wiql(self, work_item_filter: WorkItemFilter | None = None) -> str:
        """Return the WIQL statement matching the given filter."""
        work_item_filter = work_item_filter or WorkItemFilter()

        clauses: list[str] = ["[System.TeamProject] = @project"]

        if work_item_filter.state:
            clauses.append(f"[System.State] = '{self._escape(work_item_filter.state)}'")
        if work_item_filter.assigned_to:
            clauses.append(f"[System.AssignedTo] = '{self._escape(work_item_filter.assigned_to)}'")
        if work_item_filter.area_path:
            clauses.append(f"[System.AreaPath] = '{self._escape(work_item_filter.area_path)}'")
        if work_item_filter.iteration_path:
            clauses.append(
                f"[System.IterationPath] = '{self._escape(work_item_filter.iteration_path)}'"
            )
        if work_item_filter.work_item_type:
            clauses.append(
                f"[System.WorkItemType] = '{self._escape(work_item_filter.work_item_type)}'"
            )
        for tag in work_item_filter.tags:
            clauses.append(f"[System.Tags] CONTAINS '{self._escape(tag)}'")
        if work_item_filter.contains:
            escaped = self._escape(work_item_filter.contains)
            clauses.append(
                f"([System.Title] CONTAINS '{escaped}' "
                f"OR [System.Description] CONTAINS '{escaped}')"
            )
        if not work_item_filter.include_closed and not work_item_filter.state:
            closed = ", ".join(f"'{state}'" for state in CLOSED_STATES)
            clauses.append(f"[System.State] NOT IN ({closed})")

        return (
            f"SELECT [System.Id] FROM WorkItems "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY {self._default_order}"
        )

    @staticmethod
    def _escape(value: str) -> str:
        """Escape a value for inclusion in a WIQL string literal."""
        return value.replace("'", "''")
