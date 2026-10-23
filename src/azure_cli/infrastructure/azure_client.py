"""Azure DevOps REST client.

Implements the integration points requested by the user:

* :meth:`AzureDevOpsClient.list_work_items` — WIQL query filtered with the
  ``@me`` macro, returning :class:`~azure_cli.domain.entities.work_item.WorkItemSummary`
  objects ordered by ``ChangedDate DESC`` with a cap of 50 items.
* :meth:`AzureDevOpsClient.get_workitem_by_id` — returns a
  :class:`~azure_cli.domain.entities.work_item.WorkItemDetail` with HTML
  cleaned from ``Description`` and ``Acceptance Criteria``.
* :meth:`AzureDevOpsClient.get_related_prs_and_branches` — searches for
  pull requests mentioning the work item id and returns them as
  :class:`~azure_cli.domain.entities.related_link.RelatedLink` objects.

The client is pure infrastructure: it uses :mod:`requests` with
:class:`~requests.auth.HTTPBasicAuth`, respects timeouts, logs what it is
doing and raises infrastructure/domain exceptions on failure.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from azure_cli.config.settings import AzureDevOpsSettings
from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary
from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.domain.value_objects.tag import Tag
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.infrastructure.debug import debug_print, is_debug, truncate_body
from azure_cli.infrastructure.html_utils import clean_html

logger = logging.getLogger(__name__)

#: Default timeout used by the client when none is provided.
DEFAULT_TIMEOUT = 15.0

#: Maximum number of work items returned by :meth:`list_work_items`.
MAX_LIST_ITEMS = 50

#: States to exclude when listing work items.
EXCLUDED_STATES = ("Closed", "Done", "Removed")

#: Work item types to include when listing (the requirements say "User Stories").
LIST_WORK_ITEM_TYPES = ("User Story", "Task", "Bug", "Issue")

#: Fields requested for the list query.
SUMMARY_FIELDS = (
    "System.Id",
    "System.Title",
    "System.State",
    "System.AssignedTo",
    "System.WorkItemType",
    "Microsoft.VSTS.Scheduling.StoryPoints",
    "System.ChangedDate",
)

#: Fields requested for the detail query.
DETAIL_FIELDS = (
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
    "System.Description",
    "Microsoft.VSTS.Common.AcceptanceCriteria",
    "System.Tags",
    "Microsoft.VSTS.Scheduling.StoryPoints",
    "System.AreaPath",
    "System.IterationPath",
    "System.AssignedTo",
    "System.ChangedDate",
)

#: Maximum number of ids Azure DevOps accepts in a batch ``ids=`` request.
MAX_BATCH_SIZE = 200


class AzureDevOpsClient(AzureDevOpsGateway):
    """Client for the Azure DevOps REST API.

    Authentication uses :class:`requests.auth.HTTPBasicAuth` with an empty
    username and the Personal Access Token as the password.
    """

    def __init__(self, settings: AzureDevOpsSettings) -> None:
        """Create a client from the application settings.

        Args:
            settings: Configuration holding the organization, project, PAT,
                API version and timeout.
        """
        self.settings = settings
        self.organization = settings.organization
        self.project = settings.project
        self.pat = settings.pat.get_secret_value()
        self.api_version = settings.api_version
        self.timeout = float(settings.timeout) if settings.timeout is not None else DEFAULT_TIMEOUT
        self.base_url = settings.web_base_url
        self.api_base_url = settings.api_base_url

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth("", self.pat)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "azure-cli",
            }
        )

        logger.debug(
            "AzureDevOpsClient initialised for %s/%s (api_version=%s, timeout=%s)",
            self.organization,
            self.project,
            self.api_version,
            self.timeout,
        )

    # -- public API ---------------------------------------------------------
    def list_work_items(self) -> list[WorkItemSummary]:
        """List the active User Stories assigned to the current user.

        The query looks for ``User Story`` items that are not in
        ``Closed``, ``Done`` or ``Removed``, assigned to the user behind the
        credentials (``@me``), orders them by ``ChangedDate DESC`` and
        returns at most 50 of them.

        Returns:
            A list of :class:`WorkItemSummary` objects.

        Raises:
            AuthenticationError: if the credentials are rejected.
            AzureApiError: if Azure DevOps returns an error response.
            TransportError: if the API cannot be reached.
        """
        logger.info("Listing the work items of the current user (max %s)", MAX_LIST_ITEMS)

        wiql = self._build_list_wiql()
        work_item_ids = self._query_wiql_ids(wiql, limit=MAX_LIST_ITEMS)
        if not work_item_ids:
            logger.debug("No work items found for the current user")
            return []

        dtos = self._get_work_items_batch(work_item_ids, SUMMARY_FIELDS)
        summaries: list[WorkItemSummary] = []

        for dto in dtos:
            fields = dto.get("fields", {}) if isinstance(dto, Mapping) else {}
            if not isinstance(fields, Mapping):
                fields = {}

            work_item_id = _as_int(dto.get("id")) or _as_int(fields.get("System.Id"))
            if work_item_id is None:
                continue

            assignee = fields.get("System.AssignedTo")
            title = _as_text(fields.get("System.Title")) or f"Work item {work_item_id}"
            state = _as_text(fields.get("System.State")) or "New"
            work_item_type = _as_text(fields.get("System.WorkItemType")) or "User Story"
            assigned_to = _assigned_to(assignee)
            story_points = _as_float(fields.get("Microsoft.VSTS.Scheduling.StoryPoints"))
            url = _as_text(dto.get("url")) or self._work_item_url(work_item_id)
            changed_at = _parse_datetime(fields.get("System.ChangedDate"))

            try:
                summaries.append(
                    WorkItemSummary(
                        id=WorkItemId(work_item_id),
                        title=title,
                        state=WorkItemState(state),
                        type=WorkItemType(work_item_type),
                        assigned_to=assigned_to,
                        story_points=story_points,
                        url=url,
                        changed_at=changed_at,
                    )
                )
            except Exception as exc:
                logger.warning("Skipping invalid work item %s: %s", work_item_id, exc)
                continue

        logger.debug("Returning %s work item summaries", len(summaries))
        return summaries

    def get_workitem_by_id(self, workitem_id: int) -> WorkItemDetail | None:
        """Fetch a detailed work item by its identifier.

        Description and Acceptance Criteria are returned as plain text after
        HTML cleaning with BeautifulSoup.

        Args:
            workitem_id: The numeric identifier of the work item.

        Returns:
            A :class:`WorkItemDetail` or ``None`` if the work item does not
            exist.

        Raises:
            AuthenticationError: if the credentials are rejected.
            AzureApiError: if Azure DevOps returns an error response.
            TransportError: if the API cannot be reached.
        """
        logger.info("Fetching work item %s", workitem_id)

        try:
            response = self._request(
                "GET",
                f"/wit/workitems/{workitem_id}",
                params={"fields": ",".join(DETAIL_FIELDS), "api-version": self.api_version},
                not_found_message=f"Work item {workitem_id} was not found",
            )
        except WorkItemNotFoundError:
            logger.debug("Work item %s not found", workitem_id)
            return None

        payload = response.json()
        if not isinstance(payload, Mapping):
            return None

        fields = payload.get("fields", {})
        if not isinstance(fields, Mapping):
            fields = {}

        work_item_id = _as_int(payload.get("id")) or workitem_id
        title = _as_text(fields.get("System.Title")) or f"Work item {work_item_id}"
        state = _as_text(fields.get("System.State")) or "New"
        work_item_type = _as_text(fields.get("System.WorkItemType")) or "Task"
        description_html = fields.get("System.Description")
        acceptance_html = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria")
        description = clean_html(_as_text_or_none(description_html))
        acceptance_criteria = clean_html(_as_text_or_none(acceptance_html))
        tags = Tag.parse_many(_as_text_or_none(fields.get("System.Tags")))
        story_points = _as_float(fields.get("Microsoft.VSTS.Scheduling.StoryPoints"))
        area_path = _as_text(fields.get("System.AreaPath"))
        iteration_path = _as_text(fields.get("System.IterationPath"))
        assigned_to = _assigned_to(fields.get("System.AssignedTo"))
        url = _as_text(payload.get("url")) or self._work_item_url(work_item_id)
        changed_at = _parse_datetime(fields.get("System.ChangedDate"))

        try:
            return WorkItemDetail(
                id=WorkItemId(work_item_id),
                title=title,
                state=WorkItemState(state),
                type=WorkItemType(work_item_type),
                description=description,
                acceptance_criteria=acceptance_criteria,
                tags=tags,
                story_points=story_points,
                area_path=area_path,
                iteration_path=iteration_path,
                assigned_to=assigned_to,
                created_by="",
                url=url,
                related_links=(),
                changed_at=changed_at,
            )
        except Exception as exc:
            logger.warning("Could not build WorkItemDetail for %s: %s", work_item_id, exc)
            raise

    def get_related_prs_and_branches(self, workitem_id: int) -> list[RelatedLink]:
        """Search for pull requests and branches related to a work item.

        The Azure DevOps Git REST API is searched for pull requests whose
        title or description mentions the work item identifier. Branches that
        are referenced by those pull requests are returned as well when they
        can be identified.

        Errors are handled gracefully: failures return an empty list.

        Args:
            workitem_id: The numeric identifier of the work item.

        Returns:
            A list of :class:`RelatedLink` objects.
        """
        logger.info("Fetching related PRs and branches for work item %s", workitem_id)
        links: list[RelatedLink] = []

        try:
            prs = self._search_pull_requests(workitem_id)
            for pr in prs:
                link = self._pr_to_related_link(pr)
                if link is not None:
                    links.append(link)
                branch_link = self._branch_from_pr(pr)
                if branch_link is not None and branch_link not in links:
                    links.append(branch_link)
        except AuthenticationError:
            raise
        except Exception as exc:
            logger.warning(
                "Could not fetch related PRs/branches for %s: %s",
                workitem_id,
                exc,
            )
            return []

        # Deduplicate while preserving the order.
        seen: set[tuple[str, str]] = set()
        deduplicated: list[RelatedLink] = []
        for link in links:
            key = (link.kind.value, link.id)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(link)

        logger.debug("Found %s related links for %s", len(deduplicated), workitem_id)
        return deduplicated

    # -- WIQL / queries -----------------------------------------------------
    def _build_list_wiql(self) -> str:
        """Build the WIQL query for :meth:`list_work_items`.

        ``@me`` is a macro understood by Azure DevOps: it is resolved on the
        server from the credentials of the request, which avoids knowing (and
        passing around) the e-mail address of the user.
        """
        return (
            "SELECT [System.Id], [System.Title], [System.State], "
            "[System.AssignedTo], [System.WorkItemType] "
            "FROM WorkItems "
            f"WHERE [System.TeamProject] = '{self._escape_wiql(self.project)}' "
            "AND [System.WorkItemType] = 'User Story' "
            "AND [System.AssignedTo] = @me "
            "AND [System.State] NOT IN ('Closed', 'Done', 'Removed') "
            "ORDER BY [System.ChangedDate] DESC"
        )

    def _query_wiql_ids(self, wiql: str, limit: int) -> list[int]:
        """Run a WIQL query and return the work item ids."""
        response = self._request(
            "POST",
            "/wit/wiql",
            params={"api-version": self.api_version},
            json_body={"query": wiql},
        )
        payload = response.json()
        logger.info(f"Raw WIQL Response: {payload}")
        if not isinstance(payload, Mapping):
            return []

        work_items = payload.get("workItems") or payload.get("work_items") or []
        if not isinstance(work_items, Sequence):
            return []

        ids: list[int] = []
        for item in work_items:
            if not isinstance(item, Mapping):
                continue

            work_item_id = _as_int(item.get("id"))
            if work_item_id is not None:
                ids.append(work_item_id)
            if len(ids) >= limit:
                break

        return ids[:limit]

    # -- batch fetch --------------------------------------------------------
    def _get_work_items_batch(
        self,
        ids: Sequence[int],
        fields: Sequence[str],
    ) -> list[dict[str, Any]]:
        """Fetch several work items in a single batch request."""
        if not ids:
            return []

        collected: list[dict[str, Any]] = []
        ids_list = list(ids)

        for chunk in self._chunks(ids_list, MAX_BATCH_SIZE):
            response = self._request(
                "GET",
                "/wit/workitems",
                params={
                    "ids": ",".join(str(item_id) for item_id in chunk),
                    "fields": ",".join(fields),
                    "api-version": self.api_version,
                },
            )
            payload = response.json()
            if isinstance(payload, Mapping):
                value = payload.get("value") or []
            elif isinstance(payload, Sequence) and not isinstance(payload, str):
                value = payload
            else:
                value = []

            for item in value:
                if isinstance(item, Mapping):
                    collected.append(dict(item))

        return collected

    # -- pull requests / branches -------------------------------------------
    def _search_pull_requests(self, workitem_id: int) -> list[dict[str, Any]]:
        """Search for pull requests mentioning the work item.

        The search API is tried first; when it returns nothing, the pull
        requests of the project are listed and filtered locally. In both
        cases only the pull requests whose title or description mentions the
        work item identifier are kept.
        """
        candidates: list[dict[str, Any]] = []

        # The search API (newer Azure DevOps).
        for params in (
            {
                "searchCriteria": {"searchText": str(workitem_id)},
                "$top": 50,
                "api-version": self.api_version,
            },
            {"searchText": str(workitem_id), "$top": 50, "api-version": self.api_version},
        ):
            try:
                response = self._request("GET", "/git/pullrequests", params=params)
                candidates = _extract_prs(response.json())
                if candidates:
                    break
            except Exception as exc:
                logger.debug("PR search variant failed: %s", exc)
                continue

        # Fallback: list the pull requests of the project.
        if not candidates:
            try:
                response = self._request(
                    "GET",
                    "/git/pullrequests",
                    params={"api-version": self.api_version, "$top": 100},
                )
                candidates = _extract_prs(response.json())
            except Exception as exc:
                logger.debug("Fallback PR listing failed: %s", exc)
                return []

        needle = str(workitem_id)
        return [pr for pr in candidates if _mentions_work_item(pr, needle)]

    def _pr_to_related_link(self, pr: Mapping[str, Any]) -> RelatedLink | None:
        """Convert a pull request payload to a RelatedLink."""
        pr_id = (
            _as_text(pr.get("pullRequestId"))
            or _as_text(pr.get("id"))
            or _as_text((pr.get("pullRequest") or {}).get("pullRequestId"))
        )
        if not pr_id:
            return None

        title = _as_text(pr.get("title")) or ""
        url = _as_text(pr.get("url")) or ""
        if not url and pr_id.isdigit():
            url = f"{self.base_url}/_git/pullrequest/{pr_id}"

        return RelatedLink(id=pr_id, kind=LinkKind.PULL_REQUEST, url=url, title=title)

    def _branch_from_pr(self, pr: Mapping[str, Any]) -> RelatedLink | None:
        """Extract the source branch of a pull request as a RelatedLink."""
        source_ref = _as_text(pr.get("sourceRefName")) or _as_text(pr.get("sourceBranch"))
        if not source_ref:
            return None

        # ``refs/heads/feature/login`` is the branch ``feature/login``.
        branch_name = source_ref
        for prefix in ("refs/heads/", "heads/"):
            if branch_name.startswith(prefix):
                branch_name = branch_name[len(prefix) :]
                break
        if not branch_name:
            return None

        url = _as_text(pr.get("url")) or ""
        if url and "_git/pullrequest/" in url:
            url = url.replace("/pullrequest/", "/branches?refname=") + branch_name

        return RelatedLink(id=branch_name, kind=LinkKind.BRANCH, url=url, title=branch_name)

    # -- HTTP plumbing ------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        not_found_message: str | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        """Perform an HTTP call and translate failures into domain exceptions."""
        url = f"{self.api_base_url}{path}"
        request_timeout = timeout if timeout is not None else self.timeout

        if is_debug():
            debug_print(f"\n[DEBUG] Request: {method} {url}")
            debug_print(f"[DEBUG] Headers: {self.session.headers}")
            debug_print(f"[DEBUG] Params: {dict(params) if params else None}")
            debug_print(f"[DEBUG] Body: {json_body}")

        try:
            response = self.session.request(
                method,
                url,
                params=dict(params) if params else None,
                json=json_body,
                timeout=request_timeout,
            )
        except requests.RequestException as exc:
            raise TransportError(f"Could not reach Azure DevOps at {url}: {exc}") from exc

        if is_debug() and (response.status_code != 200 or not response.content):
            debug_print(f"[DEBUG] Response status: {response.status_code}")
            debug_print(f"[DEBUG] Response body: {truncate_body(response.text)}")

        self._raise_for_status(response, url, not_found_message)
        return response

    @staticmethod
    def _raise_for_status(
        response: requests.Response,
        url: str,
        not_found_message: str | None,
    ) -> None:
        """Map an HTTP error response onto the matching exception."""
        status = response.status_code
        if status < 400:
            return

        detail = _error_detail(response)

        if status in (401, 403):
            raise AuthenticationError(
                "Azure DevOps rejected the credentials. Check your PAT and its "
                f"'Work Items' scope. ({detail})"
            )
        if status == 404:
            raise WorkItemNotFoundError(not_found_message or f"Not found: {url}")
        raise AzureApiError(
            f"Azure DevOps returned HTTP {status} for {url}. {detail}",
            status_code=status,
        )

    # -- helpers ------------------------------------------------------------
    def _work_item_url(self, work_item_id: int) -> str:
        """Return the browser URL of a work item."""
        return f"{self.base_url}/_workitems/edit/{work_item_id}"

    @staticmethod
    def _escape_wiql(value: str) -> str:
        """Escape a value for inclusion in a WIQL string literal."""
        return value.replace("'", "''")

    @staticmethod
    def _chunks(items: Sequence[int], size: int) -> list[list[int]]:
        """Split a sequence into chunks of at most ``size`` elements."""
        return [list(items[index : index + size]) for index in range(0, len(items), size)]


# -- module level helpers ---------------------------------------------------


def _as_text(value: Any) -> str:
    """Return an API value as text, ignoring ``None``."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _as_text_or_none(value: Any) -> str | None:
    """Return an API value as text or ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _as_int(value: Any) -> int | None:
    """Return an API value as an int."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    """Return an API value as a float."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _assigned_to(value: Any) -> str:
    """Return the display name of an assignee."""
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return _as_text(value.get("displayName") or value.get("uniqueName"))
    return _as_text(value)


def _parse_datetime(value: Any) -> datetime | None:
    """Return an API timestamp as an aware UTC datetime.

    Azure DevOps sends ISO 8601 timestamps with a ``Z`` suffix and up to
    seven fractional digits; the fractions are truncated to the six digits
    the standard library understands. An unreadable timestamp is not an
    error: the field is simply left empty.
    """
    text = _as_text(value).strip()
    if not text:
        return None

    candidate = f"{text[:-1]}+00:00" if text.endswith(("Z", "z")) else text

    # ``2024-05-06T12:33:41.0000000+00:00`` -> ``...41.000000+00:00``
    trimmed = re.match(r"^(?P<head>.*\.\d{6})\d+(?P<tail>.*)$", candidate)
    if trimmed is not None:
        candidate = f"{trimmed.group('head')}{trimmed.group('tail')}"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        logger.debug("Could not read the timestamp %r", text)
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _mentions_work_item(pr: Mapping[str, Any], needle: str) -> bool:
    """Whether the title or the description of a pull request mentions the id."""
    text = " ".join(
        candidate
        for candidate in (_as_text(pr.get("title")), _as_text(pr.get("description")))
        if candidate
    )
    return needle in text


def _extract_prs(payload: Any) -> list[dict[str, Any]]:
    """Extract pull request objects from various API envelope shapes."""
    items: Any = payload
    if isinstance(payload, Mapping):
        for key in ("value", "results", "pullRequests"):
            if key in payload:
                items = payload[key]
                break

    if not isinstance(items, Sequence) or isinstance(items, str):
        return []

    prs: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, Mapping):
            prs.append(dict(item))
    return prs


def _error_detail(response: requests.Response) -> str:
    """Extract the human readable part of an Azure DevOps error payload."""
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200].strip()

    if isinstance(payload, Mapping):
        message = payload.get("message") or payload.get("typeName") or ""
        if message:
            return str(message)[:200]
    return str(payload)[:200]
