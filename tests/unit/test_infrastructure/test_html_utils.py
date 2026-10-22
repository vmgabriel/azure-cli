"""Unit tests of the `clean_html` helper and of the HTML text cleaner."""

from __future__ import annotations

import pytest

from azure_cli.infrastructure import html_utils
from azure_cli.infrastructure.html_utils import HtmlTextCleaner, clean_html


def test_an_empty_html_gives_an_empty_text() -> None:
    assert clean_html(None) == ""
    assert clean_html("") == ""


def test_the_tags_are_removed() -> None:
    assert clean_html("<div>Hello</div>") == "Hello"


def test_the_inline_tags_keep_the_sentence_together() -> None:
    assert clean_html("<div>The form does <b>not</b> submit.</div>") == (
        "The form does not submit."
    )


def test_the_block_elements_become_lines() -> None:
    assert clean_html("<p>First</p><p>Second</p>") == "First\nSecond"


def test_the_list_items_become_lines() -> None:
    assert clean_html("<ul><li>One</li><li>Two</li></ul>") == "One\nTwo"


def test_the_entities_are_decoded() -> None:
    assert clean_html("<div>a &amp; b</div>") == "a & b"


def test_the_script_tags_are_removed() -> None:
    assert clean_html("<div>safe<script>alert(1)</script></div>") == "safe"


def test_the_escaped_markup_stays_text() -> None:
    assert clean_html("<div>&lt;script&gt;</div>") == "<script>"


def test_the_class_exposes_the_same_behaviour() -> None:
    cleaner = HtmlTextCleaner()

    assert cleaner.clean("<div>Hello</div>") == clean_html("<div>Hello</div>")
    assert cleaner.clean(None) == ""


def test_the_regex_fallback_is_used_without_beautifulsoup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(html_utils, "BeautifulSoup", None)

    assert clean_html("<div>Hello</div><p>World</p>") == "Hello\nWorld"
    assert clean_html("<ul><li>One</li><li>Two</li></ul>") == "One\nTwo"
    assert clean_html("<div>a &amp; b</div>") == "a &amp; b"
    assert clean_html("") == ""


def test_the_attributes_are_not_part_of_the_text() -> None:
    html = '<div class="card" data-id="1">Hello <span style="color:red">world</span></div>'

    assert clean_html(html) == "Hello world"


def test_the_line_breaks_are_preserved() -> None:
    assert clean_html("<div>Hello<br>World</div>") == "Hello\nWorld"


def test_a_nested_list_keeps_its_order() -> None:
    html = "<ul><li>One<ul><li>Sub</li></ul></li><li>Two</li></ul>"

    assert clean_html(html) == "One\nSub\nTwo"


def test_the_empty_paragraphs_are_dropped() -> None:
    assert clean_html("<p>One</p><p>   </p><p>Two</p>") == "One\nTwo"


def test_a_malformed_fragment_does_not_fail() -> None:
    assert clean_html("<div><p>First<div>Second") == "First\nSecond"


def test_the_unicode_text_is_preserved() -> None:
    assert clean_html("<p>Corrección 🚀 &ntilde;andú</p>") == "Corrección 🚀 ñandú"


def test_the_regex_fallback_handles_attributes_and_line_breaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(html_utils, "BeautifulSoup", None)

    assert clean_html('<div class="card">Hello<br/>World</div>') == "Hello\nWorld"


def test_the_regex_fallback_keeps_unicode_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(html_utils, "BeautifulSoup", None)

    assert clean_html("<p>Corrección 🚀</p>") == "Corrección 🚀"
