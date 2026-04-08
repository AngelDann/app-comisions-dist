"""Etiquetas de plantilla para la app commissions."""

from urllib.parse import urlencode

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def commission_line_detail_url(request, line_pk):
    """URL de detalle de línea conservando la vuelta con ?next= codificado."""
    path = reverse("commissions:line_detail", kwargs={"pk": line_pk})
    return f"{path}?{urlencode({'next': request.get_full_path()})}"
