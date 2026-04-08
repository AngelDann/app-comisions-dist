import pytest
from django.urls import reverse

from apps.manuals.models import ManualContentFormat, ManualPage
from apps.manuals.services import render_manual_body


@pytest.mark.django_db
def test_manual_index_redirects_to_first_published_slug(client):
    ManualPage.objects.create(
        title="Primera",
        slug="primera",
        sort_order=0,
        body="# Hola",
        content_format=ManualContentFormat.MARKDOWN,
        is_published=True,
    )
    ManualPage.objects.create(
        title="Segunda",
        slug="segunda",
        sort_order=1,
        body="x",
        is_published=True,
    )
    r = client.get(reverse("manuals:index"), follow=False)
    assert r.status_code == 302
    assert r.url == reverse("manuals:page", kwargs={"slug": "primera"})


@pytest.mark.django_db
def test_manual_index_empty_shows_message(client):
    r = client.get(reverse("manuals:index"))
    assert r.status_code == 200
    assert "publicadas" in r.content.decode("utf-8")


@pytest.mark.django_db
def test_published_page_200_anonymous(client):
    ManualPage.objects.create(
        title="Guia",
        slug="guia",
        body="## T\n\nTexto.",
        content_format=ManualContentFormat.MARKDOWN,
        is_published=True,
    )
    r = client.get(reverse("manuals:page", kwargs={"slug": "guia"}))
    assert r.status_code == 200
    assert "Guia" in r.content.decode("utf-8")
    assert b"<h2>" in r.content


@pytest.mark.django_db
def test_draft_returns_404(client):
    ManualPage.objects.create(
        title="Borrador",
        slug="borrador",
        body="x",
        is_published=False,
    )
    r = client.get(reverse("manuals:page", kwargs={"slug": "borrador"}))
    assert r.status_code == 404


def test_markdown_renders_heading():
    html = render_manual_body("# Title", content_format=ManualContentFormat.MARKDOWN)
    assert "<h1>Title</h1>" in html


def test_html_script_stripped():
    html = render_manual_body(
        '<p>ok</p><script>alert(1)</script>',
        content_format=ManualContentFormat.HTML,
    )
    assert "ok" in html
    assert "script" not in html.lower()
    assert "alert" not in html
