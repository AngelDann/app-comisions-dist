from django.contrib import admin

from apps.projects.models import Project, ProjectTeam, Team


class ProjectTeamInline(admin.TabularInline):
    model = ProjectTeam
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "slug", "is_active")
    list_filter = ("company", "is_active")
    inlines = [ProjectTeamInline]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "slug", "is_active")
    list_filter = ("company", "is_active")
    prepopulated_fields = {"slug": ("name",)}
