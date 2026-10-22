"""Repositories: the adapters implementing the domain ports."""

from azure_cli.infrastructure.repositories.azure_git_repository import AzureGitRepository
from azure_cli.infrastructure.repositories.azure_work_item_repository import (
    AzureWorkItemRepository,
)

__all__ = ["AzureGitRepository", "AzureWorkItemRepository"]
