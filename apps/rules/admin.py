from django.contrib import admin

from apps.rules.models import (
    CommissionPlan,
    CommissionPlanEmployee,
    CommissionPlanTeam,
    CommissionRule,
    RuleFieldDefinition,
)


class CommissionPlanTeamInline(admin.TabularInline):
    model = CommissionPlanTeam
    extra = 0


class CommissionPlanEmployeeInline(admin.TabularInline):
    model = CommissionPlanEmployee
    extra = 0


@admin.register(RuleFieldDefinition)
class RuleFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "company", "data_type")


@admin.register(CommissionPlan)
class CommissionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "project", "is_global", "is_active", "valid_from", "valid_to")
    list_filter = ("company", "is_global", "is_active")
    inlines = [CommissionPlanTeamInline, CommissionPlanEmployeeInline]


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "commission_type", "plan", "priority", "action_type", "is_active")
    list_filter = ("company", "is_active", "action_type")
    raw_id_fields = ("plan",)

