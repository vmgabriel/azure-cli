"""HTML cleaning utilities for Azure DevOps rich-text fields."""

from __future__ import annotations

import re

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - only exercised when bs4 is missing
    BeautifulSoup = None  # type: ignore[assignment,misc]

#: Tags that start a new line.
BLOCK_TAGS = (
    "address",
    "article",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tr",
    "ul",
)


def clean_html(html_text: str | None) -> str:
    """Turn the HTML rich-text fields of Azure DevOps into plain text.

    Uses BeautifulSoup if available, falling back to a conservative regex
    strip for environments where it is missing.

    Args:
        html_text: The HTML fragment returned by Azure DevOps, or ``None``.

    Returns:
        The readable plain text. Empty strings become ``""``.
    """
    if not html_text:
        return ""

    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html_text, "html.parser")

            for tag in soup.find_all(BLOCK_TAGS):
                tag.insert_before("\n")
                tag.insert_after("\n")

            lines = (line.strip() for line in soup.get_text().splitlines())
            return "\n".join(line for line in lines if line)
        except Exception:
            pass

    # Fallback: strip tags and collapse whitespace into newlines where
    # sensible (before/after block-like tags).
    text = html_text
    for block_tag in BLOCK_TAGS:
        text = re.sub(rf"<\s*{block_tag}[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(rf"<\s*/\s*{block_tag}\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    stripped_lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in stripped_lines if line)


class HtmlTextCleaner:
    """Extracts readable text from the HTML fields of a work item.

    Kept for backwards compatibility with the existing codebase.
    """

    def clean(self, html: str | None) -> str:
        """Return the readable text of an HTML fragment."""
        return clean_html(html)


__all__ = ["HtmlTextCleaner", "clean_html"]
