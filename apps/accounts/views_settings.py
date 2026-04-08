from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from apps.accounts.decorators import company_admin_required, login_and_company_required
from apps.accounts.forms_settings import AccountUserForm, CompanySettingsForm, ProfileEmployeeForm
from apps.accounts.middleware import is_company_admin
from apps.staff.models import Employee


def _password_form_widgets(form: PasswordChangeForm) -> None:
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")


def _settings_context(request, active: str) -> dict:
    company = request.company
    return {
        "settings_active": active,
        "nav_is_company_admin": bool(company and is_company_admin(request.user, company)),
    }


@login_and_company_required
def settings_account(request):
    user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "password":
            pw_form = PasswordChangeForm(user, request.POST)
            _password_form_widgets(pw_form)
            user_form = AccountUserForm(instance=user)
            for f in user_form.fields.values():
                f.widget.attrs.setdefault("class", "form-control")
            if pw_form.is_valid():
                pw_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Contraseña actualizada.")
                return redirect("accounts:settings_account")
        else:
            user_form = AccountUserForm(request.POST, instance=user)
            for f in user_form.fields.values():
                f.widget.attrs.setdefault("class", "form-control")
            pw_form = PasswordChangeForm(user)
            _password_form_widgets(pw_form)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Datos guardados.")
                return redirect("accounts:settings_account")
    else:
        user_form = AccountUserForm(instance=user)
        for f in user_form.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
        pw_form = PasswordChangeForm(user)
        _password_form_widgets(pw_form)

    ctx = _settings_context(request, "account")
    ctx.update(
        {
            "user_form": user_form,
            "password_form": pw_form,
            "settings_account_email": user.email or "—",
        }
    )
    return render(request, "accounts/settings_account.html", ctx)


@login_and_company_required
def settings_profile(request):
    company = request.company
    assert company is not None
    employee = Employee.objects.filter(company=company, user=request.user).first()

    if request.method == "POST":
        if employee is None:
            messages.error(request, "No hay ficha de empleado vinculada a tu usuario.")
            return redirect("accounts:settings_profile")
        form = ProfileEmployeeForm(request.POST, instance=employee)
        for f in form.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("accounts:settings_profile")
    else:
        form = (
            ProfileEmployeeForm(instance=employee)
            if employee
            else None
        )
        if form:
            for f in form.fields.values():
                f.widget.attrs.setdefault("class", "form-control")

    ctx = _settings_context(request, "profile")
    ctx.update({"employee": employee, "profile_form": form})
    return render(request, "accounts/settings_profile.html", ctx)


@company_admin_required
def settings_company(request):
    company = request.company
    assert company is not None
    if request.method == "POST":
        form = CompanySettingsForm(request.POST, instance=company)
        for name, f in form.fields.items():
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault("class", "form-select")
            else:
                f.widget.attrs.setdefault("class", "form-control")
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de la empresa guardados.")
            return redirect("accounts:settings_company")
    else:
        form = CompanySettingsForm(instance=company)
        for name, f in form.fields.items():
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault("class", "form-select")
            else:
                f.widget.attrs.setdefault("class", "form-control")

    ctx = _settings_context(request, "company")
    ctx.update({"company_form": form})
    return render(request, "accounts/settings_company.html", ctx)
