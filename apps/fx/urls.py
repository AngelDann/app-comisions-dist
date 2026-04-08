from django.urls import path

from apps.fx import views

app_name = "fx"

urlpatterns = [
    path("", views.fx_list, name="list"),
    path("crear/", views.fx_create, name="create"),
    path("<int:pk>/patch/", views.fx_patch, name="patch"),
    path("<int:pk>/eliminar/", views.fx_delete, name="delete"),
]
