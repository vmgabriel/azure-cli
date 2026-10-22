# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-01

Initial release of `azure-cli`.

### Added

- Clean Architecture skeleton (domain, application, infrastructure,
  presentation and configuration layers) with ports and adapters, dependency
  injection and dependencies pointing inwards only.
- Hatch project configuration, isolated development environments and build
  targets for the sdist and wheel.
- Typer-based command-line interface with the `list`, `mine`, `detail`, `get`,
  `create`, `update`, `comment`, `links` and `config` commands, including
  human-readable tables and JSON output.
- Azure DevOps Work Items integration: WIQL queries, work item creation and
  updates, comments, tags, story points, and related pull requests and
  branches, with HTML rich text rendered as plain text.
- Layered configuration (CLI flags, environment variables, `.env` and
  `config.toml`) with support for profiles.
- Test suite with offline unit tests and stub-server integration tests, plus
  opt-in live tests against Azure DevOps; ruff, mypy and pre-commit workflows.

### Changed

- Placeholder: describe notable changes to existing functionality here.

### Fixed

- Placeholder: describe bug fixes here.

[Unreleased]: https://github.com/vmgabriel/azure-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vmgabriel/azure-cli/releases/tag/v0.1.0
