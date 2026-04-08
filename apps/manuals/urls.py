from django.urls import path

from apps.manuals import views

app_name = "manuals"

urlpatterns = [
    path("", views.manual_index, name="index"),
    path("<slug:slug>/", views.manual_page, name="page"),
]
