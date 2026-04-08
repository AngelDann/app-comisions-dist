from django import forms as django_forms
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.forms import CompanyRegistrationForm, EmailAuthenticationForm, username_from_email
from apps.accounts.models import MembershipRole, UserMembership
from apps.companies.models import Company

User = get_user_model()


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = EmailAuthenticationForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for _name, field in form.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
        return form


def app_logout(request):
    logout(request)
    return redirect("accounts:login")


def register_company(request):
    """Registro público: nueva Company + usuario administrador."""
    if getattr(settings, "ALLOW_COMPANY_REGISTRATION", True) is False:
        return render(
            request,
            "accounts/registration_closed.html",
            status=403,
        )
    if request.user.is_authenticated:
        return redirect("commissions:dashboard")

    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                slug = form.resolve_slug()
                company = Company.objects.create(
                    name=form.cleaned_data["company_name"],
                    slug=slug,
                    base_currency=form.cleaned_data["base_currency"],
                    is_active=True,
                )
                email = form.cleaned_data["email"]
                user = User.objects.create_user(
                    username=username_from_email(email),
                    email=email,
                    password=form.cleaned_data["password1"],
                )
                UserMembership.objects.create(
                    user=user,
                    company=company,
                    role=MembershipRole.COMPANY_ADMIN,
                    is_primary=True,
                )
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
            request.session["active_company_id"] = company.id
            return redirect("commissions:dashboard")
    else:
        form = CompanyRegistrationForm()

    for _name, field in form.fields.items():
        w = field.widget
        if isinstance(
            field.widget,
            (django_forms.TextInput, django_forms.EmailInput, django_forms.PasswordInput),
        ):
            w.attrs.setdefault("class", "form-control")
        if isinstance(field.widget, django_forms.Select):
            w.attrs.setdefault("class", "form-select")

    return render(request, "accounts/register_company.html", {"form": form})


class SelectCompanyView(View):
    """Superusuario o usuario sin company en sesión elige compañía activa."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        companies = Company.objects.filter(is_active=True).order_by("name")
        if not request.user.is_superuser:
            from apps.accounts.models import UserMembership

            companies = Company.objects.filter(
                id__in=UserMembership.objects.filter(user=request.user).values_list(
                    "company_id", flat=True
                ),
                is_active=True,
            ).order_by("name")
        return render(
            request,
            "accounts/select_company.html",
            {"companies": companies},
        )

    def post(self, request):
        cid = request.POST.get("company_id")
        if cid:
            request.session["active_company_id"] = int(cid)
        return redirect("commissions:dashboard")


def switch_company(request, pk: int):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    company = Company.objects.filter(pk=pk, is_active=True).first()
    if not company:
        return redirect("accounts:select_company")
    if request.user.is_superuser:
        request.session["active_company_id"] = company.id
        return redirect("commissions:dashboard")
    from apps.accounts.middleware import user_has_company_access

    if user_has_company_access(request.user, company):
        request.session["active_company_id"] = company.id
    return redirect("commissions:dashboard")
