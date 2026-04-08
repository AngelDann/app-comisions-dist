from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.middleware import is_company_admin


def login_and_company_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser and request.company is None:
            return redirect(reverse("accounts:select_company"))
        if request.company is None and not request.user.is_superuser:
            return redirect(reverse("accounts:select_company"))
        return view_func(request, *args, **kwargs)

    return _wrapped


def company_admin_required(view_func):
    """Solo administrador de compañía / encargado de comisiones / superusuario."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser and request.company is None:
            return redirect(reverse("accounts:select_company"))
        if request.company is None and not request.user.is_superuser:
            return redirect(reverse("accounts:select_company"))
        company = request.company
        if company is None or not is_company_admin(request.user, company):
            return HttpResponseForbidden("No tienes permiso para esta sección.")
        return view_func(request, *args, **kwargs)

    return _wrapped
