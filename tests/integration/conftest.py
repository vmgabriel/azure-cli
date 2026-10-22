"""Fixtures of the integration tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
import requests

from azure_cli.config.settings import AzureDevOpsSettings, load_settings
from azure_cli.domain.exceptions import ConfigurationError
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.azure_client import AzureDevOpsClient
from azure_cli.infrastructure.git.git_api_client import AzureGitApiClient
from azure_cli.infrastructure.http.session import build_session
from tests.integration.stub_server import StubAzureDevOps, start_stub_server

#: Environment variable holding the comma separated ids of known work items.
TEST_WORK_ITEM_IDS_ENV_VAR = "AZURE_DEVOPS_TEST_WORK_ITEM_IDS"

#: Environment variable holding the e-mail whose work items are listed.
TEST_EMAIL_ENV_VAR = "AZURE_DEVOPS_TEST_EMAIL"

#: Ceiling of the timeout used by the live client, in seconds.
MAX_LIVE_TIMEOUT = 30.0


@pytest.fixture
def stub() -> Iterator[StubAzureDevOps]:
    """Run a stub Azure DevOps server for the duration of a test."""
    stub, server = start_stub_server()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def session() -> requests.Session:
    """An authenticated session pointing at nothing in particular."""
    return build_session("fake-token")


@pytest.fixture
def work_item_client(
    stub: StubAzureDevOps,
    session: requests.Session,
) -> AzureWorkItemApiClient:
    """A work item API client talking to the stub server."""
    return AzureWorkItemApiClient(
        session,
        api_base_url=stub.api_base_url,
        api_version="7.1",
        timeout=5.0,
    )


@pytest.fixture
def git_client(
    stub: StubAzureDevOps,
    session: requests.Session,
) -> AzureGitApiClient:
    """A git API client talking to the stub server."""
    return AzureGitApiClient(
        session,
        api_base_url=stub.api_base_url,
        api_version="7.1",
        timeout=5.0,
    )


# -- live tests against the real Azure DevOps API ----------------------------


@pytest.fixture
def live_credentials(request: pytest.FixtureRequest) -> str:
    """Return the real PAT, or skip the test when live tests are not enabled.

    The live tests are opt-in on purpose: they need a real token, network
    access and a project they are allowed to read.
    """
    if not request.config.getoption("--run-live"):
        pytest.skip(
            "live tests are disabled; run them with `make test-integration` or `pytest --run-live`"
        )

    pat = os.environ.get("AZURE_DEVOPS_PAT", "").strip()
    if not pat:
        pytest.skip("AZURE_DEVOPS_PAT is not set; skipping the live Azure DevOps tests")
    return pat


@pytest.fixture
def live_settings(live_credentials: str) -> AzureDevOpsSettings:
    """The real configuration, with a bounded timeout for the live calls."""
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        pytest.skip(f"the live configuration is incomplete: {exc}")

    timeout = min(float(settings.timeout), MAX_LIVE_TIMEOUT)
    return settings.model_copy(update={"timeout": timeout})


@pytest.fixture
def live_client(live_settings: AzureDevOpsSettings) -> AzureDevOpsClient:
    """A client talking to the real Azure DevOps API."""
    return AzureDevOpsClient(live_settings)


@pytest.fixture
def live_email(live_settings: AzureDevOpsSettings) -> str:
    """The e-mail whose work items are listed by the live tests."""
    email = (os.environ.get(TEST_EMAIL_ENV_VAR) or live_settings.default_email or "").strip()
    if not email:
        pytest.skip(
            f"set AZURE_DEVOPS_DEFAULT_EMAIL or {TEST_EMAIL_ENV_VAR} to run the live list tests"
        )
    return email


def _parse_work_item_ids(raw: str) -> tuple[int, ...]:
    """Parse a comma or semicolon separated list of work item ids."""
    ids: list[int] = []
    for part in raw.replace(";", ",").split(","):
        candidate = part.strip()
        if candidate.isdigit() and int(candidate) > 0:
            ids.append(int(candidate))
    return tuple(ids)


@pytest.fixture
def test_work_item_ids(live_credentials: str) -> tuple[int, ...]:
    """The known work items of the project used by the live tests.

    The ids cannot be guessed, so they are configured with
    ``AZURE_DEVOPS_TEST_WORK_ITEM_IDS`` (for example ``1234,5678``). Pick
    work items of the configured project that the PAT can read.
    """
    raw = os.environ.get(TEST_WORK_ITEM_IDS_ENV_VAR, "")
    ids = _parse_work_item_ids(raw)
    if not ids:
        pytest.skip(
            f"set {TEST_WORK_ITEM_IDS_ENV_VAR}=<id>[,<id>...] to run the live work item tests"
        )
    return ids


@pytest.fixture
def test_work_item_id(test_work_item_ids: tuple[int, ...]) -> int:
    """The known work item used by the live detail tests."""
    return test_work_item_ids[0]
