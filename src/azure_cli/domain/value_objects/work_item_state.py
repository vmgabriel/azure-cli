"""Value object: the workflow state of a work item."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.exceptions import WorkItemValidationError

#: States that mean "this work item is done". The set is intentionally
#: tolerant: Azure DevOps processes define their own state names.
TERMINAL_STATES = frozenset({"closed", "done", "resolved", "removed", "approved"})

#: States that mean "this work item is being worked on".
ACTIVE_STATES = frozenset({"active", "in progress", "committed", "implementing"})


@dataclass(frozen=True, slots=True)
class WorkItemState:
    """A workflow state such as ``New``, ``Active`` or ``Closed``."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise WorkItemValidationError("Work item state cannot be empty")
        object.__setattr__(self, "value", normalized)

    @property
    def is_closed(self) -> bool:
        """Whether the work item reached a terminal state."""
        return self.value.lower() in TERMINAL_STATES

    @property
    def is_active(self) -> bool:
        """Whether the work item is currently being worked on."""
        return self.value.lower() in ACTIVE_STATES

    def __str__(self) -> str:
        return self.value
