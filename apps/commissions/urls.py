from django.urls import path

from apps.commissions import notes, ops_views, plan_views, views

app_name = "commissions"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("registrar/", views.register_event, name="register"),
    path("evento/<int:pk>/patch/", views.event_patch, name="event_patch"),
    path("evento/<int:pk>/editar/", views.event_edit, name="event_edit"),
    path("htmx/equipos/", views.htmx_teams_for_project, name="htmx_teams"),
    path("htmx/tipos/", views.htmx_types_for_project, name="htmx_types"),
    path("htmx/registro-cascada/", views.htmx_register_cascade, name="htmx_register_cascade"),
    path("htmx/regla-accion/", ops_views.rule_action_fields_partial, name="rule_action_fields_partial"),
    path("notas/imagen/", notes.upload_note_image, name="upload_note_image"),
    path("resumen-empleados/", views.employee_summary, name="employee_summary"),
    path("exportar/resumen.xlsx", views.export_summary_xlsx, name="export_summary"),
    path("periodo/<int:pk>/recalcular/", views.recalculate_period_view, name="recalculate_period"),
    path("planes/", plan_views.plan_list, name="plan_list"),
    path("planes/nuevo/", plan_views.plan_create, name="plan_create"),
    path("planes/<int:pk>/", plan_views.plan_detail, name="plan_detail"),
    path("planes/<int:pk>/editar/", plan_views.plan_edit, name="plan_edit"),
    path("planes/<int:pk>/eliminar/", plan_views.plan_delete, name="plan_delete"),
    path("planes/<int:pk>/equipo/", plan_views.plan_team_add, name="plan_team_add"),
    path("planes/<int:pk>/empleado/", plan_views.plan_employee_add, name="plan_employee_add"),
    path(
        "planes/<int:pk>/equipo/<int:assignment_pk>/eliminar/",
        plan_views.plan_team_remove,
        name="plan_team_remove",
    ),
    path(
        "planes/<int:pk>/empleado/<int:assignment_pk>/eliminar/",
        plan_views.plan_employee_remove,
        name="plan_employee_remove",
    ),
    path("reglas/", views.rules_list_redirect, name="rules_list"),
    path("reglas/nueva/", ops_views.rule_create, name="rule_create"),
    path("reglas/<int:pk>/editar/", ops_views.rule_edit, name="rule_edit"),
    path("reglas/<int:pk>/eliminar/", ops_views.rule_delete, name="rule_delete"),
    path("ajustes/", views.adjustments_list, name="adjustments_list"),
    path("ajustes/nuevo/", ops_views.adjustment_create, name="adjustment_create"),
    path("linea/<int:pk>/detalle/", views.commission_line_detail, name="line_detail"),
    path("linea/<int:pk>/detalle-modal/", views.commission_line_detail_modal, name="line_detail_modal"),
    path("linea/<int:pk>/estado/<slug:state>/", ops_views.line_set_state, name="line_set_state"),
]
