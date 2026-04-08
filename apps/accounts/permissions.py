"""Permisos y alcance operativo (comisiones por equipo, admins de compañía)."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.middleware import is_company_admin, membership_role
from apps.accounts.models import MembershipRole, UserTeamScope


def sees_all_company_commissions(user, company) -> bool:
    """Admin de compañía, encargado de comisiones o superusuario: sin filtro por equipo."""
    if user.is_superuser:
        return True
    return is_company_admin(user, company)


def user_accessible_team_ids(user, company) -> list[int]:
    """IDs de equipos cuyas comisiones puede ver/editar el usuario."""
    if sees_all_company_commissions(user, company):
        from apps.projects.models import Team

        return list(Team.objects.filter(company=company, is_active=True).values_list("pk", flat=True))
    return list(
        UserTeamScope.objects.filter(user=user, company=company).values_list("team_id", flat=True)
    )


def user_team_lead_ids(user, company) -> list[int]:
    """Equipos donde el usuario es líder (permisos elevados por equipo)."""
    return list(
        UserTeamScope.objects.filter(
            user=user, company=company, is_team_lead=True
        ).values_list("team_id", flat=True)
    )


def user_linked_employee_id(user, company) -> int | None:
    """Ficha de empleado activa ligada al usuario en la compañía, si existe."""
    from apps.staff.models import Employee

    return (
        Employee.objects.filter(company=company, user=user, is_active=True)
        .values_list("pk", flat=True)
        .first()
    )


def is_company_commission_auditor(user, company) -> bool:
    """Rol de membresía auditor: consulta de comisiones sin acciones de aprobación."""
    return membership_role(user, company) == MembershipRole.AUDITOR


def can_view_commission_line_detail(user, company, line) -> bool:
    """Puede abrir la ficha línea + evento: global, auditor, líder del equipo del evento o empleado titular."""
    if getattr(line, "company_id", None) != company.pk:
        return False
    if sees_all_company_commissions(user, company):
        return True
    if is_company_commission_auditor(user, company):
        return True
    tid = getattr(line.event, "team_id", None)
    if tid and tid in user_team_lead_ids(user, company):
        return True
    emp_id = user_linked_employee_id(user, company)
    return emp_id is not None and line.employee_id == emp_id


def applies_adjustment_self_only_scope(user, company) -> bool:
    """Colaborador sin visión global ni rol de líder de equipo: solo sus propias líneas/eventos."""
    if sees_all_company_commissions(user, company):
        return False
    if is_company_commission_auditor(user, company):
        return False
    return not user_team_lead_ids(user, company)


def filter_commission_lines_for_adjustment_form(qs: QuerySet, user, company) -> QuerySet:
    """Líneas elegibles al registrar un ajuste (equipo + opcionalmente solo el empleado vinculado al usuario)."""
    qs = filter_commission_lines_by_teams(qs, user, company)
    if not applies_adjustment_self_only_scope(user, company):
        return qs
    emp_id = user_linked_employee_id(user, company)
    if emp_id is None:
        return qs.none()
    return qs.filter(employee_id=emp_id)


def filter_commission_events_for_adjustment_form(qs: QuerySet, user, company) -> QuerySet:
    """Eventos elegibles al registrar un ajuste (equipo + opcionalmente solo el empleado vinculado)."""
    qs = filter_commission_events_by_teams(qs, user, company)
    if not applies_adjustment_self_only_scope(user, company):
        return qs
    emp_id = user_linked_employee_id(user, company)
    if emp_id is None:
        return qs.none()
    return qs.filter(employee_id=emp_id)


def commission_scoped_projects_queryset(user, company):
    """Proyectos alcanzables para captura/filtros: todos si admin; si no, vía ProjectTeam de sus equipos."""
    from apps.projects.models import Project

    qs = Project.objects.filter(company=company, is_active=True)
    if sees_all_company_commissions(user, company):
        return qs
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    return (
        qs.filter(project_teams__team_id__in=team_ids, project_teams__is_active=True)
        .distinct()
        .order_by("name")
    )


def commission_scoped_teams_queryset(user, company):
    """Equipos en dropdowns de comisiones: solo los asignados si no es admin."""
    from apps.projects.models import Team

    qs = Team.objects.filter(company=company, is_active=True)
    if sees_all_company_commissions(user, company):
        return qs.order_by("name")
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    return qs.filter(pk__in=team_ids).order_by("name")


def commission_scoped_employees_queryset(user, company):
    """Empleados visibles para eventos: ligados a los equipos accesibles (o todos si admin)."""
    from apps.staff.models import Employee

    qs = Employee.objects.filter(company=company, is_active=True)
    if sees_all_company_commissions(user, company):
        return qs.order_by("last_name", "first_name")
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    return qs.filter(employee_teams__team_id__in=team_ids).distinct().order_by("last_name", "first_name")


def filter_commission_lines_by_teams(qs: QuerySet, user, company) -> QuerySet:
    if sees_all_company_commissions(user, company):
        return qs
    if is_company_commission_auditor(user, company):
        return qs
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    return qs.filter(event__team_id__in=team_ids)


def filter_commission_events_by_teams(qs: QuerySet, user, company) -> QuerySet:
    if sees_all_company_commissions(user, company):
        return qs
    if is_company_commission_auditor(user, company):
        return qs
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    return qs.filter(team_id__in=team_ids)


def filter_adjustments_by_teams(qs: QuerySet, user, company) -> QuerySet:
    if sees_all_company_commissions(user, company):
        return qs
    if is_company_commission_auditor(user, company):
        return qs
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        out = qs.none()
    else:
        from django.db.models import Q

        out = qs.filter(
            Q(line__event__team_id__in=team_ids) | Q(event__team_id__in=team_ids)
        )
    if applies_adjustment_self_only_scope(user, company):
        from django.db.models import Q

        emp_id = user_linked_employee_id(user, company)
        if emp_id is None:
            return qs.none()
        out = out.filter(Q(line__employee_id=emp_id) | Q(event__employee_id=emp_id))
    return out


def filter_rules_by_teams(qs: QuerySet, user, company) -> QuerySet:
    """Reglas globales (sin team) visibles para todos con acceso a reglas; resto filtrado por team."""
    if sees_all_company_commissions(user, company):
        return qs
    team_ids = user_accessible_team_ids(user, company)
    if not team_ids:
        return qs.none()
    from django.db.models import Q

    return qs.filter(Q(team_id__isnull=True) | Q(team_id__in=team_ids))


def can_manage_company_users(user, company) -> bool:
    return is_company_admin(user, company)


def can_assign_company_admin_role(editor, company) -> bool:
    return editor.is_superuser or membership_role(editor, company) == MembershipRole.COMPANY_ADMIN


def can_access_people_module(user, company) -> bool:
    return can_manage_company_users(user, company) or bool(user_team_lead_ids(user, company))


def manageable_memberships_queryset(user, company):
    from apps.accounts.models import UserMembership, UserTeamScope

    if can_manage_company_users(user, company):
        return (
            UserMembership.objects.filter(company=company)
            .select_related("user")
            .order_by("user__username")
        )
    lead_team_ids = user_team_lead_ids(user, company)
    if not lead_team_ids:
        return UserMembership.objects.none()
    uids = (
        UserTeamScope.objects.filter(company=company, team_id__in=lead_team_ids)
        .values_list("user_id", flat=True)
        .distinct()
    )
    return (
        UserMembership.objects.filter(company=company, user_id__in=uids)
        .select_related("user")
        .distinct()
        .order_by("user__username")
    )
