"""Turn the HTML rich-text fields of Azure DevOps into plain text."""

from __future__ import annotations

from bs4 import BeautifulSoup

#: Tags that start a new line. Everything else (bold, italic, code, links...)
#: stays inline, so sentences are not cut in the middle.
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


class HtmlTextCleaner:
    """Extracts readable text from the HTML fields of a work item.

    Azure DevOps stores descriptions and acceptance criteria as HTML. The
    terminal cannot render it, so the markup is stripped down to its text:
    block elements become lines, inline elements keep the sentence together.
    """

    def clean(self, html: str | None) -> str:
        """Return the readable text of an HTML fragment."""
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(BLOCK_TAGS):
            tag.insert_before("\n")
            tag.insert_after("\n")

        lines = (line.strip() for line in soup.get_text().splitlines())
        return "\n".join(line for line in lines if line)
