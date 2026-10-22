"""Infrastructure exceptions for the Azure DevOps integration."""

from __future__ import annotations

from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    AzureWiError,
    TransportError,
    WorkItemNotFoundError,
)

# Keep the name expected by the infrastructure layer while reusing the
# existing domain hierarchy: a client may choose to catch these in one place.
NotFoundError = WorkItemNotFoundError
APIError = AzureApiError


class AzureDevOpsError(AzureWiError):
    """Base class for Azure DevOps integration failures."""

    pass


__all__ = [
    "APIError",
    "AuthenticationError",
    "AzureApiError",
    "AzureDevOpsError",
    "AzureWiError",
    "NotFoundError",
    "TransportError",
    "WorkItemNotFoundError",
]
