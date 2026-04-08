from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        from django.contrib import admin

        from apps.accounts.forms import EmailAdminAuthenticationForm

        admin.site.login_form = EmailAdminAuthenticationForm
