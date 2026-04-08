from __future__ import annotations

import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from openpyxl import Workbook

from apps.accounts.decorators import company_admin_required, login_and_company_required
from apps.accounts.permissions import (
    applies_adjustment_self_only_scope,
    can_view_commission_line_detail,
    filter_adjustments_by_teams,
    filter_commission_events_by_teams,
    filter_commission_events_for_adjustment_form,
    filter_commission_lines_by_teams,
    filter_rules_by_teams,
    is_company_commission_auditor,
    sees_all_company_commissions,
    user_accessible_team_ids,
    user_team_lead_ids,
)
from apps.commissions.engine import CommissionEngine
from apps.commissions.forms import CommissionEventForm, FilterForm
from apps.commissions.models import (
    CommissionEvent,
    CommissionLine,
    CommissionPeriod,
    CommissionType,
    LineState,
    PeriodState,
    ProjectCommissionType,
)
from apps.commissions.tasks import recalculate_period
from apps.projects.models import Team


def _company(request):
    return request.company


def _safe_commission_back_url(request, default: str = "commissions:employee_summary") -> str:
    nxt = (request.GET.get("next") or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    from django.urls import reverse

    return reverse(default)


def _register_smart_defaults(company, user):
    """
    Preselecciona periodo, contexto proyecto/equipo/tipo y empleado cuando el
    catálogo y la membresía lo dejan obvio (sin sustituir reglas: el motor las aplica al guardar).
    """
    from apps.accounts.permissions import (
        commission_scoped_employees_queryset,
        commission_scoped_projects_queryset,
        sees_all_company_commissions,
        user_accessible_team_ids,
    )
    from apps.staff.models import Employee

    initial = {}
    hints = []

    period = (
        CommissionPeriod.objects.filter(company=company, is_locked=False)
        .exclude(state=PeriodState.CLOSED)
        .order_by("-start_date")
        .first()
    )
    if period is None:
        period = CommissionPeriod.objects.filter(company=company).order_by("-start_date").first()
    if period:
        initial["period"] = period.pk
        hints.append("periodo operativo actual")

    if not sees_all_company_commissions(user, company):
        tids = user_accessible_team_ids(user, company)
        if len(tids) == 1:
            initial["team"] = tids[0]
            hints.append("tu equipo asignado")
            pqs = commission_scoped_projects_queryset(user, company).filter(
                project_teams__team_id=tids[0],
                project_teams__is_active=True,
            ).distinct()
            if pqs.count() == 1:
                initial["project"] = pqs.first().pk
                hints.append("único proyecto enlazado a ese equipo")

    em_qs = commission_scoped_employees_queryset(user, company)
    if em_qs.count() == 1:
        initial["employee"] = em_qs.first().pk
        hints.append("empleado único en tu alcance")
    else:
        linked = Employee.objects.filter(company=company, user=user, is_active=True).first()
        if linked and em_qs.filter(pk=linked.pk).exists():
            initial["employee"] = linked.pk
            hints.append("tu ficha de empleado")

    pid = initial.get("project")
    if pid:
        type_ids = ProjectCommissionType.objects.filter(
            project_id=pid,
            is_active=True,
        ).values_list("commission_type_id", flat=True)
        types = CommissionType.objects.filter(company=company, pk__in=type_ids)
        if types.count() == 1:
            initial["commission_type"] = types.first().pk
            hints.append("único tipo de comisión activo en el proyecto")

    banner = None
    if hints:
        banner = (
            "Se rellenaron automáticamente: "
            + ", ".join(hints)
            + ". Las reglas y el cálculo los aplica el sistema al guardar; puedes ajustar lo necesario."
        )
    return initial, banner


@login_and_company_required
def dashboard(request):
    company = _company(request)
    user = request.user
    base_ccy = (company.base_currency or "MXN").upper()
    periods = CommissionPeriod.objects.filter(company=company).order_by("-start_date")[:6]
    lines_qs = CommissionLine.objects.filter(
        company=company,
        state__in=[LineState.PENDING, LineState.PENDING_APPROVAL],
    )
    pending_lines = filter_commission_lines_by_teams(lines_qs, user, company).count()

    from apps.accounts.permissions import user_linked_employee_id

    employee_id = user_linked_employee_id(user, company)
    my_summary = None
    if employee_id:
        my_lines = CommissionLine.objects.filter(
            company=company, employee_id=employee_id
        )
        totals_by_state = (
            my_lines.values("state")
            .annotate(total=Sum("amount"))
            .order_by("state")
        )
        state_map = {row["state"]: row["total"] for row in totals_by_state}
        grand_total = sum(state_map.values(), Decimal("0"))

        current_period = periods[0] if periods else None
        period_total = Decimal("0")
        by_type_period = []
        if current_period:
            period_lines = my_lines.filter(event__period=current_period)
            period_total = period_lines.aggregate(
                total=Coalesce(Sum("amount"), Decimal("0"))
            )["total"]
            by_type_period = list(
                period_lines.values("commission_type__name")
                .annotate(total=Sum("amount"))
                .order_by("-total")
            )

        state_breakdown = []
        display_order = [
            (LineState.APPROVED, "success"),
            (LineState.PAID, "info"),
            (LineState.PENDING, "warning"),
            (LineState.PENDING_APPROVAL, "secondary"),
            (LineState.ADJUSTED, "dark"),
            (LineState.REJECTED, "danger"),
        ]
        for state_val, color in display_order:
            amt = state_map.get(state_val, Decimal("0"))
            if amt:
                state_breakdown.append({
                    "label": dict(LineState.choices).get(state_val, state_val),
                    "amount": amt,
                    "color": color,
                })

        my_summary = {
            "grand_total": grand_total,
            "period_total": period_total,
            "current_period": current_period,
            "state_breakdown": state_breakdown,
            "by_type_period": by_type_period,
            "currency": base_ccy,
        }

    return render(
        request,
        "commissions/dashboard.html",
        {
            "periods": periods,
            "pending_lines": pending_lines,
            "my_summary": my_summary,
            "base_ccy": base_ccy,
        },
    )


@login_and_company_required
def register_event(request):
    company = _company(request)
    user = request.user
    team_ids = user_accessible_team_ids(user, company)
    no_team_access = not team_ids and not user.is_superuser
    from apps.accounts.permissions import sees_all_company_commissions

    if no_team_access and not sees_all_company_commissions(user, company):
        return render(
            request,
            "commissions/register_blocked.html",
            {"message": "No tienes equipos asignados. Pide a un administrador que te asigne al menos un equipo."},
        )

    initial, register_banner = _register_smart_defaults(company, user)
    if request.method == "POST":
        form = CommissionEventForm(request.POST, company=company, user=user)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.company = company
            ev.created_by = user
            ev.save()
            CommissionEngine.evaluate(ev)
            return redirect("commissions:register")
    else:
        form = CommissionEventForm(company=company, user=user, initial=initial)
    recent_qs = CommissionEvent.objects.filter(company=company).select_related(
        "project", "team", "employee", "period", "commission_type", "fx_rate"
    )
    recent = filter_commission_events_for_adjustment_form(recent_qs, user, company).order_by("-id")[
        :25
    ]
    return render(
        request,
        "commissions/register.html",
        {
            "form": form,
            "recent_events": recent,
            "register_context_banner": register_banner if request.method != "POST" else None,
        },
    )


@login_and_company_required
@require_POST
def event_patch(request, pk: int):
    company = _company(request)
    user = request.user
    if is_company_commission_auditor(user, company):
        return HttpResponseForbidden("Los auditores no pueden editar eventos.")
    event = get_object_or_404(CommissionEvent, pk=pk, company=company)
    if not filter_commission_events_for_adjustment_form(
        CommissionEvent.objects.filter(pk=event.pk), user, company
    ).exists():
        return HttpResponseForbidden("No puedes editar este evento.")
    if event.period.is_locked or event.period.state == PeriodState.CLOSED:
        return HttpResponse(
            render_to_string("partials/field_feedback.html", {"ok": False, "message": "Periodo cerrado"}),
            status=400,
        )
    allowed = {
        "amount_usd",
        "fx_rate_id",
        "hours",
        "event_kind",
        "notes",
        "sales_channel",
        "is_business_hours",
        "occurred_on",
        "project_id",
        "team_id",
        "employee_id",
        "commission_type_id",
        "period_id",
    }
    key = None
    value = None
    for k, v in request.POST.items():
        if k in ("csrfmiddlewaretoken",):
            continue
        if k in allowed or k.endswith("_id") and k.replace("_id", "") in {
            "project",
            "team",
            "employee",
            "commission_type",
            "period",
        }:
            key = k
            value = v
            break
    if not key:
        return HttpResponse(status=400)

    _structural_patch_keys = frozenset(
        {"project_id", "team_id", "employee_id", "period_id"},
    )
    if applies_adjustment_self_only_scope(user, company) and key in _structural_patch_keys:
        return HttpResponse(
            render_to_string(
                "partials/field_feedback.html",
                {
                    "ok": False,
                    "message": "Tu perfil no permite cambiar proyecto, equipo, empleado ni periodo.",
                },
            ),
            status=403,
        )

    try:
        if key == "amount_usd":
            event.amount_usd = Decimal(value) if value not in ("", None) else None
        elif key == "fx_rate_id":
            if value in ("", None):
                event.fx_rate_id = None
            else:
                from apps.fx.models import FxRate

                rid = int(value)
                rate = FxRate.objects.filter(pk=rid, company=company).first()
                if not rate:
                    return HttpResponse(
                        render_to_string(
                            "partials/field_feedback.html",
                            {"ok": False, "message": "Tipo de cambio no válido"},
                        ),
                        status=400,
                    )
                event.fx_rate_id = rid
        elif key == "hours":
            event.hours = Decimal(value) if value not in ("", None) else None
        elif key == "event_kind":
            event.event_kind = value
        elif key == "notes":
            event.notes = value
        elif key == "sales_channel":
            event.sales_channel = value
        elif key == "is_business_hours":
            event.is_business_hours = value in ("true", "on", "1", "True")
        elif key == "occurred_on":
            event.occurred_on = value
        elif key == "project_id":
            event.project_id = int(value) if value else None
        elif key == "team_id":
            tid = int(value) if value else None
            if tid and tid not in user_accessible_team_ids(user, company):
                return HttpResponse(
                    render_to_string(
                        "partials/field_feedback.html",
                        {"ok": False, "message": "Equipo no permitido"},
                    ),
                    status=403,
                )
            event.team_id = tid
        elif key == "employee_id":
            event.employee_id = int(value) if value else None
        elif key == "commission_type_id":
            event.commission_type_id = int(value) if value else None
        elif key == "period_id":
            event.period_id = int(value) if value else None
        event.save()
        CommissionEngine.evaluate(event)
    except (InvalidOperation, ValueError, TypeError) as exc:
        return HttpResponse(
            render_to_string(
                "partials/field_feedback.html",
                {"ok": False, "message": str(exc)},
            ),
            status=400,
        )

    return render(
        request,
        "partials/field_feedback.html",
        {"ok": True, "message": "Guardado"},
    )


@login_and_company_required
def event_edit(request, pk: int):
    company = _company(request)
    user = request.user
    event = get_object_or_404(CommissionEvent, pk=pk, company=company)
    if not filter_commission_events_for_adjustment_form(
        CommissionEvent.objects.filter(pk=event.pk), user, company
    ).exists():
        return HttpResponseForbidden("No puedes editar este evento.")

    period_locked = event.period.is_locked or event.period.state == PeriodState.CLOSED

    if request.method == "POST" and not period_locked:
        form = CommissionEventForm(request.POST, instance=event, company=company, user=user)
        if form.is_valid():
            ev = form.save()
            CommissionEngine.evaluate(ev)
            messages.success(request, f"Evento #{ev.pk} actualizado y recalculado.")
            return redirect("commissions:event_edit", pk=ev.pk)
    else:
        form = CommissionEventForm(instance=event, company=company, user=user)

    lines = CommissionLine.objects.filter(event=event).select_related(
        "employee", "commission_type", "rule"
    ).order_by("-id")

    return render(
        request,
        "commissions/event_edit.html",
        {
            "form": form,
            "event": event,
            "lines": lines,
            "period_locked": period_locked,
            "summary_base_currency": (company.base_currency or "MXN").upper(),
        },
    )


@login_and_company_required
def htmx_teams_for_project(request):
    company = _company(request)
    user = request.user
    pid = request.GET.get("project")
    teams = Team.objects.none()
    if pid:
        teams = Team.objects.filter(
            company=company,
            project_teams__project_id=pid,
            project_teams__is_active=True,
            is_active=True,
        ).distinct()
        from apps.accounts.permissions import sees_all_company_commissions

        if not sees_all_company_commissions(user, company):
            allowed = user_accessible_team_ids(user, company)
            teams = teams.filter(pk__in=allowed)
    choices = [("", "---------")] + [(t.pk, str(t)) for t in teams]
    return render(
        request,
        "commissions/partials/team_select_wrap.html",
        {"teams": choices, "selected": request.GET.get("selected", "")},
    )


@login_and_company_required
def htmx_types_for_project(request):
    company = _company(request)
    user = request.user
    pid = request.GET.get("project")
    types = CommissionType.objects.none()
    if pid:
        from apps.accounts.permissions import commission_scoped_projects_queryset

        if not commission_scoped_projects_queryset(user, company).filter(pk=pid).exists():
            types = CommissionType.objects.none()
        else:
            type_ids = ProjectCommissionType.objects.filter(
                project_id=pid, is_active=True
            ).values_list("commission_type_id", flat=True)
            types = CommissionType.objects.filter(company=company, id__in=type_ids)
    return render(
        request,
        "commissions/partials/type_options.html",
        {"types": types, "field_name": request.GET.get("field_name", "commission_type")},
    )


@login_and_company_required
def htmx_register_cascade(request):
    """Al cambiar proyecto: actualiza equipos válidos y tipos activos (esquema del proyecto)."""
    from apps.accounts.permissions import (
        commission_scoped_projects_queryset,
        commission_scoped_teams_queryset,
    )

    company = _company(request)
    user = request.user
    pid = request.GET.get("project")
    selected_team = request.GET.get("selected_team") or ""
    selected_type = request.GET.get("selected_type") or ""

    team_base = commission_scoped_teams_queryset(user, company)
    if pid:
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            pid_int = None
        if pid_int is None or not commission_scoped_projects_queryset(user, company).filter(pk=pid_int).exists():
            teams = Team.objects.none()
            types = CommissionType.objects.none()
        else:
            teams = (
                team_base.filter(
                    project_teams__project_id=pid_int,
                    project_teams__is_active=True,
                )
                .distinct()
                .order_by("name")
            )
            type_ids = ProjectCommissionType.objects.filter(
                project_id=pid_int, is_active=True
            ).values_list("commission_type_id", flat=True)
            types = CommissionType.objects.filter(company=company, pk__in=type_ids).order_by("name")
    else:
        teams = team_base
        proj_qs = commission_scoped_projects_queryset(user, company)
        type_ids = ProjectCommissionType.objects.filter(
            project__in=proj_qs,
            is_active=True,
        ).values_list("commission_type_id", flat=True)
        types = CommissionType.objects.filter(company=company, pk__in=type_ids).order_by("name")

    team_choices = [("", "---------")] + [(str(t.pk), str(t)) for t in teams]

    return render(
        request,
        "commissions/partials/register_cascade_oob.html",
        {
            "teams": team_choices,
            "selected_team": str(selected_team),
            "types": types,
            "selected_type": str(selected_type),
        },
    )


@login_and_company_required
def employee_summary(request):
    company = _company(request)
    user = request.user
    form = FilterForm(request.GET or None, company=company, user=user)
    lines = CommissionLine.objects.filter(company=company).select_related(
        "employee",
        "commission_type",
        "event__period",
        "event__project",
        "event__team",
        "event__fx_rate",
        "event__commission_type",
    )
    lines = filter_commission_lines_by_teams(lines, user, company)
    if form.is_valid():
        if form.cleaned_data.get("project"):
            lines = lines.filter(event__project=form.cleaned_data["project"])
        if form.cleaned_data.get("team"):
            lines = lines.filter(event__team=form.cleaned_data["team"])
        if form.cleaned_data.get("period"):
            lines = lines.filter(event__period=form.cleaned_data["period"])

    totals = {}
    for line in lines:
        eid = line.employee_id
        totals.setdefault(eid, {"employee": line.employee, "total": Decimal("0"), "lines": []})
        totals[eid]["total"] += line.amount
        totals[eid]["lines"].append(line)
    rows = sorted(totals.values(), key=lambda x: x["employee"].last_name)
    events_without_lines_count = 0
    if not rows:
        ev_qs = (
            CommissionEvent.objects.filter(company=company)
            .annotate(_line_count=Count("lines"))
            .filter(_line_count=0)
        )
        ev_qs = filter_commission_events_by_teams(ev_qs, user, company)
        if form.is_valid():
            if form.cleaned_data.get("project"):
                ev_qs = ev_qs.filter(project=form.cleaned_data["project"])
            if form.cleaned_data.get("team"):
                ev_qs = ev_qs.filter(team=form.cleaned_data["team"])
            if form.cleaned_data.get("period"):
                ev_qs = ev_qs.filter(period=form.cleaned_data["period"])
        events_without_lines_count = ev_qs.count()
    return render(
        request,
        "commissions/employee_summary.html",
        {
            "form": form,
            "rows": rows,
            "summary_base_currency": (company.base_currency or "MXN").upper(),
            "events_without_lines_count": events_without_lines_count,
        },
    )


def _get_line_detail_context(request, pk: int):
    company = _company(request)
    user = request.user
    line = get_object_or_404(
        CommissionLine.objects.filter(company=company).select_related(
            "employee",
            "commission_type",
            "rule",
            "event__period",
            "event__project",
            "event__team",
            "event__commission_type",
            "event__fx_rate",
            "event__employee",
            "event__created_by",
        ),
        pk=pk,
    )
    if not can_view_commission_line_detail(user, company, line):
        return None
    event = line.event
    show_line_state_actions = (
        not is_company_commission_auditor(user, company)
        and (
            sees_all_company_commissions(user, company)
            or event.team_id in user_team_lead_ids(user, company)
        )
    )
    return {
        "line": line,
        "event": event,
        "summary_base_currency": (company.base_currency or "MXN").upper(),
        "show_line_state_actions": show_line_state_actions,
    }


@login_and_company_required
def commission_line_detail(request, pk: int):
    ctx = _get_line_detail_context(request, pk)
    if ctx is None:
        return HttpResponseForbidden("No puedes ver este registro.")
    ctx["back_url"] = _safe_commission_back_url(request)
    return render(request, "commissions/line_detail.html", ctx)


@login_and_company_required
def commission_line_detail_modal(request, pk: int):
    ctx = _get_line_detail_context(request, pk)
    if ctx is None:
        return HttpResponseForbidden("No puedes ver este registro.")
    return render(request, "commissions/partials/line_detail_modal.html", ctx)


@login_and_company_required
def export_summary_xlsx(request):
    company = _company(request)
    user = request.user
    form = FilterForm(request.GET or None, company=company, user=user)
    lines = CommissionLine.objects.filter(company=company).select_related("employee", "event")
    lines = filter_commission_lines_by_teams(lines, user, company)
    if form.is_valid():
        if form.cleaned_data.get("project"):
            lines = lines.filter(event__project=form.cleaned_data["project"])
        if form.cleaned_data.get("team"):
            lines = lines.filter(event__team=form.cleaned_data["team"])
        if form.cleaned_data.get("period"):
            lines = lines.filter(event__period=form.cleaned_data["period"])

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(
        ["Empleado", "Periodo", "Proyecto", "Monto", "Moneda", "Estado", "Explicación"]
    )
    for line in lines.order_by("employee__last_name", "id"):
        ws.append(
            [
                str(line.employee),
                str(line.event.period),
                str(line.event.project),
                float(line.amount),
                line.currency,
                line.get_state_display(),
                line.calculation_explanation[:500] if line.calculation_explanation else "",
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = 'attachment; filename="resumen_comisiones.xlsx"'
    return resp


@company_admin_required
@require_POST
def recalculate_period_view(request, pk: int):
    company = _company(request)
    period = get_object_or_404(CommissionPeriod, pk=pk, company=company)
    if period.is_locked:
        messages.error(
            request,
            "Este periodo está bloqueado: no se puede recalcular. "
            "Desbloquéalo en Periodos si necesitas volver a generar las líneas de comisión.",
        )
        return redirect("commissions:dashboard")
    recalculate_period.delay(period.id, request.user.id)
    messages.success(
        request,
        f"Recálculo del periodo «{period.name}» en cola. Los cambios se aplicarán en segundo plano.",
    )
    return redirect("commissions:dashboard")


@login_and_company_required
def rules_list_redirect(request):
    """Alcance compañía: planes; si no, lista filtrada por equipos (comportamiento anterior)."""
    company = _company(request)
    user = request.user
    if company and sees_all_company_commissions(user, company):
        return redirect("commissions:plan_list")
    from apps.rules.models import CommissionRule

    rules = CommissionRule.objects.filter(company=company).select_related(
        "project", "team", "commission_type", "plan"
    )
    rules = filter_rules_by_teams(rules, user, company)
    return render(request, "commissions/rules_list.html", {"rules": rules})


@login_and_company_required
def adjustments_list(request):
    company = _company(request)
    user = request.user
    from apps.commissions.models import Adjustment

    items = Adjustment.objects.filter(company=company).select_related("line", "event")
    items = filter_adjustments_by_teams(items, user, company).order_by("-id")[:200]
    return render(request, "commissions/adjustments.html", {"adjustments": items})
