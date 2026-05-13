"""
Tests F-p0-codice-2-hreflang-globale.

Coprono il context processor `apps.core.context_processors.seo_global_hreflang`
+ il `{% block hreflang %}` di `templates/base.html`:

- ogni pagina pubblica indicizzabile multilingua emette
  `<link rel="alternate" hreflang="it/fr/en/ar/x-default">`;
- canonical (quando presente) e meta robots non sono in conflitto;
- pagine noindex / parametriche (UUID) NON ricevono hreflang;
- nessun duplicato per la stessa lingua;
- la lingua corrente non manca dal set;
- /contact/ (post-pre-check-2) e' indicizzabile e ha hreflang.

Vincoli SEO Google (referenza pubblica:
https://developers.google.com/search/docs/specialty/international/localized-versions):
- ogni alternate punta a un URL assoluto;
- una sola entry per lingua;
- x-default opzionale ma raccomandato; qui obbligatorio per
  homogeneity con `apps.core.seo.build_hreflang_alternates`.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import translation

# ---------------------------------------------------------------------------
# Test isolation: reset i18n active language tra test.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    translation.deactivate_all()


# ---------------------------------------------------------------------------
# Helpers — parse hreflang dal HTML
# ---------------------------------------------------------------------------


_HREFLANG_RE = re.compile(
    r'<link\s+[^>]*rel=["\']alternate["\'][^>]*hreflang=["\']([^"\']+)["\']'
    r'[^>]*href=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)
_HREFLANG_RE_REVERSE = re.compile(
    r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*hreflang=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)
_META_ROBOTS_RE = re.compile(
    r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)


def _hreflang_pairs(html: str) -> list[tuple[str, str]]:
    """Tutte le coppie (lang, href) emesse dalla pagina."""
    pairs = []
    for lang, href in _HREFLANG_RE.findall(html):
        pairs.append((lang.lower(), href))
    for href, lang in _HREFLANG_RE_REVERSE.findall(html):
        pairs.append((lang.lower(), href))
    # de-dupe stable
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for pair in pairs:
        if pair in seen:
            continue
        seen.add(pair)
        deduped.append(pair)
    return deduped


def _meta_robots(html: str) -> str | None:
    m = _META_ROBOTS_RE.search(html)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Fixtures riusabili (calculator IT canarino)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_country(db):
    from apps.jurisdictions.models import Country

    return Country.objects.get_or_create(
        code="IT",
        defaults={"code_alpha3": "ITA", "name": "Italia"},
    )[0]


@pytest.fixture
def calculated_simulation(db, italy_country):
    from apps.cases.models import Simulation

    return Simulation.objects.create(
        country=italy_country,
        case_type="road_accident_bodily_injury",
        input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
        output_data={"sources": [], "warnings": []},
        sources_snapshot=[],
        status="calculated",
        currency="EUR",
        estimated_min=Decimal("26268.00"),
        estimated_mid=Decimal("27353.00"),
        estimated_max=Decimal("28439.00"),
    )


# ---------------------------------------------------------------------------
# Allowlist: pagine pubbliche indicizzabili — DEVONO avere hreflang
# ---------------------------------------------------------------------------

INDEXABLE_PUBLIC_PATHS = [
    # core/static
    "/",
    "/methodology/",
    "/disclaimer/",
    "/privacy/",
    "/countries/",
    "/case-types/",
    # country landings
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    # wizard hub (i 5 wizard pubblici sono noindex per scelta — vedi
    # `_GLOBAL_HREFLANG_VIEW_NAMES` in context_processors.py)
    "/wizard/",
    # contact (post-pre-check-2 P0-CODICE-2: indexable)
    "/contact/",
]


# Pagine pubbliche che restano `noindex` per scelta (non in allowlist
# hreflang, non SEO-utili). Verifichiamo che NON ricevano hreflang.
NOINDEX_PUBLIC_PATHS = [
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/thank-you/",
]


@pytest.mark.parametrize("path", INDEXABLE_PUBLIC_PATHS)
def test_indexable_public_page_has_hreflang_alternates(path, db):
    """Ogni pagina indicizzabile emette hreflang per tutte e 4 le lingue + x-default."""
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"
    html = resp.content.decode("utf-8")

    pairs = _hreflang_pairs(html)
    langs = [lang for lang, _ in pairs]

    expected_langs = {"it", "fr", "en", "ar", "x-default"}
    assert expected_langs.issubset(set(langs)), (
        f"{path}: hreflang manca lingue. atteso superset di {expected_langs}, "
        f"ottenuto {set(langs)}"
    )


@pytest.mark.parametrize("path", INDEXABLE_PUBLIC_PATHS)
def test_indexable_public_page_hreflang_has_no_duplicates(path, db):
    """Nessuna lingua duplicata negli alternates di una pagina."""
    resp = Client().get(path)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    pairs = _hreflang_pairs(html)
    langs = [lang for lang, _ in pairs]
    duplicates = [lang for lang in langs if langs.count(lang) > 1]
    assert not duplicates, (
        f"{path}: hreflang duplicati per {set(duplicates)} → pairs={pairs}"
    )


@pytest.mark.parametrize("path", INDEXABLE_PUBLIC_PATHS)
def test_indexable_public_page_hreflang_urls_are_absolute(path, db):
    """Tutti gli href negli alternates sono URL assoluti (http(s)://...)."""
    resp = Client().get(path)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    pairs = _hreflang_pairs(html)
    for lang, href in pairs:
        assert href.startswith(("http://", "https://")), (
            f"{path}: hreflang `{lang}` non assoluto: {href!r}"
        )


@pytest.mark.parametrize("path", INDEXABLE_PUBLIC_PATHS)
def test_indexable_public_page_has_x_default(path, db):
    """`x-default` obbligatorio per homogeneity con `build_hreflang_alternates`."""
    resp = Client().get(path)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    pairs = _hreflang_pairs(html)
    langs = {lang for lang, _ in pairs}
    assert "x-default" in langs, f"{path}: manca hreflang x-default"


@pytest.mark.parametrize("path", INDEXABLE_PUBLIC_PATHS)
def test_indexable_public_page_meta_robots_index_follow(path, db):
    """Pagine indicizzabili hanno `index, follow` (default base.html)."""
    resp = Client().get(path)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    value = _meta_robots(html)
    assert value is not None
    normalized = value.lower().replace(" ", "")
    assert "noindex" not in normalized, (
        f"{path}: e' nella allowlist ma ha noindex (incoerenza): got={value!r}"
    )


# ---------------------------------------------------------------------------
# I18n: pagine prefissate /fr/, /en/, /ar/ — stesso comportamento
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prefix", ["/fr", "/en", "/ar"])
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/methodology/",
        "/countries/italy/",
        "/wizard/",
        "/contact/",
    ],
)
def test_indexable_page_has_hreflang_under_lang_prefix(prefix, path, db):  # noqa: PT003 — parametrize stack
    """Anche sotto prefisso lingua, hreflang resta completo (5 voci)."""
    full_path = f"{prefix}{path}" if path != "/" else f"{prefix}/"
    resp = Client().get(full_path)
    assert resp.status_code == 200, f"GET {full_path} → {resp.status_code}"
    html = resp.content.decode("utf-8")

    pairs = _hreflang_pairs(html)
    langs = {lang for lang, _ in pairs}
    assert {"it", "fr", "en", "ar", "x-default"}.issubset(langs), (
        f"{full_path}: hreflang incompleto, ottenuto {langs}"
    )


# ---------------------------------------------------------------------------
# Pagine NOINDEX / parametriche — NON devono avere hreflang
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", NOINDEX_PUBLIC_PATHS)
def test_noindex_pages_have_no_hreflang(path, db):
    """
    Pagine pubbliche noindex (5 wizard + thank-you) NON devono
    emettere hreflang: l'allowlist le esclude esplicitamente.
    """
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"
    html = resp.content.decode("utf-8")
    pairs = _hreflang_pairs(html)
    assert pairs == [], (
        f"{path} e' noindex ma emette hreflang ({pairs}); "
        "rimuovere dalla allowlist o cambiare meta robots."
    )


def test_wizard_result_has_no_hreflang(calculated_simulation):
    """`/wizard/result/<uuid>/` e' parametrico+noindex: niente hreflang."""
    url = f"/wizard/result/{calculated_simulation.public_id}/"
    resp = Client().get(url)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    pairs = _hreflang_pairs(html)
    assert pairs == [], f"{url} non dovrebbe emettere hreflang: {pairs}"


# ---------------------------------------------------------------------------
# Coerenza con canonical (country landings)
# ---------------------------------------------------------------------------


def test_country_landing_canonical_and_hreflang_coexist(db):
    """
    Country landing aveva gia' canonical + hreflang via view; dopo
    P0-CODICE-2 lo hreflang viene emesso da base.html ma il
    canonical resta in head_extra. Verifichiamo coesistenza.
    """
    resp = Client().get("/countries/italy/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    # canonical presente (head_extra)
    assert '<link rel="canonical"' in html.lower() or "<link rel='canonical'" in html

    # hreflang presente (block hreflang in base.html, alimentato dalla view)
    pairs = _hreflang_pairs(html)
    langs = {lang for lang, _ in pairs}
    assert {"it", "fr", "en", "ar", "x-default"}.issubset(langs)


def test_country_landing_no_duplicate_hreflang_link_tags(db):
    """
    Regressione: prima di P0-CODICE-2 il country_landing.html
    aveva hreflang sia in head_extra che (ora) in block hreflang.
    Dopo la rimozione di head_extra, il numero di tag deve essere
    == numero di lingue + x-default.
    """
    resp = Client().get("/countries/italy/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    # Conta tutte le occorrenze del literal `hreflang=`. Deve essere
    # esattamente 5 (it, fr, en, ar, x-default), non 10 (doppione).
    hreflang_attr_count = len(re.findall(r'hreflang=["\']', html))
    assert hreflang_attr_count == 5, (
        f"Country landing IT: atteso 5 tag hreflang, ottenuto {hreflang_attr_count}"
    )


# ---------------------------------------------------------------------------
# Allowlist enforcement: una pagina non in allowlist non deve avere hreflang
# ---------------------------------------------------------------------------


def test_admin_login_has_no_hreflang(db):
    """`/admin/login/` non e' nella allowlist: nessun hreflang."""
    resp = Client().get("/admin/login/")
    # Accettiamo 200 (pagina di login Django) o 302/404 in alcuni
    # setup. Se 200, il body non deve avere hreflang.
    if resp.status_code == 200:
        html = resp.content.decode("utf-8")
        pairs = _hreflang_pairs(html)
        assert pairs == [], (
            f"/admin/login/ non dovrebbe avere hreflang: {pairs}"
        )


# ---------------------------------------------------------------------------
# Italia smoke 35/10/0 — il canarino calcolatore e' coperto dai test
# esistenti che caricano fixture TUN (es.
# `apps/core/test_country_landings.py::test_italy_smoke_run_simulation_35_10_0`).
# Qui duplicarlo richiederebbe popolare il test DB con CompensationDataset
# approved + CalculationFormula approved, fuori scope di un test SEO.
# ---------------------------------------------------------------------------
