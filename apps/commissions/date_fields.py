"""Campos fecha para <input type=\"date\">: valor y POST en ISO (yyyy-mm-dd)."""

from __future__ import annotations

from django import forms

ISO_DATE = "%Y-%m-%d"


def bind_iso_html_date(field: forms.Field) -> None:
    """
    Fuerza formato ISO en el widget y en input_formats para que:
    - al editar, el valor inicial se pinte en el date picker;
    - al enviar el formulario, se acepte el string que manda el navegador.
    """
    if not isinstance(field, forms.DateField):
        return
    widget = field.widget
    if not isinstance(widget, forms.DateInput):
        return
    widget.format = ISO_DATE
    widget.attrs.setdefault("type", "date")
    if ISO_DATE not in field.input_formats:
        field.input_formats = [ISO_DATE, *list(field.input_formats)]


def bind_iso_html_dates(form: forms.BaseForm, *names: str) -> None:
    for name in names:
        if name in form.fields:
            bind_iso_html_date(form.fields[name])
