"""Formatting of the domain objects: tables, JSON and colours.

The functions of this module are pure: they take the data and return the
text to print. The commands decide what to do with it.

The colours are only used when the output goes to a terminal: a pipe, a
file or a ``NO_COLOR`` environment get the plain text.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
from collections.abc import Sequence
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail, WorkItemSummary

#: Width used when the width of the terminal cannot be guessed.
DEFAULT_WIDTH = 80

#: The colour of a state, depending on how far the work item has gone.
STATE_STYLES: dict[str, str] = {
    "new": "cyan",
    "active": "green",
    "committed": "green",
    "implementing": "green",
    "in progress": "green",
    "ready for testing": "yellow",
    "ready for review": "yellow",
    "blocked": "red",
    "closed": "grey62",
    "done": "grey62",
    "removed": "grey62",
    "resolved": "grey62",
    "approved": "grey62",
}

#: The colour of a state that is not known.
DEFAULT_STATE_STYLE = "white"

#: The symbol shown in front of a state.
STATE_MARKER = "●"

#: The ANSI codes of the styles used by the terminal.
ANSI_STYLES: dict[str, str] = {
    "white": "\033[37m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "grey62": "\033[90m",
}

#: The code ending a coloured text.
ANSI_RESET = "\033[0m"

#: The columns of the table of the work items.
WORK_ITEM_COLUMNS = ("ID", "Points", "State", "Title", "URL")


def colors_enabled() -> bool:
    """Whether the output may carry colours.

    The colours are dropped when the output is not a terminal (a pipe, a
    file) and when the ``NO_COLOR`` environment variable is set.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def state_style(state: str) -> str:
    """Return the colour of a state."""
    return STATE_STYLES.get(state.strip().lower(), DEFAULT_STATE_STYLE)


def colorize(text: str, style: str) -> str:
    """Return the text in the given colour, when the terminal allows it.

    Args:
        text: The text to colour.
        style: The name of the style (see :data:`ANSI_STYLES`).

    Returns:
        The coloured text, or the plain one when the colours are disabled.
    """
    if not colors_enabled():
        return text
    code = ANSI_STYLES.get(style)
    if code is None:
        return text
    return f"{code}{text}{ANSI_RESET}"


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render the rows as a table.

    The columns are as wide as they need to be and the long values are
    folded instead of being cut. The cells are plain text: a title such as
    ``[WIP] Login`` is shown as it is, never interpreted as markup.

    Args:
        headers: The title of the columns.
        rows: The content of the table, one sequence per line.

    Returns:
        The table, ready to be printed.
    """
    table = _build_table(headers)
    for row in rows:
        table.add_row(*[Text(str(cell)) for cell in row])

    return _render(table)


def format_json(payload: Any) -> str:
    """Render the payload as JSON.

    Args:
        payload: The object to serialise.

    Returns:
        The JSON text, indented and ready to be parsed.
    """
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def work_items_table(summaries: Sequence[WorkItemSummary]) -> str:
    """Render the work items as a table.

    The state of every work item carries a coloured marker, so the state of
    the sprint can be read at a glance.

    Args:
        summaries: The work items to render.

    Returns:
        The table, ready to be printed.
    """
    table = _build_table(WORK_ITEM_COLUMNS)
    for summary in summaries:
        state = summary.state.value
        table.add_row(
            Text(str(summary.id.value)),
            Text(format_story_points(summary.story_points)),
            Text(f"{STATE_MARKER} {state}", style=state_style(state)),
            Text(summary.title),
            Text(summary.url),
        )

    return _render(table)


def work_items_summary(summaries: Sequence[WorkItemSummary]) -> str:
    """Render the total of the story points of the work items.

    Args:
        summaries: The work items to add up.

    Returns:
        The summary line, ready to be printed.
    """
    total = total_story_points(summaries)
    return (
        f"Total: {format_story_points(total)} points "
        f"in {len(summaries)} work item{'s' if len(summaries) != 1 else ''}"
    )


def total_story_points(summaries: Sequence[WorkItemSummary]) -> float:
    """Return the sum of the story points of the work items.

    The work items without story points do not count.
    """
    return sum(summary.story_points or 0.0 for summary in summaries)


def format_story_points(story_points: float | None) -> str:
    """Render the story points without a useless trailing zero."""
    if story_points is None:
        return "N/A"
    return f"{story_points:g}"


def wants_json(output_format: str | None, configured: str) -> bool:
    """Whether the JSON output is wanted.

    The ``--format`` option of a command wins over the ``--output`` option
    of the application.

    Args:
        output_format: The format asked for on the command line, if any.
        configured: The format resolved by the configuration.

    Returns:
        Whether the output must be JSON.
    """
    if output_format is not None:
        return output_format == "json"
    return configured == "json"


def summary_to_dict(summary: WorkItemSummary) -> dict[str, Any]:
    """Convert a work item summary into a JSON friendly dictionary."""
    return {
        "id": summary.id.value,
        "title": summary.title,
        "state": summary.state.value,
        "type": summary.type.value,
        "assigned_to": summary.assigned_to,
        "story_points": summary.story_points,
        "url": summary.url,
        "changed_at": summary.changed_at.isoformat() if summary.changed_at else None,
    }


def detail_to_dict(work_item: WorkItemDetail) -> dict[str, Any]:
    """Convert a work item into a JSON friendly dictionary."""
    return {
        "id": work_item.id.value,
        "title": work_item.title,
        "state": work_item.state.value,
        "type": work_item.type.value,
        "description": work_item.description,
        "acceptance_criteria": work_item.acceptance_criteria,
        "tags": [tag.value for tag in work_item.tags],
        "story_points": work_item.story_points,
        "area_path": work_item.area_path,
        "iteration_path": work_item.iteration_path,
        "assigned_to": work_item.assigned_to,
        "created_by": work_item.created_by,
        "url": work_item.url,
        "changed_at": work_item.changed_at.isoformat() if work_item.changed_at else None,
        "related_links": [link_to_dict(link) for link in work_item.related_links],
    }


def link_to_dict(link: RelatedLink) -> dict[str, Any]:
    """Convert a related link into a JSON friendly dictionary."""
    return {
        "id": link.id,
        "kind": link.kind.value,
        "url": link.url,
        "title": link.title,
    }


def _build_table(headers: Sequence[str]) -> Table:
    """Create an empty table with the given headers."""
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold", expand=False)
    for header in headers:
        table.add_column(header, overflow="fold")
    return table


def _render(table: Table) -> str:
    """Render a rich table into a string."""
    colors = colors_enabled()
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns,
        force_terminal=colors,
        no_color=not colors,
    )
    console.print(table)
    return buffer.getvalue().rstrip()
