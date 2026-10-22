"""Value object: a work item tag."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.exceptions import WorkItemValidationError


@dataclass(frozen=True, slots=True)
class Tag:
    """A work item tag.

    Azure DevOps stores tags as a single ``;``-separated string and treats
    them case-insensitively, so tags are normalized (trimmed, lower-cased)
    to make comparisons predictable.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split()).lower()
        if not normalized:
            raise WorkItemValidationError("Tag cannot be empty")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def parse_many(cls, raw: str | None) -> tuple[Tag, ...]:
        """Split the ``;``-separated tag string used by Azure DevOps."""
        if not raw:
            return ()
        tags = (cls(part) for part in raw.split(";"))
        # Deduplicate while preserving the original order.
        return tuple(dict.fromkeys(tags))

    def __str__(self) -> str:
        return self.value
