"""Composition root: wires the configuration into ready-to-use use cases.

This is the only place where the layers meet. Everything else depends on
abstractions, which is what makes the use cases testable without Azure DevOps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer

from azure_cli.application.services.work_item_field_spec import WorkItemFieldSpec
from azure_cli.application.use_cases.add_comment import AddComment
from azure_cli.application.use_cases.create_work_item import CreateWorkItem
from azure_cli.application.use_cases.get_related_links import GetRelatedLinks
from azure_cli.application.use_cases.get_work_item import GetWorkItem
from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.application.use_cases.update_work_item import UpdateWorkItem
from azure_cli.config.settings import AzureDevOpsSettings, load_settings
from azure_cli.infrastructure.azure.html_cleaner import HtmlTextCleaner
from azure_cli.infrastructure.azure.work_item_api_client import AzureWorkItemApiClient
from azure_cli.infrastructure.azure_client import AzureDevOpsClient
from azure_cli.infrastructure.git.git_api_client import AzureGitApiClient
from azure_cli.infrastructure.http.session import build_session
from azure_cli.infrastructure.repositories.azure_git_repository import AzureGitRepository
from azure_cli.infrastructure.repositories.azure_work_item_repository import (
    AzureWorkItemRepository,
)


@dataclass(frozen=True, slots=True)
class CliOptions:
    """The global options given on the command line."""

    organization: str | None = None
    project: str | None = None
    pat: str | None = None
    api_version: str | None = None
    timeout: float | None = None
    output_format: str | None = None
    profile: str | None = None

    def as_overrides(self) -> dict[str, Any]:
        """Return the options that were actually provided."""
        return {
            key: value
            for key, value in (
                ("organization", self.organization),
                ("project", self.project),
                ("pat", self.pat),
                ("api_version", self.api_version),
                ("timeout", self.timeout),
                ("output_format", self.output_format),
                ("profile", self.profile),
            )
            if value is not None
        }


@dataclass(frozen=True, slots=True)
class Container:
    """Every dependency a command may need, already wired together."""

    settings: AzureDevOpsSettings
    get_work_item: GetWorkItem
    list_work_items: ListWorkItems
    create_work_item: CreateWorkItem
    update_work_item: UpdateWorkItem
    add_comment: AddComment
    get_related_links: GetRelatedLinks
    list_my_work_items: ListMyWorkItemsUseCase
    get_workitem_details: GetWorkItemDetailsUseCase

    @classmethod
    def build(cls, settings: AzureDevOpsSettings) -> Container:
        """Build the container for the given settings."""
        session = build_session(settings.pat.get_secret_value())

        work_item_client = AzureWorkItemApiClient(
            session,
            api_base_url=settings.api_base_url,
            api_version=settings.api_version,
            timeout=settings.timeout,
        )
        git_client = AzureGitApiClient(
            session,
            api_base_url=settings.api_base_url,
            api_version=settings.api_version,
            timeout=settings.timeout,
        )

        work_item_repository = AzureWorkItemRepository(
            work_item_client,
            WorkItemFieldSpec.detail(),
            HtmlTextCleaner(),
        )
        git_repository = AzureGitRepository(
            work_item_client,
            git_client,
            web_base_url=settings.web_base_url,
        )

        gateway = AzureDevOpsClient(settings)

        return cls(
            settings=settings,
            get_work_item=GetWorkItem(work_item_repository),
            list_work_items=ListWorkItems(work_item_repository),
            create_work_item=CreateWorkItem(work_item_repository),
            update_work_item=UpdateWorkItem(work_item_repository),
            add_comment=AddComment(work_item_repository),
            get_related_links=GetRelatedLinks(git_repository, work_item_repository),
            list_my_work_items=ListMyWorkItemsUseCase(gateway),
            get_workitem_details=GetWorkItemDetailsUseCase(gateway),
        )


def resolve_container(ctx: typer.Context) -> Container:
    """Return the container the current command must work with.

    A container injected through ``ctx.obj`` (used by the tests) wins over the
    one built from the configuration.
    """
    options = ctx.obj

    if isinstance(options, Container):
        return options

    if not isinstance(options, CliOptions):
        options = CliOptions()

    settings = load_settings(overrides=options.as_overrides())
    return Container.build(settings)
