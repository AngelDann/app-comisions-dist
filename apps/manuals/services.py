"""Render seguro de cuerpos Markdown o HTML."""

from __future__ import annotations

import re

import bleach
import markdown

ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "blockquote",
        "code",
        "pre",
        "a",
        "hr",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "div",
        "span",
        "img",
    }
)

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "*": ["class"],
}

ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})

_MD_EXTENSIONS = [
    "markdown.extensions.fenced_code",
    "markdown.extensions.tables",
    "markdown.extensions.nl2br",
]

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>[\s\S]*?</\1>",
    re.IGNORECASE,
)


def _strip_script_and_style(html: str) -> str:
    """Quita bloques script/style antes de bleach (evita texto residual al strip)."""
    return _SCRIPT_STYLE_RE.sub("", html)


def render_manual_body(body: str, *, content_format: str) -> str:
    """
    Convierte Markdown a HTML o acepta HTML almacenado; en ambos casos
    devuelve fragmento sanitizado con bleach.
    """
    text = body or ""
    if content_format == "html":
        raw_html = _strip_script_and_style(text)
    else:
        raw_html = markdown.markdown(text, extensions=_MD_EXTENSIONS)
    return bleach.clean(
        raw_html,
        tags=list(ALLOWED_TAGS),
        attributes=ALLOWED_ATTRIBUTES,
        protocols=list(ALLOWED_PROTOCOLS),
        strip=True,
    )
