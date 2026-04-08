from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts.models import MembershipRole, UserMembership, UserTeamScope
from apps.projects.models import Team

User = get_user_model()


class CreateMemberForm(forms.Form):
    email = forms.EmailField(label="Correo (será el usuario de acceso)")
    first_name = forms.CharField(
        label="Nombre (empleado / comisiones)",
        required=False,
        help_text="Opcional: si lo omites, se inferirá a partir del correo.",
    )
    last_name = forms.CharField(label="Apellidos (empleado / comisiones)", required=False)
    employee_code = forms.CharField(
        label="Código de empleado",
        required=False,
        help_text="Opcional; por defecto se usa la parte local del correo.",
    )
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Rol en la compañía")
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        label="Equipos",
        widget=forms.CheckboxSelectMultiple,
    )
    team_leads = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        label="Líder en estos equipos (permisos elevados solo ahí)",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    create_employee = forms.TypedChoiceField(
        label="Ficha de empleado",
        coerce=lambda x: x == "1",
        choices=[
            (
                "1",
                "Sí: crear empleado vinculado (mismos equipos; necesario para eventos de comisión a su nombre)",
            ),
            ("0", "No: solo acceso al sistema, sin ficha de empleado"),
        ],
        initial="1",
        widget=forms.RadioSelect,
    )

    def __init__(self, editor, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._editor = editor
        self._company = company
        teams = Team.objects.filter(company=company, is_active=True).order_by("name")
        self.fields["teams"].queryset = teams
        self.fields["team_leads"].queryset = teams
        choices = [x for x in MembershipRole.choices if x[0] != MembershipRole.SUPER_ADMIN.value]
        from apps.accounts.permissions import can_assign_company_admin_role

        if not can_assign_company_admin_role(editor, company):
            choices = [x for x in choices if x[0] != MembershipRole.COMPANY_ADMIN.value]
        self.fields["role"].choices = choices
        for name, f in self.fields.items():
            if name in ("teams", "team_leads", "create_employee"):
                continue
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault("class", "form-select")
            elif not isinstance(f.widget, forms.RadioSelect):
                f.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(
            username__iexact=email
        ).exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        return email

    def clean(self):
        data = super().clean()
        if not data:
            return data
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if p1:
            try:
                validate_password(p1)
            except ValidationError as exc:
                self.add_error("password1", exc)
        teams = set(data.get("teams") or [])
        leads = set(data.get("team_leads") or [])
        if leads and not leads.issubset(teams):
            self.add_error("team_leads", "Solo puedes marcar líder en equipos que también asignaste al miembro.")
        return data


class EditMemberForm(forms.Form):
    first_name = forms.CharField(
        label="Nombre (empleado)",
        required=False,
        help_text="Si creas o actualizas la ficha de empleado, se usará este nombre si lo indicas.",
    )
    last_name = forms.CharField(label="Apellidos (empleado)", required=False)
    employee_code = forms.CharField(label="Código de empleado", required=False)
    link_employee = forms.TypedChoiceField(
        label="Ficha de empleado",
        coerce=lambda x: x == "1",
        choices=[
            (
                "1",
                "Sincronizar: crear empleado si no existe y alinear sus equipos con el acceso",
            ),
            ("0", "No modificar la ficha de empleado"),
        ],
        initial="1",
        widget=forms.RadioSelect,
    )
    role = forms.ChoiceField(label="Rol en la compañía")
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        label="Equipos",
        widget=forms.CheckboxSelectMultiple,
    )
    team_leads = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        label="Líder en estos equipos",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, editor, company, membership: UserMembership, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._membership = membership
        self._company = company
        self._editor = editor
        teams = Team.objects.filter(company=company, is_active=True).order_by("name")
        self.fields["teams"].queryset = teams
        self.fields["team_leads"].queryset = teams
        choices = [x for x in MembershipRole.choices if x[0] != MembershipRole.SUPER_ADMIN.value]
        from apps.accounts.permissions import can_assign_company_admin_role

        if not can_assign_company_admin_role(editor, company):
            choices = [x for x in choices if x[0] != MembershipRole.COMPANY_ADMIN.value]
        self.fields["role"].choices = choices
        self.fields["role"].initial = membership.role
        scoped = UserTeamScope.objects.filter(user=membership.user, company=company)
        self.fields["teams"].initial = list(scoped.values_list("team_id", flat=True))
        self.fields["team_leads"].initial = list(
            scoped.filter(is_team_lead=True).values_list("team_id", flat=True)
        )
        from apps.staff.models import Employee

        emp = Employee.objects.filter(company=company, user=membership.user).first()
        if emp:
            self.fields["first_name"].initial = emp.first_name
            self.fields["last_name"].initial = emp.last_name
            self.fields["employee_code"].initial = emp.employee_code
        for name, f in self.fields.items():
            if name in ("teams", "team_leads", "link_employee"):
                continue
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault("class", "form-select")
            elif not isinstance(f.widget, forms.RadioSelect):
                f.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        data = super().clean()
        teams = set(data.get("teams") or [])
        leads = set(data.get("team_leads") or [])
        if leads and not leads.issubset(teams):
            self.add_error("team_leads", "Líder solo en equipos asignados.")
        if self._membership.user.is_superuser:
            raise ValidationError("No se puede editar un superusuario desde aquí.")
        return data
