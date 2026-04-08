from django.urls import path

from apps.staff import views_web

app_name = "staff_web"

urlpatterns = [
    path("employees/", views_web.employee_list, name="employee_list"),
    path("employees/nuevo/", views_web.employee_create, name="employee_create"),
    path("employees/<int:pk>/", views_web.employee_edit, name="employee_edit"),
    path("employees/<int:pk>/eliminar/", views_web.employee_delete, name="employee_delete"),
]
