"""Live integration tests of the configuration layer.

They check that a real TOML file and the real environment variables are
combined with the documented precedence. Like every live test they are opt-in
(``--run-live`` + ``AZURE_DEVOPS_PAT``) and they do not touch Azure DevOps.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from azure_cli.config.settings import AzureDevOpsSettings, load_settings

pytestmark = [pytest.mark.integration, pytest.mark.live]


@pytest.fixture(autouse=True)
def _require_live_credentials(live_credentials: str) -> None:
    """Skip the whole module when the live tests are not enabled."""


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the real ``AZURE_DEVOPS_*`` variables for a deterministic test.

    The live credentials are only needed to enable the module; the file tests
    must not be influenced by the developer machine.
    """
    for name in list(os.environ):
        if name.startswith("AZURE_DEVOPS_"):
            monkeypatch.delenv(name, raising=False)


def write_config(path: Path, content: str) -> Path:
    """Write a configuration file and return its path."""
    path.write_text(content, encoding="utf-8")
    return path


def test_the_real_environment_is_loaded(live_settings: AzureDevOpsSettings) -> None:
    assert live_settings.organization
    assert live_settings.project
    assert live_settings.pat_token
    assert live_settings.web_base_url.startswith("https://")
    assert live_settings.api_base_url.endswith("/_apis")
    assert live_settings.timeout > 0


def test_an_explicit_config_file_is_loaded(
    tmp_path: Path,
    clean_environment: None,
) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\n'
        'azure_project = "widgets"\n'
        'pat = "file-token"\n'
        'default_email = "ada@acme.com"\n'
        "timeout = 21.0\n",
    )

    settings = load_settings(config_path=config)

    assert settings.organization == "acme"
    assert settings.project == "widgets"
    assert settings.pat_token == "file-token"
    assert settings.default_email == "ada@acme.com"
    assert settings.timeout == 21.0


def test_the_config_file_is_discovered_through_the_environment(
    tmp_path: Path,
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\nazure_project = "widgets"\npat = "file-token"\n',
    )
    monkeypatch.setenv("AZURE_CLI_CONFIG_PATH", str(config))

    settings = load_settings()

    assert settings.organization == "acme"
    assert settings.project == "widgets"
    assert settings.pat_token == "file-token"


def test_a_profile_of_the_config_file_is_applied(
    tmp_path: Path,
    clean_environment: None,
) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\n'
        'azure_project = "widgets"\n'
        'pat = "file-token"\n'
        "[profiles.work]\n"
        'azure_org = "work-org"\n',
    )

    settings = load_settings(config_path=config, profile="work")

    assert settings.organization == "work-org"
    assert settings.project == "widgets"
    assert settings.profile == "work"


def test_environment_variables_override_the_config_file(
    tmp_path: Path,
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "from-file"\nazure_project = "from-file"\npat = "file-token"\n',
    )
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "env-token")

    settings = load_settings(config_path=config)

    assert settings.organization == "from-env"
    assert settings.project == "from-file"
    assert settings.pat_token == "env-token"


def test_command_line_overrides_win_over_every_source(
    tmp_path: Path,
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "from-file"\nazure_project = "from-file"\npat = "file-token"\n',
    )
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")

    settings = load_settings(
        config_path=config,
        overrides={"organization": "from-cli", "project": "from-cli"},
    )

    assert settings.organization == "from-cli"
    assert settings.project == "from-cli"
    assert settings.pat_token == "file-token"
