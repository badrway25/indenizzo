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
        "wizard/it/medical-malpractice/",
        views.wizard_italy_medical,
        name="wizard_italy_medical",
    ),
    path(
        "wizard/fr/road-accident/",
        views.wizard_france_road_accident,
        name="wizard_france_road_accident",
    ),
    path(
        "wizard/be/road-accident/",
        views.wizard_belgium_road_accident,
        name="wizard_belgium_road_accident",
    ),
    path(
        "wizard/ma/inheritance/",
        views.wizard_morocco_inheritance,
        name="wizard_morocco_inheritance",
    ),
    path(
        "wizard/tn/inheritance/",
        views.wizard_tunisia_inheritance,
        name="wizard_tunisia_inheritance",
    ),
    path(
        "wizard/result/<uuid:public_id>/",
        views.wizard_result,
        name="wizard_result",
    ),
]
