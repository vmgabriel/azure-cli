"""Ports: the interfaces the domain needs from the outside world."""

from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway
from azure_cli.domain.interfaces.git_repository import GitRepository
from azure_cli.domain.interfaces.work_item_repository import WorkItemRepository

__all__ = ["AzureDevOpsGateway", "GitRepository", "WorkItemRepository"]
