"""Value object: the type of a work item (Bug, Task, User Story...)."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.exceptions import WorkItemValidationError

#: Work item types shipped with Azure DevOps out of the box. Custom process
#: types are perfectly valid too, so this set is informational only.
KNOWN_TYPES = (
    "epic",
    "feature",
    "user story",
    "requirement",
    "task",
    "bug",
    "test case",
    "test plan",
    "issue",
)


@dataclass(frozen=True, slots=True)
class WorkItemType:
    """The type of a work item, e.g. ``Bug`` or ``User Story``."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise WorkItemValidationError("Work item type cannot be empty")
        object.__setattr__(self, "value", normalized)

    @property
    def slug(self) -> str:
        """Lower-cased type name, handy for comparisons and URLs."""
        return self.value.lower()

    @property
    def is_known(self) -> bool:
        """Whether the type is one of the standard Azure DevOps types."""
        return self.slug in KNOWN_TYPES

    def __str__(self) -> str:
        return self.value
