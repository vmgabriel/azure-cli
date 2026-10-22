"""Use case: find the git artifacts related to a work item."""

from __future__ import annotations

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.interfaces.git_repository import GitRepository
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository
from azure_cli.domain.value_objects.work_item_id import WorkItemId


class GetRelatedLinks:
    """Collects the pull requests and branches connected to a work item.

    Azure DevOps links work items to code in two ways: explicit ``ArtifactLink``
    relations and implicit references (``#1234``) in pull request titles and
    descriptions. Both are gathered here.
    """

    def __init__(
        self,
        git_repository: GitRepository,
        work_item_repository: WorkItemRepository | None = None,
    ) -> None:
        self._git_repository = git_repository
        self._work_item_repository = work_item_repository

    def execute(self, work_item_id: WorkItemId | str | int) -> list[RelatedLink]:
        """Return the links related to the given work item.

        Raises:
            WorkItemNotFoundError: if the work item does not exist.
        """
        parsed_id = WorkItemId.parse(work_item_id)

        if self._work_item_repository is not None:
            # Fail fast with a clear "not found" instead of an empty link list.
            self._work_item_repository.get(parsed_id)

        return self._git_repository.find_related_links(parsed_id)
