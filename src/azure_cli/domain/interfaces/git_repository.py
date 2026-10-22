"""Port: everything the domain needs from the git side of Azure DevOps."""

from __future__ import annotations

from abc import ABC, abstractmethod

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.value_objects.work_item_id import WorkItemId


class GitRepository(ABC):
    """Source of the git artifacts related to a work item.

    Implemented by the infrastructure layer (``AzureGitRepository``) and faked
    in the tests.
    """

    @abstractmethod
    def find_related_links(self, work_item_id: WorkItemId) -> list[RelatedLink]:
        """Return the pull requests and branches related to a work item."""
