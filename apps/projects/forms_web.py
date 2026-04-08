from django import forms
from django.utils.text import slugify

from apps.projects.models import Project, ProjectTeam, Team


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "slug", "description", "is_active"]
        labels = {
            "name": "Nombre",
            "slug": "Identificador (slug)",
            "description": "Descripción",
            "is_active": "Activo",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-check-input")
                continue
            f.widget.attrs.setdefault("class", "form-control")
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or ""
        if not slug and self.cleaned_data.get("name"):
            slug = slugify(self.cleaned_data["name"]) or "proyecto"
        base = slug
        qs = Project.objects.filter(company=self.instance.company)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        candidate = base
        n = 0
        while qs.filter(slug=candidate).exists():
            n += 1
            candidate = f"{base}-{n}"
        return candidate


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "slug", "is_active"]
        labels = {
            "name": "Nombre",
            "slug": "Identificador (slug)",
            "is_active": "Activo",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-check-input")
                continue
            f.widget.attrs.setdefault("class", "form-control")
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or ""
        if not slug and self.cleaned_data.get("name"):
            slug = slugify(self.cleaned_data["name"]) or "equipo"
        base = slug
        qs = Team.objects.filter(company=self.instance.company)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        candidate = base
        n = 0
        while qs.filter(slug=candidate).exists():
            n += 1
            candidate = f"{base}-{n}"
        return candidate


class ProjectTeamForm(forms.ModelForm):
    class Meta:
        model = ProjectTeam
        fields = ["team", "sort_order", "is_active"]

    def __init__(self, *args, company=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.filter(company=company, is_active=True)
        self.fields["team"].widget.attrs.setdefault("class", "form-select")
        self.fields["sort_order"].widget.attrs.setdefault("class", "form-control")
        self.fields["is_active"].widget.attrs.setdefault("class", "form-check-input")
