"""Azure DevOps work item tracking REST client."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import requests

from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.infrastructure.azure.dto import (
    CommentDto,
    WiqlResultDto,
    WorkItemDto,
    WorkItemListDto,
)
from azure_cli.infrastructure.debug import debug_print, is_debug, truncate_body

#: Maximum number of ids Azure DevOps accepts in a batch ``ids=`` request.
MAX_BATCH_SIZE = 200


class AzureWorkItemApiClient:
    """Thin wrapper around the Azure DevOps work item tracking REST API.

    It knows about URLs, verbs and payloads; it does not know about business
    rules — mapping the payloads to domain objects is the repository's job.
    """

    def __init__(
        self,
        session: requests.Session,
        *,
        api_base_url: str,
        api_version: str = "7.1",
        timeout: float = 15.0,
    ) -> None:
        self._session = session
        self._api_base_url = api_base_url.rstrip("/")
        self._api_version = api_version
        self._timeout = timeout

    # -- reading ------------------------------------------------------------
    def get_work_item(self, work_item_id: int, fields: Sequence[str]) -> WorkItemDto:
        """Return a single work item with the requested fields."""
        response = self._request(
            "GET",
            f"/wit/workitems/{work_item_id}",
            params={"fields": ",".join(fields), "api-version": self._api_version},
            not_found_message=f"Work item {work_item_id} was not found",
        )
        return WorkItemDto.model_validate(response.json())

    def get_work_items(self, ids: Sequence[int], fields: Sequence[str]) -> list[WorkItemDto]:
        """Return several work items in a single request."""
        if not ids:
            return []

        collected: list[WorkItemDto] = []
        for chunk in self._chunks(ids, MAX_BATCH_SIZE):
            response = self._request(
                "GET",
                "/wit/workitems",
                params={
                    "ids": ",".join(str(item_id) for item_id in chunk),
                    "fields": ",".join(fields),
                    "api-version": self._api_version,
                },
            )
            payload = WorkItemListDto.model_validate(response.json())
            collected.extend(payload.value)
        return collected

    def query_by_wiql(
        self,
        wiql: str,
        fields: Sequence[str],
        *,
        top: int | None = None,
    ) -> list[WorkItemDto]:
        """Run a WIQL query and return the matching work items."""
        response = self._request(
            "POST",
            "/wit/wiql",
            params={"api-version": self._api_version},
            json_body={"query": wiql},
        )
        result = WiqlResultDto.model_validate(response.json())
        if is_debug():
            debug_print(f"[DEBUG] WIQL response: {response.text}")
        ids = [relation.id for relation in result.work_item_relations]
        if top is not None:
            ids = ids[:top]
        return self.get_work_items(ids, fields)

    # -- writing ------------------------------------------------------------
    def create_work_item(
        self,
        work_item_type: str,
        fields: Mapping[str, Any],
    ) -> WorkItemDto:
        """Create a work item of the given type."""
        response = self._request(
            "POST",
            f"/wit/workitems/${work_item_type}",
            params={"api-version": self._api_version},
            json_body={"fields": dict(fields)},
        )
        return WorkItemDto.model_validate(response.json())

    def update_work_item(
        self,
        work_item_id: int,
        changes: Mapping[str, Any],
    ) -> WorkItemDto:
        """Apply field changes to a work item using a JSON Patch document."""
        operations = [
            {"op": "add", "path": f"/fields/{field}", "value": value}
            for field, value in changes.items()
        ]
        response = self._request(
            "PATCH",
            f"/wit/workitems/{work_item_id}",
            params={"api-version": self._api_version},
            json_body=operations,
            not_found_message=f"Work item {work_item_id} was not found",
        )
        return WorkItemDto.model_validate(response.json())

    def add_comment(self, work_item_id: int, text: str) -> CommentDto:
        """Add a comment to a work item."""
        response = self._request(
            "POST",
            f"/wit/workitems/{work_item_id}/comments",
            params={"api-version": self._api_version},
            json_body={"text": text},
            not_found_message=f"Work item {work_item_id} was not found",
        )
        return CommentDto.model_validate(response.json())

    # -- plumbing -----------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        not_found_message: str | None = None,
    ) -> requests.Response:
        """Perform an HTTP call and translate the failures into domain errors."""
        url = f"{self._api_base_url}{path}"
        if is_debug():
            debug_print(f"\n[DEBUG] Request: {method} {url}")
            debug_print(f"[DEBUG] Headers: {self._session.headers}")
            debug_print(f"[DEBUG] Params: {dict(params) if params else None}")
            debug_print(f"[DEBUG] Body: {json_body}")

        try:
            response = self._session.request(
                method,
                url,
                params=dict(params) if params else None,
                json=json_body,
                timeout=self._timeout,
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
        """Map an HTTP error response onto the matching domain exception."""
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

    @staticmethod
    def _chunks(items: Sequence[int], size: int) -> list[list[int]]:
        """Split a sequence into chunks of at most ``size`` elements."""
        return [list(items[index : index + size]) for index in range(0, len(items), size)]


def _error_detail(response: requests.Response) -> str:
    """Extract the human readable part of an Azure DevOps error payload."""
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200].strip()

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("typeName") or ""
        if message:
            return str(message)[:200]
    return str(payload)[:200]
