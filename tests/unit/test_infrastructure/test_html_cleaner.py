"""Unit tests of the infrastructure helpers."""

from __future__ import annotations

from azure_cli.infrastructure.azure.html_cleaner import HtmlTextCleaner


def test_an_empty_html_gives_an_empty_text() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean(None) == ""
    assert cleaner.clean("") == ""


def test_the_tags_are_removed() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>Hello</div>") == "Hello"


def test_the_inline_tags_keep_the_sentence_together() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>The form does <b>not</b> submit.</div>") == (
        "The form does not submit."
    )


def test_the_block_elements_become_lines() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<p>First</p><p>Second</p>") == "First\nSecond"


def test_the_list_items_become_lines() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<ul><li>One</li><li>Two</li></ul>") == "One\nTwo"


def test_the_entities_are_decoded() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>a &amp; b</div>") == "a & b"


def test_the_script_tags_are_removed() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>safe<script>alert(1)</script></div>") == "safe"


def test_the_escaped_markup_stays_text() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>&lt;script&gt;</div>") == "<script>"
