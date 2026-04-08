from django import forms
from django.core.exceptions import ValidationError

from apps.commissions.date_fields import bind_iso_html_dates
from apps.commissions.models import CommissionEvent, CommissionPeriod, CommissionType, ProjectCommissionType
from apps.fx.models import FxRate
from apps.projects.models import Project, Team
from apps.staff.models import Employee


class CommissionEventForm(forms.ModelForm):
    class Meta:
        model = CommissionEvent
        fields = [
            "period",
            "project",
            "team",
            "commission_type",
            "employee",
            "event_kind",
            "occurred_on",
            "amount_usd",
            "fx_rate",
            "hours",
            "is_business_hours",
            "sales_channel",
            "notes",
        ]
        labels = {
            "period": "Periodo",
            "project": "Proyecto",
            "team": "Equipo",
            "commission_type": "Tipo de comisión",
            "employee": "Empleado",
            "event_kind": "Clase de evento",
            "occurred_on": "Fecha",
            "amount_usd": "Monto",
            "fx_rate": "Tipo de cambio",
            "hours": "Horas",
            "is_business_hours": "Horario laboral",
            "sales_channel": "Canal de ventas",
            "notes": "Notas",
        }
        widgets = {
            "occurred_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "notes": forms.HiddenInput(attrs={"id": "id_notes"}),
        }

    def __init__(self, *args, company=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        bind_iso_html_dates(self, "occurred_on")
        self.company = company
        self._user = user
        for _name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif isinstance(field.widget, (forms.Textarea,)):
                field.widget.attrs.setdefault("class", "form-control")
            elif getattr(field.widget, "input_type", None) in ("text", "number", "email", "date"):
                field.widget.attrs.setdefault("class", "form-control")
        if company and user:
            from apps.accounts.permissions import commission_scoped_projects_queryset
            from apps.accounts.permissions import commission_scoped_teams_queryset
            from apps.accounts.permissions import commission_scoped_employees_queryset

            self.fields["period"].queryset = CommissionPeriod.objects.filter(company=company).order_by(
                "-start_date"
            )
            self.fields["project"].queryset = commission_scoped_projects_queryset(user, company)
            team_base = commission_scoped_teams_queryset(user, company)
            self.fields["team"].queryset = team_base
            self.fields["employee"].queryset = commission_scoped_employees_queryset(user, company)
            proj_qs = self.fields["project"].queryset
            proj_pk = self._resolved_project_pk()
            if proj_pk:
                self.fields["team"].queryset = team_base.filter(
                    project_teams__project_id=proj_pk,
                    project_teams__is_active=True,
                ).distinct()
                type_ids = ProjectCommissionType.objects.filter(
                    project_id=proj_pk,
                    is_active=True,
                ).values_list("commission_type_id", flat=True)
            else:
                type_ids = ProjectCommissionType.objects.filter(
                    project__in=proj_qs,
                    is_active=True,
                ).values_list("commission_type_id", flat=True)
            self.fields["commission_type"].queryset = CommissionType.objects.filter(
                company=company,
                pk__in=type_ids,
            ).order_by("name")
        elif company:
            self.fields["period"].queryset = CommissionPeriod.objects.filter(company=company)
            self.fields["project"].queryset = Project.objects.filter(company=company, is_active=True)
            self.fields["team"].queryset = Team.objects.filter(company=company, is_active=True)
            self.fields["employee"].queryset = Employee.objects.filter(company=company, is_active=True)
            self.fields["commission_type"].queryset = CommissionType.objects.filter(company=company)
        if company:
            self.fields["fx_rate"].queryset = FxRate.objects.filter(company=company).order_by(
                "-rate_date", "currency_code"
            )
            self.fields["fx_rate"].required = False
            self.fields["fx_rate"].empty_label = "— Monto en moneda base (sin conversión) —"
            self.fields["amount_usd"].help_text = (
                "Si eliges un tipo de cambio, el monto está en esa moneda; "
                "si no, en la moneda base de la compañía."
            )
            self.fields["fx_rate"].help_text = (
                "Registro de la tabla de tipos de cambio. Opcional si el monto ya está en moneda base."
            )

    def clean_notes(self):
        from apps.commissions.notes import sanitize_notes

        return sanitize_notes(self.cleaned_data.get("notes") or "")

    def clean(self):
        cleaned = super().clean()
        if not self.company or not self._user:
            return cleaned
        from apps.accounts.permissions import sees_all_company_commissions, user_accessible_team_ids
        from apps.projects.models import ProjectTeam

        team = cleaned.get("team")
        project = cleaned.get("project")
        if team and not sees_all_company_commissions(self._user, self.company):
            allowed_teams = user_accessible_team_ids(self._user, self.company)
            if team.pk not in allowed_teams:
                raise ValidationError({"team": "No perteneces a este equipo."})
        if team and project:
            if not ProjectTeam.objects.filter(
                project=project, team=team, is_active=True
            ).exists():
                raise ValidationError("El equipo no participa en el proyecto seleccionado.")
        ct = cleaned.get("commission_type")
        if ct and project:
            if not ProjectCommissionType.objects.filter(
                project=project,
                commission_type=ct,
                is_active=True,
            ).exists():
                raise ValidationError(
                    {"commission_type": "Este tipo no está activo en el proyecto seleccionado."}
                )
        fx = cleaned.get("fx_rate")
        if fx and self.company and fx.company_id != self.company.pk:
            raise ValidationError({"fx_rate": "El tipo de cambio no pertenece a esta compañía."})
        return cleaned

    def _resolved_project_pk(self) -> int | None:
        if self.is_bound:
            raw = self.data.get("project")
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        val = self.initial.get("project")
        if val is None:
            return None
        if hasattr(val, "pk"):
            return int(val.pk)
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


class FilterForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(), required=False, label="Proyecto"
    )
    team = forms.ModelChoiceField(queryset=Team.objects.none(), required=False, label="Equipo")
    period = forms.ModelChoiceField(
        queryset=CommissionPeriod.objects.none(), required=False, label="Periodo"
    )

    def __init__(self, *args, company=None, user=None, **kwargs):
        from apps.accounts.permissions import commission_scoped_projects_queryset
        from apps.accounts.permissions import commission_scoped_teams_queryset

        super().__init__(*args, **kwargs)
        if company and user:
            self.fields["project"].queryset = commission_scoped_projects_queryset(user, company)
            self.fields["team"].queryset = commission_scoped_teams_queryset(user, company)
            self.fields["period"].queryset = CommissionPeriod.objects.filter(company=company).order_by(
                "-start_date"
            )
        for _name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
