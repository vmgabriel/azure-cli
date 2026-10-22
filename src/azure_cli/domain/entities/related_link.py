"""Entity: an artifact (pull request, branch, commit...) linked to a work item."""

from __future__ import annotations

from dataclasses import dataclass

from azure_cli.domain.value_objects.link_kind import LinkKind


@dataclass(frozen=True, slots=True)
class RelatedLink:
    """A link between a work item and another artifact."""

    id: str
    kind: LinkKind
    url: str = ""
    title: str = ""

    @property
    def type(self) -> LinkKind:
        """The kind of artifact the link points at (alias of ``kind``)."""
        return self.kind

    def __str__(self) -> str:
        return f"[{self.kind}] {self.id}"
