"""URL pubblici di `apps.core` (F7)."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("methodology/", views.methodology, name="methodology"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("privacy/", views.privacy, name="privacy"),
    path("countries/", views.countries, name="countries"),
    # Pass F-product-country-landing-seo-multilang: 5 landing per paese.
    path("countries/italy/", views.country_italy, name="country_italy"),
    path("countries/france/", views.country_france, name="country_france"),
    path("countries/belgium/", views.country_belgium, name="country_belgium"),
    path("countries/morocco/", views.country_morocco, name="country_morocco"),
    path("countries/tunisia/", views.country_tunisia, name="country_tunisia"),
    path("case-types/", views.case_types, name="case_types"),
    path("staff/project-status/", views.project_status, name="project_status"),
]
