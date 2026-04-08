from django.contrib import admin

from apps.commissions.models import (
    Adjustment,
    CalculationRun,
    CommissionEvent,
    CommissionLine,
    CommissionPeriod,
    CommissionType,
    ProjectCommissionType,
)


@admin.register(CommissionType)
class CommissionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "slug")
    list_filter = ("company",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProjectCommissionType)
class ProjectCommissionTypeAdmin(admin.ModelAdmin):
    list_display = ("project", "commission_type", "is_active")
    list_filter = ("project__company", "is_active")


@admin.register(CommissionPeriod)
class CommissionPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "start_date", "end_date", "state", "is_locked")
    list_filter = ("company", "state")


@admin.register(CommissionEvent)
class CommissionEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "period",
        "project",
        "employee",
        "event_kind",
        "occurred_on",
        "amount_usd",
        "fx_rate",
    )
    list_filter = ("company", "project", "period")


@admin.register(CommissionLine)
class CommissionLineAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "amount", "state", "company", "rule_id")
    list_filter = ("company", "state")


@admin.register(CalculationRun)
class CalculationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "period", "status", "started_at", "finished_at")


@admin.register(Adjustment)
class AdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "amount", "company", "line", "event")
