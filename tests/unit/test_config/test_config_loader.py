"""Tests of the configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from azure_cli.config.config_loader import (
    DEFAULT_PROFILE,
    ConfigLoader,
    available_profiles,
    candidate_config_paths,
    default_config_path,
    legacy_config_path,
    load_config,
    read_config_file,
    resolve_config_path,
    resolve_profile,
    select_profile,
)
from azure_cli.domain.exceptions import ConfigurationError


def write_config(path: Path, content: str) -> Path:
    """Write a configuration file and return its path."""
    path.write_text(content, encoding="utf-8")
    return path


def test_the_default_path_lives_in_the_home_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_CLI_CONFIG_PATH", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_CONFIG_FILE", raising=False)

    assert default_config_path() == Path.home() / ".azure_cli" / "config.toml"


def test_the_candidate_path_is_the_default_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_CLI_CONFIG_PATH", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_CONFIG_FILE", raising=False)

    assert legacy_config_path() == default_config_path()
    assert candidate_config_paths() == (default_config_path(),)


def test_an_explicit_path_wins_over_the_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CLI_CONFIG_PATH", str(tmp_path / "from-env.toml"))

    assert resolve_config_path(tmp_path / "explicit.toml") == tmp_path / "explicit.toml"


def test_the_environment_variable_wins_over_the_default_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CLI_CONFIG_PATH", str(tmp_path / "from-env.toml"))

    assert resolve_config_path() == tmp_path / "from-env.toml"


def test_the_legacy_environment_variable_is_still_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_CLI_CONFIG_PATH", raising=False)
    monkeypatch.setenv("AZURE_DEVOPS_CONFIG_FILE", str(tmp_path / "legacy.toml"))

    assert resolve_config_path() == tmp_path / "legacy.toml"


def test_a_missing_file_falls_back_to_the_default_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_CLI_CONFIG_PATH", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_CONFIG_FILE", raising=False)

    assert resolve_config_path() == Path.home() / ".azure_cli" / "config.toml"


def test_a_malformed_file_is_reported_as_a_configuration_error(tmp_path: Path) -> None:
    broken = write_config(tmp_path / "config.toml", "this is = not = toml\n")

    with pytest.raises(ConfigurationError, match="not valid TOML"):
        read_config_file(broken)


def test_the_profiles_of_a_file_are_listed() -> None:
    data: dict[str, Any] = {"profiles": {"work": {}, "personal": {}}}

    assert available_profiles(data) == ("work", "personal")


def test_the_root_keys_describe_the_default_profile() -> None:
    data = {"azure_org": "acme", "azure_project": "widgets"}

    assert select_profile(data, DEFAULT_PROFILE) == data


def test_the_nested_sections_are_flattened() -> None:
    data: dict[str, Any] = {
        "azure": {
            "org": "acme",
            "project": "widgets",
            "api_version": "7.1",
        },
        "user": {"email": "ada@acme.com"},
        "slack": {"channel": "#workitems", "token": "slack-token"},
    }

    assert select_profile(data, DEFAULT_PROFILE) == {
        "azure_org": "acme",
        "azure_project": "widgets",
        "api_version": "7.1",
        "default_email": "ada@acme.com",
        "slack_channel": "#workitems",
        "slack_token": "slack-token",
    }


def test_a_nested_profile_section_overrides_the_root_keys() -> None:
    data: dict[str, Any] = {
        "azure": {"org": "acme", "project": "widgets"},
        "profiles": {"work": {"azure": {"org": "work-org"}}},
    }

    selected = select_profile(data, "work")

    assert selected["azure_org"] == "work-org"
    assert selected["azure_project"] == "widgets"


def test_flat_keys_win_over_the_nested_sections() -> None:
    data: dict[str, Any] = {
        "azure_org": "flat-org",
        "azure": {"org": "nested-org"},
    }

    assert select_profile(data, DEFAULT_PROFILE)["azure_org"] == "flat-org"


def test_a_profile_overrides_the_root_keys() -> None:
    data: dict[str, Any] = {
        "azure_org": "acme",
        "azure_project": "widgets",
        "profiles": {"work": {"azure_project": "other"}},
    }

    selected = select_profile(data, "work")

    assert selected["azure_org"] == "acme"
    assert selected["azure_project"] == "other"


def test_an_unknown_profile_is_reported() -> None:
    data: dict[str, Any] = {"profiles": {"work": {}}}

    with pytest.raises(ConfigurationError, match="Unknown configuration profile"):
        select_profile(data, "nope")


def test_the_requested_profile_wins_over_the_environment() -> None:
    assert resolve_profile(requested="work", env_profile="other") == "work"


def test_the_environment_wins_over_the_file() -> None:
    assert resolve_profile(env_profile="work", data={"profile": "other"}) == "work"


def test_the_file_provides_the_default_profile() -> None:
    assert resolve_profile(data={"profile": "work"}) == "work"


def test_the_default_profile_is_used_when_nothing_is_requested() -> None:
    assert resolve_profile() == DEFAULT_PROFILE


def test_the_loader_reads_the_configuration_file(tmp_path: Path) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\nazure_project = "widgets"\npat = "a-token"\n',
    )

    settings = ConfigLoader(config_path=config).load()

    assert settings.organization == "acme"
    assert settings.project == "widgets"
    assert settings.pat.get_secret_value() == "a-token"


def test_the_loader_applies_the_requested_profile(tmp_path: Path) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\npat = "a-token"\n[profiles.work]\nazure_org = "work-org"\n',
    )

    settings = ConfigLoader(config_path=config, profile="work").load()

    assert settings.organization == "work-org"
    assert settings.profile == "work"


def test_the_minimal_example_configuration_is_supported() -> None:
    example = Path(__file__).resolve().parents[3] / "config" / "example_config.toml"

    settings = load_config(config_path=example, overrides={"pat": "a-token"})

    assert settings.organization == "serviciosfintech"
    assert settings.project == "bold"
    assert settings.api_version == "7.1"
    assert settings.default_email == "gabriel.vargas@bold.co"
    assert settings.slack_channel == "#workitems"
    assert settings.slack_token is not None
    assert settings.slack_token.get_secret_value() == ""


def test_the_full_example_configuration_is_supported() -> None:
    example = Path(__file__).resolve().parents[3] / "config.example.toml"

    settings = load_config(
        config_path=example,
        profile="work",
        overrides={"pat": "a-token"},
    )

    assert settings.organization == "serviciosfintech"
    assert settings.project == "bold"
    assert settings.profile == "work"
    assert settings.timeout == 15.0


def test_the_loader_validates_the_configuration(tmp_path: Path) -> None:
    config = write_config(tmp_path / "config.toml", 'azure_org = "acme"\n')

    with pytest.raises(ConfigurationError, match="Missing configuration"):
        ConfigLoader(config_path=config).load()


def test_the_shortcut_loads_the_configuration(tmp_path: Path) -> None:
    config = write_config(
        tmp_path / "config.toml",
        'azure_org = "acme"\npat = "a-token"\n',
    )

    settings = load_config(config_path=config)

    assert settings.organization == "acme"
