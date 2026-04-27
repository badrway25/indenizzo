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
    path("case-types/", views.case_types, name="case_types"),
    path("staff/project-status/", views.project_status, name="project_status"),
]
