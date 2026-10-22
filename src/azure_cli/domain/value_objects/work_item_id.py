"""Value object: the identifier of an Azure DevOps work item."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.exceptions import InvalidWorkItemIdError


@dataclass(frozen=True, slots=True)
class WorkItemId:
    """A validated work item identifier.

    Azure DevOps work item ids are always positive integers; anything else is
    rejected at the boundary of the domain instead of failing deep inside the
    HTTP layer.
    """

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise InvalidWorkItemIdError(f"Work item id must be an integer, got {self.value!r}")
        if self.value <= 0:
            raise InvalidWorkItemIdError(
                f"Work item id must be a positive integer, got {self.value}"
            )

    @classmethod
    def parse(cls, raw: str | int | WorkItemId) -> WorkItemId:
        """Build a `WorkItemId` from user input (string or integer)."""
        if isinstance(raw, WorkItemId):
            return raw
        if isinstance(raw, bool):
            raise InvalidWorkItemIdError(f"Work item id must be an integer, got {raw!r}")
        if isinstance(raw, int):
            return cls(raw)
        text = str(raw).strip()
        if not text:
            raise InvalidWorkItemIdError("Work item id cannot be empty")
        try:
            return cls(int(text))
        except ValueError as exc:
            raise InvalidWorkItemIdError(
                f"'{text}' is not a valid work item id (expected a number)"
            ) from exc

    def __str__(self) -> str:
        return str(self.value)
