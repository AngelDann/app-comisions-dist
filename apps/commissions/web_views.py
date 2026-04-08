from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.accounts.decorators import company_admin_required
from apps.commissions.date_fields import bind_iso_html_dates
from apps.commissions.models import CommissionPeriod, CommissionType, ProjectCommissionType
from apps.projects.models import Project


class PeriodForm(forms.ModelForm):
    class Meta:
        model = CommissionPeriod
        fields = ["name", "start_date", "end_date", "state", "fx_policy", "is_locked"]
        labels = {
            "name": "Nombre",
            "start_date": "Fecha de inicio",
            "end_date": "Fecha de fin",
            "state": "Estado",
            "fx_policy": "Tipo de cambio",
            "is_locked": "Bloqueado",
        }
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        bind_iso_html_dates(self, "start_date", "end_date")
        for name, f in self.fields.items():
            if name in ("start_date", "end_date"):
                continue
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-check-input")
                continue
            f.widget.attrs.setdefault("class", "form-select" if isinstance(f.widget, forms.Select) else "form-control")


class CommissionTypeForm(forms.ModelForm):
    class Meta:
        model = CommissionType
        fields = ["name", "slug", "description"]
        labels = {
            "name": "Nombre",
            "slug": "Identificador (slug)",
            "description": "Descripción",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or ""
        if not slug and self.cleaned_data.get("name"):
            slug = slugify(self.cleaned_data["name"]) or "tipo"
        base = slug
        qs = CommissionType.objects.filter(company=self.instance.company)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        candidate = base
        n = 0
        while qs.filter(slug=candidate).exists():
            n += 1
            candidate = f"{base}-{n}"
        return candidate


def _c(request):
    return request.company


@company_admin_required
def period_list(request):
    company = _c(request)
    items = CommissionPeriod.objects.filter(company=company).order_by("-start_date")
    return render(request, "commissions_web/period_list.html", {"periods": items})


@company_admin_required
def period_create(request):
    company = _c(request)
    if request.method == "POST":
        form = PeriodForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions_web:period_list")
    else:
        form = PeriodForm(company=company)
    return render(request, "commissions_web/period_form.html", {"form": form, "title": "Nuevo periodo"})


@company_admin_required
def period_edit(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(CommissionPeriod, pk=pk, company=company)
    if request.method == "POST":
        form = PeriodForm(request.POST, instance=obj, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions_web:period_list")
    else:
        form = PeriodForm(instance=obj, company=company)
    return render(request, "commissions_web/period_form.html", {"form": form, "title": f"Editar {obj}"})


@company_admin_required
@require_POST
def period_delete(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(CommissionPeriod, pk=pk, company=company)
    obj.delete()
    return redirect("commissions_web:period_list")


@company_admin_required
def commission_type_list(request):
    company = _c(request)
    items = CommissionType.objects.filter(company=company).order_by("name")
    return render(request, "commissions_web/type_list.html", {"types": items})


@company_admin_required
def commission_type_create(request):
    company = _c(request)
    if request.method == "POST":
        form = CommissionTypeForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions_web:commission_type_list")
    else:
        form = CommissionTypeForm(company=company)
    return render(request, "commissions_web/type_form.html", {"form": form, "title": "Nuevo tipo"})


@company_admin_required
def commission_type_edit(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(CommissionType, pk=pk, company=company)
    if request.method == "POST":
        form = CommissionTypeForm(request.POST, instance=obj, company=company)
        if form.is_valid():
            form.save()
            return redirect("commissions_web:commission_type_list")
    else:
        form = CommissionTypeForm(instance=obj, company=company)
    projects = Project.objects.filter(company=company, is_active=True)
    links = {l.project_id: l for l in ProjectCommissionType.objects.filter(commission_type=obj)}
    project_rows = [{"project": pr, "link": links.get(pr.id)} for pr in projects]
    return render(
        request,
        "commissions_web/type_detail.html",
        {"form": form, "type_obj": obj, "project_rows": project_rows},
    )


@company_admin_required
@require_POST
def project_type_toggle(request, type_pk: int, project_pk: int):
    company = _c(request)
    ct = get_object_or_404(CommissionType, pk=type_pk, company=company)
    pr = get_object_or_404(Project, pk=project_pk, company=company)
    link, created = ProjectCommissionType.objects.get_or_create(
        project=pr,
        commission_type=ct,
        defaults={"is_active": True},
    )
    if created:
        link.is_active = True
    else:
        link.is_active = not link.is_active
    link.save(update_fields=["is_active"])
    return redirect("commissions_web:commission_type_edit", pk=type_pk)
