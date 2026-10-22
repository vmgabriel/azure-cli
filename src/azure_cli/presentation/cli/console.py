"""Rendering of the domain objects for the terminal."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from azure_cli.domain.entities.related_link import RelatedLink
from azure_cli.domain.entities.work_item import WorkItemDetail
from azure_cli.domain.entities.work_item_comment import WorkItemComment
from azure_cli.domain.value_objects.link_kind import LinkKind
from azure_cli.presentation.cli.formatters import (
    STATE_MARKER,
    colorize,
    detail_to_dict,
    format_story_points,
    link_to_dict,
    state_style,
)

#: Width of the separator lines of the text output.
SEPARATOR_WIDTH = 60

_LINK_ICONS = {
    LinkKind.BRANCH: "🌿",
    LinkKind.PULL_REQUEST: "🔀",
    LinkKind.COMMIT: "📦",
    LinkKind.WORK_ITEM: "🔗",
    LinkKind.OTHER: "•",
}


class WorkItemRenderer:
    """Renders work items either as human text or as JSON."""

    def __init__(self, output_format: str = "text", *, colored: bool = False) -> None:
        """Create the renderer.

        Args:
            output_format: ``text`` for the human output, ``json`` for the
                machine readable one.
            colored: Whether the state of the work items may be coloured.
        """
        self.output_format = output_format
        self.colored = colored

    @property
    def is_json(self) -> bool:
        """Whether the JSON output is requested."""
        return self.output_format == "json"

    # -- work items ---------------------------------------------------------
    def render_work_item(self, work_item: WorkItemDetail) -> str:
        """Render a single work item."""
        if self.is_json:
            return json.dumps(work_item_to_dict(work_item), indent=2, ensure_ascii=False)

        separator = "=" * SEPARATOR_WIDTH
        state = self._state(work_item.state.value)
        lines = [
            separator,
            f"📄 ID: {work_item.id.value} | Estado: {state}",
            f"🔗 URL: {work_item.url}",
            f"🏷️  Título: {work_item.title}",
            f"🧩 Tipo: {work_item.type.value}",
            f"📍 Área: {work_item.area_path or 'N/A'}",
            f"🔄 Iteración: {work_item.iteration_path or 'N/A'}",
            f"👤 Asignado a: {work_item.assigned_to or 'N/A'}",
            f"⭐ Puntos: {format_story_points(work_item.story_points)}",
            f"🏷️  Tags: {', '.join(tag.value for tag in work_item.tags) or 'Ninguno'}",
            "-" * SEPARATOR_WIDTH,
            "📝 Descripción:",
            work_item.description or "Sin descripción",
            "-" * SEPARATOR_WIDTH,
            "✅ Criterios de Aceptación:",
            work_item.acceptance_criteria or "No especificados",
            "-" * SEPARATOR_WIDTH,
            "🔗 Relaciones (Ramas/PRs):",
        ]
        lines.extend(self._render_link_lines(work_item.related_links))
        lines.append(separator)
        return "\n".join(lines)

    def render_work_items(self, work_items: Sequence[WorkItemDetail]) -> str:
        """Render a list of work items."""
        if self.is_json:
            return json.dumps(
                [work_item_to_dict(work_item) for work_item in work_items],
                indent=2,
                ensure_ascii=False,
            )

        if not work_items:
            return "No se encontraron work items."

        header = f"{'ID':>6}  {'ESTADO':<12}  {'TIPO':<12}  TÍTULO"
        rows = [
            f"{work_item.id.value:>6}  {work_item.state.value:<12}  "
            f"{work_item.type.value:<12}  {work_item.title}"
            for work_item in work_items
        ]
        return "\n".join([header, "-" * len(header), *rows])

    # -- related links ------------------------------------------------------
    def render_links(self, links: Sequence[RelatedLink]) -> str:
        """Render the links related to a work item."""
        if self.is_json:
            return json.dumps(
                [link_to_dict(link) for link in links],
                indent=2,
                ensure_ascii=False,
            )
        if not links:
            return "No se encontraron ramas o PRs vinculados."
        return "\n".join(self._render_link_lines(links))

    def _render_link_lines(self, links: Sequence[RelatedLink]) -> list[str]:
        """Render one line per related link."""
        if not links:
            return ["   No se encontraron ramas o PRs vinculados automáticamente."]
        return [
            f"   {_LINK_ICONS.get(link.kind, '•')} [{link.kind.value}] ID: {link.id}"
            + (f" — {link.url}" if link.url else "")
            for link in links
        ]

    # -- comments -----------------------------------------------------------
    def render_comment(self, comment: WorkItemComment) -> str:
        """Render a comment that was just added."""
        if self.is_json:
            return json.dumps(comment_to_dict(comment), indent=2, ensure_ascii=False)
        author = comment.author or "unknown"
        return f"💬 Comentario #{comment.id} añadido por {author}."

    # -- misc ---------------------------------------------------------------
    def render_message(self, message: str) -> str:
        """Render a plain message."""
        return message

    def _state(self, state: str) -> str:
        """Render the state of a work item, coloured when it is allowed."""
        if not self.colored:
            return state
        return colorize(f"{STATE_MARKER} {state}", state_style(state))


def work_item_to_dict(work_item: WorkItemDetail) -> dict[str, Any]:
    """Convert a work item into a JSON friendly dictionary."""
    return detail_to_dict(work_item)


def comment_to_dict(comment: WorkItemComment) -> dict[str, Any]:
    """Convert a comment into a JSON friendly dictionary."""
    return {
        "id": comment.id,
        "work_item_id": comment.work_item_id.value,
        "text": comment.text,
        "author": comment.author,
        "created_at": comment.created_at,
        "url": comment.url,
    }
