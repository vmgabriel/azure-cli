"""Discovery and reading of the configuration file.

This module only knows about the *file*: where it lives, how it is parsed and
which profile of it must be applied. It knows nothing about the settings
model itself, so both the settings and the tests can use it without creating
a circular import.

The configuration file is TOML::

    [azure]
    org = "serviciosfintech"
    project = "bold"

    [profiles.work.azure]
    org = "another-organization"

The flat keys of older versions (``azure_org``, ``azure_project``, ...) are
still accepted. The values of the selected profile are merged over the root
keys, and the environment variables are applied on top of the result.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from azure_cli.domain.exceptions import ConfigurationError

if TYPE_CHECKING:  # pragma: no cover - imported for the type checker only
    from azure_cli.config.settings import AzureDevOpsSettings

#: Name of the environment variable pointing at the TOML configuration file.
CONFIG_FILE_ENV_VAR = "AZURE_CLI_CONFIG_PATH"

#: Previous name of the configuration path variable, still accepted.
LEGACY_CONFIG_FILE_ENV_VAR = "AZURE_DEVOPS_CONFIG_FILE"

#: Name of the environment variable holding the profile to use.
PROFILE_ENV_VAR = "AZURE_CLI_PROFILE"

#: Previous name of the profile variable, still accepted.
LEGACY_PROFILE_ENV_VAR = "AZURE_DEVOPS_PROFILE"

#: Directory holding the user level configuration.
CONFIG_DIR_NAME = ".azure_cli"

#: Name of the configuration file inside the configuration directory.
CONFIG_FILE_NAME = "config.toml"

#: Name of the profile applied when none is requested.
DEFAULT_PROFILE = "default"

#: Keys of the TOML file holding the profiles.
PROFILES_KEYS = ("profiles", "profile")

#: Nested sections accepted by the file, and the flat setting each key feeds.
#:
#: The flat keys (``azure_org``, ``default_email``, ...) are still supported;
#: the nested sections are the recommended form because they group the values
#: by the part of the configuration they belong to.
SECTION_ALIASES: dict[str, dict[str, str]] = {
    "azure": {
        "org": "azure_org",
        "organization": "azure_org",
        "project": "azure_project",
        "pat": "pat_token",
        "api_version": "api_version",
        "base_url": "base_url",
    },
    "user": {
        "email": "default_email",
    },
    "slack": {
        "channel": "slack_channel",
        "token": "slack_token",
    },
}


def _flatten_sections(data: Mapping[str, Any]) -> dict[str, Any]:
    """Expand the nested sections into the flat keys the settings expect.

    Flat keys win over their nested equivalent, so a file that mixes both
    forms keeps working exactly as before. Profiles are flattened one by one
    by :func:`select_profile`, which keeps the profile precedence intact.
    """
    flattened = {
        key: value
        for key, value in data.items()
        if not (key in SECTION_ALIASES and isinstance(value, Mapping))
    }
    for section_name, section in data.items():
        aliases = SECTION_ALIASES.get(section_name)
        if aliases is None or not isinstance(section, Mapping):
            continue
        for key, value in section.items():
            canonical_key = aliases.get(str(key))
            flattened.setdefault(canonical_key or str(key), value)
    return flattened


def _environment_value(primary: str, legacy: str) -> str | None:
    """Return the value of the primary variable, falling back to the legacy one."""
    return os.environ.get(primary) or os.environ.get(legacy)


def default_config_path() -> Path:
    """Return the path of the user level TOML configuration file.

    ``AZURE_CLI_CONFIG_PATH`` wins over the legacy
    ``AZURE_DEVOPS_CONFIG_FILE``; without either, the file lives in
    ``~/.azure_cli/config.toml``.
    """
    override = _environment_value(CONFIG_FILE_ENV_VAR, LEGACY_CONFIG_FILE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / CONFIG_DIR_NAME / CONFIG_FILE_NAME


def legacy_config_path() -> Path:
    """Deprecated alias of :func:`default_config_path`."""
    return default_config_path()


def candidate_config_paths() -> tuple[Path, ...]:
    """Return the configuration locations, most specific first."""
    return (default_config_path(),)


def resolve_config_path(explicit: Path | None = None) -> Path:
    """Return the configuration file to read.

    An explicit path wins over ``AZURE_CLI_CONFIG_PATH`` (or its legacy
    ``AZURE_DEVOPS_CONFIG_FILE`` alias), which wins over
    ``~/.azure_cli/config.toml``. When the file does not exist the default
    location is returned so that the error messages can point at it.
    """
    if explicit is not None:
        return explicit.expanduser()
    return default_config_path()


def read_config_file(path: Path) -> dict[str, Any]:
    """Return the content of a TOML configuration file.

    An unreadable or malformed file is reported as a configuration error
    instead of a raw ``TOMLDecodeError``.
    """
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except OSError as exc:
        raise ConfigurationError(f"Cannot read the configuration file {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"The configuration file {path} is not valid TOML: {exc}") from exc


def available_profiles(data: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the names of the profiles declared in a configuration file."""
    profiles: dict[str, Any] = {}
    for key in PROFILES_KEYS:
        section = data.get(key)
        if isinstance(section, Mapping):
            profiles.update(section)
    return tuple(profiles)


def select_profile(data: Mapping[str, Any], profile: str) -> dict[str, Any]:
    """Return the values of the given profile, merged over the root keys.

    The root keys of the file describe the ``default`` profile. The values of
    the requested profile are applied on top of them. Both the root keys and
    the profile may use the nested ``[azure]``, ``[user]`` and ``[slack]``
    sections.

    Raises:
        ConfigurationError: if the requested profile is not declared in the
            file.
    """
    base = _flatten_sections(
        {
            key: value
            for key, value in data.items()
            if not (key in PROFILES_KEYS and isinstance(value, Mapping))
        }
    )

    profiles: dict[str, Any] = {}
    for key in PROFILES_KEYS:
        section = data.get(key)
        if isinstance(section, Mapping):
            profiles.update(section)

    if profile in profiles:
        selected = profiles[profile]
    elif profile == DEFAULT_PROFILE:
        selected = {}
    else:
        known = ", ".join(sorted(profiles)) or "none"
        raise ConfigurationError(
            f"Unknown configuration profile {profile!r}. Available profiles: {known}."
        )

    if not isinstance(selected, Mapping):
        raise ConfigurationError(f"The configuration profile {profile!r} must be a table.")

    return {**base, **_flatten_sections(selected)}


def resolve_profile(
    *,
    requested: str | None = None,
    env_profile: str | None = None,
    data: Mapping[str, Any] | None = None,
) -> str:
    """Return the profile to apply.

    The explicitly requested profile wins over ``AZURE_CLI_PROFILE`` (or its
    legacy ``AZURE_DEVOPS_PROFILE`` alias), which wins over the ``profile``
    key of the configuration file.
    """
    if requested:
        return requested
    if env_profile:
        return env_profile
    if data:
        file_profile = data.get("profile")
        if isinstance(file_profile, str) and file_profile:
            return file_profile
    return DEFAULT_PROFILE


class ConfigLoader:
    """Load the configuration of the tool.

    The loader is the programmatic entry point of the configuration layer:
    it resolves the file to read, applies the profile and validates the
    result.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        profile: str | None = None,
    ) -> None:
        """Create a loader.

        Args:
            config_path: the configuration file to read. When omitted, the
                well known locations are used.
            profile: the profile to apply. When omitted, it is deduced from
                the environment or from the configuration file.
        """
        self.config_path = resolve_config_path(config_path)
        self.profile = profile

    def load(self, overrides: Mapping[str, Any] | None = None) -> AzureDevOpsSettings:
        """Return the validated settings.

        Args:
            overrides: values that win over every other source, typically the
                options given on the command line.

        Raises:
            ConfigurationError: if the configuration is missing or invalid.
        """
        from azure_cli.config.settings import load_settings

        return load_settings(
            config_path=self.config_path,
            overrides=overrides,
            profile=self.profile,
        )


def load_config(
    *,
    config_path: Path | None = None,
    profile: str | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> AzureDevOpsSettings:
    """Return the validated settings of the given configuration.

    Shortcut around :class:`ConfigLoader`.
    """
    return ConfigLoader(config_path=config_path, profile=profile).load(overrides)
