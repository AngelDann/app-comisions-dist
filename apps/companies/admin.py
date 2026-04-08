from django.contrib import admin

from apps.companies.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "base_currency", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
