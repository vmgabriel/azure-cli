"""Azure DevOps git REST client."""

from __future__ import annotations

from collections.abc import Mapping

import requests

from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    TransportError,
)
from azure_cli.infrastructure.azure.dto import PullRequestDto

#: How many pull requests are inspected when looking for implicit references.
DEFAULT_TOP = 50


class AzureGitApiClient:
    """Thin wrapper around the Azure DevOps git REST API."""

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

    def list_pull_requests(
        self,
        *,
        top: int = DEFAULT_TOP,
        status: str = "all",
    ) -> list[PullRequestDto]:
        """Return the most recent pull requests of the project."""
        response = self._request(
            "GET",
            "/git/pullrequests",
            params={
                "searchCriteria.status": status,
                "$top": top,
                "api-version": self._api_version,
            },
        )
        payload = response.json()
        raw_items = payload.get("value", []) if isinstance(payload, dict) else []
        return [PullRequestDto.model_validate(item) for item in raw_items]

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
    ) -> requests.Response:
        """Perform an HTTP call and translate the failures into domain errors."""
        url = f"{self._api_base_url}{path}"
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise TransportError(f"Could not reach Azure DevOps at {url}: {exc}") from exc

        status = response.status_code
        if status < 400:
            return response
        if status in (401, 403):
            raise AuthenticationError(
                "Azure DevOps rejected the credentials while reading git data."
            )
        raise AzureApiError(
            f"Azure DevOps returned HTTP {status} for {url}.",
            status_code=status,
        )
