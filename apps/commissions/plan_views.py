"""CRUD de planes de comisión y asignaciones."""

from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.decorators import company_admin_required
from apps.commissions.date_fields import bind_iso_html_dates
from apps.projects.models import Project, Team
from apps.rules.models import (
    CommissionPlan,
    CommissionPlanEmployee,
    CommissionPlanTeam,
    CommissionRule,
)
from apps.staff.models import Employee


def _c(request):
    return request.company


class CommissionPlanForm(forms.ModelForm):
    class Meta:
        model = CommissionPlan
        fields = [
            "name",
            "description",
            "project",
            "is_active",
            "is_global",
            "valid_from",
            "valid_to",
        ]
        labels = {
            "name": "Nombre",
            "description": "Descripción",
            "project": "Proyecto",
            "is_active": "Activo",
            "is_global": "Global",
            "valid_from": "Válido desde",
            "valid_to": "Válido hasta",
        }
        widgets = {
            "valid_from": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "valid_to": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        bind_iso_html_dates(self, "valid_from", "valid_to")
        self.fields["project"].queryset = Project.objects.filter(company=company, is_active=True)
        self.fields["project"].required = False
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class CommissionPlanTeamForm(forms.ModelForm):
    class Meta:
        model = CommissionPlanTeam
        fields = ["team", "valid_from", "valid_to"]
        labels = {
            "team": "Equipo",
            "valid_from": "Válido desde",
            "valid_to": "Válido hasta",
        }
        widgets = {
            "valid_from": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "valid_to": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        bind_iso_html_dates(self, "valid_from", "valid_to")
        self.fields["team"].queryset = Team.objects.filter(company=company, is_active=True)
        self.fields["team"].widget.attrs.setdefault("class", "form-select")
        for name in ("valid_from", "valid_to"):
            self.fields[name].widget.attrs.setdefault("class", "form-control")
            self.fields[name].required = False


class CommissionPlanEmployeeForm(forms.ModelForm):
    class Meta:
        model = CommissionPlanEmployee
        fields = ["employee", "valid_from", "valid_to"]
        labels = {
            "employee": "Empleado",
            "valid_from": "Válido desde",
            "valid_to": "Válido hasta",
        }
        widgets = {
            "valid_from": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "valid_to": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        bind_iso_html_dates(self, "valid_from", "valid_to")
        self.fields["employee"].queryset = Employee.objects.filter(company=company, is_active=True)
        self.fields["employee"].widget.attrs.setdefault("class", "form-select")
        for name in ("valid_from", "valid_to"):
            self.fields[name].widget.attrs.setdefault("class", "form-control")
            self.fields[name].required = False


@company_admin_required
def plan_list(request):
    company = _c(request)
    plans = (
        CommissionPlan.objects.filter(company=company)
        .select_related("project")
        .order_by("name")
    )
    return render(request, "commissions/plan_list.html", {"plans": plans})


@company_admin_required
def plan_create(request):
    company = _c(request)
    if request.method == "POST":
        form = CommissionPlanForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions:plan_detail", pk=form.instance.pk)
    else:
        form = CommissionPlanForm(company=company)
    return render(
        request,
        "commissions/plan_form.html",
        {"form": form, "title": "Nuevo plan"},
    )


@company_admin_required
def plan_edit(request, pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    if request.method == "POST":
        form = CommissionPlanForm(request.POST, instance=plan, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions:plan_detail", pk=plan.pk)
    else:
        form = CommissionPlanForm(instance=plan, company=company)
    return render(
        request,
        "commissions/plan_form.html",
        {"form": form, "title": f"Editar {plan.name}", "plan": plan},
    )


@company_admin_required
@require_POST
def plan_delete(request, pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    plan.delete()
    return redirect("commissions:plan_list")


@company_admin_required
def plan_detail(request, pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    tab = request.GET.get("tab", "rules")
    if tab not in ("rules", "assignments"):
        tab = "rules"

    rules = (
        CommissionRule.objects.filter(company=company, plan=plan)
        .select_related("project", "team", "commission_type")
        .order_by("priority", "id")
    )
    team_assignments = plan.plan_teams.select_related("team").order_by("team__name")
    employee_assignments = plan.plan_employees.select_related("employee").order_by(
        "employee__last_name", "employee__first_name"
    )

    team_form = CommissionPlanTeamForm(company=company)
    employee_form = CommissionPlanEmployeeForm(company=company)

    return render(
        request,
        "commissions/plan_detail.html",
        {
            "plan": plan,
            "tab": tab,
            "rules": rules,
            "team_assignments": team_assignments,
            "employee_assignments": employee_assignments,
            "team_form": team_form,
            "employee_form": employee_form,
        },
    )


@company_admin_required
@require_POST
def plan_team_add(request, pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    form = CommissionPlanTeamForm(request.POST, company=company)
    if form.is_valid():
        row = form.save(commit=False)
        row.plan = plan
        row.save()
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": plan.pk}) + "?tab=assignments")


@company_admin_required
@require_POST
def plan_employee_add(request, pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    form = CommissionPlanEmployeeForm(request.POST, company=company)
    if form.is_valid():
        row = form.save(commit=False)
        row.plan = plan
        row.save()
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": plan.pk}) + "?tab=assignments")


@company_admin_required
@require_POST
def plan_team_remove(request, pk: int, assignment_pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    row = get_object_or_404(CommissionPlanTeam, pk=assignment_pk, plan=plan)
    row.delete()
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": plan.pk}) + "?tab=assignments")


@company_admin_required
@require_POST
def plan_employee_remove(request, pk: int, assignment_pk: int):
    company = _c(request)
    plan = get_object_or_404(CommissionPlan, pk=pk, company=company)
    row = get_object_or_404(CommissionPlanEmployee, pk=assignment_pk, plan=plan)
    row.delete()
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": plan.pk}) + "?tab=assignments")
