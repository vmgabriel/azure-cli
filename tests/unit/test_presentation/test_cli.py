"""Tests of the command line interface."""

from __future__ import annotations

import dataclasses
import json
from importlib.metadata import PackageNotFoundError

import pytest
from typer.testing import CliRunner

from azure_cli.domain.entities.work_item import WorkItemSummary
from azure_cli.domain.exceptions import AuthenticationError
from azure_cli.domain.value_objects.work_item_id import WorkItemId
from azure_cli.domain.value_objects.work_item_state import WorkItemState
from azure_cli.domain.value_objects.work_item_type import WorkItemType
from azure_cli.presentation.cli.container import Container
from azure_cli.presentation.cli.main import app
from azure_cli.presentation.main import get_app_version
from tests.conftest import FakeAzureDevOpsGateway, FakeGitRepository, FakeWorkItemRepository


def test_the_help_does_not_need_any_configuration(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "work items" in result.output.lower()


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_the_version_flag_prints_the_version(
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
) -> None:
    monkeypatch.setattr("azure_cli.presentation.main.get_app_version", lambda: "9.9.9")

    result = cli_runner.invoke(app, [flag])

    assert result.exit_code == 0
    assert result.output.strip() == "azure-cli version 9.9.9"


def test_the_version_falls_back_when_the_package_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_package(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr("azure_cli.presentation.main.version", missing_package)

    assert get_app_version() == "0.1.0-dev"


def test_the_console_script_points_at_the_application() -> None:
    from azure_cli.presentation.main import app as entry_point

    assert entry_point is app


def test_the_entry_point_runs_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr("azure_cli.presentation.main.app", lambda: calls.append(True))

    from azure_cli.presentation.main import main

    main()

    assert calls == [True]


def test_every_command_is_registered(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["--help"])

    for command in (
        "get",
        "list",
        "create",
        "update",
        "comment",
        "links",
        "config",
        "mine",
        "workitems",
        "detail",
    ):
        assert command in result.output


def test_get_renders_the_work_item(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["get", "42"], obj=container)

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "Estado: Active" in result.output


def test_get_can_show_the_related_links(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["get", "42", "--links"], obj=container)

    assert result.exit_code == 0
    assert "pull_request" in result.output
    assert "feature/login" in result.output


def test_get_reports_a_missing_work_item(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["get", "999"], obj=container)

    assert result.exit_code == 1
    assert "was not found" in result.output


def test_get_rejects_a_non_numeric_id(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["get", "abc"])

    assert result.exit_code == 2


def test_list_renders_a_table(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["list"], obj=container)

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "ESTADO" in result.output


def test_list_uses_the_filters(
    cli_runner: CliRunner,
    container: Container,
    repository: FakeWorkItemRepository,
) -> None:
    result = cli_runner.invoke(app, ["list", "--state", "Active"], obj=container)

    assert result.exit_code == 0
    assert repository.last_query is not None
    assert "[System.State] = 'Active'" in repository.last_query


def test_list_can_render_json(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["list", "--format", "json"], obj=container)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert payload[0]["id"] == 42


def test_the_list_help_lists_the_format_option(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["list", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.output
    assert "json" in result.output


def test_create_creates_the_work_item(
    cli_runner: CliRunner,
    container: Container,
    repository: FakeWorkItemRepository,
) -> None:
    result = cli_runner.invoke(
        app,
        ["create", "--type", "Bug", "--title", "A new bug"],
        obj=container,
    )

    assert result.exit_code == 0
    assert repository.last_create is not None
    assert repository.last_create[0] == "Bug"
    assert repository.last_create[1] == "A new bug"


def test_update_changes_the_state(
    cli_runner: CliRunner,
    container: Container,
    repository: FakeWorkItemRepository,
) -> None:
    result = cli_runner.invoke(app, ["update", "42", "--state", "Closed"], obj=container)

    assert result.exit_code == 0
    assert repository.last_changes == {"System.State": "Closed"}


def test_update_without_any_field_fails(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["update", "42"], obj=container)

    assert result.exit_code == 1
    assert "Nothing to update" in result.output


def test_comment_adds_the_comment(
    cli_runner: CliRunner,
    container: Container,
    repository: FakeWorkItemRepository,
) -> None:
    result = cli_runner.invoke(app, ["comment", "42", "Looks good"], obj=container)

    assert result.exit_code == 0
    assert repository.comments == [(42, "Looks good")]


def test_links_lists_the_related_artifacts(
    cli_runner: CliRunner,
    container: Container,
    git_repository: FakeGitRepository,
) -> None:
    result = cli_runner.invoke(app, ["links", "42"], obj=container)

    assert result.exit_code == 0
    assert git_repository.requested_ids == [42]
    assert "feature/login" in result.output


def test_config_shows_the_masked_token(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["config"], obj=container)

    assert result.exit_code == 0
    assert "fake-token" not in result.output
    assert "acme" in result.output


def test_the_json_output_is_machine_readable(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    json_container = dataclasses.replace(
        container,
        settings=container.settings.model_copy(update={"output_format": "json"}),
    )

    result = cli_runner.invoke(app, ["get", "42"], obj=json_container)

    assert result.exit_code == 0
    assert '"title": "Login fails on Safari"' in result.output


def test_a_missing_configuration_is_reported(
    cli_runner: CliRunner,
) -> None:
    result = cli_runner.invoke(app, ["get", "42"])

    assert result.exit_code == 1
    assert "Missing configuration" in result.output


# -- mine ---------------------------------------------------------------------
def test_mine_shows_the_work_items_of_the_user(
    cli_runner: CliRunner,
    container: Container,
    gateway: FakeAzureDevOpsGateway,
) -> None:
    result = cli_runner.invoke(app, ["mine"], obj=container)

    assert result.exit_code == 0
    assert gateway.list_calls == 1
    assert "Login fails on Safari" in result.output
    assert "ID" in result.output
    assert "Points" in result.output
    assert "Total: 3 points in 1 work item" in result.output


def test_mine_lists_the_urls_of_the_work_items(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["mine"], obj=container)

    assert result.exit_code == 0
    assert "URLs:" in result.output
    assert "/_workitems/edit/42" in result.output


def test_mine_can_be_called_by_its_alias(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["workitems"], obj=container)

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output


def test_mine_limits_the_number_of_work_items(
    cli_runner: CliRunner,
    container: Container,
    gateway: FakeAzureDevOpsGateway,
) -> None:
    gateway.summaries.append(
        WorkItemSummary(
            id=WorkItemId(43),
            title="A brand new bug",
            state=WorkItemState("New"),
            type=WorkItemType("Bug"),
            story_points=2.0,
        )
    )

    result = cli_runner.invoke(app, ["mine", "--limit", "1"], obj=container)

    assert result.exit_code == 0
    assert "Login fails on Safari" in result.output
    assert "A brand new bug" not in result.output
    assert "in 1 work item" in result.output


def test_mine_rejects_a_non_positive_limit(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["mine", "--limit", "0"], obj=container)

    assert result.exit_code == 2
    assert "--limit" in result.output


def test_mine_exposes_the_work_items_as_json(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["mine", "--format", "json"], obj=container)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["count"] == 1
    assert payload["total_story_points"] == 3.0
    assert payload["work_items"][0]["title"] == "Login fails on Safari"


def test_mine_explains_the_emptiness(
    cli_runner: CliRunner,
    container: Container,
    gateway: FakeAzureDevOpsGateway,
) -> None:
    gateway.summaries.clear()

    result = cli_runner.invoke(app, ["mine"], obj=container)

    assert result.exit_code == 0
    assert "No tienes work items activos asignados." in result.output


def test_mine_reports_the_errors_of_the_use_case(
    cli_runner: CliRunner,
    container: Container,
    gateway: FakeAzureDevOpsGateway,
) -> None:
    gateway.error = AuthenticationError("token rejected")

    result = cli_runner.invoke(app, ["mine"], obj=container)

    assert result.exit_code == 1
    assert "token rejected" in result.output
    assert "AZURE_DEVOPS_PAT" in result.output


# -- detail -------------------------------------------------------------------
def test_detail_shows_the_work_item(
    cli_runner: CliRunner,
    container: Container,
    gateway: FakeAzureDevOpsGateway,
) -> None:
    result = cli_runner.invoke(app, ["detail", "42"], obj=container)

    assert result.exit_code == 0
    assert gateway.requested_ids == [42, 42]
    assert "ID: 42" in result.output
    assert "Active" in result.output
    assert "Login fails on Safari" in result.output
    assert "📍 Área: Acme/Frontend" in result.output
    assert "🔄 Iteración: Acme/Sprint 12" in result.output
    assert "⭐ Puntos: 3" in result.output
    assert "frontend, p1" in result.output
    assert "The login form does not submit." in result.output
    assert "The user can log in." in result.output
    assert "pull_request" in result.output
    assert "feature/login" in result.output


def test_detail_exposes_the_work_item_as_json(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["detail", "42", "--format", "json"], obj=container)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["id"] == 42
    assert payload["acceptance_criteria"] == "The user can log in."
    assert payload["related_links"][0]["kind"] == "pull_request"


def test_detail_reports_a_missing_work_item(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["detail", "999"], obj=container)

    assert result.exit_code == 1
    assert "was not found" in result.output


def test_detail_rejects_a_non_numeric_id(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["detail", "abc"])

    assert result.exit_code == 2


def test_detail_rejects_a_non_positive_id(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["detail", "0"], obj=container)

    assert result.exit_code == 1
    assert "positive integer" in result.output


def test_detail_follows_the_global_json_output(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    json_container = dataclasses.replace(
        container,
        settings=container.settings.model_copy(update={"output_format": "json"}),
    )

    result = cli_runner.invoke(app, ["detail", "42"], obj=json_container)

    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == 42


def test_the_command_format_wins_over_the_global_output(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    json_container = dataclasses.replace(
        container,
        settings=container.settings.model_copy(update={"output_format": "json"}),
    )

    result = cli_runner.invoke(app, ["detail", "42", "--format", "table"], obj=json_container)

    assert result.exit_code == 0
    assert "ID: 42" in result.output


def test_the_table_shows_the_identifier_of_each_work_item(
    cli_runner: CliRunner,
    container: Container,
) -> None:
    result = cli_runner.invoke(app, ["mine"], obj=container)

    assert result.exit_code == 0
    assert "42" in result.output


def test_the_detail_help_lists_the_format_option(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["detail", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.output
    assert "json" in result.output


def test_the_mine_help_lists_the_format_option(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["mine", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--limit" in result.output


@pytest.mark.parametrize("command", [["list"], ["mine"], ["detail", "42"]])
def test_an_unknown_format_is_rejected(
    cli_runner: CliRunner,
    container: Container,
    command: list[str],
) -> None:
    result = cli_runner.invoke(app, [*command, "--format", "yaml"], obj=container)

    assert result.exit_code == 2
    assert "yaml" in result.output
