from django import forms

from apps.staff.models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["first_name", "last_name", "employee_code", "user", "is_active", "teams", "projects"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "employee_code": "Código de empleado",
            "user": "Usuario",
            "is_active": "Activo",
            "teams": "Equipos",
            "projects": "Proyectos",
        }
        widgets = {
            "teams": forms.CheckboxSelectMultiple,
            "projects": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        from apps.projects.models import Project, Team

        self.fields["teams"].queryset = Team.objects.filter(company=company, is_active=True)
        self.fields["projects"].queryset = Project.objects.filter(company=company, is_active=True)
        self.fields["user"].queryset = self.fields["user"].queryset.none()  # type: ignore
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.fields["user"].queryset = User.objects.filter(
            memberships__company=company
        ).distinct()
        self.fields["user"].required = False
        for name, f in self.fields.items():
            if name in ("teams", "projects"):
                continue
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-check-input")
                continue
            f.widget.attrs.setdefault("class", "form-control")
            if isinstance(f.widget, forms.Select):
                f.widget.attrs["class"] = "form-select"
