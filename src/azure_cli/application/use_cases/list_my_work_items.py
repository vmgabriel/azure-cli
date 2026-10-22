"""Use case: list the work items the current user is working on."""

from __future__ import annotations

import logging
from typing import Protocol

from azure_cli.application.services.work_item_selection import WorkItemSelection
from azure_cli.domain.entities.work_item import WorkItemSummary
from azure_cli.domain.exceptions import AzureWiError, ConfigurationError
from azure_cli.domain.interfaces.azure_devops_gateway import AzureDevOpsGateway

logger = logging.getLogger(__name__)


class UserSettings(Protocol):
    """The configuration the use case needs from the user.

    ``azure_cli.config.settings.AzureDevOpsSettings`` satisfies it: the
    use case only asks for the e-mail address of the current user, and does
    not need to know how the configuration was loaded.
    """

    @property
    def default_email(self) -> str | None:
        """The e-mail address of the user, when it is configured."""


class ListMyWorkItemsUseCase:
    """Returns the work items assigned to the current user.

    The use case orchestrates the workflow: it reads the identity of the user
    from the configuration, asks Azure DevOps for the work items assigned to
    that user through the gateway port, and applies the selection rules of
    the application layer.

    It knows nothing about HTTP, of the terminal, nor of the way the
    configuration was loaded: everything it needs is injected.
    """

    def __init__(
        self,
        gateway: AzureDevOpsGateway,
        settings: UserSettings,
        selection: WorkItemSelection | None = None,
    ) -> None:
        """Create the use case.

        Args:
            gateway: The port used to read the work items of Azure DevOps.
            settings: The configuration holding the e-mail address of the user.
            selection: The rules deciding which work items are shown. A
                default one is created when it is not given.
        """
        self._gateway = gateway
        self._settings = settings
        self._selection = selection or WorkItemSelection()

    def execute(self) -> list[WorkItemSummary]:
        """Return the work items the current user is working on.

        The work items are the active ones, the most recently changed first.

        Returns:
            The summaries of the work items, in that order.

        Raises:
            ConfigurationError: if no e-mail address is configured.
            AuthenticationError: if Azure DevOps rejected the credentials.
            AzureApiError: if Azure DevOps returned an unexpected response.
            TransportError: if Azure DevOps could not be reached.
        """
        email = self._current_email()

        logger.info("Listing the work items assigned to %s", email)
        try:
            summaries = self._gateway.list_work_items(email)
        except AzureWiError as exc:
            logger.error("Could not list the work items of %s: %s", email, exc)
            raise

        selected = self._selection.select(summaries)
        logger.info("%s active work items found for %s", len(selected), email)
        return selected

    def _current_email(self) -> str:
        """Return the e-mail address of the current user.

        Raises:
            ConfigurationError: if no e-mail address is configured.
        """
        email = (self._settings.default_email or "").strip()
        if not email:
            raise ConfigurationError(
                "No e-mail address is configured: set 'default_email' in the "
                "configuration file or AZURE_DEVOPS_DEFAULT_EMAIL in the "
                "environment to know which work items are yours."
            )
        return email
