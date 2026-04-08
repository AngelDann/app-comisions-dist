from django.urls import path

from apps.projects import views_web

app_name = "projects"

urlpatterns = [
    path("projects/", views_web.project_list, name="project_list"),
    path("projects/nuevo/", views_web.project_create, name="project_create"),
    path("projects/<int:pk>/", views_web.project_edit, name="project_edit"),
    path("projects/<int:pk>/eliminar/", views_web.project_delete, name="project_delete"),
    path("projects/<int:pk>/equipo/", views_web.project_add_team, name="project_add_team"),
    path("projects/<int:pk>/equipo/<int:team_id>/quitar/", views_web.project_remove_team, name="project_remove_team"),
    path("equipos/", views_web.team_list, name="team_list"),
    path("equipos/nuevo/", views_web.team_create, name="team_create"),
    path("equipos/<int:pk>/", views_web.team_edit, name="team_edit"),
    path("equipos/<int:pk>/eliminar/", views_web.team_delete, name="team_delete"),
]
