"""Adapter: implements the git port on top of the Azure DevOps API."""

from __future__ import annotations

import re

from azure_cli.application.services.work_item_fields import WorkItemField
from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.interfaces.git_repository import GitRepository
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.infrastructure.azure.dto import RelationDto
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.git.git_api_client import AzureGitApiClient

#: How many pull requests are scanned looking for implicit references.
DEFAULT_PULL_REQUEST_SCAN = 50

#: Maps the name of an Azure DevOps artifact relation onto a link kind.
_RELATION_KINDS = {
    "pull request": LinkKind.PULL_REQUEST,
    "branch": LinkKind.BRANCH,
    "commit": LinkKind.COMMIT,
    "fixed in commit": LinkKind.COMMIT,
    "work item": LinkKind.WORK_ITEM,
}


class AzureGitRepository(GitRepository):
    """Finds the pull requests and branches related to a work item.

    Two sources are combined:

    * the explicit ``ArtifactLink`` relations attached to the work item;
    * the pull requests whose title or description mentions ``#<id>``.
    """

    def __init__(
        self,
        work_item_client: AzureWorkItemApiClient,
        git_client: AzureGitApiClient,
        *,
        web_base_url: str,
        top: int = DEFAULT_PULL_REQUEST_SCAN,
    ) -> None:
        self._work_item_client = work_item_client
        self._git_client = git_client
        self._web_base_url = web_base_url.rstrip("/")
        self._top = top

    def find_related_links(self, work_item_id: WorkItemId) -> list[RelatedLink]:
        """Return the links related to the given work item."""
        links: list[RelatedLink] = []
        seen: set[tuple[str, str]] = set()

        def add(link: RelatedLink) -> None:
            key = (link.kind.value, link.id)
            if key not in seen:
                seen.add(key)
                links.append(link)

        for link in self._explicit_relations(work_item_id):
            add(link)

        for link in self._implicit_pull_request_references(work_item_id):
            add(link)

        return links

    # -- explicit artifact relations ----------------------------------------
    def _explicit_relations(self, work_item_id: WorkItemId) -> list[RelatedLink]:
        """Read the artifact relations attached to the work item itself."""
        dto = self._work_item_client.get_work_item(work_item_id.value, [WorkItemField.ID])
        links: list[RelatedLink] = []

        for relation in dto.relations:
            link = self._link_from_relation(relation)
            if link is not None:
                links.append(link)

        return links

    def _link_from_relation(self, relation: RelationDto) -> RelatedLink | None:
        """Map an artifact relation onto a related link."""
        if relation.rel != "ArtifactLink":
            return None

        name = str(relation.attributes.get("name") or "")
        kind = _RELATION_KINDS.get(name.lower(), LinkKind.OTHER)
        artifact_id = str(relation.attributes.get("id") or relation.url or "")

        url = relation.url or ""
        if kind is LinkKind.PULL_REQUEST:
            url = _to_web_pull_request_url(url, artifact_id)
        elif kind is LinkKind.BRANCH:
            url = self._branch_url(artifact_id)

        return RelatedLink(id=artifact_id, kind=kind, url=url, title=name)

    # -- implicit references ------------------------------------------------
    def _implicit_pull_request_references(self, work_item_id: WorkItemId) -> list[RelatedLink]:
        """Find the pull requests mentioning ``#<id>`` in their text."""
        token = f"#{work_item_id.value}"
        links: list[RelatedLink] = []

        for pull_request in self._git_client.list_pull_requests(top=self._top):
            haystack = f"{pull_request.title or ''}\n{pull_request.description or ''}"
            if token not in haystack:
                continue

            links.append(
                RelatedLink(
                    id=str(pull_request.pull_request_id),
                    kind=LinkKind.PULL_REQUEST,
                    url=_to_web_pull_request_url(
                        pull_request.url or "",
                        str(pull_request.pull_request_id),
                    ),
                    title=pull_request.title or "",
                )
            )

            source_branch = (pull_request.source_ref_name or "").removeprefix("refs/heads/")
            if source_branch:
                links.append(
                    RelatedLink(
                        id=source_branch,
                        kind=LinkKind.BRANCH,
                        url=self._branch_url(source_branch),
                        title=source_branch,
                    )
                )

        return links

    def _branch_url(self, branch: str) -> str:
        """Return the browser URL of a branch."""
        return f"{self._web_base_url}/_git/branches?refname={branch}"


def _to_web_pull_request_url(api_url: str, pull_request_id: str) -> str:
    """Convert an Azure DevOps REST pull request URL into a browser URL.

    ``.../_apis/git/repositories/<repo>/pullRequests/<id>`` becomes
    ``.../_git/pullrequest/<id>``.
    """
    if not api_url:
        return ""
    web_url = re.sub(r"/_apis/git/repositories/[^/]+", "/_git", api_url)
    return re.sub(r"/pullRequests/\d+", f"/pullrequest/{pull_request_id}", web_url)
