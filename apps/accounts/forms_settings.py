from django import forms
from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.staff.models import Employee

User = get_user_model()


class AccountUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]


class ProfileEmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["first_name", "last_name", "employee_code"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "employee_code": "Código de empleado",
        }


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "base_currency"]
