"""Domain exceptions.

The domain layer knows nothing about HTTP, Azure DevOps or the terminal; it
only signals *why* an operation could not be completed. The infrastructure and
presentation layers translate these into transport errors and exit codes.
"""

from __future__ import annotations


class AzureWiError(Exception):
    """Base class for every error raised by this tool."""


class DomainError(AzureWiError):
    """Base class for business-rule violations."""


class ConfigurationError(AzureWiError):
    """Missing or invalid configuration (organization, project, PAT...)."""


class AuthenticationError(AzureWiError):
    """Azure DevOps rejected the credentials (401/403)."""


class TransportError(AzureWiError):
    """The Azure DevOps API could not be reached."""


class AzureApiError(AzureWiError):
    """Azure DevOps returned an unexpected error response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InvalidWorkItemIdError(DomainError, ValueError):
    """A work item identifier is not a positive integer.

    It is a ``ValueError`` too: an identifier that cannot be used is an
    invalid argument value, and the callers should be able to catch it as
    such without knowing the domain hierarchy.
    """


class WorkItemValidationError(DomainError):
    """A work item violates a business rule (e.g. blank title)."""


class WorkItemNotFoundError(DomainError):
    """The requested work item does not exist."""


class WorkItemTypeError(DomainError):
    """The work item type is not supported for the requested operation."""
