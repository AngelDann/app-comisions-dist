"""Sanitización de notas HTML y subida de imágenes."""

from __future__ import annotations

import uuid
from pathlib import Path

import bleach
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.accounts.decorators import login_and_company_required

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s",
    "h1", "h2", "h3",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "img",
    "hr",
]

ALLOWED_ATTRS = {
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "style"],
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def sanitize_notes(html: str) -> str:
    if not html or not html.strip():
        return ""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )


@login_and_company_required
@require_POST
def upload_note_image(request):
    img = request.FILES.get("image")
    if not img:
        return JsonResponse({"error": "No se envió ninguna imagen."}, status=400)
    if img.size > MAX_IMAGE_SIZE:
        return JsonResponse({"error": "La imagen excede 5 MB."}, status=400)

    ext = Path(img.name).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return JsonResponse({"error": "Formato no permitido."}, status=400)

    filename = f"notes/{uuid.uuid4().hex}{ext}"
    saved = default_storage.save(filename, img)
    url = settings.MEDIA_URL + saved
    return JsonResponse({"url": url})
