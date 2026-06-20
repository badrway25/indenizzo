"""Guard: no multi-line Django ``{# ... #}`` comments in templates.

Django's ``{# #}`` comment syntax is SINGLE-LINE only (the template lexer's
regex is not DOTALL). A ``{#`` that does not close with ``#}`` on the same
line is therefore NOT treated as a comment — Django renders the text as
literal page content, leaking developer notes onto public pages.

This was found by local visual QA (a multi-line ``{# #}`` block was visible
on the result and thank-you pages). Multi-line comments must use
``{% comment %} ... {% endcomment %}`` instead. This test fails if any
template reintroduces a multi-line ``{# #}`` comment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"

# A line that opens a {# comment but does not close it (#}) on the same line.
_OPENS_UNCLOSED = re.compile(r"\{#(?:(?!#\}).)*$")


def _offending_lines(path: Path) -> list[int]:
    out: list[int] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "{#" in line and _OPENS_UNCLOSED.search(line):
            out.append(n)
    return out


@pytest.mark.parametrize("template", sorted(TEMPLATES_DIR.rglob("*.html")), ids=str)
def test_no_multiline_django_comment(template: Path):
    offending = _offending_lines(template)
    assert not offending, (
        f"{template} has multi-line {{# #}} comment(s) at line(s) {offending}. "
        "Django renders these as literal text — use {% comment %}{% endcomment %}."
    )
