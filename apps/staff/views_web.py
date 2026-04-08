from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import company_admin_required
from apps.staff.forms_web import EmployeeForm
from apps.staff.models import Employee


def _c(request):
    return request.company


@company_admin_required
def employee_list(request):
    company = _c(request)
    items = Employee.objects.filter(company=company).prefetch_related("teams", "projects").order_by(
        "last_name", "first_name"
    )
    return render(request, "staff/employee_list.html", {"employees": items})


@company_admin_required
def employee_create(request):
    company = _c(request)
    if request.method == "POST":
        form = EmployeeForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("staff_web:employee_list")
    else:
        form = EmployeeForm(company=company)
    return render(request, "staff/employee_form.html", {"form": form, "title": "Nuevo empleado"})


@company_admin_required
def employee_edit(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Employee, pk=pk, company=company)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=obj, company=company)
        if form.is_valid():
            form.save()
            return redirect("staff_web:employee_list")
    else:
        form = EmployeeForm(instance=obj, company=company)
    return render(request, "staff/employee_form.html", {"form": form, "title": f"Editar {obj}"})


@company_admin_required
@require_POST
def employee_delete(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Employee, pk=pk, company=company)
    obj.delete()
    return redirect("staff_web:employee_list")
