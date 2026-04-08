from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.urls import reverse

from apps.accounts.decorators import company_admin_required
from apps.accounts.employee_sync import link_or_sync_employee_for_user
from apps.accounts.forms_people import CreateMemberForm, EditMemberForm
from apps.accounts.models import UserMembership, UserTeamScope
from apps.accounts.permissions import (
    can_access_people_module,
    can_manage_company_users,
    manageable_memberships_queryset,
)
from apps.staff.models import Employee

User = get_user_model()


def people_module_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser and request.company is None:
            return redirect(reverse("accounts:select_company"))
        if request.company is None and not request.user.is_superuser:
            return redirect(reverse("accounts:select_company"))
        if not can_access_people_module(request.user, request.company):
            messages.warning(
                request,
                "No tienes acceso al módulo de usuarios para tu perfil actual.",
            )
            return redirect("commissions:dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _c(request):
    return request.company


@people_module_required
def people_list(request):
    company = _c(request)
    memberships = manageable_memberships_queryset(request.user, company)
    member_rows = []
    for m in memberships:
        scopes = list(
            UserTeamScope.objects.filter(user=m.user, company=company).select_related("team")
        )
        has_employee = Employee.objects.filter(company=company, user=m.user).exists()
        member_rows.append({"membership": m, "scopes": scopes, "has_employee": has_employee})
    return render(
        request,
        "accounts/people_list.html",
        {
            "member_rows": member_rows,
            "can_create": can_manage_company_users(request.user, company),
            "can_edit": can_manage_company_users(request.user, company),
        },
    )


@company_admin_required
def people_create(request):
    company = _c(request)
    if request.method == "POST":
        form = CreateMemberForm(request.user, company, request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=form.cleaned_data["password1"],
                )
                UserMembership.objects.create(
                    user=user,
                    company=company,
                    role=form.cleaned_data["role"],
                    is_primary=True,
                )
                teams = form.cleaned_data["teams"]
                leads = set(form.cleaned_data.get("team_leads") or [])
                for t in teams:
                    UserTeamScope.objects.create(
                        user=user,
                        company=company,
                        team=t,
                        is_team_lead=t in leads,
                    )
                link_or_sync_employee_for_user(
                    company=company,
                    user=user,
                    teams=teams,
                    enabled=form.cleaned_data["create_employee"],
                    first_name=form.cleaned_data.get("first_name") or "",
                    last_name=form.cleaned_data.get("last_name") or "",
                    employee_code=form.cleaned_data.get("employee_code") or "",
                )
            return redirect("accounts:people_list")
    else:
        form = CreateMemberForm(request.user, company)
    return render(request, "accounts/people_form.html", {"form": form, "title": "Nuevo miembro"})


@company_admin_required
def people_edit(request, pk: int):
    company = _c(request)
    membership = get_object_or_404(
        UserMembership.objects.select_related("user"),
        pk=pk,
        company=company,
    )
    if membership.user.is_superuser:
        return HttpResponseForbidden("No editable.")
    if request.method == "POST":
        form = EditMemberForm(request.user, company, membership, request.POST)
        if form.is_valid():
            membership.role = form.cleaned_data["role"]
            membership.save(update_fields=["role"])
            teams = set(form.cleaned_data["teams"])
            leads = set(form.cleaned_data.get("team_leads") or [])
            UserTeamScope.objects.filter(user=membership.user, company=company).delete()
            for t in teams:
                UserTeamScope.objects.create(
                    user=membership.user,
                    company=company,
                    team=t,
                    is_team_lead=t in leads,
                )
            link_or_sync_employee_for_user(
                company=company,
                user=membership.user,
                teams=teams,
                enabled=form.cleaned_data["link_employee"],
                first_name=form.cleaned_data.get("first_name") or "",
                last_name=form.cleaned_data.get("last_name") or "",
                employee_code=form.cleaned_data.get("employee_code") or "",
            )
            return redirect("accounts:people_list")
    else:
        form = EditMemberForm(request.user, company, membership)
    return render(
        request,
        "accounts/people_edit.html",
        {"form": form, "membership": membership, "title": f"Editar {membership.user.email}"},
    )


@company_admin_required
@require_POST
def people_delete(request, pk: int):
    company = _c(request)
    membership = get_object_or_404(
        UserMembership.objects.select_related("user"),
        pk=pk,
        company=company,
    )
    if membership.user == request.user:
        return HttpResponseForbidden("No puedes eliminar tu propia membresía.")
    if membership.user.is_superuser:
        return HttpResponseForbidden("No editable.")
    user = membership.user
    UserTeamScope.objects.filter(user=user, company=company).delete()
    membership.delete()
    remaining = UserMembership.objects.filter(user=user).exists()
    if not remaining:
        user.delete()
    return redirect("accounts:people_list")
