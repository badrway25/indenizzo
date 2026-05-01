from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.sitemaps import SITEMAPS
from apps.core.views import healthz

urlpatterns = [
    # /healthz/ è OUT of i18n_patterns: il monitoring deve hittare
    # un path stabile e indipendente dalla lingua del browser.
    path("healthz/", healthz, name="healthz"),
    # /sitemap.xml è OUT of i18n_patterns: i motori di ricerca
    # consumano un singolo XML neutrale; gli URL al suo interno sono
    # già la versione default (no prefisso) e i bot scoprono le altre
    # lingue via hreflang già presenti in <head>.
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
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
