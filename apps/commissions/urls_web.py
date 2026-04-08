from django.urls import path

from apps.commissions import web_views

app_name = "commissions_web"

urlpatterns = [
    path("periods/", web_views.period_list, name="period_list"),
    path("periods/nuevo/", web_views.period_create, name="period_create"),
    path("periods/<int:pk>/", web_views.period_edit, name="period_edit"),
    path("periods/<int:pk>/eliminar/", web_views.period_delete, name="period_delete"),
    path("commission-types/", web_views.commission_type_list, name="commission_type_list"),
    path("commission-types/nuevo/", web_views.commission_type_create, name="commission_type_create"),
    path("commission-types/<int:pk>/", web_views.commission_type_edit, name="commission_type_edit"),
    path(
        "commission-types/<int:type_pk>/proyecto/<int:project_pk>/toggle/",
        web_views.project_type_toggle,
        name="project_type_toggle",
    ),
]
