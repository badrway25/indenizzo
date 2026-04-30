from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from apps.core.views import healthz

urlpatterns = [
    # /healthz/ è OUT of i18n_patterns: il monitoring deve hittare
    # un path stabile e indipendente dalla lingua del browser.
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("", include("apps.core.urls")),
    path("", include("apps.crm.urls")),
    path("", include("apps.cases.urls")),
    path("", include("apps.reports.urls")),
    prefix_default_language=False,
)
