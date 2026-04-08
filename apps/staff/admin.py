from django.contrib import admin

from apps.staff.models import Employee, EmployeeProject, EmployeeTeam


class EmployeeTeamInline(admin.TabularInline):
    model = EmployeeTeam
    extra = 1


class EmployeeProjectInline(admin.TabularInline):
    model = EmployeeProject
    extra = 1


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "company", "employee_code", "is_active")
    list_filter = ("company", "is_active")
    inlines = [EmployeeTeamInline, EmployeeProjectInline]
