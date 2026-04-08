from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path


def landing_page(request):
    if request.user.is_authenticated:
        from apps.commissions.views import dashboard

        return dashboard(request)
    return render(request, "landing.html")


urlpatterns = [
    path("", landing_page, name="landing"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("fx/", include("apps.fx.urls")),
    path("", include("apps.projects.urls_web")),
    path("", include("apps.commissions.urls_web")),
    path("", include("apps.staff.urls_web")),
    path("", include("apps.commissions.urls")),
    path("manuales/", include("apps.manuals.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
