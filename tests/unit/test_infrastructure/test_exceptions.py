"""Unit tests of the infrastructure exceptions."""

from __future__ import annotations

from azure_cli.domain.exceptions import (
    AuthenticationError,
    AzureApiError,
    AzureWiError,
    TransportError,
    WorkItemNotFoundError,
)
from azure_cli.infrastructure.exceptions import (
    APIError,
    AzureDevOpsError,
    NotFoundError,
)
from azure_cli.infrastructure.exceptions import (
    AuthenticationError as InfrastructureAuthenticationError,
)


def test_the_base_error_catches_every_infrastructure_failure() -> None:
    assert issubclass(AzureDevOpsError, AzureWiError)


def test_the_authentication_error_is_the_one_of_the_domain() -> None:
    assert InfrastructureAuthenticationError is AuthenticationError


def test_the_not_found_error_is_the_one_of_the_domain() -> None:
    assert NotFoundError is WorkItemNotFoundError


def test_the_api_error_is_the_one_of_the_domain() -> None:
    assert APIError is AzureApiError


def test_the_api_error_keeps_the_status_code() -> None:
    error = APIError("boom", status_code=500)

    assert error.status_code == 500
    assert str(error) == "boom"


def test_the_transport_error_is_available() -> None:
    assert issubclass(TransportError, AzureWiError)
