"""Use cases: one class per action the user can perform."""

from azure_cli.application.use_cases.add_comment import AddComment
from azure_cli.application.use_cases.create_work_item import CreateWorkItem
from azure_cli.application.use_cases.get_related_links import GetRelatedLinks
from azure_cli.application.use_cases.get_work_item import GetWorkItem
from azure_cli.application.use_cases.get_workitem_details import GetWorkItemDetailsUseCase
from azure_cli.application.use_cases.list_my_work_items import ListMyWorkItemsUseCase
from azure_cli.application.use_cases.list_work_items import ListWorkItems
from azure_cli.application.use_cases.update_work_item import UpdateWorkItem

__all__ = [
    "AddComment",
    "CreateWorkItem",
    "GetRelatedLinks",
    "GetWorkItem",
    "GetWorkItemDetailsUseCase",
    "ListMyWorkItemsUseCase",
    "ListWorkItems",
    "UpdateWorkItem",
]
