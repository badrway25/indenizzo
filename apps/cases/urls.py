"""URL pubblici di `apps.cases` — wizard simulazione."""

from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    path("wizard/", views.wizard_start, name="wizard_start"),
    path(
        "wizard/it/road-accident/",
        views.wizard_italy_road_accident,
        name="wizard_italy_road_accident",
    ),
    path(
        "wizard/result/<uuid:public_id>/",
        views.wizard_result,
        name="wizard_result",
    ),
]
