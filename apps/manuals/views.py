from __future__ import annotations

from collections import defaultdict

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.manuals.models import ManualPage
from apps.manuals.services import render_manual_body


def _published_qs():
    return ManualPage.objects.filter(is_published=True).order_by(
        "parent_id", "sort_order", "id"
    )


def _pages_by_parent(pages: list[ManualPage]) -> dict[int | None, list[ManualPage]]:
    by_parent: dict[int | None, list[ManualPage]] = defaultdict(list)
    for p in pages:
        by_parent[p.parent_id].append(p)
    return by_parent


def _nav_branches(parent_id: int | None, by_parent: dict[int | None, list[ManualPage]]):
    return [
        {
            "page": p,
            "children": _nav_branches(p.pk, by_parent),
        }
        for p in by_parent.get(parent_id, [])
    ]


def _preorder_first_slug(by_parent: dict[int | None, list[ManualPage]]) -> str | None:
    """Primer documento en recorrido preorden (raíz izquierda a derecha, luego hijos)."""

    def preorder(pid: int | None):
        for p in by_parent.get(pid, []):
            yield p
            yield from preorder(p.pk)

    first = next(preorder(None), None)
    return first.slug if first else None


def manual_index(request):
    pages = list(_published_qs())
    if not pages:
        return _render_manual(
            request,
            current_page=None,
            rendered_html="",
            nav_branches=[],
            search_query="",
            search_matches=[],
            empty_catalog=True,
        )
    by_parent = _pages_by_parent(pages)
    slug = _preorder_first_slug(by_parent)
    if not slug:
        return _render_manual(
            request,
            current_page=None,
            rendered_html="",
            nav_branches=[],
            search_query="",
            search_matches=[],
            empty_catalog=True,
        )
    return redirect(reverse("manuals:page", kwargs={"slug": slug}))


def manual_page(request, slug: str):
    page = get_object_or_404(ManualPage, slug=slug, is_published=True)
    pages = list(_published_qs())
    by_parent = _pages_by_parent(pages)
    nav_branches = _nav_branches(None, by_parent)
    q = (request.GET.get("q") or "").strip()
    search_matches: list[ManualPage] = []
    if q:
        search_matches = list(
            _published_qs().filter(Q(title__icontains=q) | Q(body__icontains=q))[:50]
        )
    rendered = render_manual_body(page.body, content_format=page.content_format)
    return _render_manual(
        request,
        current_page=page,
        rendered_html=rendered,
        nav_branches=nav_branches,
        search_query=q,
        search_matches=search_matches,
        empty_catalog=False,
    )


def _render_manual(
    request,
    *,
    current_page: ManualPage | None,
    rendered_html: str,
    nav_branches: list,
    search_query: str,
    search_matches: list[ManualPage],
    empty_catalog: bool,
):
    ctx = {
        "current_page": current_page,
        "rendered_html": rendered_html,
        "nav_branches": nav_branches,
        "search_query": search_query,
        "search_matches": search_matches,
        "empty_catalog": empty_catalog,
    }
    if request.user.is_authenticated:
        tpl = "manuals/page_app.html"
    else:
        tpl = "manuals/page_public.html"
    return render(request, tpl, ctx)
