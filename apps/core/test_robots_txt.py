"""
Tests F-p0-codice-1-robots-txt.

Coprono /robots.txt:
- HTTP 200 + content-type text/plain;
- e' fuori da i18n_patterns (raggiungibile senza prefisso lingua, e
  non duplicato sotto /it/ /fr/ /en/ /ar/);
- contiene Disallow per back-office e pagine post-submit con dati
  utente (admin, staff, reports, wizard/result, contact/thank-you);
- NON disallowa /contact/ (pagina pubblica utile a SEO/lead);
- punta a /sitemap.xml come Sitemap directive.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.utils import translation


@pytest.fixture(autouse=True)
def _reset_active_language():
    """
    Reset il `LANGUAGE_CODE` attivo al default tra un test e l'altro.

    I test che fanno GET su `/it/...`, `/fr/...`, `/ar/robots.txt`
    (anche per ottenere 404) attivano LocaleMiddleware sul thread
    di test, lasciando lo state per i test successivi e creando
    failure intermittenti su test sensibili alla lingua attiva
    (es. `apps/core/test_status_banner_partial_pass7.py`).
    """
    yield
    translation.deactivate_all()


# ---------------------------------------------------------------------------
# Basic shape
# ---------------------------------------------------------------------------


def test_robots_txt_returns_200():
    resp = Client().get("/robots.txt")
    assert resp.status_code == 200


def test_robots_txt_content_type_is_text_plain():
    resp = Client().get("/robots.txt")
    ct = resp["Content-Type"]
    assert ct.startswith("text/plain"), f"unexpected content-type: {ct!r}"


def test_robots_txt_has_user_agent_universal():
    resp = Client().get("/robots.txt")
    body = resp.content.decode("utf-8")
    assert "User-agent: *" in body


# ---------------------------------------------------------------------------
# Disallow critici
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/admin/",
        "/staff/",
        "/reports/",
        "/wizard/result/",
        "/contact/thank-you/",
    ],
)
def test_robots_txt_disallows_back_office_and_post_submit_paths(path):
    resp = Client().get("/robots.txt")
    body = resp.content.decode("utf-8")
    assert f"Disallow: {path}" in body, (
        f"robots.txt non blocca {path}\n--- body ---\n{body}"
    )


# ---------------------------------------------------------------------------
# /contact/ resta pubblica e indicizzabile
# ---------------------------------------------------------------------------


def test_robots_txt_does_not_disallow_contact_page():
    """`/contact/` e' utile per SEO e lead capture: NON deve essere bloccata."""
    resp = Client().get("/robots.txt")
    body = resp.content.decode("utf-8")
    # Cerchiamo specificamente la regola "Disallow: /contact/" (con
    # eventuale newline subito dopo): NON deve esistere. La regola
    # "Disallow: /contact/thank-you/" e' invece valida.
    for line in body.splitlines():
        stripped = line.strip()
        if stripped == "Disallow: /contact/":
            pytest.fail("robots.txt blocca /contact/ — regressione SEO/lead.")


def test_robots_txt_explicit_allow_contact():
    """Allow esplicito di /contact/ per chiarezza."""
    resp = Client().get("/robots.txt")
    body = resp.content.decode("utf-8")
    assert "Allow: /contact/" in body


# ---------------------------------------------------------------------------
# Sitemap directive
# ---------------------------------------------------------------------------


def test_robots_txt_points_to_sitemap():
    resp = Client().get("/robots.txt")
    body = resp.content.decode("utf-8")
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body


# ---------------------------------------------------------------------------
# Out of i18n_patterns: nessun prefisso /it/, /fr/, /en/, /ar/.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prefix", ["/it", "/fr", "/en", "/ar"])
def test_robots_txt_not_under_i18n_prefix(prefix):
    """`/<lang>/robots.txt` deve essere 404, non un duplicato."""
    resp = Client().get(f"{prefix}/robots.txt")
    assert resp.status_code == 404, (
        f"{prefix}/robots.txt e' raggiungibile (status={resp.status_code}); "
        "il file deve esistere SOLO su /robots.txt."
    )
