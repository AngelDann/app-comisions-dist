"""Vincular usuarios de la compañía con fichas Employee (comisiones)."""

from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth.base_user import AbstractBaseUser


def names_from_email_and_optional(email: str, first_name: str, last_name: str) -> tuple[str, str]:
    fn, ln = (first_name or "").strip(), (last_name or "").strip()
    if fn and ln:
        return fn, ln
    local, _, _ = (email or "").partition("@")
    local = local.replace("_", " ").replace(".", " ")
    tokens = [t for t in local.split() if t]
    if fn and not ln:
        return fn, (tokens[1].title() if len(tokens) > 1 else ".")
    if ln and not fn:
        return (tokens[0].title() if tokens else "Usuario"), ln
    if len(tokens) >= 2:
        return tokens[0].title(), " ".join(x.title() for x in tokens[1:])
    if tokens:
        return tokens[0].title(), "."
    return "Usuario", "."


def default_employee_code(email: str) -> str:
    local, _, _ = (email or "user").partition("@")
    return (local or "user")[:64]


def link_or_sync_employee_for_user(
    *,
    company,
    user: AbstractBaseUser,
    teams: Iterable,
    enabled: bool,
    first_name: str = "",
    last_name: str = "",
    employee_code: str = "",
):
    """Si enabled, crea o actualiza Employee vinculado a user y alinea equipos con `teams`."""
    from apps.staff.models import Employee

    if not enabled:
        return None

    team_list = list(teams)
    email = getattr(user, "email", None) or user.username
    fn, ln = names_from_email_and_optional(email, first_name, last_name)
    code_in = (employee_code or "").strip()[:64]

    emp = Employee.objects.filter(company=company, user=user).first()
    if emp:
        emp.first_name = fn
        emp.last_name = ln
        if code_in:
            emp.employee_code = code_in
        emp.is_active = True
        emp.save()
    else:
        code = code_in or default_employee_code(email)
        emp = Employee.objects.create(
            company=company,
            user=user,
            first_name=fn,
            last_name=ln,
            employee_code=code,
            is_active=True,
        )
    emp.teams.set(team_list)
    return emp
