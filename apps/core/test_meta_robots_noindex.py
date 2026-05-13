"""
Tests F-p0-codice-1-meta-robots.

Coprono che le pagine pubbliche con dati utente (`/wizard/result/`,
`/contact/thank-you/`) emettano `<meta name="robots" content="noindex,
nofollow">` nel `<head>`.

robots.txt da solo non basta a evitare l'indicizzazione di URL gia'
scoperti: il meta tag e' la difesa autorevole. Questo test e' un
canarino per evitare regressioni nei template (qualcuno potrebbe
involontariamente rimuovere il `{% block meta_robots %}` override).

Le pagine indicizzabili (es. /contact/, /, /methodology/) NON
devono avere noindex: aggiungiamo un canarino su /contact/ per
prevenire regressioni inverse.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import translation


@pytest.fixture(autouse=True)
def _reset_active_language():
    """
    Reset il `LANGUAGE_CODE` attivo tra un test e l'altro per evitare
    contagio di state i18n verso test sensibili alla lingua attiva.
    """
    yield
    translation.deactivate_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_META_ROBOTS_RE = re.compile(
    r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)


def _meta_robots_value(html: str) -> str | None:
    match = _META_ROBOTS_RE.search(html)
    if match is None:
        return None
    return match.group(1).strip()


# ---------------------------------------------------------------------------
# Fixtures (riusiamo lo stesso pattern di test_email_notifications.py)
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
    """Crea una Simulation calcolata per testare il rendering result page."""
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
# /wizard/result/<uuid>/ — must noindex
# ---------------------------------------------------------------------------


def test_wizard_result_emits_noindex_meta_robots(calculated_simulation):
    """`/wizard/result/<uuid>/` deve emettere `noindex, nofollow`."""
    client = Client()
    url = f"/wizard/result/{calculated_simulation.public_id}/"
    resp = client.get(url)
    assert resp.status_code == 200, f"GET {url} → {resp.status_code}"
    html = resp.content.decode("utf-8")
    value = _meta_robots_value(html)
    assert value is not None, "<meta name='robots'> mancante nel result page"
    normalized = value.lower().replace(" ", "")
    assert "noindex" in normalized, (
        f"meta robots non contiene noindex: got={value!r}"
    )
    assert "nofollow" in normalized, (
        f"meta robots non contiene nofollow: got={value!r}"
    )


# ---------------------------------------------------------------------------
# /contact/thank-you/ — must noindex
# ---------------------------------------------------------------------------


def test_contact_thank_you_emits_noindex_meta_robots(db):
    client = Client()
    resp = client.get("/contact/thank-you/")
    assert resp.status_code == 200, (
        f"GET /contact/thank-you/ → {resp.status_code}"
    )
    html = resp.content.decode("utf-8")
    value = _meta_robots_value(html)
    assert value is not None, "<meta name='robots'> mancante nel thank-you"
    normalized = value.lower().replace(" ", "")
    assert "noindex" in normalized, (
        f"meta robots non contiene noindex: got={value!r}"
    )
    assert "nofollow" in normalized, (
        f"meta robots non contiene nofollow: got={value!r}"
    )


# ---------------------------------------------------------------------------
# Canarino inverso: /contact/ deve restare INDICIZZABILE
# ---------------------------------------------------------------------------


def test_contact_form_is_indexable(db):
    """
    `/contact/` deve essere indicizzabile (index, follow).

    Coerenza con la decisione SEO documentata in robots.txt
    (Allow: /contact/). Il template eredita il default
    `index, follow` da base.html. Canarino contro regressioni
    che reintroducano `noindex` accidentalmente.
    """
    client = Client()
    resp = client.get("/contact/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    value = _meta_robots_value(html)
    assert value is not None, "<meta name='robots'> mancante nel contact form"
    normalized = value.lower().replace(" ", "")
    assert "noindex" not in normalized, (
        f"/contact/ ha `noindex` (regressione SEO/lead): got={value!r}"
    )
    assert "nofollow" not in normalized, (
        f"/contact/ ha `nofollow` (regressione SEO/lead): got={value!r}"
    )


# ---------------------------------------------------------------------------
# Home/methodology resta indicizzabile (default base.html: index, follow)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/methodology/", "/countries/"])
def test_public_pages_default_to_index_follow(path, db):
    """Pagine pubbliche standard ereditano `index, follow` dal base."""
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"
    html = resp.content.decode("utf-8")
    value = _meta_robots_value(html)
    assert value is not None, f"<meta name='robots'> mancante su {path}"
    normalized = value.lower().replace(" ", "")
    assert "noindex" not in normalized, (
        f"{path} non dovrebbe avere noindex (e' una pagina pubblica): got={value!r}"
    )
