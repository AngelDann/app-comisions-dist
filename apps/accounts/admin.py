from django.contrib import admin

from apps.accounts.models import UserMembership, UserProjectScope, UserTeamScope


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_primary")
    list_filter = ("role", "company")


@admin.register(UserProjectScope)
class UserProjectScopeAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "project")


@admin.register(UserTeamScope)
class UserTeamScopeAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "team", "is_team_lead")
    list_filter = ("is_team_lead", "company")
