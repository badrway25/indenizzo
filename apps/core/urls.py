"""URL pubblici di `apps.core` (F7)."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("methodology/", views.methodology, name="methodology"),
    # P40: public documentation hub (plain-language guides; indexable, multilingual).
    path("documentation/", views.documentation, name="documentation"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("privacy/", views.privacy, name="privacy"),
    # Workstream-3 public content pages (indexable, multilingual — see the
    # hreflang allowlist in context_processors.py and StaticSitemap).
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("services/", views.services, name="services"),
    path("faq/", views.faq, name="faq"),
    path("about/", views.about, name="about"),
    # Arabic/French-speaking community landing (Ta3ouid).
    path("ta3ouid/", views.community, name="community"),
    path("countries/", views.countries, name="countries"),
    # E1: leak-safe public readiness state per country (JSON). No internal detail.
    path("countries/readiness.json", views.country_readiness_json, name="country_readiness_json"),
    # Pass F-product-country-landing-seo-multilang: 5 landing per paese.
    path("countries/italy/", views.country_italy, name="country_italy"),
    path("countries/france/", views.country_france, name="country_france"),
    path("countries/belgium/", views.country_belgium, name="country_belgium"),
    path("countries/morocco/", views.country_morocco, name="country_morocco"),
    path("countries/tunisia/", views.country_tunisia, name="country_tunisia"),
    path("case-types/", views.case_types, name="case_types"),
    # P29: official source library + smart public search (indexable, multilingual).
    path("sources/", views.sources, name="sources"),
    path("sources/<slug:slug>/", views.source_detail, name="source_detail"),
    path("search/", views.search, name="search"),
    # P30: intelligent document intake (landing + secure stateless upload).
    path("documents/", views.documents, name="documents"),
    path("documents/upload/", views.documents_upload, name="documents_upload"),
    # P15: country × category guided router — pick country → category → route.
    path("guided/", views.guided_router, name="guided_router"),
    # P15: guided documental pre-check flows for non-numeric sections.
    path("precheck/<slug:slug>/", views.precheck, name="precheck"),
    # F-product-4-case-type-landings: per-case-type SEO/product
    # landings. Slug is resolved against `apps.core.case_type_landings.LANDINGS`;
    # an unknown slug returns 404 (no DB lookup). See
    # `docs/product/CASE_TYPE_LANDING_AUDIT_2026-05-12.md`.
    path(
        "case-types/<slug:slug>/",
        views.case_type_landing,
        name="case_type_landing",
    ),
    path("staff/project-status/", views.project_status, name="project_status"),
]
