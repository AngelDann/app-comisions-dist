from django.urls import path

from apps.accounts import views
from apps.accounts import views_people
from apps.accounts import views_settings

app_name = "accounts"

urlpatterns = [
    path("ajustes/cuenta/", views_settings.settings_account, name="settings_account"),
    path("ajustes/perfil/", views_settings.settings_profile, name="settings_profile"),
    path("ajustes/empresa/", views_settings.settings_company, name="settings_company"),
    path("usuarios/", views_people.people_list, name="people_list"),
    path("usuarios/nuevo/", views_people.people_create, name="people_create"),
    path("usuarios/<int:pk>/editar/", views_people.people_edit, name="people_edit"),
    path("usuarios/<int:pk>/eliminar/", views_people.people_delete, name="people_delete"),
    path("registrar-empresa/", views.register_company, name="register_company"),
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.app_logout, name="logout"),
    path("select-company/", views.SelectCompanyView.as_view(), name="select_company"),
    path("switch-company/<int:pk>/", views.switch_company, name="switch_company"),
]
