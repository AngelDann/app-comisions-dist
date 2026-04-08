from django.contrib import admin

from apps.fx.models import FxRate


@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):
    list_display = ("company", "currency_code", "rate_date", "value", "source")
    list_filter = ("company", "currency_code")
