from django.contrib import admin

from apps.manuals.models import ManualPage


@admin.register(ManualPage)
class ManualPageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "parent",
        "sort_order",
        "content_format",
        "is_published",
        "updated_at",
    )
    list_filter = ("is_published", "content_format")
    search_fields = ("title", "slug", "body")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("parent_id", "sort_order", "id")
    raw_id_fields = ("parent",)
