"""
Tests F-product-public-site-qa-polish-pass2-a11y-seo.

Estendono pass1 con controlli mirati su:

1. nessuna duplicate H1 sulle pagine principali;
2. immagini Pexels servite SEMPRE da `/media/pexels/` (mai URL remoto
   `images.pexels.com`) o fallback locale;
3. `decoding="async"` presente sulle immagini hero rilevanti;
4. canonical + hreflang ancora intatti sulle 5 country landing;
5. `/sitemap.xml` 200 e contiene country landing;
6. nessuna attribution Pexels visibile;
7. nessuna `PEXELS_API_KEY` esposta nell'HTML;
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR (smoke engine,
   contratto storico mai cambiato);
9. tutte le pagine principali hanno una `<meta name="description">`
   non vuota — pass2 garantisce override per wizard / methodology /
   contact / countries / case_types che prima ereditavano il default;
10. badge contrast micro-fix: la chip "Legal sources under review"
    sui card stone/white non usa più la combinazione poco contrastata
    `text-gold-600` su `bg-gold-500/10`. Verifichiamo via marker
    `text-gold-700` introdotto da pass2.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.test import Client, override_settings

PRINCIPAL_PAGES = [
    "/",
    "/fr/",
    "/ar/",
    "/countries/",
    "/countries/italy/",
    "/fr/countries/france/",
    "/ar/countries/morocco/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/contact/",
]


def _body(client: Client, url: str) -> str:
    response = client.get(url)
    assert response.status_code == 200, f"{url} status {response.status_code}"
    return response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# 1 — exactly one <h1> per principal page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PAGES)
def test_single_h1_per_principal_page(path: str):
    body = _body(Client(), path)
    h1_count = len(re.findall(r"<h1\b", body, flags=re.IGNORECASE))
    assert h1_count == 1, f"{path} has {h1_count} <h1> tags (expected exactly 1)"


# ---------------------------------------------------------------------------
# 2 — no remote pexels images leaked in public HTML
# ---------------------------------------------------------------------------

REMOTE_PEXELS_PATTERNS = [
    re.compile(r"https?://images\.pexels\.com/", re.IGNORECASE),
    re.compile(r"https?://www\.pexels\.com/[^\"'\s]*\.jpe?g", re.IGNORECASE),
]


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PAGES)
def test_no_remote_pexels_image_url(path: str):
    body = _body(Client(), path)
    for pat in REMOTE_PEXELS_PATTERNS:
        assert not pat.search(body), f"remote pexels URL leaked on {path}: {pat.pattern}"


# ---------------------------------------------------------------------------
# 3 — decoding="async" present on hero images that were edited in pass2
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/countries/italy/",
        "/fr/countries/france/",
        "/wizard/",
        "/wizard/it/road-accident/",
    ],
)
def test_hero_images_have_decoding_async(path: str):
    body = _body(Client(), path)
    if "/media/pexels/" not in body:
        # Page rendered without a Pexels hero (manifest miss): nothing to assert.
        return
    img_tags = re.findall(r"<img\b[^>]*src=\"[^\"]*?/media/pexels/[^\"]*\"[^>]*>", body)
    assert img_tags, f"{path} references /media/pexels/ but no <img> tag matched"
    for tag in img_tags:
        assert 'decoding="async"' in tag, f'decoding="async" missing on {path}: {tag[:140]}'


# ---------------------------------------------------------------------------
# 4 — canonical + hreflang preserved on country landings
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/countries/italy/",
        "/countries/france/",
        "/countries/belgium/",
        "/countries/morocco/",
        "/countries/tunisia/",
    ],
)
def test_country_landing_has_canonical_and_hreflang(path: str):
    body = _body(Client(), path)
    assert '<link rel="canonical"' in body, f"canonical missing on {path}"
    # Expect at least one hreflang alternate per landing (one per supported lang).
    hreflang_count = len(re.findall(r'<link rel="alternate" hreflang="', body))
    assert hreflang_count >= 2, f"{path} has only {hreflang_count} hreflang alternates"


# ---------------------------------------------------------------------------
# 5 — sitemap.xml 200 + lists 5 country landings
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sitemap_lists_country_landings_pass2():
    body = _body(Client(), "/sitemap.xml")
    for slug in ("italy", "france", "belgium", "morocco", "tunisia"):
        assert f"/countries/{slug}/" in body, f"sitemap missing /countries/{slug}/"


# ---------------------------------------------------------------------------
# 6 — no visible Pexels attribution leaks (re-check, defense in depth)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PAGES)
def test_no_visible_pexels_attribution_pass2(path: str):
    body = _body(Client(), path)
    assert "Photographed by" not in body
    assert "Crédit photo" not in body
    assert "Foto di" not in body
    assert not re.search(r"Photo by [A-Z]", body)
    assert not re.search(r"on Pexels\b", body)


# ---------------------------------------------------------------------------
# 7 — no PEXELS_API_KEY leak in HTML (re-check)
# ---------------------------------------------------------------------------


SENTINEL_API_KEY_PASS2 = "QA-PASS2-SENTINEL-KEY-A1B2C3D4E5"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/fr/", "/ar/", "/countries/", "/contact/", "/wizard/"])
@override_settings(PEXELS_API_KEY=SENTINEL_API_KEY_PASS2)
def test_no_api_key_leak_pass2(path: str):
    body = _body(Client(), path)
    assert SENTINEL_API_KEY_PASS2 not in body, f"API key leaked on {path}"


# ---------------------------------------------------------------------------
# 8 — Italy 35/10/0 contract preserved (engine-level, mirror of pass1)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_qa_pass2(db):
    """Mirror of pass1 fixture (different slug to avoid uniqueness clashes
    when the suite runs both pass1 and pass2 in the same session)."""
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-qa-pass2",
        title="D.P.R. 12/2025",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_qa_pass2",
        name="qa-pass2-smoke",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_engine_preserves_pass2_contract(italy_smoke_qa_pass2):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")


# ---------------------------------------------------------------------------
# 9 — non-default <meta name="description"> on pages overridden by pass2
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,must_contain",
    [
        # Default IT locale now renders the Italian description after
        # F-inheritance-wizard-input-completeness-visual-pass1 cleared
        # stale fuzzy headers; check for a locale-stable token.
        ("/wizard/", "simul"),
        ("/wizard/it/road-accident/", "TUN 2025"),
        ("/wizard/fr/road-accident/", "Loi Badinter"),
        ("/wizard/be/road-accident/", "Tableau Indicatif"),
        ("/wizard/ma/inheritance/", "Moudawana"),
        ("/wizard/tn/inheritance/", "Code du statut personnel"),
        ("/methodology/", "validation lifecycle"),
        # /contact/ meta is now translated in IT; "Studio" is the locale-stable
        # token present in both the EN source and the IT translation.
        ("/contact/", "Studio"),
        # Pass-5 rewrote the meta description; default IT renders the
        # Italian translation. We check for the brand token that anchors
        # the description in any locale.
        ("/countries/", "Badrane"),
    ],
)
def test_meta_description_overridden_pass2(path: str, must_contain: str):
    body = _body(Client(), path)
    match = re.search(
        r'<meta name="description" content="([^"]+)"',
        body,
    )
    assert match, f'no <meta name="description"> on {path}'
    assert must_contain in match.group(
        1
    ), f"{path} description does not contain {must_contain!r}: {match.group(1)[:160]}"


# ---------------------------------------------------------------------------
# 10 — badge contrast micro-fix marker
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_badge_contrast_marker_on_country_landing():
    """Pass2 replaces text-gold-600 with text-gold-700 on the
    'Legal sources under review' chips inside white cards. The token
    must appear on at least one under-review country landing."""
    body = _body(Client(), "/countries/france/")
    assert (
        "text-gold-700" in body
    ), "pass2 badge contrast marker text-gold-700 not present on /countries/france/"


@pytest.mark.django_db
def test_low_contrast_badge_combo_removed_on_countries_index():
    """The old fragile combo `bg-gold-500/10 text-gold-600` must not
    leak into /countries/ — pass2 replaces it with either the high
    contrast variant (`bg-gold-500 text-ink-950` on photo cards) or
    `bg-gold-500/15 text-gold-700` on no-photo cards."""
    body = _body(Client(), "/countries/")
    fragile = re.compile(r"bg-gold-500/10\s+text-gold-600")
    assert not fragile.search(
        body
    ), "fragile bg-gold-500/10 + text-gold-600 combo still rendered on /countries/"
