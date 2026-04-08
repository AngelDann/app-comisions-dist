import hashlib

from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from apps.companies.models import Company

User = get_user_model()

# User.username tiene max_length=150; correos más largos usan un identificador derivado.
USERNAME_MAX_LEN = 150


def username_from_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) <= USERNAME_MAX_LEN:
        return normalized
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"u_{digest}"[:USERNAME_MAX_LEN]


class EmailAuthenticationForm(AuthenticationForm):
    """Login de la app: el campo interno sigue llamándose *username* para compatibilidad con Django."""

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )


class EmailAdminAuthenticationForm(AdminAuthenticationForm):
    """Login del admin de Django con correo en lugar de nombre de usuario."""

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )


class CompanyRegistrationForm(forms.Form):
    """Alta de compañía nueva + primer usuario administrador."""

    company_name = forms.CharField(
        max_length=255,
        label="Nombre de la compañía",
        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
    )
    company_slug = forms.SlugField(
        required=False,
        max_length=80,
        label="Identificador (URL)",
        help_text="Opcional. Solo letras, números y guiones. Si lo dejas vacío se genera a partir del nombre.",
        widget=forms.TextInput(attrs={"placeholder": "ej. mi-empresa"}),
    )
    base_currency = forms.CharField(
        max_length=3,
        min_length=3,
        initial="MXN",
        label="Moneda base (ISO 4217)",
        widget=forms.TextInput(attrs={"class": "text-uppercase", "maxlength": "3"}),
    )

    email = forms.EmailField(
        label="Correo electrónico (será tu usuario de acceso)",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_base_currency(self):
        return self.cleaned_data["base_currency"].upper()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        uname = username_from_email(email)
        if User.objects.filter(username__iexact=uname).exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        return email

    def clean(self):
        data = super().clean()
        if not data:
            return data
        p1 = data.get("password1")
        p2 = data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if p1:
            try:
                validate_password(p1)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return data

    def clean_company_slug(self):
        slug = (self.cleaned_data.get("company_slug") or "").strip()
        return slug or None

    def resolve_slug(self) -> str:
        name = self.cleaned_data["company_name"]
        slug = self.cleaned_data.get("company_slug")
        if not slug:
            slug = slugify(name) or "empresa"
        base = slug
        candidate = base
        n = 0
        while Company.objects.filter(slug=candidate).exists():
            n += 1
            candidate = f"{base}-{n}"
        return candidate
