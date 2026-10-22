"""Tests of the configuration layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from azure_cli.config.settings import (
    AzureDevOpsSettings,
    default_config_path,
    load_settings,
)
from azure_cli.domain.exceptions import ConfigurationError


def test_the_settings_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "acme")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "widgets")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings()

    assert settings.organization == "acme"
    assert settings.project == "widgets"
    assert settings.pat.get_secret_value() == "a-token"


def test_the_settings_are_read_from_a_toml_file(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'organization = "acme"\nproject = "widgets"\npat = "a-token"\noutput_format = "json"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path=config)

    assert settings.organization == "acme"
    assert settings.output_format == "json"


def test_the_environment_wins_over_the_toml_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'organization = "from-file"\nproject = "widgets"\npat = "a-token"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")

    settings = load_settings(config_path=config)

    assert settings.organization == "from-env"


def test_the_command_line_wins_over_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "widgets")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings(overrides={"organization": "from-cli"})

    assert settings.organization == "from-cli"


def test_a_missing_configuration_is_reported_clearly() -> None:
    with pytest.raises(ConfigurationError, match="Missing configuration"):
        load_settings()


def test_the_api_url_is_built_from_the_organization_and_the_project(
    settings: AzureDevOpsSettings,
) -> None:
    assert settings.web_base_url == "https://dev.azure.com/acme/widgets"
    assert settings.api_base_url == "https://dev.azure.com/acme/widgets/_apis"


def test_the_base_url_can_be_overridden() -> None:
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="a-token",
        base_url="https://server/tfs/collection/widgets",
    )

    assert settings.api_base_url == "https://server/tfs/collection/widgets/_apis"


def test_the_pat_is_masked(settings: AzureDevOpsSettings) -> None:
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="super-secret-token",
    )

    assert settings.masked_pat.endswith("oken")
    assert "super" not in settings.masked_pat


def test_a_short_pat_is_fully_masked() -> None:
    settings = AzureDevOpsSettings(organization="acme", project="widgets", pat="abc")

    assert settings.masked_pat == "***"


def test_the_default_config_path_lives_in_the_home_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_CLI_CONFIG_PATH", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_CONFIG_FILE", raising=False)

    assert default_config_path() == Path.home() / ".azure_cli" / "config.toml"


def test_the_organization_and_the_project_have_a_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings()

    assert settings.organization == "serviciosfintech"
    assert settings.project == "bold"
    assert settings.api_version == "7.1"


def test_the_settings_can_be_written_with_their_aliases(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "acme"\nazure_project = "widgets"\npat_token = "a-token"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path=config)

    assert settings.organization == "acme"
    assert settings.project == "widgets"
    assert settings.pat.get_secret_value() == "a-token"


def test_the_aliases_are_exposed_by_the_settings() -> None:
    settings = AzureDevOpsSettings(
        organization="acme",
        project="widgets",
        pat="a-token",
    )

    assert settings.azure_org == "acme"
    assert settings.azure_project == "widgets"
    assert settings.pat_token == "a-token"


def test_the_email_of_the_user_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings()

    assert settings.default_email is None


def test_the_email_of_the_user_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_DEFAULT_EMAIL", "  ada@acme.com  ")

    settings = load_settings()

    assert settings.default_email == "ada@acme.com"


def test_an_invalid_email_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_DEFAULT_EMAIL", "not-an-email")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_settings()


def test_the_slack_settings_are_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings()

    assert settings.slack_channel is None
    assert settings.slack_token is None
    assert settings.masked_slack_token == ""


def test_the_slack_settings_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_SLACK_CHANNEL", "#work-items")
    monkeypatch.setenv("AZURE_DEVOPS_SLACK_TOKEN", "xoxb-secret-token")

    settings = load_settings()

    assert settings.slack_channel == "#work-items"
    assert settings.slack_token is not None
    assert settings.slack_token.get_secret_value() == "xoxb-secret-token"
    assert settings.masked_slack_token.endswith("oken")
    assert "secret" not in settings.masked_slack_token


def test_an_empty_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "   ")

    with pytest.raises(ConfigurationError, match="personal access token is empty"):
        load_settings()


def test_the_missing_token_names_the_variable_to_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ConfigurationError, match=r"pat \(AZURE_DEVOPS_PAT\)"):
        load_settings()


def test_a_profile_of_the_file_is_applied(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "acme"\npat = "a-token"\n'
        '[profiles.work]\nazure_org = "work-org"\ndefault_email = "ada@acme.com"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path=config, profile="work")

    assert settings.organization == "work-org"
    assert settings.default_email == "ada@acme.com"
    assert settings.profile == "work"


def test_the_profile_of_the_environment_is_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "acme"\npat = "a-token"\n[profiles.work]\nazure_org = "work-org"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_CLI_PROFILE", "work")

    settings = load_settings(config_path=config)

    assert settings.organization == "work-org"
    assert settings.profile == "work"


def test_the_legacy_profile_variable_is_still_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "acme"\npat = "a-token"\n[profiles.work]\nazure_org = "work-org"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_DEVOPS_PROFILE", "work")

    settings = load_settings(config_path=config)

    assert settings.organization == "work-org"
    assert settings.profile == "work"


def test_an_unknown_profile_is_reported(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('azure_org = "acme"\npat = "a-token"\n', encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Unknown configuration profile"):
        load_settings(config_path=config, profile="nope")


def test_the_environment_wins_over_the_profile_of_the_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "acme"\npat = "a-token"\n[profiles.work]\nazure_org = "work-org"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")

    settings = load_settings(config_path=config, profile="work")

    assert settings.organization == "from-env"


def test_the_defaults_are_used_when_the_file_does_not_set_a_value(
    tmp_path: Path,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text('pat = "a-token"\n', encoding="utf-8")

    settings = load_settings(config_path=config)

    assert settings.organization == "serviciosfintech"
    assert settings.project == "bold"
    assert settings.api_version == "7.1"
    assert settings.timeout == 15.0
    assert settings.output_format == "text"


def test_the_priority_is_defaults_then_file_then_environment_then_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'azure_org = "from-file"\n'
        'azure_project = "from-file"\n'
        'pat = "file-token"\n'
        'output_format = "json"\n'
        'api_version = "6.0"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "from-env")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "env-token")

    settings = load_settings(
        config_path=config,
        overrides={"project": "from-flag"},
    )

    # Flags win over the environment, which wins over the file, which wins
    # over the built-in defaults.
    assert settings.organization == "from-env"
    assert settings.project == "from-flag"
    assert settings.pat_token == "env-token"
    assert settings.output_format == "json"
    assert settings.api_version == "6.0"
    assert settings.timeout == 15.0


def test_the_environment_aliases_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_AZURE_ORG", "acme")
    monkeypatch.setenv("AZURE_DEVOPS_AZURE_PROJECT", "widgets")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings()

    assert settings.organization == "acme"
    assert settings.project == "widgets"


def test_the_timeout_is_read_as_a_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_TIMEOUT", "30.5")

    settings = load_settings()

    assert settings.timeout == 30.5


def test_an_invalid_output_format_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_OUTPUT_FORMAT", "yaml")

    with pytest.raises(ConfigurationError, match="Invalid configuration") as excinfo:
        load_settings()

    assert "output_format" in str(excinfo.value)


def test_an_invalid_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_TIMEOUT", "soon")

    with pytest.raises(ConfigurationError, match="Invalid configuration") as excinfo:
        load_settings()

    assert "timeout" in str(excinfo.value)


def test_a_malformed_file_is_reported_by_the_settings_loader(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('organization = "unterminated\n', encoding="utf-8")

    with pytest.raises(ConfigurationError, match="not valid TOML"):
        load_settings(config_path=config)


def test_an_explicitly_missing_file_falls_back_to_the_other_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")

    settings = load_settings(config_path=tmp_path / "does-not-exist.toml")

    assert settings.organization == "serviciosfintech"
    assert settings.pat_token == "a-token"


def test_a_blank_email_is_treated_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "a-token")
    monkeypatch.setenv("AZURE_DEVOPS_DEFAULT_EMAIL", "   ")

    assert load_settings().default_email is None
