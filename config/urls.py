from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from apps.core.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("", home, name="home"),
    prefix_default_language=False,
)
