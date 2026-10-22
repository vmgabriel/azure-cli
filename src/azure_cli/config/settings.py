"""Configuration of the Azure DevOps connection.

Precedence (highest wins):

1. CLI flags (``--org``, ``--project``, ...)
2. environment variables (``AZURE_DEVOPS_*`` for the connection and
   ``AZURE_CLI_*`` for tool settings)
3. the ``.env`` file of the project
4. the TOML configuration file (``~/.azure_cli/config.toml``)
5. the built-in defaults

The settings are built by Pydantic, but the *values* they hold are plain
Python objects, so the rest of the code never depends on the validation
library.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from azure_cli.config.config_loader import (
    CONFIG_DIR_NAME,
    CONFIG_FILE_ENV_VAR,
    DEFAULT_PROFILE,
    LEGACY_PROFILE_ENV_VAR,
    PROFILE_ENV_VAR,
    default_config_path,
    read_config_file,
    resolve_config_path,
    resolve_profile,
    select_profile,
)
from azure_cli.domain.exceptions import ConfigurationError

__all__ = [
    "CONFIG_DIR_NAME",
    "CONFIG_FILE_ENV_VAR",
    "DEFAULT_ORGANIZATION",
    "DEFAULT_PROJECT",
    "AzureDevOpsSettings",
    "OutputFormat",
    "TomlProfileSettingsSource",
    "default_config_path",
    "load_settings",
]

#: Organization used when nothing else is configured.
DEFAULT_ORGANIZATION = "serviciosfintech"

#: Project used when nothing else is configured.
DEFAULT_PROJECT = "bold"

#: REST API version used when nothing else is configured.
DEFAULT_API_VERSION = "7.1"

OutputFormat = Literal["text", "json"]

#: Overrides the TOML location for the current call of `load_settings`.
_CONFIG_PATH: ContextVar[Path | None] = ContextVar("azure_cli_config_path", default=None)

#: Overrides the profile for the current call of `load_settings`.
_PROFILE: ContextVar[str | None] = ContextVar("azure_cli_profile", default=None)


def _alias_keys(field: FieldInfo) -> tuple[str, ...]:
    """Return the alternative names accepted for a field."""
    alias = field.validation_alias
    if alias is None:
        return ()
    if isinstance(alias, str):
        return (alias,)
    if isinstance(alias, AliasChoices):
        return tuple(choice for choice in alias.choices if isinstance(choice, str))
    return ()


class TomlProfileSettingsSource(PydanticBaseSettingsSource):
    """Read the settings from the TOML configuration file.

    The file may declare several profiles: the values of the selected profile
    are applied over the root keys of the file, which describe the
    ``default`` profile.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        toml_file: Path,
        profile: str | None = None,
    ) -> None:
        super().__init__(settings_cls)
        self._toml_file = toml_file
        self._data = read_config_file(toml_file)
        self._profile = resolve_profile(
            requested=profile,
            env_profile=os.environ.get(PROFILE_ENV_VAR) or os.environ.get(LEGACY_PROFILE_ENV_VAR),
            data=self._data,
        )
        self._values = select_profile(self._data, self._profile)

    @property
    def profile(self) -> str:
        """The profile applied by this source."""
        return self._profile

    @property
    def toml_file(self) -> Path:
        """The file this source reads."""
        return self._toml_file

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the value of a field, read from the file."""
        for key in (field_name, *_alias_keys(field)):
            if key in self._values:
                return self._values[key], field_name, False
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return the values of the file, keyed by field name."""
        values: dict[str, Any] = {}
        for name, field in self.settings_cls.model_fields.items():
            for key in (name, *_alias_keys(field)):
                if key in self._values:
                    values[name] = self._values[key]
                    break
        return values


class AzureDevOpsSettings(BaseSettings):
    """Everything needed to talk to Azure DevOps."""

    model_config = SettingsConfigDict(
        env_prefix="AZURE_DEVOPS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    organization: str = Field(
        default=DEFAULT_ORGANIZATION,
        validation_alias=AliasChoices(
            "AZURE_DEVOPS_ORGANIZATION",
            "AZURE_DEVOPS_AZURE_ORG",
            "organization",
            "azure_org",
        ),
    )
    project: str = Field(
        default=DEFAULT_PROJECT,
        validation_alias=AliasChoices(
            "AZURE_DEVOPS_PROJECT",
            "AZURE_DEVOPS_AZURE_PROJECT",
            "project",
            "azure_project",
        ),
    )
    pat: SecretStr = Field(
        validation_alias=AliasChoices(
            "AZURE_DEVOPS_PAT",
            "pat",
            "pat_token",
        ),
    )
    api_version: str = DEFAULT_API_VERSION
    default_email: str | None = None
    slack_channel: str | None = None
    slack_token: SecretStr | None = None
    profile: str = Field(
        default=DEFAULT_PROFILE,
        validation_alias=AliasChoices(
            "AZURE_CLI_PROFILE",
            "AZURE_DEVOPS_PROFILE",
            "profile",
        ),
    )
    timeout: float = 15.0
    output_format: OutputFormat = "text"
    base_url: str | None = None

    @field_validator("pat")
    @classmethod
    def _reject_empty_pat(cls, value: SecretStr) -> SecretStr:
        """Refuse an empty token: it would fail with a confusing 401."""
        if not value.get_secret_value().strip():
            raise ValueError("the personal access token is empty")
        return value

    @field_validator("default_email")
    @classmethod
    def _normalize_default_email(cls, value: str | None) -> str | None:
        """Normalize the email used to filter the work items."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if "@" not in normalized or " " in normalized:
            raise ValueError("default_email must be a valid email address")
        return normalized

    # -- aliases ------------------------------------------------------------
    @property
    def azure_org(self) -> str:
        """The Azure DevOps organization (alias of ``organization``)."""
        return self.organization

    @property
    def azure_project(self) -> str:
        """The Azure DevOps project (alias of ``project``)."""
        return self.project

    @property
    def pat_token(self) -> str:
        """The personal access token, in clear text (alias of ``pat``)."""
        return self.pat.get_secret_value()

    # -- URLs ----------------------------------------------------------------
    @property
    def web_base_url(self) -> str:
        """The browser URL of the project (without the ``/_apis`` suffix)."""
        if self.base_url:
            return self.base_url.rstrip("/")
        return f"https://dev.azure.com/{self.organization}/{self.project}"

    @property
    def api_base_url(self) -> str:
        """The root URL of the Azure DevOps REST API for this project."""
        return f"{self.web_base_url}/_apis"

    # -- secrets -------------------------------------------------------------
    @property
    def masked_pat(self) -> str:
        """The PAT, safe to print: only the last four characters are shown."""
        return _mask(self.pat.get_secret_value())

    @property
    def masked_slack_token(self) -> str:
        """The Slack token, safe to print: only the last four characters show."""
        if self.slack_token is None:
            return ""
        return _mask(self.slack_token.get_secret_value())

    # -- sources -------------------------------------------------------------
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Add the TOML configuration file to the standard sources."""
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
            dotenv_settings,
        ]

        path = _CONFIG_PATH.get() or resolve_config_path()
        if path.is_file():
            sources.append(
                TomlProfileSettingsSource(
                    settings_cls,
                    toml_file=path,
                    profile=_PROFILE.get(),
                )
            )

        sources.append(file_secret_settings)
        return tuple(sources)


def _mask(secret: str) -> str:
    """Return a secret safe to print: only its last four characters show."""
    if len(secret) <= 4:
        return "*" * len(secret)
    return f"{'*' * 8}{secret[-4:]}"


def load_settings(
    *,
    config_path: Path | None = None,
    overrides: Mapping[str, Any] | None = None,
    profile: str | None = None,
) -> AzureDevOpsSettings:
    """Build the settings from every configuration source.

    Args:
        config_path: the TOML file to read. When omitted, the well known
            locations of the user's home directory are used.
        overrides: values that win over every other source, typically the
            options given on the command line.
        profile: the profile of the TOML file to apply.

    Raises:
        ConfigurationError: if a mandatory setting is missing or invalid.
    """
    path_token = _CONFIG_PATH.set(config_path)
    values = dict(overrides or {})
    requested_profile = profile or values.get("profile")
    if requested_profile:
        # The selected profile is part of the configuration itself: it shows
        # up in `azure-cli config` and it selects the section of the file.
        values["profile"] = requested_profile
    profile_token = _PROFILE.set(requested_profile)
    try:
        return AzureDevOpsSettings(**values)
    except ValidationError as exc:
        raise ConfigurationError(_describe(exc)) from exc
    finally:
        _CONFIG_PATH.reset(path_token)
        _PROFILE.reset(profile_token)


def _describe(exc: ValidationError) -> str:
    """Turn a pydantic validation error into an actionable message."""
    missing = [
        _missing_label(str(error["loc"][0])) for error in exc.errors() if error["type"] == "missing"
    ]
    if missing:
        names = ", ".join(sorted(missing))
        return (
            f"Missing configuration: {names}. Set it in the environment "
            "(AZURE_DEVOPS_*), in a .env file or in "
            f"{default_config_path()}."
        )
    details = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    )
    return f"Invalid configuration: {details}"


def _missing_label(location: str) -> str:
    """Return the name of the missing setting and the variable to set.

    Pydantic reports the alias it was looking for, which is the name of the
    environment variable for most of the settings.
    """
    for name, field in AzureDevOpsSettings.model_fields.items():
        if location == name or location in _alias_keys(field):
            return f"{name} ({location})"
    return location
