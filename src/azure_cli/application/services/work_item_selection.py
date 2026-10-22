"""Service: the rules that decide which work items the user is working on.

The rules live here, and not in a use case, because they are shared: the
"my work items" screen and the "list" command both want to know what an
active work item is and in which order they should be shown.
"""

from __future__ import annotations

from collections.abc import Iterable

from azure_cli.domain.entities.work_item import WorkItemSummary


def _recency_key(summary: WorkItemSummary) -> tuple[int, float]:
    """Return the sort key of a summary: the newest change comes first.

    The work items without a known change date are pushed to the end, but
    they keep the order they were given in.
    """
    if summary.changed_at is None:
        return (0, 0.0)
    return (1, summary.changed_at.timestamp())


class WorkItemSelection:
    """Selects and orders the work items shown to the user.

    The service is stateless: it holds no data of its own and can be shared
    by several use cases.
    """

    def active_only(self, summaries: Iterable[WorkItemSummary]) -> list[WorkItemSummary]:
        """Drop the work items that already reached a terminal state.

        Azure DevOps may return a work item that was closed between the query
        and the reading of its fields; it is not something the user works on
        any more.

        Args:
            summaries: The work items to filter.

        Returns:
            The work items that are not closed yet.
        """
        return [summary for summary in summaries if not summary.is_closed]

    def most_recent_first(self, summaries: Iterable[WorkItemSummary]) -> list[WorkItemSummary]:
        """Order the work items by their last change, the most recent first.

        Args:
            summaries: The work items to order.

        Returns:
            The work items, the most recently changed first. The work items
            without a known change date come last, in their original order.
        """
        return sorted(summaries, key=_recency_key, reverse=True)

    def select(self, summaries: Iterable[WorkItemSummary]) -> list[WorkItemSummary]:
        """Return the work items the user is working on, the most recent first.

        Args:
            summaries: The work items read from Azure DevOps.

        Returns:
            The active work items, the most recently changed first.
        """
        return self.most_recent_first(self.active_only(summaries))
