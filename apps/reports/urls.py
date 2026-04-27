"""URL config per `apps.reports`."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path(
        "reports/simulation/<uuid:public_id>/pdf/",
        views.simulation_pdf_download,
        name="simulation_pdf",
    ),
]
